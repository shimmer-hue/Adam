from __future__ import annotations

import re
from typing import Any, Iterable


INFORMATION_KIND = "information"
MEME_KIND = "meme"
MEMODE_KIND = "memode"

CONSTATIVE_MODE = "constative"
PERFORMATIVE_MODE = "performative"
RUNTIME_MODE = "runtime"

_NAME_CONNECTORS = {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
_INITIAL_RE = re.compile(r"^[A-Z]\.$")
_CAPITALIZED_RE = re.compile(r"^[A-Z][A-Za-z0-9'’:-]+$")


def looks_like_person_name(label: str) -> bool:
    parts = [part for part in re.split(r"\s+", str(label or "").strip()) if part]
    if len(parts) < 2:
        return False
    if any(part.lower() in _NAME_CONNECTORS for part in parts):
        return False
    return all(bool(_INITIAL_RE.fullmatch(part) or _CAPITALIZED_RE.fullmatch(part)) for part in parts)


def infer_information_entity_type(
    *,
    label: str,
    metadata: dict[str, Any] | None = None,
    outgoing_edge_types: Iterable[str] = (),
    incoming_edge_types: Iterable[str] = (),
) -> str:
    metadata = metadata or {}
    explicit = str(metadata.get("entity_type") or metadata.get("relation_role") or "").strip().lower()
    if explicit in {"author", "work", "information"}:
        return explicit
    outgoing = {str(item or "").strip().upper() for item in outgoing_edge_types if str(item or "").strip()}
    incoming = {str(item or "").strip().upper() for item in incoming_edge_types if str(item or "").strip()}
    if "AUTHOR_OF" in outgoing:
        return "author"
    if "AUTHOR_OF" in incoming:
        return "work"
    candidate_kind = str(metadata.get("candidate_kind") or "").strip().lower()
    if candidate_kind == "relation_entity":
        return "author" if looks_like_person_name(label) else "work"
    return "information"


def project_node_ontology(
    *,
    storage_kind: str,
    domain: str,
    label: str,
    metadata: dict[str, Any] | None = None,
    outgoing_edge_types: Iterable[str] = (),
    incoming_edge_types: Iterable[str] = (),
) -> dict[str, Any]:
    metadata = metadata or {}
    normalized_storage_kind = str(storage_kind or "").strip().lower()
    normalized_domain = str(domain or "").strip().lower()
    if normalized_storage_kind == MEMODE_KIND:
        return {
            "kind": MEMODE_KIND,
            "entity_type": "memode",
            "speech_act_mode": PERFORMATIVE_MODE,
            "memetic_role": "second_order",
            "storage_kind": MEMODE_KIND,
        }
    if normalized_storage_kind != MEME_KIND:
        return {
            "kind": normalized_storage_kind or storage_kind,
            "entity_type": normalized_storage_kind or storage_kind or "runtime",
            "speech_act_mode": RUNTIME_MODE,
            "memetic_role": "non_memetic",
            "storage_kind": normalized_storage_kind or storage_kind or "runtime",
        }
    if normalized_domain == "behavior":
        explicit_entity_type = str(metadata.get("entity_type") or "").strip().lower()
        return {
            "kind": MEME_KIND,
            "entity_type": explicit_entity_type or "behavior_meme",
            "speech_act_mode": PERFORMATIVE_MODE,
            "memetic_role": "first_order",
            "storage_kind": MEME_KIND,
        }
    entity_type = infer_information_entity_type(
        label=label,
        metadata=metadata,
        outgoing_edge_types=outgoing_edge_types,
        incoming_edge_types=incoming_edge_types,
    )
    return {
        "kind": INFORMATION_KIND,
        "entity_type": entity_type,
        "speech_act_mode": CONSTATIVE_MODE,
        "memetic_role": "non_memetic",
        "storage_kind": MEME_KIND,
    }


def memode_materialization_allowed(domain: str) -> bool:
    return str(domain or "").strip().lower() == "behavior"


def memode_members_are_behavioral(member_ids: Iterable[str], node_lookup: dict[str, dict[str, Any]]) -> bool:
    ordered_ids = [str(member_id) for member_id in member_ids if str(member_id)]
    if len(ordered_ids) < 2:
        return False
    for member_id in ordered_ids:
        node = node_lookup.get(member_id) or {}
        if str(node.get("kind") or "") != MEME_KIND:
            return False
        if str(node.get("domain") or "").lower() != "behavior":
            return False
    return True
