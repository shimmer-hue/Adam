from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LOG_DIR = REPO_ROOT / "logs"
EXPORT_DIR = REPO_ROOT / "exports"
DOCS_DIR = REPO_ROOT / "docs"
ASSETS_DIR = REPO_ROOT / "assets"
MODELS_DIR = REPO_ROOT / "models"
SEED_CANON_DIR = ASSETS_DIR / "seed_canon"
DB_PATH = DATA_DIR / "eden.db"
RUNTIME_LOG_PATH = LOG_DIR / "runtime.jsonl"
DEFAULT_MLX_MODEL_REPO = "RepublicOfKorokke/Qwen3.5-35B-A3B-mlx-lm-mxfp4"
DEFAULT_MLX_MODEL_LABEL = "Qwen 3.5 35B A3B"
DEFAULT_MLX_MODEL_BASE = "Qwen/Qwen3.5-35B-A3B"
DEFAULT_MLX_MODEL_DIRNAME = "qwen3.5-35b-a3b-mlx-mxfp4"
DEFAULT_MLX_MODEL_DIR = MODELS_DIR / DEFAULT_MLX_MODEL_DIRNAME
TANAKH_CACHE_DIR = DATA_DIR / "tanakh_cache"


@dataclass(slots=True)
class RegardWeights:
    reward: float = 1.25
    evidence: float = 0.75
    coherence: float = 0.95
    persistence: float = 0.8
    decay: float = 0.65
    isolation: float = 0.7
    risk: float = 1.1


@dataclass(slots=True)
class SelectionWeights:
    semantic_similarity: float = 1.2
    activation: float = 0.7
    regard: float = 0.95
    session_bias: float = 0.35
    explicit_feedback: float = 0.5
    scope_penalty: float = 0.4
    membrane_penalty: float = 0.75


@dataclass(slots=True)
class RuntimeSettings:
    model_backend: str = "mlx"
    model_path: str | None = str(DEFAULT_MLX_MODEL_DIR)
    max_context_items: int = 8
    retrieval_depth: int = 12
    ui_look: str = "amber_dark"
    low_motion: bool = False
    debug: bool = True
    observatory_host: str = "127.0.0.1"
    observatory_port: int = 8741
    observatory_port_span: int = 24
    regard_weights: RegardWeights = field(default_factory=RegardWeights)
    selection_weights: SelectionWeights = field(default_factory=SelectionWeights)


DEFAULT_SETTINGS = RuntimeSettings()
