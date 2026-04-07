/*
 * eden_http.c -- HTTP server for the EDEN observatory.
 *
 * Single-threaded, blocking accept loop.  Supports GET, POST, OPTIONS.
 * Sends CORS headers on every response.  SSE (Server-Sent Events)
 * support for live graph invalidation notifications.
 *
 * Platform:
 *   _WIN32 / __MSYS__ / __CYGWIN__  -> Winsock2
 *   else                            -> POSIX sockets
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "eden_http.h"

/* ================================================================
 * Platform socket abstraction
 * ================================================================ */

#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)

#include <winsock2.h>
#include <ws2tcpip.h>

/* Winsock needs explicit init/cleanup */
static int wsa_inited = 0;

static void ensure_wsa(void) {
    if (!wsa_inited) {
        WSADATA wsa;
        WSAStartup(MAKEWORD(2,2), &wsa);
        wsa_inited = 1;
    }
}

typedef SOCKET sock_t;
#define SOCK_INVALID INVALID_SOCKET
#define SOCK_ERROR   SOCKET_ERROR
#define CLOSESOCK(s) closesocket(s)
#define SOCK_SEND(s, buf, len) send((s), (buf), (int)(len), 0)
#define SOCK_RECV(s, buf, len) recv((s), (buf), (int)(len), 0)

#else /* POSIX */

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <errno.h>

typedef int sock_t;
#define SOCK_INVALID (-1)
#define SOCK_ERROR   (-1)
#define CLOSESOCK(s) close(s)
#define SOCK_SEND(s, buf, len) send((s), (buf), (size_t)(len), 0)
#define SOCK_RECV(s, buf, len) recv((s), (buf), (size_t)(len), 0)

#endif

/* ================================================================
 * SSE client tracking (max 8 concurrent SSE connections)
 * ================================================================ */

#define EDEN_SSE_MAX_CLIENTS 8

static sock_t sse_clients[EDEN_SSE_MAX_CLIENTS];
static int sse_client_count = 0;
static int sse_initialized = 0;

static void sse_init(void) {
    if (!sse_initialized) {
        for (int i = 0; i < EDEN_SSE_MAX_CLIENTS; i++) {
            sse_clients[i] = SOCK_INVALID;
        }
        sse_initialized = 1;
    }
}

/* ================================================================
 * Internal request buffer -- stores raw request for multi-pass parsing
 * ================================================================ */

#define EDEN_HTTP_REQBUF_SIZE 65536

static char  g_reqbuf[EDEN_HTTP_REQBUF_SIZE];
static int   g_reqbuf_len = 0;
static int   g_body_offset = 0;  /* offset where body begins in g_reqbuf */

/* ================================================================
 * eden_http_start  -- bind + listen on the given port
 * ================================================================ */

int eden_http_start(int port) {
#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)
    ensure_wsa();
#endif

    sse_init();

    sock_t srv = socket(AF_INET, SOCK_STREAM, 0);
    if (srv == SOCK_INVALID) return -1;

    /* Allow port reuse so restarts don't fail with EADDRINUSE */
    int opt = 1;
#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, (const char *)&opt, sizeof(opt));
#else
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family      = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port        = htons((unsigned short)port);

    if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) == SOCK_ERROR) {
        CLOSESOCK(srv);
        return -1;
    }

    if (listen(srv, 8) == SOCK_ERROR) {
        CLOSESOCK(srv);
        return -1;
    }

    return (int)srv;
}

/* ================================================================
 * eden_http_accept  -- block until a client connects
 * ================================================================ */

int eden_http_accept(int server_fd) {
    sock_t srv = (sock_t)server_fd;
    struct sockaddr_in cli;
    int cli_len = sizeof(cli);

#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)
    sock_t client = accept(srv, (struct sockaddr *)&cli, &cli_len);
#else
    socklen_t slen = (socklen_t)cli_len;
    sock_t client = accept(srv, (struct sockaddr *)&cli, &slen);
#endif

    if (client == SOCK_INVALID) return -1;
    return (int)client;
}

/* ================================================================
 * eden_http_read_request  -- read HTTP request, return path string
 *
 * Reads up to 64KB, parses "METHOD /path HTTP/1.x", returns the path.
 * Also stores the full request in g_reqbuf for subsequent parsing
 * of method, headers, and body.
 * Returns "" on error.
 * Caller must free the returned string.
 * ================================================================ */

char *eden_http_read_request(int client_fd) {
    sock_t client = (sock_t)client_fd;
    int n = (int)SOCK_RECV(client, g_reqbuf, EDEN_HTTP_REQBUF_SIZE - 1);
    if (n <= 0) {
        g_reqbuf_len = 0;
        g_body_offset = 0;
        char *empty = (char *)malloc(1);
        if (empty) empty[0] = '\0';
        return empty ? empty : "";
    }
    g_reqbuf[n] = '\0';
    g_reqbuf_len = n;

    /* Find end of headers (\r\n\r\n) to record body offset */
    g_body_offset = 0;
    char *hdr_end = strstr(g_reqbuf, "\r\n\r\n");
    if (hdr_end) {
        g_body_offset = (int)(hdr_end - g_reqbuf) + 4;
    }

    /* Parse method: GET, POST, OPTIONS */
    char *space1 = strchr(g_reqbuf, ' ');
    if (!space1) {
        char *empty = (char *)malloc(1);
        if (empty) empty[0] = '\0';
        return empty ? empty : "";
    }

    /* Handle OPTIONS */
    if (strncmp(g_reqbuf, "OPTIONS ", 8) == 0) {
        char *opt = (char *)malloc(8);
        if (opt) strcpy(opt, "OPTIONS");
        return opt ? opt : "";
    }

    /* For GET and POST, extract the path */
    char *path_start = space1 + 1;
    char *path_end   = strchr(path_start, ' ');
    if (!path_end) path_end = strchr(path_start, '\r');
    if (!path_end) path_end = strchr(path_start, '\n');
    if (!path_end) {
        char *empty = (char *)malloc(1);
        if (empty) empty[0] = '\0';
        return empty ? empty : "";
    }

    size_t path_len = (size_t)(path_end - path_start);
    char *path = (char *)malloc(path_len + 1);
    if (!path) return "";
    memcpy(path, path_start, path_len);
    path[path_len] = '\0';

    return path;
}

/* ================================================================
 * eden_http_get_method  -- return HTTP method from last request
 *
 * Returns "GET", "POST", "OPTIONS", or "" for unknown/error.
 * Caller must free the returned string.
 * ================================================================ */

char *eden_http_get_method(int client_fd) {
    (void)client_fd;
    const char *method = "";

    if (g_reqbuf_len > 0) {
        if (strncmp(g_reqbuf, "GET ", 4) == 0)     method = "GET";
        else if (strncmp(g_reqbuf, "POST ", 5) == 0) method = "POST";
        else if (strncmp(g_reqbuf, "OPTIONS ", 8) == 0) method = "OPTIONS";
    }

    char *result = (char *)malloc(strlen(method) + 1);
    if (result) strcpy(result, method);
    return result ? result : "";
}

/* ================================================================
 * eden_http_get_content_length  -- parse Content-Length header
 *
 * Returns the Content-Length value, or 0 if not present/parseable.
 * ================================================================ */

int eden_http_get_content_length(int client_fd) {
    (void)client_fd;

    if (g_reqbuf_len <= 0) return 0;

    /* Case-insensitive search for Content-Length header */
    const char *p = g_reqbuf;
    while (*p) {
        if ((*p == 'C' || *p == 'c') &&
            (strncmp(p, "Content-Length:", 15) == 0 ||
             strncmp(p, "content-length:", 15) == 0 ||
             strncmp(p, "Content-length:", 15) == 0)) {
            p += 15;
            while (*p == ' ') p++;
            return atoi(p);
        }
        /* Skip to next line */
        while (*p && *p != '\n') p++;
        if (*p == '\n') p++;
    }
    return 0;
}

/* ================================================================
 * eden_http_read_body  -- read POST body up to content_length bytes
 *
 * Uses data already buffered in g_reqbuf after the headers, and
 * reads additional data from the socket if needed.
 * Returns a malloc'd string. Caller must free.
 * ================================================================ */

char *eden_http_read_body(int client_fd, int content_length) {
    sock_t client = (sock_t)client_fd;

    if (content_length <= 0 || content_length > 1048576) {
        /* Cap at 1MB for safety */
        if (content_length > 1048576) content_length = 1048576;
        if (content_length <= 0) {
            char *empty = (char *)malloc(1);
            if (empty) empty[0] = '\0';
            return empty ? empty : "";
        }
    }

    char *body = (char *)malloc((size_t)content_length + 1);
    if (!body) return "";

    int already_have = 0;

    /* Copy any body data already in g_reqbuf */
    if (g_body_offset > 0 && g_body_offset < g_reqbuf_len) {
        already_have = g_reqbuf_len - g_body_offset;
        if (already_have > content_length) already_have = content_length;
        memcpy(body, g_reqbuf + g_body_offset, (size_t)already_have);
    }

    /* Read remaining body from socket if needed */
    int total = already_have;
    while (total < content_length) {
        int remaining = content_length - total;
        int r = (int)SOCK_RECV(client, body + total, remaining);
        if (r <= 0) break;
        total += r;
    }

    body[total] = '\0';
    return body;
}

/* ================================================================
 * eden_http_send_response  -- send HTTP 200 with CORS headers
 * ================================================================ */

void eden_http_send_response(int client_fd, const char *content_type, const char *body) {
    sock_t client = (sock_t)client_fd;
    size_t body_len = body ? strlen(body) : 0;

    /* Build header */
    char header[1024];
    int hlen = snprintf(header, sizeof(header),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "Access-Control-Allow-Headers: Content-Type\r\n"
        "Connection: close\r\n"
        "\r\n",
        content_type ? content_type : "text/plain",
        body_len);

    SOCK_SEND(client, header, hlen);
    if (body && body_len > 0) {
        /* Send body in chunks to handle large payloads */
        size_t sent = 0;
        while (sent < body_len) {
            size_t chunk = body_len - sent;
            if (chunk > 65536) chunk = 65536;
            int r = (int)SOCK_SEND(client, body + sent, chunk);
            if (r <= 0) break;
            sent += (size_t)r;
        }
    }
}

/* ================================================================
 * eden_http_send_sse_headers  -- send SSE headers, register client
 *
 * Sends the initial HTTP response headers for an SSE stream and
 * registers the client fd in the SSE client list.
 * Returns 1 on success, 0 if SSE slots are full.
 * ================================================================ */

int eden_http_send_sse_headers(int client_fd) {
    sock_t client = (sock_t)client_fd;

    sse_init();

    /* Find a free slot */
    int slot = -1;
    for (int i = 0; i < EDEN_SSE_MAX_CLIENTS; i++) {
        if (sse_clients[i] == SOCK_INVALID) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        /* No room -- evict oldest (slot 0) and shift */
        CLOSESOCK(sse_clients[0]);
        for (int i = 0; i < EDEN_SSE_MAX_CLIENTS - 1; i++) {
            sse_clients[i] = sse_clients[i + 1];
        }
        sse_clients[EDEN_SSE_MAX_CLIENTS - 1] = SOCK_INVALID;
        slot = EDEN_SSE_MAX_CLIENTS - 1;
    }

    /* Send SSE response headers */
    const char *headers =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/event-stream\r\n"
        "Cache-Control: no-cache\r\n"
        "Connection: keep-alive\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "Access-Control-Allow-Headers: Content-Type\r\n"
        "\r\n";

    int r = (int)SOCK_SEND(client, headers, strlen(headers));
    if (r <= 0) return 0;

    /* Send an initial comment to confirm the stream */
    const char *init_msg = ": connected\n\n";
    SOCK_SEND(client, init_msg, strlen(init_msg));

    sse_clients[slot] = client;
    if (slot >= sse_client_count) {
        sse_client_count = slot + 1;
    }

    return 1;
}

/* ================================================================
 * eden_http_send_sse  -- push an SSE event to all connected clients
 *
 * Sends "event: <event>\ndata: <data>\n\n" to each registered
 * SSE client. Removes disconnected clients.
 * ================================================================ */

void eden_http_send_sse(const char *event, const char *data) {
    if (!sse_initialized) return;

    /* Build the SSE message */
    size_t evt_len  = event ? strlen(event) : 0;
    size_t data_len = data  ? strlen(data)  : 0;
    /* "event: " + event + "\ndata: " + data + "\n\n" + NUL */
    size_t msg_len = 7 + evt_len + 7 + data_len + 2 + 1;
    char *msg = (char *)malloc(msg_len);
    if (!msg) return;

    snprintf(msg, msg_len, "event: %s\ndata: %s\n\n",
             event ? event : "message",
             data  ? data  : "{}");

    size_t actual_len = strlen(msg);

    for (int i = 0; i < EDEN_SSE_MAX_CLIENTS; i++) {
        if (sse_clients[i] != SOCK_INVALID) {
            int r = (int)SOCK_SEND(sse_clients[i], msg, actual_len);
            if (r <= 0) {
                /* Client disconnected -- remove it */
                CLOSESOCK(sse_clients[i]);
                sse_clients[i] = SOCK_INVALID;
            }
        }
    }

    free(msg);
}

/* ================================================================
 * eden_http_close  -- close client connection
 * ================================================================ */

void eden_http_close(int client_fd) {
    sock_t client = (sock_t)client_fd;
    if (client != SOCK_INVALID) {
        /* Check if this is an SSE client -- if so, don't close it */
        for (int i = 0; i < EDEN_SSE_MAX_CLIENTS; i++) {
            if (sse_clients[i] == client) {
                /* SSE client -- leave it open */
                return;
            }
        }

        /* Graceful shutdown */
#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)
        shutdown(client, SD_BOTH);
#else
        shutdown(client, SHUT_RDWR);
#endif
        CLOSESOCK(client);
    }
}

/* ================================================================
 * eden_http_stop  -- close server socket
 * ================================================================ */

void eden_http_stop(int server_fd) {
    sock_t srv = (sock_t)server_fd;
    if (srv != SOCK_INVALID) {
        CLOSESOCK(srv);
    }

    /* Close all SSE clients */
    for (int i = 0; i < EDEN_SSE_MAX_CLIENTS; i++) {
        if (sse_clients[i] != SOCK_INVALID) {
            CLOSESOCK(sse_clients[i]);
            sse_clients[i] = SOCK_INVALID;
        }
    }
    sse_client_count = 0;
}
