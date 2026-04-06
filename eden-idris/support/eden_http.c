/*
 * eden_http.c -- Minimal HTTP server for the EDEN observatory.
 *
 * Single-threaded, blocking accept loop.  Read-only (GET only).
 * Sends CORS headers on every response.
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
 * eden_http_start  -- bind + listen on the given port
 * ================================================================ */

int eden_http_start(int port) {
#if defined(_WIN32) || defined(__MSYS__) || defined(__CYGWIN__)
    ensure_wsa();
#endif

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
 * Reads up to 8KB, parses "GET /path HTTP/1.x", returns the path.
 * Returns "" on error or non-GET.
 * Caller must free the returned string.
 * ================================================================ */

char *eden_http_read_request(int client_fd) {
    sock_t client = (sock_t)client_fd;
    char buf[8192];
    int n = (int)SOCK_RECV(client, buf, sizeof(buf) - 1);
    if (n <= 0) {
        char *empty = (char *)malloc(1);
        if (empty) empty[0] = '\0';
        return empty ? empty : "";
    }
    buf[n] = '\0';

    /* Parse "GET /path HTTP/..." */
    if (strncmp(buf, "GET ", 4) != 0) {
        /* Not a GET -- could be OPTIONS (CORS preflight) */
        if (strncmp(buf, "OPTIONS ", 8) == 0) {
            char *opt = (char *)malloc(9);
            if (opt) strcpy(opt, "OPTIONS");
            return opt ? opt : "";
        }
        char *empty = (char *)malloc(1);
        if (empty) empty[0] = '\0';
        return empty ? empty : "";
    }

    char *path_start = buf + 4;
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
        "Access-Control-Allow-Methods: GET, OPTIONS\r\n"
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
 * eden_http_close  -- close client connection
 * ================================================================ */

void eden_http_close(int client_fd) {
    sock_t client = (sock_t)client_fd;
    if (client != SOCK_INVALID) {
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
}
