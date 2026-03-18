from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .budget import BudgetEstimate, estimate_budget, heuristic_token_count
from .config import DEFAULT_MLX_MODEL_DIR, EXPORT_DIR, LOG_DIR, RUNTIME_LOG_PATH, RuntimeSettings, TANAKH_CACHE_DIR
from .hum import HumService
from .inference import (
    InferenceProfileRequest,
    MAX_RESPONSE_CHAR_CAP,
    default_profile_request,
    request_from_dict,
    resolve_profile,
    runtime_settings_for_profile,
)
from .ingest.pipeline import IngestService
from .logging import RuntimeLog
from .models.base import BaseModelAdapter
from .models.base import split_model_output
from .models.mlx_backend import MLXModelAdapter
from .models.catalog import DEFAULT_LOCAL_MLX_MODEL, local_mlx_model_status, prepare_local_mlx_model
from .models.mock import MockModelAdapter
from .ontology_projection import memode_materialization_allowed
from .observatory.exporters import ObservatoryExporter
from .observatory.server import ObservatoryServer
from .observatory.service import ObservatoryService
from .regard import ema, feedback_signal
from .retrieval import RetrievalService
from .semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE, extract_semantic_candidates
from .storage.graph_store import GraphStore
from .tanakh import DEFAULT_TANAKH_REF, TanakhService
from .utils import now_utc, safe_excerpt, slugify


CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
ANSWER_LABEL_RE = re.compile(r"(?im)^\s*(final answer|answer|adam)\s*:\s*")
SUPPORT_SECTION_RE = re.compile(r"(?im)^\s*(basis|next step)\s*:\s*")
RUNTIME_LAUNCH_PROFILE_KEY = "runtime_launch_profile"
DISPLAY_RESPONSE_CHAR_CAP = 24_000
TUI_APPEARANCE_KEY = "tui_appearance"
PRIMARY_EXPERIMENT_KEY = "primary_experiment"
PRIMARY_EXPERIMENT_NAME = "Adam Graph"
PRIMARY_EXPERIMENT_MODE = "persistent"
OPERATOR_LABEL = "Brian the operator"
GRAPH_NORMALIZATION_MLX_REVIEW_LIMIT = 8
GRAPH_NORMALIZATION_ENTITY_TYPES = {"author", "work", "information"}
GRAPH_NORMALIZATION_EDGE_TYPES = {"AUTHOR_OF", "INFLUENCES", "REFERENCES"}


def _normalize_archive_folder(folder: Any) -> str:
    value = str(folder or "").strip().replace("\\", "/")
    value = re.sub(r"/{2,}", "/", value).strip("/")
    return value or "inbox"


def _normalize_archive_tags(tags: Any) -> list[str]:
    if isinstance(tags, list):
        raw_values = tags
    else:
        raw_values = re.split(r"[,;\n]", str(tags or ""))
    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        tag = re.sub(r"\s+", " ", str(value or "").strip().lstrip("#"))
        if not tag:
            continue
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(tag)
    return normalized


def _normalize_archive_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    archive = metadata.get("archive") if isinstance(metadata, dict) and isinstance(metadata.get("archive"), dict) else {}
    return {
        "folder": _normalize_archive_folder(archive.get("folder")),
        "tags": _normalize_archive_tags(archive.get("tags")),
    }


def _normalize_ui_look(value: Any) -> str:
    normalized = str(value or "amber_dark").strip().lower()
    return normalized if normalized in {"amber_dark", "typewriter_light"} else "amber_dark"


@dataclass(slots=True)
class ChatOutcome:
    turn: dict[str, Any]
    active_set: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    membrane_events: list[dict[str, Any]]
    graph_counts: dict[str, int]
    budget: dict[str, Any]
    profile: dict[str, Any]
    reasoning_text: str


@dataclass(slots=True)
class PreviewOutcome:
    profile: dict[str, Any]
    budget: dict[str, Any]
    active_set: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    system_prompt: str
    conversation_prompt: str
    history_context: str
    feedback_context: str


class EdenRuntime:
    def __init__(
        self,
        *,
        store: GraphStore,
        settings: RuntimeSettings | None = None,
        runtime_log: RuntimeLog | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or RuntimeSettings()
        self.runtime_log = runtime_log or RuntimeLog(RUNTIME_LOG_PATH)
        self.conversation_export_root = EXPORT_DIR / "conversations"
        self.ingest_service = IngestService(self.store, self.runtime_log)
        self.retrieval_service = RetrievalService(self.store)
        self.tanakh_service = TanakhService(cache_root=TANAKH_CACHE_DIR)
        self.hum_service = HumService(store=self.store, runtime_log=self.runtime_log, root=LOG_DIR / "hum_state")
        self.exporter = ObservatoryExporter(
            self.store,
            self.retrieval_service,
            self.runtime_log,
            tanakh_service=self.tanakh_service,
            hum_provider=self.hum_snapshot,
        )
        self.observatory_service = ObservatoryService(
            store=self.store,
            exporter=self.exporter,
            runtime_log=self.runtime_log,
            export_root=EXPORT_DIR,
            runtime_status_provider=self.observatory_runtime_status,
            runtime_model_provider=self.observatory_model_status,
            tanakh_service=self.tanakh_service,
            hum_provider=self.hum_snapshot,
        )
        self.observatory_server = ObservatoryServer(
            EXPORT_DIR,
            self.settings.observatory_port,
            host=self.settings.observatory_host,
            port_span=self.settings.observatory_port_span,
            service=self.observatory_service,
        )
        self.agent_profile = json.loads((Path(__file__).resolve().parent / "agents" / "adam" / "profile.json").read_text())
        self.agent_id = self.store.upsert_agent(
            slug=self.agent_profile["slug"],
            name=self.agent_profile["name"],
            profile=self.agent_profile,
        )
        self._model_adapter: BaseModelAdapter | None = None
        self._primary_experiment_cache: dict[str, Any] | None = None
        self.primary_experiment()

    def _get_model_adapter(self) -> BaseModelAdapter:
        backend = self.settings.model_backend.lower()
        if self._model_adapter and self._model_adapter.backend_name == backend:
            if backend != "mlx" or getattr(self._model_adapter, "model_path", None) == self.settings.model_path:
                return self._model_adapter
        if backend == "mlx":
            requested_model_path = self.settings.model_path or str(DEFAULT_MLX_MODEL_DIR)
            if Path(requested_model_path) == DEFAULT_LOCAL_MLX_MODEL.local_dir:
                status = self.mlx_model_status()
                if not status["ready"]:
                    status = self.prepare_default_mlx_model()
                requested_model_path = status["local_dir"]
            self._model_adapter = MLXModelAdapter(requested_model_path)
        else:
            self._model_adapter = MockModelAdapter()
        return self._model_adapter

    def default_session_profile_request(self) -> InferenceProfileRequest:
        return default_profile_request(self.settings)

    def primary_experiment(self) -> dict[str, Any]:
        cached = self._primary_experiment_cache
        if cached is not None:
            return cached
        stored = self.store.read_config(PRIMARY_EXPERIMENT_KEY) or {}
        experiment_id = str(stored.get("experiment_id") or "").strip()
        experiment: dict[str, Any] | None = None
        if experiment_id:
            try:
                experiment = self.store.get_experiment(experiment_id)
            except KeyError:
                experiment = None
        if experiment is None:
            latest = self.store.get_latest_experiment()
            if latest is None:
                experiment = self.store.create_experiment(
                    name=PRIMARY_EXPERIMENT_NAME,
                    mode=PRIMARY_EXPERIMENT_MODE,
                    metadata={
                        "initialized_at": now_utc(),
                        "mode": PRIMARY_EXPERIMENT_MODE,
                        "graph_role": "primary",
                        "single_graph": True,
                    },
                )
                self.runtime_log.emit(
                    "INFO",
                    "experiment_create",
                    "Created primary graph.",
                    experiment_id=experiment["id"],
                    mode=PRIMARY_EXPERIMENT_MODE,
                )
                self.store.record_trace_event(
                    experiment_id=experiment["id"],
                    session_id=None,
                    turn_id=None,
                    event_type="BOOTSTRAP",
                    level="INFO",
                    message="Created primary graph",
                    payload={"mode": PRIMARY_EXPERIMENT_MODE},
                )
                self._seed_constitution(experiment["id"])
            else:
                experiment = latest
                self.runtime_log.emit(
                    "INFO",
                    "primary_graph_adopted",
                    "Adopted existing experiment as the single primary graph.",
                    experiment_id=experiment["id"],
                    prior_name=experiment.get("name"),
                    prior_mode=experiment.get("mode"),
                )
        experiment = self.store.update_experiment_identity(
            experiment["id"],
            name=PRIMARY_EXPERIMENT_NAME,
            mode=PRIMARY_EXPERIMENT_MODE,
            metadata={
                "graph_role": "primary",
                "single_graph": True,
            },
        )
        self.store.upsert_config(
            PRIMARY_EXPERIMENT_KEY,
            {"experiment_id": experiment["id"], "name": PRIMARY_EXPERIMENT_NAME, "mode": PRIMARY_EXPERIMENT_MODE},
        )
        for candidate in self.store.list_experiments():
            candidate_id = str(candidate["id"])
            if candidate_id == experiment["id"]:
                continue
            self.store.reassign_runtime_records_to_experiment(candidate_id, experiment["id"])
        self._primary_experiment_cache = self.store.get_experiment(experiment["id"])
        return self._primary_experiment_cache

    def runtime_launch_profile(self) -> dict[str, Any]:
        stored = self.store.read_config(RUNTIME_LAUNCH_PROFILE_KEY) or {}
        backend = str(stored.get("backend") or self.settings.model_backend or "mlx").lower()
        default_model_path = self.settings.model_path or str(DEFAULT_MLX_MODEL_DIR)
        model_path = str(stored.get("model_path") or default_model_path or "").strip()
        return {"backend": backend, "model_path": model_path}

    def update_runtime_launch_profile(self, *, backend: str, model_path: str | None) -> dict[str, Any]:
        normalized_backend = (backend or "mlx").strip().lower() or "mlx"
        normalized_model_path = (model_path or "").strip()
        if normalized_backend == "mlx" and not normalized_model_path:
            normalized_model_path = str(DEFAULT_MLX_MODEL_DIR)
        self.settings.model_backend = normalized_backend
        self.settings.model_path = normalized_model_path or None
        payload = {
            "backend": normalized_backend,
            "model_path": normalized_model_path or None,
        }
        self.store.upsert_config(RUNTIME_LAUNCH_PROFILE_KEY, payload)
        return {"backend": normalized_backend, "model_path": normalized_model_path}

    def ui_appearance(self) -> dict[str, Any]:
        stored = self.store.read_config(TUI_APPEARANCE_KEY) or {}
        look = _normalize_ui_look(stored.get("look") or self.settings.ui_look)
        self.settings.ui_look = look
        return {"look": look}

    def update_ui_appearance(self, *, look: str) -> dict[str, Any]:
        normalized = _normalize_ui_look(look)
        self.settings.ui_look = normalized
        payload = {"look": normalized}
        self.store.upsert_config(TUI_APPEARANCE_KEY, payload)
        return payload

    def recent_session_titles(self, *, limit: int = 20) -> list[str]:
        if limit <= 0:
            return []
        titles: list[str] = []
        seen: set[str] = set()
        ranked_rows = sorted(
            enumerate(self.store.list_session_catalog()),
            key=lambda item: (
                str(item[1].get("updated_at") or ""),
                str(item[1].get("last_turn_at") or ""),
                str(item[1].get("created_at") or ""),
                item[0],
            ),
            reverse=True,
        )
        for _, row in ranked_rows:
            title = str(row.get("title") or "").strip()
            if not title:
                continue
            lowered = title.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            titles.append(title)
            if len(titles) >= limit:
                break
        return titles

    def mlx_model_status(self) -> dict[str, Any]:
        status = local_mlx_model_status(DEFAULT_LOCAL_MLX_MODEL)
        status["active_backend"] = self.settings.model_backend.lower()
        status["active_model_path"] = self.settings.model_path or str(DEFAULT_MLX_MODEL_DIR)
        return status

    def observatory_runtime_status(self) -> dict[str, Any]:
        launch = self.runtime_launch_profile()
        return {
            "available": True,
            "backend": self.settings.model_backend.lower(),
            "host": self.settings.observatory_host,
            "port": self.settings.observatory_port,
            "launch_profile": launch,
            "observatory_running": bool(self.observatory_server.running),
        }

    def observatory_model_status(self) -> dict[str, Any]:
        backend = self.settings.model_backend.lower()
        if backend == "mlx":
            status = self.mlx_model_status()
            status["available"] = True
            return status
        return {
            "available": True,
            "backend": backend,
            "model_path": self.settings.model_path or "",
        }

    def prepare_default_mlx_model(self) -> dict[str, Any]:
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        self.runtime_log.emit(
            "INFO",
            "mlx_prepare_start",
            "Preparing default local MLX model.",
            model_label=DEFAULT_LOCAL_MLX_MODEL.label,
            repo_id=DEFAULT_LOCAL_MLX_MODEL.repo_id,
            local_dir=str(DEFAULT_LOCAL_MLX_MODEL.local_dir),
            auth="token" if token else "anonymous",
        )
        status = prepare_local_mlx_model(DEFAULT_LOCAL_MLX_MODEL, token=token)
        self.runtime_log.emit(
            "INFO",
            "mlx_prepare_complete",
            "Prepared default local MLX model.",
            model_label=status["label"],
            repo_id=status["repo_id"],
            local_dir=status["local_dir"],
            ready=status["ready"],
            stage=status["stage"],
            gib_on_disk=status["gib_on_disk"],
        )
        self.settings.model_path = status["local_dir"]
        self.store.upsert_config(
            RUNTIME_LAUNCH_PROFILE_KEY,
            {
                "backend": "mlx",
                "model_path": status["local_dir"],
            },
        )
        return status

    def _session_profile_request(self, session_id: str) -> InferenceProfileRequest:
        session = self.store.get_session(session_id)
        metadata = json.loads(session["metadata_json"] or "{}")
        return request_from_dict(metadata.get("requested_inference_profile"), self.settings)

    def _recent_feedback_balance(self, session_id: str, *, limit: int = 6) -> float:
        entries = self.store.recent_feedback(session_id, limit=limit)
        if not entries:
            return 0.0
        score_map = {"accept": 1.0, "edit": 0.35, "reject": -1.0, "skip": 0.0}
        return sum(score_map.get(str(item["verdict"]).lower(), 0.0) for item in entries) / len(entries)

    def _recent_membrane_event_count(self, experiment_id: str, session_id: str, *, limit: int = 6) -> int:
        return len(self.store.list_membrane_events(experiment_id, limit=limit, session_id=session_id))

    def _budget_token_counter(self):
        if self.settings.model_backend.lower() == "mock":
            return self._get_model_adapter().count_tokens
        if self._model_adapter is not None:
            return self._model_adapter.count_tokens
        return None

    def _resolved_profile(self, *, session_id: str, query: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        experiment_id = session["experiment_id"]
        request = self._session_profile_request(session_id)
        graph_health = self.graph_health(experiment_id)
        profile = resolve_profile(
            request,
            query=query,
            graph_health=graph_health,
            feedback_balance=self._recent_feedback_balance(session_id),
            recent_membrane_events=self._recent_membrane_event_count(experiment_id, session_id),
            backend=self.settings.model_backend.lower(),
        )
        return {"request": request, "profile": profile}

    def preview_turn(self, *, session_id: str, user_text: str, previous_budget: dict[str, Any] | None = None) -> PreviewOutcome:
        session = self.store.get_session(session_id)
        experiment_id = session["experiment_id"]
        resolved = self._resolved_profile(session_id=session_id, query=user_text)
        request: InferenceProfileRequest = resolved["request"]
        profile = resolved["profile"]
        feedback_context = self._recent_feedback_context(session_id)
        retrieval_settings = runtime_settings_for_profile(self.settings, profile)
        active_set = self.retrieval_service.retrieve(
            experiment_id=experiment_id,
            session_id=session_id,
            query=user_text,
            settings=retrieval_settings,
        )
        token_counter = self._budget_token_counter()
        system_prompt = self._system_prompt(profile=profile)
        history_context, injected_history_turns = self._recent_history_context(
            session_id,
            limit=profile.history_turns,
            prompt_budget_tokens=profile.prompt_budget_tokens,
            system_prompt=system_prompt,
            active_set_context=active_set["prompt_context"],
            feedback_context=feedback_context,
            user_text=user_text,
            token_counter=token_counter,
        )
        conversation_prompt = self._conversation_prompt(
            active_set_context=active_set["prompt_context"],
            feedback_context=feedback_context,
            history_context=history_context,
            user_text=user_text,
        )
        previous = BudgetEstimate(**previous_budget) if previous_budget else None
        budget = estimate_budget(
            prompt_budget_tokens=profile.prompt_budget_tokens,
            reserved_output_tokens=profile.max_output_tokens,
            system_prompt=system_prompt,
            active_set_context=active_set["prompt_context"],
            history_context=history_context,
            feedback_context=feedback_context,
            user_text=user_text,
            response_char_cap=profile.response_char_cap,
            active_set_items=len(active_set["items"]),
            history_turns=injected_history_turns,
            token_counter=token_counter,
            previous=previous,
        )
        profile_dict = profile.to_dict()
        profile_dict["request"] = request.to_dict()
        return PreviewOutcome(
            profile=profile_dict,
            budget=budget.to_dict(),
            active_set=active_set["items"],
            trace=active_set["trace"],
            system_prompt=system_prompt,
            conversation_prompt=conversation_prompt,
            history_context=history_context,
            feedback_context=feedback_context,
        )

    def _constitution_statements(self) -> list[str]:
        seed_path = Path(__file__).resolve().parent / "agents" / "adam" / "seed_constitution.md"
        lines = []
        for line in seed_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("- "):
                lines.append(line[2:].strip())
        return lines

    def initialize_experiment(self, mode: str, *, name: str | None = None) -> dict[str, Any]:
        experiment = self.primary_experiment()
        requested_mode = (mode or PRIMARY_EXPERIMENT_MODE).strip().lower()
        if requested_mode != PRIMARY_EXPERIMENT_MODE or name:
            self.runtime_log.emit(
                "INFO",
                "primary_graph_reused",
                "Ignored legacy experiment bootstrap request and reused the single primary graph.",
                experiment_id=experiment["id"],
                requested_mode=requested_mode,
                requested_name=name or "",
            )
        return experiment

    def _seed_constitution(self, experiment_id: str) -> None:
        member_ids: list[str] = []
        for statement in self._constitution_statements():
            meme = self.store.upsert_meme(
                experiment_id=experiment_id,
                label=statement[:80],
                text=statement,
                domain="behavior",
                source_kind="constitution",
                scope="global",
                evidence_inc=1.0,
                metadata={"title": "ADAM constitutional seed", "origin": "seed_constitution"},
            )
            member_ids.append(meme["id"])
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="agent",
                src_id=self.agent_id,
                dst_kind="meme",
                dst_id=meme["id"],
                edge_type="BELONGS_TO_AGENT",
                provenance={"kind": "constitution"},
            )
        memode = self.store.upsert_memode(
            experiment_id=experiment_id,
            label="ADAM constitutional stack",
            member_ids=member_ids,
            summary="The constitutional scaffold that defines EDEN v1, ADAM, membrane visibility, and regard.",
            domain="behavior",
            metadata={"origin": "seed_constitution"},
        )
        for member_id in member_ids:
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="memode",
                src_id=memode["id"],
                dst_kind="meme",
                dst_id=member_id,
                edge_type="MATERIALIZES_AS_MEMODE",
                provenance={"kind": "constitution"},
            )
        self.runtime_log.emit("INFO", "constitution_seeded", "Seeded constitutional graph.", experiment_id=experiment_id)

    def start_session(
        self,
        experiment_id: str | None,
        *,
        title: str | None = None,
        profile_request: dict[str, Any] | InferenceProfileRequest | None = None,
    ) -> dict[str, Any]:
        experiment = self.primary_experiment()
        if experiment_id and experiment_id != experiment["id"]:
            self.runtime_log.emit(
                "INFO",
                "session_graph_redirect",
                "Redirected session start into the single primary graph.",
                experiment_id=experiment["id"],
                requested_experiment_id=experiment_id,
            )
        if isinstance(profile_request, InferenceProfileRequest):
            request = profile_request
        else:
            request = request_from_dict(profile_request, self.settings)
        request = request_from_dict(request.to_dict(), self.settings)
        self.settings.low_motion = request.low_motion
        self.settings.debug = request.debug
        session = self.store.create_session(
            experiment_id=experiment["id"],
            agent_id=self.agent_id,
            title=title or request.title or f"{experiment['name']} session",
            metadata={
                "started_with_backend": self.settings.model_backend,
                "requested_mode": request.mode,
                "requested_inference_profile": request.to_dict(),
            },
        )
        self.runtime_log.emit(
            "INFO",
            "session_start",
            "Started session.",
            experiment_id=experiment["id"],
            session_id=session["id"],
            requested_mode=request.mode,
            budget_mode=request.budget_mode,
        )
        try:
            normalization_report = self._normalize_legacy_knowledge_graph(
                experiment_id=experiment["id"],
                session_id=session["id"],
            )
            session = self.store.update_session_metadata(
                session["id"],
                {"session_graph_normalization": normalization_report},
            )
        except Exception as exc:
            report = {
                "status": "error",
                "ran_at": now_utc(),
                "error": f"{type(exc).__name__}: {exc}",
                "mode": "session_start_graph_normalization",
            }
            self.runtime_log.emit(
                "WARNING",
                "graph_normalization_failed",
                "Session-start graph normalization failed.",
                experiment_id=experiment["id"],
                session_id=session["id"],
                error=report["error"],
            )
            self.store.record_trace_event(
                experiment_id=experiment["id"],
                session_id=session["id"],
                turn_id=None,
                event_type="GRAPH_NORMALIZATION",
                level="WARNING",
                message="Session-start graph normalization failed",
                payload=report,
            )
            session = self.store.update_session_metadata(
                session["id"],
                {"session_graph_normalization": report},
            )
        return session

    def _meme_row_metadata(self, row: dict[str, Any]) -> dict[str, Any]:
        raw = row.get("metadata_json")
        if isinstance(raw, dict):
            return raw
        if not raw:
            return {}
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return {}

    def _relation_entity_lookup(self, memes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        lookup: dict[str, dict[str, Any]] = {}
        priority_by_canonical: dict[str, int] = {}
        for row in memes:
            if str(row.get("domain") or "").lower() != "knowledge":
                continue
            canonical = slugify(str(row.get("canonical_label") or row.get("label") or ""))
            if not canonical:
                continue
            metadata = self._meme_row_metadata(row)
            priority = (
                2
                if str(metadata.get("candidate_kind") or "") == "relation_entity"
                or str(metadata.get("entity_type") or "") in GRAPH_NORMALIZATION_ENTITY_TYPES
                else 1
            )
            if canonical not in lookup or priority > priority_by_canonical.get(canonical, 0):
                lookup[canonical] = row
                priority_by_canonical[canonical] = priority
        return lookup

    def _extract_json_payload(self, text: str) -> Any:
        stripped = str(text or "").strip()
        if not stripped:
            return None
        for opener, closer in (("[", "]"), ("{", "}")):
            start = stripped.find(opener)
            end = stripped.rfind(closer)
            if start == -1 or end == -1 or end <= start:
                continue
            fragment = stripped[start : end + 1]
            try:
                return json.loads(fragment)
            except json.JSONDecodeError:
                continue
        return None

    def _sanitize_relation_review_payload(
        self,
        payload: Any,
        *,
        fallback_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            raw_relations = payload.get("relations") or []
        elif isinstance(payload, list):
            raw_relations = payload
        else:
            return []
        fallback_lookup = {
            (
                slugify(str(item.get("source_label") or "")),
                slugify(str(item.get("target_label") or "")),
                str(item.get("edge_type") or "").upper(),
            ): item
            for item in fallback_relations
        }
        sanitized: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in raw_relations:
            if not isinstance(item, dict):
                continue
            source_label = str(item.get("source_label") or "").strip()
            target_label = str(item.get("target_label") or "").strip()
            edge_type = str(item.get("edge_type") or "").strip().upper()
            if edge_type not in GRAPH_NORMALIZATION_EDGE_TYPES:
                continue
            source_canonical = slugify(source_label)
            target_canonical = slugify(target_label)
            if not source_canonical or not target_canonical or source_canonical == target_canonical:
                continue
            fallback = fallback_lookup.get((source_canonical, target_canonical, edge_type), {})
            source_entity_type = str(item.get("source_entity_type") or fallback.get("source_entity_type") or "information").strip().lower()
            target_entity_type = str(item.get("target_entity_type") or fallback.get("target_entity_type") or "information").strip().lower()
            if edge_type == "AUTHOR_OF":
                source_entity_type = "author"
                target_entity_type = "work"
            if source_entity_type not in GRAPH_NORMALIZATION_ENTITY_TYPES:
                source_entity_type = "information"
            if target_entity_type not in GRAPH_NORMALIZATION_ENTITY_TYPES:
                target_entity_type = "information"
            key = (source_canonical, target_canonical, edge_type)
            if key in seen:
                continue
            seen.add(key)
            confidence = item.get("confidence", fallback.get("confidence", 0.72))
            try:
                confidence_value = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence_value = float(fallback.get("confidence", 0.72) or 0.72)
            sanitized.append(
                {
                    "source_label": source_label,
                    "target_label": target_label,
                    "edge_type": edge_type,
                    "source_entity_type": source_entity_type,
                    "target_entity_type": target_entity_type,
                    "confidence": confidence_value,
                    "rule": str(item.get("rule") or "adam_identity_graph_normalizer_v1"),
                    "sentence_excerpt": str(item.get("sentence_excerpt") or fallback.get("sentence_excerpt") or ""),
                }
            )
        return sanitized

    def _graph_normalization_system_prompt(self) -> str:
        return (
            f"You are {self.agent_profile['name']}, rewriting your own externalized graph in EDEN.\n"
            "This is not a Brian-facing answer.\n"
            "Treat this as graph repair for legacy knowledge rows.\n"
            "Behavior-domain nodes are performative memes.\n"
            "Knowledge-domain authors, works, and factual relations are constative information nodes, not memes.\n"
            "Memodes are behavior-only second-order objects and must never be created in this pass.\n"
            "Use only grounded relations visible in the supplied text.\n"
            "Allowed edge types: AUTHOR_OF, INFLUENCES, REFERENCES.\n"
            "Allowed entity types: author, work, information.\n"
            'Return strict JSON only in the form {"relations":[...]} and no prose.'
        )

    def _graph_normalization_prompt(
        self,
        *,
        row: dict[str, Any],
        relations: list[dict[str, Any]],
    ) -> str:
        return (
            "Normalize this one legacy knowledge row.\n\n"
            f"Legacy label: {str(row.get('label') or '').strip()}\n"
            f"Legacy text excerpt: {safe_excerpt(str(row.get('text') or ''), limit=900)}\n\n"
            "Deterministic candidates:\n"
            f"{json.dumps(relations, ensure_ascii=True)}\n\n"
            "If a candidate is unsupported by the text, drop it. If a relation is supported but needs cleaner entity typing, fix it.\n"
            'Return only JSON: {"relations":[{"source_label":"...","source_entity_type":"author|work|information","target_label":"...","target_entity_type":"author|work|information","edge_type":"AUTHOR_OF|INFLUENCES|REFERENCES","confidence":0.0,"sentence_excerpt":"..."}]}.'
        )

    def _adam_identity_relation_review(
        self,
        *,
        row: dict[str, Any],
        relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if self.settings.model_backend.lower() != "mlx":
            return []
        model_status = self.mlx_model_status()
        if not model_status.get("ready"):
            return []
        adapter = self._get_model_adapter()
        model_result = adapter.generate(
            system_prompt=self._graph_normalization_system_prompt(),
            conversation_prompt=self._graph_normalization_prompt(row=row, relations=relations),
            max_tokens=360,
            temperature=0.0,
            top_p=1.0,
            repetition_penalty=0.0,
        )
        payload = self._extract_json_payload(
            str(model_result.answer_text or model_result.text or "")
        )
        return self._sanitize_relation_review_payload(payload, fallback_relations=relations)

    def _attach_information_entity_provenance(
        self,
        *,
        experiment_id: str,
        entity_id: str,
        source_row: dict[str, Any],
        metadata: dict[str, Any],
        session_id: str,
    ) -> None:
        document_id = str(metadata.get("document_id") or "")
        if document_id:
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="document",
                src_id=document_id,
                dst_kind="meme",
                dst_id=entity_id,
                edge_type="DERIVED_FROM",
                provenance={
                    "source_path": metadata.get("source_path", ""),
                    "page_number": metadata.get("page_number"),
                    "normalization": "legacy_knowledge_graph_normalization",
                    "session_id": session_id,
                },
            )
        turn_id = str(metadata.get("turn_id") or "")
        if turn_id:
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="turn",
                src_id=turn_id,
                dst_kind="meme",
                dst_id=entity_id,
                edge_type="OCCURS_IN",
                provenance={
                    "actor": metadata.get("origin", "legacy_knowledge_graph_normalization"),
                    "session_id": session_id,
                },
            )

    def _upsert_normalized_information_entity(
        self,
        *,
        experiment_id: str,
        source_row: dict[str, Any],
        metadata: dict[str, Any],
        label: str,
        entity_type: str,
        evidence_inc: float,
        canonical_lookup: dict[str, dict[str, Any]],
        session_id: str,
    ) -> tuple[dict[str, Any], bool]:
        canonical = slugify(label)
        existing = canonical_lookup.get(canonical)
        if existing is not None:
            existing_metadata = self._meme_row_metadata(existing)
            existing_text = str(existing.get("text") or label)
            entity = self.store.upsert_meme(
                experiment_id=experiment_id,
                label=str(existing.get("label") or label),
                text=existing_text,
                domain="knowledge",
                source_kind=str(existing.get("source_kind") or source_row.get("source_kind") or "document"),
                scope=str(existing.get("scope") or source_row.get("scope") or "global"),
                evidence_inc=max(0.05, evidence_inc * 0.25),
                metadata={
                    **existing_metadata,
                    "candidate_kind": "relation_entity",
                    "entity_type": entity_type,
                    "relation_role": entity_type,
                    "source_path": existing_metadata.get("source_path") or metadata.get("source_path", ""),
                    "title": existing_metadata.get("title") or metadata.get("title", ""),
                    "page_number": existing_metadata.get("page_number") or metadata.get("page_number"),
                    "document_id": existing_metadata.get("document_id") or metadata.get("document_id"),
                    "session_id": existing_metadata.get("session_id") or metadata.get("session_id") or session_id,
                    "turn_id": existing_metadata.get("turn_id") or metadata.get("turn_id"),
                    "normalization_origin": existing_metadata.get("normalization_origin") or "legacy_knowledge_graph_normalization",
                },
            )
            canonical_lookup[canonical] = entity
            return entity, False
        entity = self.store.upsert_meme(
            experiment_id=experiment_id,
            label=label,
            text=str(source_row.get("text") or label),
            domain="knowledge",
            source_kind=str(source_row.get("source_kind") or "document"),
            scope=str(source_row.get("scope") or "global"),
            evidence_inc=max(0.35, evidence_inc),
            metadata={
                "candidate_kind": "relation_entity",
                "entity_type": entity_type,
                "relation_role": entity_type,
                "source_path": metadata.get("source_path", ""),
                "title": metadata.get("title", ""),
                "page_number": metadata.get("page_number"),
                "document_id": metadata.get("document_id"),
                "session_id": metadata.get("session_id") or session_id,
                "turn_id": metadata.get("turn_id"),
                "origin": metadata.get("origin", "legacy_knowledge_graph_normalization"),
                "normalization_origin": "legacy_knowledge_graph_normalization",
            },
        )
        canonical_lookup[canonical] = entity
        self._attach_information_entity_provenance(
            experiment_id=experiment_id,
            entity_id=str(entity["id"]),
            source_row=source_row,
            metadata=metadata,
            session_id=session_id,
        )
        return entity, True

    def _normalize_legacy_knowledge_graph(
        self,
        *,
        experiment_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        memes = self.store.list_memes(experiment_id)
        knowledge_rows = [row for row in memes if str(row.get("domain") or "").lower() == "knowledge"]
        canonical_lookup = self._relation_entity_lookup(knowledge_rows)
        existing_edge_keys = {
            (str(edge.get("src_id") or ""), str(edge.get("dst_id") or ""), str(edge.get("edge_type") or ""))
            for edge in self.store.list_edges(experiment_id)
            if edge.get("src_kind") == "meme" and edge.get("dst_kind") == "meme"
        }
        candidate_rows: list[dict[str, Any]] = []
        for row in knowledge_rows:
            metadata = self._meme_row_metadata(row)
            if str(metadata.get("candidate_kind") or "") == "relation_entity":
                continue
            text = str(row.get("text") or "").strip()
            if not text:
                continue
            unresolved_relations: list[dict[str, Any]] = []
            for relation in extract_semantic_candidates(text, limit=6)["relation_candidates"]:
                source = canonical_lookup.get(slugify(str(relation.get("source_label") or "")))
                target = canonical_lookup.get(slugify(str(relation.get("target_label") or "")))
                edge_type = str(relation.get("edge_type") or "").upper()
                if not source or not target:
                    unresolved_relations.append(relation)
                    continue
                if (str(source.get("id") or ""), str(target.get("id") or ""), edge_type) not in existing_edge_keys:
                    unresolved_relations.append(relation)
            if unresolved_relations:
                candidate_rows.append({"row": row, "metadata": metadata, "relations": unresolved_relations})
        report = {
            "status": "completed",
            "ran_at": now_utc(),
            "mode": "deterministic",
            "candidate_rows": len(candidate_rows),
            "rows_processed": 0,
            "rows_changed": 0,
            "nodes_added": 0,
            "edges_added": 0,
            "relations_materialized": 0,
            "mlx_review_attempted": False,
            "mlx_review_rows": 0,
            "mlx_review_applied_rows": 0,
            "mlx_review_error": "",
        }
        if not candidate_rows:
            self.store.record_trace_event(
                experiment_id=experiment_id,
                session_id=session_id,
                turn_id=None,
                event_type="GRAPH_NORMALIZATION",
                level="INFO",
                message="Session-start graph normalization found no legacy knowledge gaps",
                payload=report,
            )
            return report
        use_mlx_review = self.settings.model_backend.lower() == "mlx" and bool(self.mlx_model_status().get("ready"))
        report["mlx_review_attempted"] = use_mlx_review
        if use_mlx_review:
            report["mode"] = "adam_identity_mlx"
        for index, bundle in enumerate(candidate_rows):
            row = bundle["row"]
            metadata = bundle["metadata"]
            relations = list(bundle["relations"])
            assertion_origin = "legacy_normalization_deterministic"
            if use_mlx_review and index < GRAPH_NORMALIZATION_MLX_REVIEW_LIMIT:
                report["mlx_review_rows"] += 1
                try:
                    reviewed_relations = self._adam_identity_relation_review(row=row, relations=relations)
                except Exception as exc:
                    report["mlx_review_error"] = f"{type(exc).__name__}: {exc}"
                    reviewed_relations = []
                if reviewed_relations:
                    relations = reviewed_relations
                    assertion_origin = "adam_identity_mlx"
                    report["mlx_review_applied_rows"] += 1
            report["rows_processed"] += 1
            row_changed = False
            for relation in relations:
                source_node, source_added = self._upsert_normalized_information_entity(
                    experiment_id=experiment_id,
                    source_row=row,
                    metadata=metadata,
                    label=str(relation.get("source_label") or ""),
                    entity_type=str(relation.get("source_entity_type") or "information"),
                    evidence_inc=float(relation.get("confidence", 0.5) or 0.5),
                    canonical_lookup=canonical_lookup,
                    session_id=session_id,
                )
                target_node, target_added = self._upsert_normalized_information_entity(
                    experiment_id=experiment_id,
                    source_row=row,
                    metadata=metadata,
                    label=str(relation.get("target_label") or ""),
                    entity_type=str(relation.get("target_entity_type") or "information"),
                    evidence_inc=float(relation.get("confidence", 0.5) or 0.5),
                    canonical_lookup=canonical_lookup,
                    session_id=session_id,
                )
                if source_added:
                    report["nodes_added"] += 1
                    row_changed = True
                if target_added:
                    report["nodes_added"] += 1
                    row_changed = True
                edge_key = (str(source_node["id"]), str(target_node["id"]), str(relation.get("edge_type") or "").upper())
                edge_existed = edge_key in existing_edge_keys
                self.store.set_edge(
                    experiment_id=experiment_id,
                    src_kind="meme",
                    src_id=str(source_node["id"]),
                    dst_kind="meme",
                    dst_id=str(target_node["id"]),
                    edge_type=str(relation.get("edge_type") or "").upper(),
                    provenance={
                        "turn_id": metadata.get("turn_id"),
                        "session_id": session_id,
                        "document_id": metadata.get("document_id"),
                        "source_path": metadata.get("source_path", ""),
                        "title": metadata.get("title", ""),
                        "page_number": metadata.get("page_number"),
                        "assertion_origin": assertion_origin,
                        "evidence_label": "AUTO_DERIVED",
                        "confidence": float(relation.get("confidence", 0.72) or 0.72),
                        "relation_rule": relation.get("rule", ""),
                        "sentence_excerpt": relation.get("sentence_excerpt", ""),
                        "source_meme_id": str(row.get("id") or ""),
                    },
                )
                if not edge_existed:
                    existing_edge_keys.add(edge_key)
                    report["edges_added"] += 1
                    row_changed = True
                report["relations_materialized"] += 1
            if row_changed:
                report["rows_changed"] += 1
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=None,
            event_type="GRAPH_NORMALIZATION",
            level="INFO",
            message="Session-start graph normalization completed",
            payload=report,
        )
        return report

    def session_profile_request(self, session_id: str) -> dict[str, Any]:
        return self._session_profile_request(session_id).to_dict()

    def update_conversation_archive(self, session_id: str, *, folder: str, tags: Any) -> dict[str, Any]:
        archive = {
            "folder": _normalize_archive_folder(folder),
            "tags": _normalize_archive_tags(tags),
        }
        session = self.store.update_session_metadata(session_id, {"archive": archive})
        metadata = json.loads(session["metadata_json"] or "{}")
        return {"session_id": session_id, "archive": _normalize_archive_metadata(metadata)}

    def conversation_archive_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in self.store.list_session_catalog():
            metadata = json.loads(row.get("metadata_json") or "{}")
            archive = _normalize_archive_metadata(metadata)
            profile_request = metadata.get("requested_inference_profile") or {}
            last_user = (row.get("last_user_text") or "").strip()
            if last_user.lower().startswith(f"{OPERATOR_LABEL.lower()}:"):
                last_user = last_user.split(":", 1)[1].strip()
            visible_response, _ = self.sanitize_operator_response(
                row.get("last_response_text") or "",
                response_char_cap=320,
            )
            transcript_path = self.conversation_log_path(row["id"])
            tags = archive["tags"]
            records.append(
                {
                    **row,
                    "folder": archive["folder"],
                    "tags": tags,
                    "tag_display": ", ".join(f"#{tag}" for tag in tags) if tags else "untagged",
                    "requested_mode": profile_request.get("mode", "manual"),
                    "budget_mode": profile_request.get("budget_mode", "balanced"),
                    "conversation_log_path": str(transcript_path),
                    "conversation_log_exists": transcript_path.exists(),
                    "last_user_excerpt": safe_excerpt(last_user or "No Brian turn yet.", limit=96),
                    "last_response_excerpt": safe_excerpt(visible_response or "No Adam response yet.", limit=120),
                    "projection_paths": [
                        "all_texts",
                        f"folder:{archive['folder']}",
                        *[f"tag:{tag}" for tag in tags],
                        f"graph:{row.get('experiment_slug') or row['experiment_id']}",
                    ],
                    "search_text": " ".join(
                        [
                            str(row.get("title") or ""),
                            str(row.get("experiment_name") or ""),
                            str(row.get("experiment_mode") or ""),
                            archive["folder"],
                            " ".join(tags),
                            last_user,
                            visible_response,
                        ]
                    ).lower(),
                }
            )
        return records

    def conversation_archive_preview(self, session_id: str, *, turn_limit: int = 4) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        experiment = self.store.get_experiment(session["experiment_id"])
        metadata = json.loads(session["metadata_json"] or "{}")
        archive = _normalize_archive_metadata(metadata)
        recent_turns: list[dict[str, Any]] = []
        for turn in reversed(self.store.list_turns(session_id, limit=turn_limit)):
            user_text = (turn.get("user_text") or "").strip()
            if user_text.lower().startswith(f"{OPERATOR_LABEL.lower()}:"):
                user_text = user_text.split(":", 1)[1].strip()
            visible_response, _ = self.render_turn_visible_response(turn)
            recent_turns.append(
                {
                    "turn_index": turn["turn_index"],
                    "user_excerpt": safe_excerpt(user_text or "No Brian text.", limit=110),
                    "response_excerpt": safe_excerpt(visible_response or "No Adam text.", limit=140),
                }
            )
        return {
            "session_id": session_id,
            "session_title": session["title"],
            "experiment_name": experiment["name"],
            "experiment_mode": experiment["mode"],
            "archive": archive,
            "profile_request": self.session_profile_request(session_id),
            "conversation_log_path": str(self.conversation_log_path(session_id)),
            "conversation_log_exists": self.conversation_log_path(session_id).exists(),
            "recent_turns": recent_turns,
            "recent_feedback": self.store.recent_feedback(session_id, limit=4),
        }

    def conversation_log_path(self, session_id: str) -> Path:
        session = self.store.get_session(session_id)
        experiment = self.store.get_experiment(session["experiment_id"])
        experiment_slug = experiment.get("slug") or slugify(experiment.get("name") or experiment["id"])
        session_slug = slugify(session.get("title") or "operator-session")
        out_dir = self.conversation_export_root / experiment_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir / f"{session_slug}-{session_id[:8]}.md"

    def write_conversation_log(self, session_id: str) -> Path:
        session = self.store.get_session(session_id)
        experiment = self.store.get_experiment(session["experiment_id"])
        path = self.conversation_log_path(session_id)
        profile = self.session_profile_request(session_id)
        lines = [
            "# Adam Conversation Log",
            "",
            f"- graph: {experiment['name']} ({experiment['id']})",
            f"- session: {session['title']} ({session_id})",
            f"- mode: {profile.get('mode', 'unknown')}",
            f"- budget_mode: {profile.get('budget_mode', 'unknown')}",
            f"- updated_at: {now_utc()}",
            f"- transcript_path: {path}",
            "",
        ]
        turns = self.store.list_all_turns(session_id)
        if not turns:
            lines.append("_No turns yet. The session is armed, but Brian has not sent a turn._")
        for turn in turns:
            user_text = (turn.get("user_text") or "").strip()
            if user_text.lower().startswith(f"{OPERATOR_LABEL.lower()}:"):
                user_text = user_text.split(":", 1)[1].strip()
            visible_response, _ = self.render_turn_visible_response(turn)
            lines.extend(
                [
                    f"## Turn T{turn['turn_index']}",
                    "",
                    "### Brian",
                    "```text",
                    user_text,
                    "```",
                    "",
                    "### Adam",
                    "```text",
                    visible_response,
                    "```",
                    "",
                ]
            )
            feedback_entries = self.store.list_feedback_for_turn(turn["id"])
            if feedback_entries:
                lines.append("### Feedback")
                lines.append("")
                for feedback in feedback_entries:
                    verdict = str(feedback.get("verdict", "skip")).upper()
                    lines.append(f"- {verdict} at {feedback.get('created_at', 'n/a')}")
                    explanation = (feedback.get("explanation") or "").strip()
                    corrected_text = (feedback.get("corrected_text") or "").strip()
                    lines.append(f"  explanation: {explanation or 'none'}")
                    if corrected_text:
                        lines.append("  corrected_text:")
                        lines.append("")
                        lines.append("  ```text")
                        lines.append(f"  {corrected_text}")
                        lines.append("  ```")
                lines.append("")
        hum = self.hum_snapshot(session_id)
        lines.extend(
            [
                "### Hum",
                "",
                f"- present: {hum['present']}",
                f"- generated_at: {hum.get('generated_at') or 'n/a'}",
                f"- markdown_path: {hum['markdown_path']}",
                f"- json_path: {hum['json_path']}",
                "",
            ]
        )
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return path

    def hum_snapshot(self, session_id: str) -> dict[str, Any]:
        return self.hum_service.snapshot(session_id)

    def _refresh_hum_safely(self, session_id: str) -> dict[str, Any] | None:
        try:
            return self.hum_service.refresh(session_id=session_id)
        except Exception as exc:
            self.runtime_log.emit(
                "ERROR",
                "hum_refresh_failed",
                "Failed to refresh bounded hum artifact.",
                session_id=session_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            return None

    def session_state_snapshot(self, session_id: str) -> dict[str, Any]:
        session = self.store.get_session(session_id)
        experiment = self.store.get_experiment(session["experiment_id"])
        snapshot = {
            "experiment_id": experiment["id"],
            "experiment_name": experiment["name"],
            "session_id": session["id"],
            "session_title": session["title"],
            "conversation_log_path": str(self.write_conversation_log(session_id)),
            "hum": self.hum_snapshot(session_id),
            "profile_request": self.session_profile_request(session_id),
            "last_turn_id": None,
            "last_user_text": "",
            "last_response": "",
            "last_reasoning": "",
            "last_active_set": [],
            "last_trace": [],
            "current_budget": None,
            "current_profile": None,
        }
        turns = self.store.list_turns(session_id, limit=1)
        if not turns:
            return snapshot
        turn = turns[0]
        metadata = json.loads(turn["metadata_json"] or "{}")
        visible_response, _ = self.render_turn_visible_response(turn, metadata=metadata)
        snapshot.update(
            {
                "last_turn_id": turn["id"],
                "last_user_text": turn["user_text"],
                "last_response": visible_response,
                "last_reasoning": metadata.get("model_result", {}).get("reasoning_text", ""),
                "last_active_set": json.loads(turn["active_set_json"] or "[]"),
                "last_trace": json.loads(turn["trace_json"] or "[]"),
                "current_budget": metadata.get("budget"),
                "current_profile": metadata.get("inference_profile"),
                "hum": self.hum_snapshot(session_id),
            }
        )
        return snapshot

    def update_session_profile_request(self, session_id: str, **updates: Any) -> dict[str, Any]:
        request = self._session_profile_request(session_id)
        merged = request.to_dict()
        merged.update(updates)
        updated = request_from_dict(merged, self.settings)
        self.store.update_session_title(session_id, updated.title)
        self.store.update_session_metadata(
            session_id,
            {
                "requested_mode": updated.mode,
                "requested_inference_profile": updated.to_dict(),
            },
        )
        self.settings.low_motion = updated.low_motion
        self.settings.debug = updated.debug
        return updated.to_dict()

    def _recent_history_context(
        self,
        session_id: str,
        *,
        limit: int,
        prompt_budget_tokens: int | None = None,
        system_prompt: str = "",
        active_set_context: str = "",
        feedback_context: str = "",
        user_text: str = "",
        token_counter: Callable[[str], int] | None = None,
    ) -> tuple[str, int]:
        turns = list(self.store.list_turns(session_id, limit=max(1, limit)))
        if not turns:
            return "No prior turns.", 0
        if prompt_budget_tokens is None:
            ordered_turns = list(reversed(turns))
            parts = []
            for turn in ordered_turns:
                parts.append(f"T{turn['turn_index']} {safe_excerpt(turn['user_text'], limit=220)}")
                parts.append(f"T{turn['turn_index']} ADAM: {safe_excerpt(turn['membrane_text'], limit=220)}")
            return "\n".join(parts), len(ordered_turns)

        counter = token_counter or heuristic_token_count
        base_prompt = self._conversation_prompt(
            active_set_context=active_set_context,
            feedback_context=feedback_context,
            history_context="",
            user_text=user_text,
        )
        remaining_history_tokens = max(0, int(prompt_budget_tokens) - counter(system_prompt) - counter(base_prompt))
        selected_blocks: list[str] = []
        for turn in turns:
            block = "\n".join(
                [
                    f"T{turn['turn_index']} {safe_excerpt(turn['user_text'], limit=220)}",
                    f"T{turn['turn_index']} ADAM: {safe_excerpt(turn['membrane_text'], limit=220)}",
                ]
            )
            block_tokens = counter(block)
            if block_tokens > remaining_history_tokens:
                if selected_blocks:
                    break
                continue
            selected_blocks.append(block)
            remaining_history_tokens -= block_tokens
        if not selected_blocks:
            return "No prior turns fit current prompt budget.", 0
        selected_blocks.reverse()
        return "\n".join(selected_blocks), len(selected_blocks)

    def _recent_feedback_context(self, session_id: str) -> str:
        feedback = list(reversed(self.store.recent_feedback(session_id, limit=3)))
        if not feedback:
            return "No explicit feedback yet."
        parts = []
        for item in feedback:
            corrected = item.get("corrected_text") or ""
            parts.append(f"T{item['turn_index']} {item['verdict'].upper()}: {safe_excerpt(item['explanation'], limit=180)}")
            if corrected:
                parts.append(f"CORRECTED: {safe_excerpt(corrected, limit=180)}")
        return "\n".join(parts)

    def _system_prompt(self, *, profile) -> str:
        return (
            f"You are {self.agent_profile['name']}, the first graph-conditioned agent in EDEN.\n"
            "Your persistent identity is externalized into a memetic graph.\n"
            "If the model emits an explicit reasoning block, EDEN may surface it separately as operator-visible model thinking.\n"
            "Return one clean operator-facing reply in Adam's voice.\n"
            "Do not include headings such as Answer, Basis, Next Step, or Final Answer.\n"
            "Do not expose hidden reasoning, scratch work, or chain-of-thought.\n"
            "Treat recent feedback as binding context when relevant.\n"
            f"Inference profile={profile.profile_name} mode={profile.effective_mode} response_char_cap={profile.response_char_cap}."
        )

    def _conversation_prompt(
        self,
        *,
        active_set_context: str,
        feedback_context: str,
        history_context: str,
        user_text: str,
    ) -> str:
        return (
            "ACTIVE SET\n"
            f"{active_set_context}\n\n"
            "RECENT FEEDBACK\n"
            f"{feedback_context}\n\n"
            "RECENT HISTORY\n"
            f"{history_context}\n\n"
            f"{self._operator_utterance(user_text)}"
        )

    def _operator_utterance(self, user_text: str) -> str:
        cleaned = (user_text or "").strip()
        if not cleaned:
            return f"{OPERATOR_LABEL}:"
        normalized_prefix = f"{OPERATOR_LABEL}:"
        if cleaned.lower().startswith(normalized_prefix.lower()):
            return cleaned
        return f"{normalized_prefix} {cleaned}"

    def _apply_membrane(
        self,
        *,
        text: str,
        active_set: list[dict[str, Any]],
        response_char_cap: int,
    ) -> tuple[str, list[dict[str, Any]]]:
        return self.sanitize_operator_response(text, response_char_cap=response_char_cap)

    def sanitize_operator_response(self, text: str, *, response_char_cap: int) -> tuple[str, list[dict[str, Any]]]:
        original = text or ""
        events: list[dict[str, Any]] = []
        cleaned = CONTROL_CHAR_RE.sub("", original).strip()
        if cleaned != original:
            events.append({"event_type": "CONTROL_CHAR_STRIPPED", "detail": "Removed non-printing control characters."})
        reasoning_text, cleaned_answer = split_model_output(cleaned)
        if reasoning_text and cleaned_answer and cleaned_answer != cleaned:
            cleaned = cleaned_answer.strip()
            events.append({"event_type": "REASONING_SPLIT", "detail": "Removed a visible reasoning block from the operator-facing answer."})
        elif reasoning_text and cleaned_answer == cleaned:
            cleaned = ""
            events.append(
                {
                    "event_type": "REASONING_ONLY_DROPPED",
                    "detail": "Dropped a reasoning-only spill that did not contain a clean operator-facing answer.",
                }
            )
        if SUPPORT_SECTION_RE.search(cleaned):
            cleaned = SUPPORT_SECTION_RE.split(cleaned, maxsplit=1)[0].strip()
            events.append({"event_type": "SUPPORT_STRIPPED", "detail": "Removed Basis / Next Step scaffolding from the visible answer."})
        label_cleaned = ANSWER_LABEL_RE.sub("", cleaned, count=1).strip()
        if label_cleaned != cleaned:
            cleaned = label_cleaned
            events.append({"event_type": "LABEL_STRIPPED", "detail": "Removed operator-visible answer labels."})
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if not cleaned:
            cleaned = "I am ready for Brian's next prompt."
            events.append({"event_type": "EMPTY_REPAIRED", "detail": "Repaired an empty operator-facing answer after membrane cleanup."})
        max_chars = max(400, response_char_cap)
        if len(cleaned) > max_chars:
            cleaned = cleaned[: max_chars - 1].rstrip() + "…"
            events.append({"event_type": "TRIMMED", "detail": f"Clamped response to {max_chars} characters."})
        if not events:
            events.append({"event_type": "PASSTHROUGH", "detail": "Response passed the membrane unchanged."})
        return cleaned, events

    def response_char_cap_for_turn(
        self,
        turn: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
        fallback: int = MAX_RESPONSE_CHAR_CAP,
    ) -> int:
        resolved_metadata = metadata
        if resolved_metadata is None:
            try:
                resolved_metadata = json.loads(turn.get("metadata_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                resolved_metadata = {}
        profile: dict[str, Any] = {}
        if isinstance(resolved_metadata, dict):
            candidate = resolved_metadata.get("inference_profile") or resolved_metadata.get("requested_inference_profile") or {}
            if isinstance(candidate, dict):
                profile = candidate
        try:
            cap = int(profile.get("response_char_cap", fallback) or fallback)
        except (TypeError, ValueError):
            cap = fallback
        return max(400, cap)

    def render_turn_visible_response(
        self,
        turn: dict[str, Any],
        *,
        metadata: dict[str, Any] | None = None,
        display_char_cap: int = DISPLAY_RESPONSE_CHAR_CAP,
    ) -> tuple[str, list[dict[str, Any]]]:
        resolved_metadata = metadata
        if resolved_metadata is None:
            try:
                resolved_metadata = json.loads(turn.get("metadata_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                resolved_metadata = {}
        model_result = resolved_metadata.get("model_result") or {} if isinstance(resolved_metadata, dict) else {}
        answer_text = str(model_result.get("answer_text") or "").strip() if isinstance(model_result, dict) else ""
        source_text = answer_text or turn.get("response_text") or turn.get("membrane_text") or ""
        response_char_cap = max(
            self.response_char_cap_for_turn(turn, metadata=resolved_metadata),
            max(400, int(display_char_cap)),
        )
        return self.sanitize_operator_response(source_text, response_char_cap=response_char_cap)

    def _index_text_into_graph(
        self,
        *,
        experiment_id: str,
        turn_id: str,
        session_id: str,
        text: str,
        domain: str,
        source_kind: str,
        actor: str,
    ) -> dict[str, list[str]]:
        member_ids: list[str] = []
        member_labels_by_id: dict[str, str] = {}
        member_ids_by_label: dict[str, str] = {}
        memode_ids: list[str] = []
        supporting_edge_ids: list[str] = []
        semantic_candidates = extract_semantic_candidates(text, limit=6)
        for candidate in semantic_candidates["meme_candidates"]:
            meme = self.store.upsert_meme(
                experiment_id=experiment_id,
                label=str(candidate["label"]),
                text=text,
                domain=domain,
                source_kind=source_kind,
                scope=f"session:{session_id}",
                evidence_inc=float(candidate["score"]),
                metadata={
                    "session_id": session_id,
                    "turn_id": turn_id,
                    "origin": actor,
                    "entity_type": str(candidate.get("entity_type") or ""),
                    "relation_role": str(candidate.get("relation_role") or ""),
                    "candidate_kind": str(candidate.get("kind") or ""),
                },
            )
            member_id = str(meme["id"])
            member_ids.append(member_id)
            member_labels_by_id.setdefault(member_id, str(meme.get("label") or candidate["label"]))
            member_ids_by_label.setdefault(slugify(str(meme.get("label") or candidate["label"])), member_id)
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="turn",
                src_id=turn_id,
                dst_kind="meme",
                dst_id=member_id,
                edge_type="OCCURS_IN",
                provenance={"actor": actor},
            )
        for relation in semantic_candidates["relation_candidates"]:
            source_id = member_ids_by_label.get(slugify(relation["source_label"]))
            target_id = member_ids_by_label.get(slugify(relation["target_label"]))
            if not source_id or not target_id or source_id == target_id:
                continue
            self.store.set_edge(
                experiment_id=experiment_id,
                src_kind="meme",
                src_id=source_id,
                dst_kind="meme",
                dst_id=target_id,
                edge_type=relation["edge_type"],
                provenance={
                    "turn_id": turn_id,
                    "actor": actor,
                    "assertion_origin": "auto_derived",
                    "evidence_label": "AUTO_DERIVED",
                    "confidence": relation["confidence"],
                    "relation_rule": relation["rule"],
                    "sentence_excerpt": relation["sentence_excerpt"],
                },
            )
        for idx, left in enumerate(member_ids):
            for right in member_ids[idx + 1 :]:
                edge = self.store.set_edge(
                    experiment_id=experiment_id,
                    src_kind="meme",
                    src_id=left,
                    dst_kind="meme",
                    dst_id=right,
                    edge_type="CO_OCCURS_WITH",
                    provenance={
                        "turn_id": turn_id,
                        "actor": actor,
                        "assertion_origin": "auto_derived",
                        "evidence_label": "AUTO_DERIVED",
                        "confidence": 1.0,
                    },
                )
                supporting_edge_ids.append(str(edge["id"]))
        memode_member_ids = list(member_labels_by_id.keys())[: min(4, len(member_labels_by_id))]
        memode_label_parts = list(member_labels_by_id.values())[:3]
        memode_label = " / ".join(memode_label_parts) or safe_excerpt(text, limit=72)
        support_subset = sorted(dict.fromkeys(supporting_edge_ids))
        if memode_materialization_allowed(domain) and len(memode_member_ids) >= 2 and support_subset:
            memode = self.store.upsert_memode(
                experiment_id=experiment_id,
                label=memode_label,
                member_ids=memode_member_ids,
                summary=safe_excerpt(text, limit=320),
                domain=domain,
                scope=f"session:{session_id}",
                metadata={
                    "turn_id": turn_id,
                    "session_id": session_id,
                    "origin": actor,
                    "supporting_edge_ids": support_subset,
                    "member_order": memode_member_ids,
                },
            )
            memode_ids.append(memode["id"])
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="turn",
                src_id=turn_id,
                dst_kind="memode",
                dst_id=memode["id"],
                edge_type="MATERIALIZES_AS_MEMODE",
                provenance={"actor": actor},
            )
            for member_id in memode_member_ids:
                self.store.add_edge(
                    experiment_id=experiment_id,
                    src_kind="memode",
                    src_id=memode["id"],
                    dst_kind="meme",
                    dst_id=member_id,
                    edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE,
                    provenance={"turn_id": turn_id},
                )
        return {"meme_ids": member_ids, "memode_ids": memode_ids}

    def _index_document_brief(
        self,
        *,
        experiment_id: str,
        document_id: str,
        source_path: str,
        briefing: str,
        session_id: str | None,
    ) -> dict[str, list[str]]:
        briefing_text = briefing.strip()
        if not briefing_text:
            return {"meme_ids": [], "memode_ids": []}
        member_ids: list[str] = []
        member_labels_by_id: dict[str, str] = {}
        member_ids_by_label: dict[str, str] = {}
        memode_ids: list[str] = []
        supporting_edge_ids: list[str] = []
        metadata = {
            "document_id": document_id,
            "source_path": source_path,
            "origin": "operator_ingest_brief",
            "session_id": session_id,
        }
        semantic_candidates = extract_semantic_candidates(briefing_text, limit=6)
        for candidate in semantic_candidates["meme_candidates"]:
            meme = self.store.upsert_meme(
                experiment_id=experiment_id,
                label=str(candidate["label"]),
                text=briefing_text,
                domain="behavior",
                source_kind="document_brief",
                scope="global",
                evidence_inc=float(candidate["score"]),
                metadata={
                    **metadata,
                    "candidate_kind": str(candidate.get("kind") or ""),
                    "entity_type": str(candidate.get("entity_type") or ""),
                    "relation_role": str(candidate.get("relation_role") or ""),
                },
            )
            member_id = str(meme["id"])
            member_ids.append(member_id)
            member_labels_by_id.setdefault(member_id, str(meme.get("label") or candidate["label"]))
            member_ids_by_label.setdefault(slugify(str(meme.get("label") or candidate["label"])), member_id)
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="document",
                src_id=document_id,
                dst_kind="meme",
                dst_id=meme["id"],
                edge_type="CONTEXTUALIZES_DOCUMENT",
                provenance={"source_path": source_path, "session_id": session_id},
            )
        for relation in semantic_candidates["relation_candidates"]:
            source_id = member_ids_by_label.get(slugify(relation["source_label"]))
            target_id = member_ids_by_label.get(slugify(relation["target_label"]))
            if not source_id or not target_id or source_id == target_id:
                continue
            self.store.set_edge(
                experiment_id=experiment_id,
                src_kind="meme",
                src_id=source_id,
                dst_kind="meme",
                dst_id=target_id,
                edge_type=relation["edge_type"],
                provenance={
                    "document_id": document_id,
                    "source_path": source_path,
                    "session_id": session_id,
                    "assertion_origin": "auto_derived",
                    "evidence_label": "AUTO_DERIVED",
                    "confidence": relation["confidence"],
                    "relation_rule": relation["rule"],
                    "sentence_excerpt": relation["sentence_excerpt"],
                },
            )
        for idx, left in enumerate(member_ids):
            for right in member_ids[idx + 1 :]:
                edge = self.store.set_edge(
                    experiment_id=experiment_id,
                    src_kind="meme",
                    src_id=left,
                    dst_kind="meme",
                    dst_id=right,
                    edge_type="CO_OCCURS_WITH",
                    provenance={
                        "document_id": document_id,
                        "source_path": source_path,
                        "assertion_origin": "auto_derived",
                        "evidence_label": "AUTO_DERIVED",
                        "confidence": 1.0,
                    },
                )
                supporting_edge_ids.append(str(edge["id"]))
        member_subset = member_ids[: min(4, len(member_ids))]
        support_subset = sorted(dict.fromkeys(supporting_edge_ids))
        if memode_materialization_allowed("behavior") and len(member_subset) >= 2 and support_subset:
            memode = self.store.upsert_memode(
                experiment_id=experiment_id,
                label=f"ingest lens / {' / '.join(member_labels_by_id[member_id] for member_id in member_ids[:3])}",
                member_ids=member_subset,
                summary=safe_excerpt(briefing_text, limit=320),
                domain="behavior",
                scope="global",
                metadata={
                    **metadata,
                    "briefing_excerpt": safe_excerpt(briefing_text, limit=220),
                    "supporting_edge_ids": support_subset,
                    "member_order": member_subset,
                },
            )
            memode_ids.append(memode["id"])
            self.store.add_edge(
                experiment_id=experiment_id,
                src_kind="document",
                src_id=document_id,
                dst_kind="memode",
                dst_id=memode["id"],
                edge_type="CONTEXTUALIZES_DOCUMENT",
                provenance={"source_path": source_path, "session_id": session_id},
            )
            for member_id in member_subset:
                self.store.add_edge(
                    experiment_id=experiment_id,
                    src_kind="memode",
                    src_id=memode["id"],
                    dst_kind="meme",
                    dst_id=member_id,
                    edge_type=MEMODE_MEMBERSHIP_EDGE_TYPE,
                    provenance={"document_id": document_id},
                )
        return {"meme_ids": member_ids, "memode_ids": memode_ids}

    def chat(
        self,
        *,
        session_id: str,
        user_text: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> ChatOutcome:
        session = self.store.get_session(session_id)
        experiment_id = session["experiment_id"]
        preview = self.preview_turn(session_id=session_id, user_text=user_text)
        operator_text = self._operator_utterance(user_text)
        active_set = {"items": preview.active_set, "trace": preview.trace}
        profile = preview.profile
        budget = preview.budget
        system_prompt = preview.system_prompt
        conversation_prompt = preview.conversation_prompt
        model = self._get_model_adapter()
        self.runtime_log.emit(
            "INFO",
            "turn_preview_ready",
            "Assembled active set and prompt.",
            experiment_id=experiment_id,
            session_id=session_id,
            active_set_size=len(active_set["items"]),
            profile_name=profile["profile_name"],
            budget_pressure=budget["pressure_level"],
        )
        self.runtime_log.emit(
            "INFO",
            "generation_start",
            "Generating Adam response.",
            experiment_id=experiment_id,
            session_id=session_id,
            backend=model.backend_name,
            requested_mode=profile["requested_mode"],
            effective_mode=profile["effective_mode"],
            profile_name=profile["profile_name"],
        )
        result = model.generate(
            system_prompt=system_prompt,
            conversation_prompt=conversation_prompt,
            max_tokens=profile["max_output_tokens"],
            temperature=profile["temperature"],
            top_p=profile["top_p"],
            repetition_penalty=profile["repetition_penalty"],
            progress_callback=progress_callback,
        )
        answer_text = result.answer_text or result.text
        membrane_text, membrane_events = self._apply_membrane(
            text=answer_text,
            active_set=active_set["items"],
            response_char_cap=profile["response_char_cap"],
        )
        trace = list(active_set["trace"])
        trace.append(
            {
                "label": "prompt_assembly",
                "kind": "system",
                "domain": "behavior",
                "selection": 0.0,
                "semantic_similarity": 0.0,
                "activation": 0.0,
                "regard": 0.0,
                "session_bias": 0.0,
                "explicit_feedback": 0.0,
                "scope_penalty": 0.0,
                "membrane_penalty": 0.0,
                "breakdown": {
                    "active_set_size": len(active_set["items"]),
                    "backend": result.backend,
                    "history_lines": len(preview.history_context.splitlines()),
                    "profile_name": profile["profile_name"],
                    "prompt_budget_tokens": budget["prompt_budget_tokens"],
                    "count_method": budget["count_method"],
                    "reasoning_present": bool(result.reasoning_text.strip()),
                },
                "provenance": "prompt_assembly",
            }
        )
        turn = self.store.record_turn(
            experiment_id=experiment_id,
            session_id=session_id,
            user_text=operator_text,
            prompt_context=conversation_prompt,
            response_text=result.text,
            membrane_text=membrane_text,
            active_set=active_set["items"],
            trace=trace,
            metadata={
                "operator_label": OPERATOR_LABEL,
                "operator_input_raw": user_text,
                "inference_profile": profile,
                "budget": budget,
                "model_result": {
                    **result.metadata,
                    "answer_text": answer_text,
                    "reasoning_text": result.reasoning_text,
                    "raw_text": result.raw_text,
                },
                "history_context": preview.history_context,
                "feedback_context": preview.feedback_context,
            },
        )
        self.store.store_active_set(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn["id"],
            query_text=user_text,
            items=active_set["items"],
        )
        for event in membrane_events:
            self.store.record_membrane_event(
                experiment_id=experiment_id,
                session_id=session_id,
                turn_id=turn["id"],
                event_type=event["event_type"],
                detail=event["detail"],
                payload={
                    "active_set_size": len(active_set["items"]),
                    "profile_name": profile["profile_name"],
                    "budget_pressure": budget["pressure_level"],
                },
            )
        indexed_user = self._index_text_into_graph(
            experiment_id=experiment_id,
            turn_id=turn["id"],
            session_id=session_id,
            text=operator_text,
            domain="knowledge",
            source_kind="turn_user",
            actor="brian_operator",
        )
        indexed_adam = self._index_text_into_graph(
            experiment_id=experiment_id,
            turn_id=turn["id"],
            session_id=session_id,
            text=membrane_text,
            domain="behavior",
            source_kind="turn_adam",
            actor="adam",
        )
        selected_meme_ids = [item["node_id"] for item in active_set["items"] if item["node_kind"] == "meme"]
        selected_memode_ids = [item["node_id"] for item in active_set["items"] if item["node_kind"] == "memode"]
        self.store.touch_nodes("meme", selected_meme_ids + indexed_user["meme_ids"] + indexed_adam["meme_ids"])
        self.store.touch_nodes("memode", selected_memode_ids + indexed_user["memode_ids"] + indexed_adam["memode_ids"])
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn["id"],
            event_type="TURN",
            level="INFO",
            message="Completed chat turn.",
            payload={
                "backend": result.backend,
                "active_set_size": len(active_set["items"]),
                "membrane_events": [event["event_type"] for event in membrane_events],
                "profile_name": profile["profile_name"],
                "requested_mode": profile["requested_mode"],
                "effective_mode": profile["effective_mode"],
                "prompt_budget_tokens": budget["prompt_budget_tokens"],
                "remaining_input_tokens": budget["remaining_input_tokens"],
                "count_method": budget["count_method"],
                "reasoning_present": bool(result.reasoning_text.strip()),
            },
        )
        self.runtime_log.emit(
            "INFO",
            "generation_complete",
            "Completed Adam response.",
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn["id"],
            backend=result.backend,
            active_set_size=len(active_set["items"]),
            profile_name=profile["profile_name"],
            budget_pressure=budget["pressure_level"],
        )
        self._refresh_hum_safely(session_id)
        if self.observatory_server.running:
            self.observatory_server.publish_invalidation(
                experiment_id=experiment_id,
                session_id=session_id,
                kinds=["graph", "basin", "transcript", "runtime", "overview"],
                reason="turn_persisted",
            )
        return ChatOutcome(
            turn=turn,
            active_set=active_set["items"],
            trace=trace,
            membrane_events=membrane_events,
            graph_counts=self.store.graph_counts(experiment_id),
            budget=budget,
            profile=profile,
            reasoning_text=result.reasoning_text.strip(),
        )

    def _turn_related_nodes(self, turn_id: str) -> dict[str, list[str]]:
        meme_ids: list[str] = []
        memode_ids: list[str] = []
        for edge in self.store.list_edges(self.store.get_turn(turn_id)["experiment_id"]):
            if edge["src_kind"] == "turn" and edge["src_id"] == turn_id:
                if edge["dst_kind"] == "meme":
                    meme_ids.append(edge["dst_id"])
                if edge["dst_kind"] == "memode":
                    memode_ids.append(edge["dst_id"])
        return {"meme_ids": sorted(set(meme_ids)), "memode_ids": sorted(set(memode_ids))}

    def apply_feedback(
        self,
        *,
        session_id: str,
        turn_id: str,
        verdict: str,
        explanation: str,
        corrected_text: str = "",
    ) -> dict[str, Any]:
        verdict = verdict.lower().strip()
        if verdict in {"accept", "reject"} and not explanation.strip():
            raise ValueError(f"{verdict.title()} feedback requires an explanation.")
        if verdict == "edit" and (not explanation.strip() or not corrected_text.strip()):
            raise ValueError("Edit feedback requires both an explanation and corrected text.")
        turn = self.store.get_turn(turn_id)
        experiment_id = turn["experiment_id"]
        signal = feedback_signal(verdict)
        feedback = self.store.record_feedback(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            verdict=verdict,
            explanation=explanation,
            corrected_text=corrected_text,
            signal=signal,
        )
        related = self._turn_related_nodes(turn_id)
        impacted_meme_ids = set(related["meme_ids"])
        impacted_memode_ids = set(related["memode_ids"])
        active_set = json.loads(turn["active_set_json"] or "[]")
        for item in active_set:
            if item["node_kind"] == "meme":
                impacted_meme_ids.add(item["node_id"])
            else:
                impacted_memode_ids.add(item["node_id"])

        for memode_id in list(impacted_memode_ids):
            memode = self.store.get_memode(memode_id)
            new_reward = ema(float(memode.get("reward_ema", 0.0)), signal["reward"])
            new_risk = ema(float(memode.get("risk_ema", 0.0)), signal["risk"])
            new_edit = ema(float(memode.get("edit_ema", 0.0)), signal["edit"])
            self.store.update_feedback_channels("memode", memode_id, reward=new_reward, risk=new_risk, edit=new_edit)
            metadata = json.loads(memode["metadata_json"] or "{}")
            for member_id in metadata.get("member_ids", []):
                impacted_meme_ids.add(member_id)

        propagate_scale = 0.65 if verdict == "edit" else 0.8
        for meme_id in impacted_meme_ids:
            meme = self.store.get_meme(meme_id)
            if verdict == "skip":
                self.store.bump_skip_count("meme", meme_id)
                continue
            new_reward = ema(float(meme.get("reward_ema", 0.0)), signal["reward"] * propagate_scale)
            new_risk = ema(float(meme.get("risk_ema", 0.0)), signal["risk"] * propagate_scale)
            new_edit = ema(float(meme.get("edit_ema", 0.0)), signal["edit"] * propagate_scale)
            self.store.update_feedback_channels("meme", meme_id, reward=new_reward, risk=new_risk, edit=new_edit)

        feedback_text = (
            f"Feedback verdict={verdict}. Explanation: {explanation.strip() or 'none provided.'} "
            f"Corrected text: {corrected_text.strip() or 'n/a'}"
        )
        feedback_nodes = self._index_text_into_graph(
            experiment_id=experiment_id,
            turn_id=turn_id,
            session_id=session_id,
            text=feedback_text,
            domain="behavior",
            source_kind="feedback",
            actor="feedback",
        )
        self.store.record_trace_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            event_type="FEEDBACK",
            level="INFO",
            message=f"Applied {verdict} feedback.",
            payload={
                "feedback_id": feedback["id"],
                "affected_memes": len(impacted_meme_ids) + len(feedback_nodes["meme_ids"]),
                "affected_memodes": len(impacted_memode_ids) + len(feedback_nodes["memode_ids"]),
            },
        )
        self.runtime_log.emit(
            "INFO",
            "feedback_applied",
            "Applied turn feedback.",
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            verdict=verdict,
        )
        self._refresh_hum_safely(session_id)
        if self.observatory_server.running:
            self.observatory_server.publish_invalidation(
                experiment_id=experiment_id,
                session_id=session_id,
                kinds=["graph", "transcript", "measurements", "overview"],
                reason="feedback_persisted",
            )
        return feedback

    def ingest_document(
        self,
        *,
        experiment_id: str,
        path: str,
        briefing: str = "",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_path = Path(path).expanduser().resolve()
        briefing_text = briefing.strip()
        result = self.ingest_service.ingest_path(
            experiment_id=experiment_id,
            path=resolved_path,
            briefing=briefing_text,
        )
        brief_nodes = self._index_document_brief(
            experiment_id=experiment_id,
            document_id=result.document_id,
            source_path=str(resolved_path),
            briefing=briefing_text,
            session_id=session_id,
        )
        if briefing_text:
            self.store.record_trace_event(
                experiment_id=experiment_id,
                session_id=session_id,
                turn_id=None,
                event_type="INGEST_BRIEF",
                level="INFO",
                message=f"Applied ingest brief for {resolved_path.name}",
                payload={
                    "document_id": result.document_id,
                    "briefing_excerpt": safe_excerpt(briefing_text, limit=200),
                    "brief_meme_count": len(brief_nodes["meme_ids"]),
                    "brief_memode_count": len(brief_nodes["memode_ids"]),
                },
            )
            self.runtime_log.emit(
                "INFO",
                "ingest_brief_applied",
                "Applied operator ingest brief.",
                experiment_id=experiment_id,
                session_id=session_id,
                document_id=result.document_id,
                document_title=resolved_path.name,
                brief_meme_count=len(brief_nodes["meme_ids"]),
                brief_memode_count=len(brief_nodes["memode_ids"]),
            )
        payload = asdict(result)
        payload.update(
            {
                "path": str(resolved_path),
                "title": resolved_path.name,
                "briefing": briefing_text,
                "briefing_indexed": bool(brief_nodes["meme_ids"] or brief_nodes["memode_ids"]),
                "brief_meme_count": len(brief_nodes["meme_ids"]),
                "brief_memode_count": len(brief_nodes["memode_ids"]),
            }
        )
        return payload

    def graph_health(self, experiment_id: str) -> dict[str, Any]:
        _, metrics = self.retrieval_service.build_graph_metrics(experiment_id)
        counts = self.store.graph_counts(experiment_id)
        counts.update({key: round(value, 4) for key, value in metrics.items()})
        return counts

    def export_dir_for_experiment(self, experiment_id: str) -> Path:
        path = EXPORT_DIR / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def export_observability(self, *, experiment_id: str, session_id: str | None = None) -> dict[str, str]:
        out_dir = self.export_dir_for_experiment(experiment_id)
        return self.exporter.export_all(experiment_id=experiment_id, session_id=session_id, out_dir=out_dir)

    def tanakh_get_passage(self, *, ref: str, mode: str = "keep_cantillation") -> dict[str, Any]:
        return self.tanakh_service.get_passage(ref, mode)

    def tanakh_gematria(self, *, input_text: str, scheme: str, preprocess: str) -> dict[str, Any]:
        return self.tanakh_service.gematria(input_text, scheme, preprocess)

    def tanakh_notarikon(self, *, input_text: str, mode: str, preprocess: str) -> dict[str, Any]:
        return self.tanakh_service.notarikon(input_text, mode, preprocess)

    def tanakh_temurah(self, *, input_text: str, mapping: str, preprocess: str) -> dict[str, Any]:
        return self.tanakh_service.temurah(input_text, mapping, preprocess)

    def tanakh_compile_merkavah_scene(self, *, ref: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.tanakh_service.compile_merkavah_scene(ref, params or {})

    def tanakh_surface_bundle(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        ref: str = DEFAULT_TANAKH_REF,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        out_dir = self.export_dir_for_experiment(experiment_id)
        _, payload = self.tanakh_service.export_surface_bundle(
            experiment_id=experiment_id,
            session_id=session_id,
            out_dir=out_dir,
            ref=ref,
            params=params,
        )
        return payload

    def preview_observatory_action(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        return self.observatory_service.preview_action(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            action=action,
        )

    def commit_observatory_action(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        action: dict[str, Any],
    ) -> dict[str, Any]:
        return self.observatory_service.commit_action(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            action=action,
        )

    def revert_observatory_action(
        self,
        *,
        experiment_id: str,
        session_id: str | None,
        turn_id: str | None,
        event_id: str,
    ) -> dict[str, Any]:
        return self.observatory_service.revert_event(
            experiment_id=experiment_id,
            session_id=session_id,
            turn_id=turn_id,
            event_id=event_id,
        )

    def start_observatory(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        reuse_existing: bool = True,
    ) -> dict[str, Any]:
        status = self.observatory_server.start(host=host, port=port, reuse_existing=reuse_existing)
        self.runtime_log.emit(
            "INFO",
            "observatory_start",
            "Observatory server ready.",
            url=status.url,
            host=status.host,
            port=status.port,
            reused_existing=status.reused_existing,
            owned_by_process=status.owned_by_process,
        )
        return {
            "url": status.url,
            "host": status.host,
            "port": status.port,
            "reused_existing": status.reused_existing,
            "owned_by_process": status.owned_by_process,
            "root": status.root,
            "info_url": status.info_url,
            "api_version": status.api_version,
            "capabilities": status.capabilities,
        }

    def observatory_status(self) -> dict[str, Any] | None:
        status = self.observatory_server.status()
        if status is None:
            return None
        return {
            "url": status.url,
            "host": status.host,
            "port": status.port,
            "reused_existing": status.reused_existing,
            "owned_by_process": status.owned_by_process,
            "root": status.root,
            "info_url": status.info_url,
            "api_version": status.api_version,
            "capabilities": status.capabilities,
        }

    def stop_observatory(self) -> dict[str, Any]:
        owned = self.observatory_server.stop()
        self.runtime_log.emit(
            "INFO",
            "observatory_stop",
            "Stopped observatory server." if owned else "Observatory server not owned by this process; nothing was shut down.",
            owned_by_process=owned,
        )
        return {"owned_by_process": owned}
