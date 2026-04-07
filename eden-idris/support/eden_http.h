#ifndef EDEN_HTTP_H
#define EDEN_HTTP_H

/* HTTP server for the EDEN observatory.
 * Single-threaded, blocking.  Supports GET, POST, OPTIONS.
 * SSE for live graph invalidation.
 * Platform: Winsock2 on Windows/MinGW, POSIX sockets elsewhere. */

int   eden_http_start(int port);
int   eden_http_accept(int server_fd);
char *eden_http_read_request(int client_fd);
char *eden_http_get_method(int client_fd);
int   eden_http_get_content_length(int client_fd);
char *eden_http_read_body(int client_fd, int content_length);
void  eden_http_send_response(int client_fd, const char *content_type, const char *body);
int   eden_http_send_sse_headers(int client_fd);
void  eden_http_send_sse(const char *event, const char *data);
void  eden_http_close(int client_fd);
void  eden_http_stop(int server_fd);

#endif
