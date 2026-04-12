/* eden_sqlite.c — SQLite3 persistence for the EDEN graph store.
 *
 * FFI layer between Idris2 (via %foreign) and SQLite3.
 * Save functions use prepared statements with parameter binding.
 * Load functions return newline-separated rows of tab-separated fields
 * matching Eden.Export serialization format.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sqlite3.h>
#include "eden_sqlite.h"

/* ================================================================
 *  String buffer helpers
 * ================================================================ */

typedef struct { char *data; size_t len; size_t cap; } strbuf;

static void sb_init(strbuf *sb) {
    sb->cap = 4096;
    sb->data = (char *)malloc(sb->cap);
    sb->data[0] = '\0';
    sb->len = 0;
}

static void sb_ensure(strbuf *sb, size_t extra) {
    if (sb->len + extra + 1 > sb->cap) {
        while (sb->len + extra + 1 > sb->cap) sb->cap *= 2;
        sb->data = (char *)realloc(sb->data, sb->cap);
    }
}

static void sb_cat(strbuf *sb, const char *s) {
    size_t n = strlen(s);
    sb_ensure(sb, n);
    memcpy(sb->data + sb->len, s, n);
    sb->len += n;
    sb->data[sb->len] = '\0';
}

static void sb_ch(strbuf *sb, char c) {
    sb_ensure(sb, 1);
    sb->data[sb->len++] = c;
    sb->data[sb->len] = '\0';
}

/* Tab-sep field escaping (matches Eden.Export.escField). */
static void sb_esc(strbuf *sb, const char *s) {
    if (!s) return;
    for (; *s; s++) {
        switch (*s) {
            case '\t': sb_cat(sb, "\\t");  break;
            case '\n': sb_cat(sb, "\\n");  break;
            case '\\': sb_cat(sb, "\\\\"); break;
            default:   sb_ch(sb, *s);      break;
        }
    }
}

static void sb_tab(strbuf *sb) { sb_ch(sb, '\t'); }
static void sb_nl(strbuf *sb)  { sb_ch(sb, '\n'); }

static void sb_i64(strbuf *sb, int64_t v) {
    char buf[32];
    snprintf(buf, sizeof(buf), "%lld", (long long)v);
    sb_cat(sb, buf);
}

static void sb_dbl(strbuf *sb, double v) {
    char buf[64];
    snprintf(buf, sizeof(buf), "%.15g", v);
    sb_cat(sb, buf);
}

static const char *col_s(sqlite3_stmt *st, int c) {
    const char *v = (const char *)sqlite3_column_text(st, c);
    return v ? v : "";
}

/* ================================================================
 *  Lifecycle
 * ================================================================ */

void *eden_db_open(const char *path) {
    sqlite3 *db = NULL;
    if (sqlite3_open(path, &db) != SQLITE_OK) {
        fprintf(stderr, "[eden] db open: %s\n", db ? sqlite3_errmsg(db) : "?");
        if (db) sqlite3_close(db);
        return NULL;
    }
    sqlite3_exec(db, "PRAGMA journal_mode=WAL", NULL, NULL, NULL);
    sqlite3_exec(db, "PRAGMA synchronous=NORMAL", NULL, NULL, NULL);
    return db;
}

int eden_db_close(void *db) {
    return db && sqlite3_close((sqlite3 *)db) == SQLITE_OK ? 0 : -1;
}

int eden_db_is_null(void *p) {
    return p == NULL ? 1 : 0;
}

int eden_db_init_schema(void *db) {
    if (!db) return -1;
    const char *ddl =
        "CREATE TABLE IF NOT EXISTS experiments ("
        "id TEXT PRIMARY KEY,name TEXT,slug TEXT,mode TEXT,status TEXT,"
        "created_at TEXT,updated_at TEXT);"

        "CREATE TABLE IF NOT EXISTS sessions ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,agent_id TEXT,title TEXT,"
        "created_at TEXT,updated_at TEXT,ended_at TEXT);"

        "CREATE TABLE IF NOT EXISTS turns ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,session_id TEXT,"
        "turn_index INTEGER,user_text TEXT,prompt_context TEXT,"
        "response_text TEXT,membrane_text TEXT,created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS memes ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,"
        "label TEXT,canonical_label TEXT,text TEXT,"
        "domain TEXT,source_kind TEXT,scope TEXT,"
        "evidence_n REAL DEFAULT 0,usage_count INTEGER DEFAULT 0,"
        "reward_ema REAL DEFAULT 0,risk_ema REAL DEFAULT 0,edit_ema REAL DEFAULT 0,"
        "skip_count INTEGER DEFAULT 0,contradiction_count INTEGER DEFAULT 0,"
        "membrane_conflicts INTEGER DEFAULT 0,feedback_count INTEGER DEFAULT 0,"
        "activation_tau REAL DEFAULT 86400,"
        "last_active_at TEXT,created_at TEXT,updated_at TEXT);"

        "CREATE TABLE IF NOT EXISTS memodes ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,"
        "label TEXT,member_hash TEXT,summary TEXT,"
        "domain TEXT,scope TEXT,"
        "evidence_n REAL DEFAULT 0,usage_count INTEGER DEFAULT 0,"
        "reward_ema REAL DEFAULT 0,risk_ema REAL DEFAULT 0,edit_ema REAL DEFAULT 0,"
        "feedback_count INTEGER DEFAULT 0,activation_tau REAL DEFAULT 86400,"
        "last_active_at TEXT,created_at TEXT,updated_at TEXT);"

        "CREATE TABLE IF NOT EXISTS edges ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,"
        "src_kind TEXT,src_id TEXT,dst_kind TEXT,dst_id TEXT,"
        "edge_type TEXT,weight REAL DEFAULT 1,"
        "created_at TEXT,updated_at TEXT);"

        "CREATE TABLE IF NOT EXISTS feedback ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,"
        "session_id TEXT,turn_id TEXT,"
        "verdict TEXT,explanation TEXT,corrected TEXT,"
        "sig_reward REAL DEFAULT 0,sig_risk REAL DEFAULT 0,sig_edit REAL DEFAULT 0,"
        "created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS membrane_events ("
        "id TEXT PRIMARY KEY,event_type TEXT,detail TEXT,created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS trace_events ("
        "id TEXT PRIMARY KEY,event_type TEXT,level TEXT,message TEXT,"
        "created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS documents ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,"
        "path TEXT,kind TEXT,title TEXT,sha256 TEXT,status TEXT,"
        "created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS chunks ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,document_id TEXT,"
        "chunk_index INTEGER,page_number INTEGER,text TEXT,created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY,value TEXT);"

        "CREATE TABLE IF NOT EXISTS agents ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,name TEXT,persona TEXT,"
        "created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS active_sets ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,session_id TEXT,turn_id TEXT,"
        "node_kind TEXT,node_id TEXT,label TEXT,domain TEXT,"
        "selection_score REAL,semantic_sim REAL,activation REAL,regard REAL,"
        "created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS measurement_events ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,session_id TEXT,"
        "action_type TEXT,state TEXT,operator TEXT,evidence TEXT,"
        "before_state TEXT,proposed_state TEXT,committed_state TEXT,"
        "revert_of TEXT,created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS export_artifacts ("
        "id TEXT PRIMARY KEY,experiment_id TEXT,artifact_type TEXT,"
        "path TEXT,graph_hash TEXT,created_at TEXT);"

        "CREATE TABLE IF NOT EXISTS turn_metadata ("
        "turn_id TEXT PRIMARY KEY,inference_mode_req TEXT,inference_mode_eff TEXT,"
        "budget_mode TEXT,budget_pressure TEXT,"
        "budget_used_tokens INTEGER,budget_remaining_tokens INTEGER,"
        "active_set_size INTEGER,reasoning_text TEXT,"
        "temperature REAL,max_output INTEGER,response_cap INTEGER,"
        "created_at TEXT);";

    char *err = NULL;
    if (sqlite3_exec((sqlite3 *)db, ddl, NULL, NULL, &err) != SQLITE_OK) {
        fprintf(stderr, "[eden] schema: %s\n", err);
        sqlite3_free(err);
        return -1;
    }
    return 0;
}

/* ================================================================
 *  Save functions — INSERT OR REPLACE, return 0 on success
 * ================================================================ */

int eden_db_save_experiment(void *db,
    const char *id, const char *name, const char *slug,
    const char *mode, const char *status,
    const char *created_at, const char *updated_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO experiments "
        "(id,name,slug,mode,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, name, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, slug, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, mode, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, status, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, created_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, updated_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_session(void *db,
    const char *id, const char *experiment_id, const char *agent_id,
    const char *title, const char *created_at, const char *updated_at,
    const char *ended_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO sessions "
        "(id,experiment_id,agent_id,title,created_at,updated_at,ended_at) "
        "VALUES(?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, agent_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, title, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, created_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, updated_at, -1, SQLITE_TRANSIENT);
    if (ended_at && ended_at[0])
        sqlite3_bind_text(s, 7, ended_at, -1, SQLITE_TRANSIENT);
    else
        sqlite3_bind_null(s, 7);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_turn(void *db,
    const char *id, const char *experiment_id, const char *session_id,
    int64_t turn_index, const char *user_text, const char *prompt_context,
    const char *response_text, const char *membrane_text,
    const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO turns "
        "(id,experiment_id,session_id,turn_index,user_text,prompt_context,"
        "response_text,membrane_text,created_at) VALUES(?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, session_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int64(s, 4, turn_index);
    sqlite3_bind_text(s, 5, user_text, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, prompt_context, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, response_text, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 8, membrane_text, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 9, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_meme(void *db,
    const char *id, const char *experiment_id,
    const char *label, const char *canonical_label, const char *text,
    const char *domain, const char *source_kind, const char *scope,
    double evidence_n, int64_t usage_count,
    double reward_ema, double risk_ema, double edit_ema,
    int64_t skip_count, int64_t contradiction_count,
    int64_t membrane_conflicts, int64_t feedback_count,
    double activation_tau,
    const char *last_active_at, const char *created_at, const char *updated_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO memes "
        "(id,experiment_id,label,canonical_label,text,"
        "domain,source_kind,scope,"
        "evidence_n,usage_count,reward_ema,risk_ema,edit_ema,"
        "skip_count,contradiction_count,membrane_conflicts,feedback_count,"
        "activation_tau,last_active_at,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, label, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, canonical_label, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, text, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, domain, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, source_kind, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 8, scope, -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 9, evidence_n);
    sqlite3_bind_int64(s, 10, usage_count);
    sqlite3_bind_double(s, 11, reward_ema);
    sqlite3_bind_double(s, 12, risk_ema);
    sqlite3_bind_double(s, 13, edit_ema);
    sqlite3_bind_int64(s, 14, skip_count);
    sqlite3_bind_int64(s, 15, contradiction_count);
    sqlite3_bind_int64(s, 16, membrane_conflicts);
    sqlite3_bind_int64(s, 17, feedback_count);
    sqlite3_bind_double(s, 18, activation_tau);
    sqlite3_bind_text(s, 19, last_active_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 20, created_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 21, updated_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ── TSV-based save (workaround for RefC high-arity FFI limit) ── */

/* Split a tab-separated string into fields.  Returns field count.
   Fills ptrs[] with pointers into a MUTABLE COPY of the input.
   Caller must free the copy (returned via *buf). */
static int tsv_split(const char *line, char **buf, char **ptrs, int max_fields) {
    *buf = strdup(line);
    int n = 0;
    char *p = *buf;
    ptrs[n++] = p;
    while (*p && n < max_fields) {
        if (*p == '\t') { *p = '\0'; ptrs[n++] = p + 1; }
        p++;
    }
    return n;
}

static double tsv_dbl(const char *s) { return s ? atof(s) : 0.0; }
static int64_t tsv_i64(const char *s) { return s ? (int64_t)atoll(s) : 0; }

int eden_db_save_meme_tsv(void *db, const char *tsv_line) {
    if (!db || !tsv_line) return -1;
    char *buf; char *f[22]; /* fields: id eid label clabel text dom sk scope en uc rw rk ed sc cc mc fc at la ca ua */
    int n = tsv_split(tsv_line, &buf, f, 22);
    if (n < 21) { free(buf); return -1; }
    int rc = eden_db_save_meme(db, f[0], f[1], f[2], f[3], f[4],
        f[5], f[6], f[7],
        tsv_dbl(f[8]), tsv_i64(f[9]),
        tsv_dbl(f[10]), tsv_dbl(f[11]), tsv_dbl(f[12]),
        tsv_i64(f[13]), tsv_i64(f[14]), tsv_i64(f[15]), tsv_i64(f[16]),
        tsv_dbl(f[17]), f[18], f[19], f[20]);
    free(buf);
    return rc;
}

int eden_db_save_memode_tsv(void *db, const char *tsv_line) {
    if (!db || !tsv_line) return -1;
    char *buf; char *f[18];
    int n = tsv_split(tsv_line, &buf, f, 18);
    if (n < 17) { free(buf); return -1; }
    int rc = eden_db_save_memode(db, f[0], f[1], f[2], f[3], f[4],
        f[5], f[6],
        tsv_dbl(f[7]), tsv_i64(f[8]),
        tsv_dbl(f[9]), tsv_dbl(f[10]), tsv_dbl(f[11]),
        tsv_i64(f[12]), tsv_dbl(f[13]), f[14], f[15], f[16]);
    free(buf);
    return rc;
}

int eden_db_save_memode(void *db,
    const char *id, const char *experiment_id,
    const char *label, const char *member_hash, const char *summary,
    const char *domain, const char *scope,
    double evidence_n, int64_t usage_count,
    double reward_ema, double risk_ema, double edit_ema,
    int64_t feedback_count, double activation_tau,
    const char *last_active_at, const char *created_at, const char *updated_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO memodes "
        "(id,experiment_id,label,member_hash,summary,"
        "domain,scope,evidence_n,usage_count,"
        "reward_ema,risk_ema,edit_ema,feedback_count,activation_tau,"
        "last_active_at,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, label, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, member_hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, summary, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, domain, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, scope, -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 8, evidence_n);
    sqlite3_bind_int64(s, 9, usage_count);
    sqlite3_bind_double(s, 10, reward_ema);
    sqlite3_bind_double(s, 11, risk_ema);
    sqlite3_bind_double(s, 12, edit_ema);
    sqlite3_bind_int64(s, 13, feedback_count);
    sqlite3_bind_double(s, 14, activation_tau);
    sqlite3_bind_text(s, 15, last_active_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 16, created_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 17, updated_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_edge(void *db,
    const char *id, const char *experiment_id,
    const char *src_kind, const char *src_id,
    const char *dst_kind, const char *dst_id,
    const char *edge_type, double weight,
    const char *created_at, const char *updated_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO edges "
        "(id,experiment_id,src_kind,src_id,dst_kind,dst_id,"
        "edge_type,weight,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, src_kind, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, src_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, dst_kind, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, dst_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, edge_type, -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 8, weight);
    sqlite3_bind_text(s, 9, created_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 10, updated_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_feedback(void *db,
    const char *id, const char *experiment_id,
    const char *session_id, const char *turn_id,
    const char *verdict, const char *explanation, const char *corrected,
    double sig_reward, double sig_risk, double sig_edit,
    const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO feedback "
        "(id,experiment_id,session_id,turn_id,"
        "verdict,explanation,corrected,"
        "sig_reward,sig_risk,sig_edit,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, session_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, turn_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, verdict, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, explanation, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, corrected, -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 8, sig_reward);
    sqlite3_bind_double(s, 9, sig_risk);
    sqlite3_bind_double(s, 10, sig_edit);
    sqlite3_bind_text(s, 11, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_membrane_event(void *db,
    const char *id, const char *event_type, const char *detail,
    const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO membrane_events "
        "(id,event_type,detail,created_at) VALUES(?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, event_type, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, detail, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_trace_event(void *db,
    const char *id, const char *event_type, const char *level,
    const char *message, const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO trace_events "
        "(id,event_type,level,message,created_at) VALUES(?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, event_type, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, level, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, message, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_document(void *db,
    const char *id, const char *experiment_id,
    const char *path, const char *kind, const char *title,
    const char *sha256, const char *status, const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO documents "
        "(id,experiment_id,path,kind,title,sha256,status,created_at) "
        "VALUES(?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, path, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, kind, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, title, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, sha256, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, status, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 8, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_chunk(void *db,
    const char *id, const char *experiment_id, const char *document_id,
    int64_t chunk_index, int64_t page_number,
    const char *text, const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO chunks "
        "(id,experiment_id,document_id,chunk_index,page_number,text,created_at) "
        "VALUES(?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, document_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int64(s, 4, chunk_index);
    sqlite3_bind_int64(s, 5, page_number);
    sqlite3_bind_text(s, 6, text, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 7, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ================================================================
 *  Targeted updates
 * ================================================================ */

int eden_db_update_meme_channels(void *db,
    const char *id, double reward_ema, double risk_ema, double edit_ema)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "UPDATE memes SET reward_ema=?,risk_ema=?,edit_ema=? WHERE id=?";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_double(s, 1, reward_ema);
    sqlite3_bind_double(s, 2, risk_ema);
    sqlite3_bind_double(s, 3, edit_ema);
    sqlite3_bind_text(s, 4, id, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_update_meme_usage(void *db,
    const char *id, int64_t usage_count, const char *updated_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "UPDATE memes SET usage_count=?,updated_at=? WHERE id=?";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_int64(s, 1, usage_count);
    sqlite3_bind_text(s, 2, updated_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, id, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_end_session(void *db, const char *id, const char *ended_at) {
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "UPDATE sessions SET ended_at=? WHERE id=?";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, ended_at, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, id, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ================================================================
 *  Load functions — return malloc'd tab-separated strings
 *
 *  Format matches Eden.Export serialization:
 *    PREFIX\tfield1\tfield2\t...\n   (one row per entity)
 *  Text fields are escaped (tab→\t, newline→\n, backslash→\\).
 *  Idris runtime copies the string then the caller frees it.
 * ================================================================ */

char *eden_db_load_experiments(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,name,slug,mode,status,created_at,updated_at "
                      "FROM experiments";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "EXP");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));  /* id */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 1));  /* name */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 2));  /* slug */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 3));  /* mode */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));  /* status */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));  /* created_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));  /* updated_at */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_sessions(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,agent_id,title,"
                      "created_at,updated_at,ended_at FROM sessions";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "SESS");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));  /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));  /* experiment_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 2));  /* agent_id */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 3));  /* title */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));  /* created_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));  /* updated_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));  /* ended_at (empty if NULL) */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_turns(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,session_id,turn_index,"
                      "user_text,prompt_context,response_text,membrane_text,"
                      "created_at FROM turns ORDER BY turn_index";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "TURN");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));  /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));  /* experiment_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 2));  /* session_id */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 3)); /* turn_index */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 4));  /* user_text */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 5));  /* prompt_context */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 6));  /* response_text */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 7));  /* membrane_text */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 8));  /* created_at */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_memes(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    /* Note: canonical_label is NOT in serialized format — Idris recomputes it
       from label via toLower at deserialization time. */
    const char *sql = "SELECT id,experiment_id,label,text,"
        "domain,source_kind,scope,"
        "evidence_n,usage_count,reward_ema,risk_ema,edit_ema,"
        "skip_count,contradiction_count,membrane_conflicts,feedback_count,"
        "activation_tau,last_active_at,created_at,updated_at FROM memes";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "MEME");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));   /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));   /* experiment_id */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 2));   /* label */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 3));   /* text */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));   /* domain */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));   /* source_kind */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));   /* scope */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 7));  /* evidence_n */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 8));   /* usage_count */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 9));  /* reward_ema */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 10)); /* risk_ema */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 11)); /* edit_ema */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 12));  /* skip_count */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 13));  /* contradiction_count */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 14));  /* membrane_conflicts */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 15));  /* feedback_count */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 16)); /* activation_tau */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 17));  /* last_active_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 18));  /* created_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 19));  /* updated_at */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_memodes(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,label,member_hash,summary,"
        "domain,scope,evidence_n,usage_count,"
        "reward_ema,risk_ema,edit_ema,feedback_count,activation_tau,"
        "last_active_at,created_at,updated_at FROM memodes";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "MEMODE");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));   /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));   /* experiment_id */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 2));   /* label */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 3));   /* member_hash */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 4));   /* summary */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));   /* domain */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));   /* scope */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 7));  /* evidence_n */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 8));   /* usage_count */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 9));  /* reward_ema */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 10)); /* risk_ema */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 11)); /* edit_ema */
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 12));  /* feedback_count */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 13)); /* activation_tau */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 14));  /* last_active_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 15));  /* created_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 16));  /* updated_at */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_edges(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,src_kind,src_id,dst_kind,dst_id,"
                      "edge_type,weight,created_at,updated_at FROM edges";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "EDGE");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));  /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));  /* experiment_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 2));  /* src_kind */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 3));  /* src_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));  /* dst_kind */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));  /* dst_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));  /* edge_type */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 7)); /* weight */
        sb_tab(&sb); sb_cat(&sb, "");                         /* provenance_json */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 8));  /* created_at */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 9));  /* updated_at */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_feedback(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    /* Note: created_at is stored but NOT in serialized format
       (FeedbackRecord has no createdAt field). */
    const char *sql = "SELECT id,experiment_id,session_id,turn_id,"
                      "verdict,explanation,corrected,"
                      "sig_reward,sig_risk,sig_edit FROM feedback";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "FB");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));  /* id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));  /* experiment_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 2));  /* session_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 3));  /* turn_id */
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));  /* verdict */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 5));  /* explanation */
        sb_tab(&sb); sb_esc(&sb, col_s(s, 6));  /* corrected */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 7)); /* sig_reward */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 8)); /* sig_risk */
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 9)); /* sig_edit */
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

/* ================================================================
 *  Config store (for next_id persistence etc.)
 * ================================================================ */

int eden_db_set_config(void *db, const char *key, const char *value) {
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO config (key,value) VALUES(?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, key, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, value, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

char *eden_db_get_config(void *db, const char *key) {
    if (!db) {
        char *empty = (char *)malloc(1);
        empty[0] = '\0';
        return empty;
    }
    sqlite3_stmt *s;
    const char *sql = "SELECT value FROM config WHERE key=?";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) {
        char *empty = (char *)malloc(1);
        empty[0] = '\0';
        return empty;
    }
    sqlite3_bind_text(s, 1, key, -1, SQLITE_TRANSIENT);
    char *result;
    if (sqlite3_step(s) == SQLITE_ROW) {
        const char *v = col_s(s, 0);
        result = (char *)malloc(strlen(v) + 1);
        strcpy(result, v);
    } else {
        result = (char *)malloc(1);
        result[0] = '\0';
    }
    sqlite3_finalize(s);
    return result;
}

/* ================================================================
 *  New entity save functions (agents, active_sets, etc.)
 * ================================================================ */

int eden_db_save_agent(void *db,
    const char *id, const char *experiment_id,
    const char *name, const char *persona, const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO agents "
        "(id,experiment_id,name,persona,created_at) VALUES(?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, name, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, persona, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_active_set_tsv(void *db, const char *tsv_line) {
    if (!db || !tsv_line) return -1;
    char *buf; char *f[16];
    int n = tsv_split(tsv_line, &buf, f, 16);
    if (n < 13) { free(buf); return -1; }
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO active_sets "
        "(id,experiment_id,session_id,turn_id,node_kind,node_id,label,domain,"
        "selection_score,semantic_sim,activation,regard,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) {
        free(buf); return -1;
    }
    for (int i = 0; i < 8; i++)
        sqlite3_bind_text(s, i+1, f[i], -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 9, tsv_dbl(f[8]));
    sqlite3_bind_double(s, 10, tsv_dbl(f[9]));
    sqlite3_bind_double(s, 11, tsv_dbl(f[10]));
    sqlite3_bind_double(s, 12, tsv_dbl(f[11]));
    sqlite3_bind_text(s, 13, f[12], -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    free(buf);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_measurement_event_tsv(void *db, const char *tsv_line) {
    if (!db || !tsv_line) return -1;
    char *buf; char *f[16];
    int n = tsv_split(tsv_line, &buf, f, 16);
    if (n < 12) { free(buf); return -1; }
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO measurement_events "
        "(id,experiment_id,session_id,action_type,state,operator,evidence,"
        "before_state,proposed_state,committed_state,revert_of,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) {
        free(buf); return -1;
    }
    for (int i = 0; i < 12; i++)
        sqlite3_bind_text(s, i+1, f[i], -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    free(buf);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_export_artifact(void *db,
    const char *id, const char *experiment_id,
    const char *artifact_type, const char *path,
    const char *graph_hash, const char *created_at)
{
    if (!db) return -1;
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO export_artifacts "
        "(id,experiment_id,artifact_type,path,graph_hash,created_at) "
        "VALUES(?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) return -1;
    sqlite3_bind_text(s, 1, id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 3, artifact_type, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 4, path, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 5, graph_hash, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 6, created_at, -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    return rc == SQLITE_DONE ? 0 : -1;
}

int eden_db_save_turn_metadata_tsv(void *db, const char *tsv_line) {
    if (!db || !tsv_line) return -1;
    char *buf; char *f[16];
    int n = tsv_split(tsv_line, &buf, f, 16);
    if (n < 13) { free(buf); return -1; }
    sqlite3_stmt *s;
    const char *sql = "INSERT OR REPLACE INTO turn_metadata "
        "(turn_id,inference_mode_req,inference_mode_eff,"
        "budget_mode,budget_pressure,budget_used_tokens,budget_remaining_tokens,"
        "active_set_size,reasoning_text,temperature,max_output,response_cap,"
        "created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK) {
        free(buf); return -1;
    }
    for (int i = 0; i < 5; i++)
        sqlite3_bind_text(s, i+1, f[i], -1, SQLITE_TRANSIENT);
    sqlite3_bind_int64(s, 6, tsv_i64(f[5]));
    sqlite3_bind_int64(s, 7, tsv_i64(f[6]));
    sqlite3_bind_int64(s, 8, tsv_i64(f[7]));
    sqlite3_bind_text(s, 9, f[8], -1, SQLITE_TRANSIENT);
    sqlite3_bind_double(s, 10, tsv_dbl(f[9]));
    sqlite3_bind_int64(s, 11, tsv_i64(f[10]));
    sqlite3_bind_int64(s, 12, tsv_i64(f[11]));
    sqlite3_bind_text(s, 13, f[12], -1, SQLITE_TRANSIENT);
    int rc = sqlite3_step(s);
    sqlite3_finalize(s);
    free(buf);
    return rc == SQLITE_DONE ? 0 : -1;
}

/* ================================================================
 *  Load functions for new entities
 * ================================================================ */

char *eden_db_load_agents(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,name,persona,created_at FROM agents";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "AGENT");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 2));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 3));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 4));
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_active_sets(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,session_id,turn_id,"
        "node_kind,node_id,label,domain,"
        "selection_score,semantic_sim,activation,regard,created_at "
        "FROM active_sets ORDER BY turn_id,selection_score DESC";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "ASET");
        for (int i = 0; i < 8; i++) { sb_tab(&sb); sb_esc(&sb, col_s(s, i)); }
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 8));
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 9));
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 10));
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 11));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 12));
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_turn_metadata(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT turn_id,inference_mode_req,inference_mode_eff,"
        "budget_mode,budget_pressure,budget_used_tokens,budget_remaining_tokens,"
        "active_set_size,reasoning_text,temperature,max_output,response_cap,"
        "created_at FROM turn_metadata";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "TMETA");
        for (int i = 0; i < 5; i++) { sb_tab(&sb); sb_esc(&sb, col_s(s, i)); }
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 5));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 6));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 7));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 8));
        sb_tab(&sb); sb_dbl(&sb, sqlite3_column_double(s, 9));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 10));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 11));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 12));
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

/* ================================================================
 *  Transaction helpers
 * ================================================================ */

int eden_db_begin(void *db) {
    if (!db) return -1;
    return sqlite3_exec((sqlite3 *)db, "BEGIN", NULL, NULL, NULL) == SQLITE_OK ? 0 : -1;
}

int eden_db_commit(void *db) {
    if (!db) return -1;
    return sqlite3_exec((sqlite3 *)db, "COMMIT", NULL, NULL, NULL) == SQLITE_OK ? 0 : -1;
}

/* ================================================================
 *  Schema migration support
 * ================================================================ */

int eden_db_exec_sql(void *db, const char *sql) {
    if (!db || !sql) return -1;
    return sqlite3_exec((sqlite3 *)db, sql, NULL, NULL, NULL) == SQLITE_OK ? 0 : -1;
}

/* ================================================================
 *  Document SHA deduplication
 * ================================================================ */

int eden_db_document_exists_sha(void *db, const char *experiment_id, const char *sha256) {
    if (!db || !experiment_id || !sha256) return 0;
    sqlite3_stmt *s;
    const char *sql = "SELECT COUNT(*) FROM documents WHERE experiment_id=? AND sha256=?";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return 0;
    sqlite3_bind_text(s, 1, experiment_id, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(s, 2, sha256, -1, SQLITE_TRANSIENT);
    int count = 0;
    if (sqlite3_step(s) == SQLITE_ROW)
        count = sqlite3_column_int(s, 0);
    sqlite3_finalize(s);
    return count;
}

/* ================================================================
 *  Load functions for chunks, documents, measurement events
 * ================================================================ */

char *eden_db_load_chunks(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,document_id,chunk_index,page_number,text,created_at FROM chunks ORDER BY document_id,chunk_index";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "CHUNK");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 2));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 3));
        sb_tab(&sb); sb_i64(&sb, sqlite3_column_int64(s, 4));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 5));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_documents(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,path,kind,title,sha256,status,created_at FROM documents ORDER BY created_at";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "DOC");
        sb_tab(&sb); sb_cat(&sb, col_s(s, 0));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 1));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 2));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 3));
        sb_tab(&sb); sb_esc(&sb, col_s(s, 4));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 5));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 6));
        sb_tab(&sb); sb_cat(&sb, col_s(s, 7));
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}

char *eden_db_load_measurement_events(void *db) {
    strbuf sb; sb_init(&sb);
    if (!db) return sb.data;
    sqlite3_stmt *s;
    const char *sql = "SELECT id,experiment_id,session_id,action_type,state,operator,evidence,"
        "before_state,proposed_state,committed_state,revert_of,created_at "
        "FROM measurement_events ORDER BY created_at";
    if (sqlite3_prepare_v2((sqlite3*)db, sql, -1, &s, NULL) != SQLITE_OK)
        return sb.data;
    while (sqlite3_step(s) == SQLITE_ROW) {
        sb_cat(&sb, "MEAS");
        for (int i = 0; i < 12; i++) {
            sb_tab(&sb); sb_esc(&sb, col_s(s, i));
        }
        sb_nl(&sb);
    }
    sqlite3_finalize(s);
    return sb.data;
}
