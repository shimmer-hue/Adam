#ifndef EDEN_HTTP_H
#define EDEN_HTTP_H

/* Minimal HTTP server for the EDEN observatory.
 * Single-threaded, blocking, read-only.
 * Platform: Winsock2 on Windows/MinGW, POSIX sockets elsewhere. */

int   eden_http_start(int port);
int   eden_http_accept(int server_fd);
char *eden_http_read_request(int client_fd);
void  eden_http_send_response(int client_fd, const char *content_type, const char *body);
void  eden_http_close(int client_fd);
void  eden_http_stop(int server_fd);

#endif
