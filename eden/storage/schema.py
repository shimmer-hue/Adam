from __future__ import annotations


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ended_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    user_text TEXT NOT NULL,
    prompt_context TEXT NOT NULL,
    response_text TEXT NOT NULL,
    membrane_text TEXT NOT NULL,
    active_set_json TEXT NOT NULL DEFAULT '[]',
    trace_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(session_id, turn_index)
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    corrected_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    signal_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    text TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS memes (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    canonical_label TEXT NOT NULL,
    text TEXT NOT NULL,
    domain TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    evidence_n REAL NOT NULL DEFAULT 0,
    usage_count INTEGER NOT NULL DEFAULT 0,
    reward_ema REAL NOT NULL DEFAULT 0,
    risk_ema REAL NOT NULL DEFAULT 0,
    edit_ema REAL NOT NULL DEFAULT 0,
    skip_count INTEGER NOT NULL DEFAULT 0,
    contradiction_count INTEGER NOT NULL DEFAULT 0,
    membrane_conflicts INTEGER NOT NULL DEFAULT 0,
    feedback_count INTEGER NOT NULL DEFAULT 0,
    activation_tau REAL NOT NULL DEFAULT 86400,
    last_active_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(experiment_id, canonical_label, domain)
);

CREATE TABLE IF NOT EXISTS memodes (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    member_hash TEXT NOT NULL,
    summary TEXT NOT NULL,
    domain TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    evidence_n REAL NOT NULL DEFAULT 0,
    usage_count INTEGER NOT NULL DEFAULT 0,
    reward_ema REAL NOT NULL DEFAULT 0,
    risk_ema REAL NOT NULL DEFAULT 0,
    edit_ema REAL NOT NULL DEFAULT 0,
    feedback_count INTEGER NOT NULL DEFAULT 0,
    activation_tau REAL NOT NULL DEFAULT 172800,
    last_active_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(experiment_id, member_hash, domain)
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    src_kind TEXT NOT NULL,
    src_id TEXT NOT NULL,
    dst_kind TEXT NOT NULL,
    dst_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(experiment_id, src_kind, src_id, dst_kind, dst_id, edge_type)
);

CREATE TABLE IF NOT EXISTS active_sets (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_id TEXT NOT NULL REFERENCES turns(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    items_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trace_events (
    id TEXT PRIMARY KEY,
    experiment_id TEXT REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    turn_id TEXT REFERENCES turns(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS membrane_events (
    id TEXT PRIMARY KEY,
    experiment_id TEXT REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    turn_id TEXT REFERENCES turns(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    detail TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS export_artifacts (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL,
    path TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS measurement_events (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
    turn_id TEXT REFERENCES turns(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    target_ids_json TEXT NOT NULL DEFAULT '[]',
    before_state_json TEXT NOT NULL DEFAULT '{}',
    proposed_state_json TEXT NOT NULL DEFAULT '{}',
    committed_state_json TEXT NOT NULL DEFAULT '{}',
    rationale TEXT NOT NULL DEFAULT '',
    operator_label TEXT NOT NULL DEFAULT '',
    evidence_label TEXT NOT NULL DEFAULT 'SPECULATIVE',
    measurement_method TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    reverted_from_event_id TEXT REFERENCES measurement_events(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS config_store (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS meme_fts USING fts5(
    meme_id UNINDEXED,
    label,
    text,
    domain,
    tokenize = 'porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memode_fts USING fts5(
    memode_id UNINDEXED,
    label,
    summary,
    domain,
    tokenize = 'porter unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
    chunk_id UNINDEXED,
    title,
    text,
    tokenize = 'porter unicode61'
);

CREATE INDEX IF NOT EXISTS idx_sessions_experiment ON sessions(experiment_id);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_feedback_turn ON feedback_events(turn_id);
CREATE INDEX IF NOT EXISTS idx_documents_experiment ON documents(experiment_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_memes_experiment ON memes(experiment_id, domain);
CREATE INDEX IF NOT EXISTS idx_memodes_experiment ON memodes(experiment_id, domain);
CREATE INDEX IF NOT EXISTS idx_edges_experiment ON edges(experiment_id, edge_type);
CREATE INDEX IF NOT EXISTS idx_trace_experiment ON trace_events(experiment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_measurement_events_experiment ON measurement_events(experiment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_measurement_events_reverted_from ON measurement_events(reverted_from_event_id);
"""
