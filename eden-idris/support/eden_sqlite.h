#ifndef EDEN_SQLITE_H
#define EDEN_SQLITE_H

#include <stdint.h>

/* Lifecycle */
void *eden_db_open(const char *path);
int   eden_db_close(void *db);
int   eden_db_init_schema(void *db);
int   eden_db_is_null(void *p);

/* Write functions — return 0 on success */
int eden_db_save_experiment(void *db,
    const char *id, const char *name, const char *slug,
    const char *mode, const char *status,
    const char *created_at, const char *updated_at);

int eden_db_save_session(void *db,
    const char *id, const char *experiment_id, const char *agent_id,
    const char *title, const char *created_at, const char *updated_at,
    const char *ended_at);

int eden_db_save_turn(void *db,
    const char *id, const char *experiment_id, const char *session_id,
    int64_t turn_index, const char *user_text, const char *prompt_context,
    const char *response_text, const char *membrane_text,
    const char *created_at);

int eden_db_save_meme(void *db,
    const char *id, const char *experiment_id,
    const char *label, const char *canonical_label, const char *text,
    const char *domain, const char *source_kind, const char *scope,
    double evidence_n, int64_t usage_count,
    double reward_ema, double risk_ema, double edit_ema,
    int64_t skip_count, int64_t contradiction_count,
    int64_t membrane_conflicts, int64_t feedback_count,
    double activation_tau,
    const char *last_active_at, const char *created_at, const char *updated_at);

/* Tab-separated line insert (for high-arity workaround via FFI) */
int eden_db_save_meme_tsv(void *db, const char *tsv_line);
int eden_db_save_memode_tsv(void *db, const char *tsv_line);

int eden_db_save_memode(void *db,
    const char *id, const char *experiment_id,
    const char *label, const char *member_hash, const char *summary,
    const char *domain, const char *scope,
    double evidence_n, int64_t usage_count,
    double reward_ema, double risk_ema, double edit_ema,
    int64_t feedback_count, double activation_tau,
    const char *last_active_at, const char *created_at, const char *updated_at);

int eden_db_save_edge(void *db,
    const char *id, const char *experiment_id,
    const char *src_kind, const char *src_id,
    const char *dst_kind, const char *dst_id,
    const char *edge_type, double weight,
    const char *created_at, const char *updated_at);

int eden_db_save_feedback(void *db,
    const char *id, const char *experiment_id,
    const char *session_id, const char *turn_id,
    const char *verdict, const char *explanation, const char *corrected,
    double sig_reward, double sig_risk, double sig_edit,
    const char *created_at);

int eden_db_save_membrane_event(void *db,
    const char *id, const char *event_type, const char *detail,
    const char *created_at);

int eden_db_save_trace_event(void *db,
    const char *id, const char *event_type, const char *level,
    const char *message, const char *created_at);

int eden_db_save_document(void *db,
    const char *id, const char *experiment_id,
    const char *path, const char *kind, const char *title,
    const char *sha256, const char *status, const char *created_at);

int eden_db_save_chunk(void *db,
    const char *id, const char *experiment_id, const char *document_id,
    int64_t chunk_index, int64_t page_number,
    const char *text, const char *created_at);

/* Targeted updates */
int eden_db_update_meme_channels(void *db,
    const char *id, double reward_ema, double risk_ema, double edit_ema);

int eden_db_update_meme_usage(void *db,
    const char *id, int64_t usage_count, const char *updated_at);

int eden_db_end_session(void *db, const char *id, const char *ended_at);

/* Load functions — return malloc'd strings, Idris runtime copies them.
   Format: newline-separated rows, tab-separated fields with type prefix.
   Matches Export.idr serialization format. */
char *eden_db_load_experiments(void *db);
char *eden_db_load_sessions(void *db);
char *eden_db_load_turns(void *db);
char *eden_db_load_memes(void *db);
char *eden_db_load_memodes(void *db);
char *eden_db_load_edges(void *db);
char *eden_db_load_feedback(void *db);

/* New entity saves */
int eden_db_save_agent(void *db,
    const char *id, const char *experiment_id,
    const char *name, const char *persona, const char *created_at);
int eden_db_save_active_set_tsv(void *db, const char *tsv_line);
int eden_db_save_measurement_event_tsv(void *db, const char *tsv_line);
int eden_db_save_export_artifact(void *db,
    const char *id, const char *experiment_id,
    const char *artifact_type, const char *path,
    const char *graph_hash, const char *created_at);
int eden_db_save_turn_metadata_tsv(void *db, const char *tsv_line);

/* New entity loads */
char *eden_db_load_agents(void *db);
char *eden_db_load_active_sets(void *db);
char *eden_db_load_turn_metadata(void *db);

/* Config store (for next_id persistence) */
int   eden_db_set_config(void *db, const char *key, const char *value);
char *eden_db_get_config(void *db, const char *key);

/* Transaction helpers */
int eden_db_begin(void *db);
int eden_db_commit(void *db);

#endif
