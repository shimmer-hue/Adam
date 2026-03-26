from __future__ import annotations

from ..semantic_relations import MEMODE_MEMBERSHIP_EDGE_TYPE
from ..utils import sha256_text

OBSERVATORY_GRAPH_SCHEMA_VERSION = 5
OBSERVATORY_BASIN_SCHEMA_VERSION = 2
OBSERVATORY_CLUSTER_ALGORITHM = "louvain"
OBSERVATORY_CLUSTER_RESOLUTION = 1.0
OBSERVATORY_CLUSTER_SEED = 1729
OBSERVATORY_CLUSTER_TOKENIZER_VERSION = "tokenize:v1"
OBSERVATORY_CLUSTER_LABELER_VERSION = "labeler:v1"
OBSERVATORY_CLUSTER_CENTRALITY_VERSION = "degree:v1"
OBSERVATORY_CLUSTER_STOPWORDS_VERSION = sha256_text("|".join(sorted({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "with",
})))[:12]
OBSERVATORY_CLUSTER_ALGORITHM_VERSION = (
    f"{OBSERVATORY_CLUSTER_ALGORITHM}:seed={OBSERVATORY_CLUSTER_SEED}:"
    f"resolution={OBSERVATORY_CLUSTER_RESOLUTION}:"
    f"tokenizer={OBSERVATORY_CLUSTER_TOKENIZER_VERSION}:"
    f"stopwords={OBSERVATORY_CLUSTER_STOPWORDS_VERSION}:"
    f"labeler={OBSERVATORY_CLUSTER_LABELER_VERSION}:"
    f"centrality={OBSERVATORY_CLUSTER_CENTRALITY_VERSION}"
)

MEMODE_SUPPORT_EDGE_ALLOWLIST = {
    "CO_OCCURS_WITH",
    "REINFORCES",
    "SUPPORTS",
    "REFINES",
    "CONTRADICTS",
}
MEMODE_SUPPORT_EDGE_DENYLIST = {
    "BELONGS_TO_AGENT",
    "BELONGS_TO_SESSION",
    "FED_BACK_BY",
    "MATERIALIZES_AS_MEMODE",
    MEMODE_MEMBERSHIP_EDGE_TYPE,
    "DERIVED_FROM",
}

GRAPH_UI_MODES = [
    "Semantic Map",
    "Assemblies",
    "Runtime",
    "Active Set",
    "Compare",
]

ASSEMBLY_RENDER_MODES = ["hulls", "collapsed-meta-node", "hidden"]

BASIN_LIFT_MODES = ["flat", "time_lift", "density_lift", "session_offset"]

DETACHED_TRANSFER_STATUS = "detached"
EXACT_TRANSFER_STATUS = "exact"
TRANSFERRED_TRANSFER_STATUS = "transferred"
NONE_TRANSFER_STATUS = "none"
