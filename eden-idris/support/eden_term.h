#ifndef EDEN_TERM_H
#define EDEN_TERM_H

/* Low-level terminal I/O */
int eden_term_init(void);
void eden_term_cleanup(void);
void eden_term_rearm(void);
int eden_term_width(void);
int eden_term_height(void);
int eden_term_read_key(int timeout_ms);
void eden_term_write(char *s);
void eden_term_flush(void);

/* Paste drain: read all available chars with short timeout */
char *eden_term_drain_paste(int timeout_ms);

/* Mouse tracking (SGR mode) */
void eden_term_enable_mouse(void);
void eden_term_disable_mouse(void);
int eden_term_mouse_button(void);
int eden_term_mouse_col(void);
int eden_term_mouse_row(void);
int eden_term_mouse_press(void);

/* Subprocess execution — returns "<exit_code>\n<output>" */
char *eden_run_cmd(const char *cmd);

/* Cell-buffer screen compositor */
void eden_screen_init(int w, int h);
void eden_screen_set(int row, int col, int ch,
                     int fr, int fg, int fb,
                     int br, int bg, int bb,
                     int bold);
void eden_screen_clear(void);
void eden_screen_nebula(int row, int col, int w, int h,
                        int bgr, int bgg, int bgb);
void eden_screen_present(void);

#endif
