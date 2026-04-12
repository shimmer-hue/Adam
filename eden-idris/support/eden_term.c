/*
 * eden_term.c — Terminal I/O + cell-buffer compositor for EDEN TUI.
 *
 * Two layers:
 *   1. Low-level: raw mode, key reading (platform-specific)
 *   2. Screen buffer: 2D cell grid with diff-based rendering (shared)
 *
 * Platform:
 *   __MSYS__ / __CYGWIN__  -> POSIX termios
 *   _WIN32 (MinGW/MSVC)    -> Reader thread + ring buffer
 *   else                   -> POSIX termios (macOS, Linux)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

#ifndef _WIN32
#include <sys/wait.h>   /* WIFEXITED, WEXITSTATUS — needed on macOS */
#endif

/* Forward declarations — defined in platform sections below. */
void eden_term_rearm(void);
#ifdef _WIN32
#include <windows.h>
#include <io.h>
#include <fcntl.h>
/* Variables — declared here, defined/initialized in the Win32 section below. */
static int raw_active = 0;
static volatile int reader_running = 0;
static HANDLE reader_thread = NULL;
/* Ring buffer + reader thread forward declarations (used by eden_run_cmd) */
static int ring_empty(void);
static int ring_pop(void);
static DWORD WINAPI reader_fn(LPVOID arg);
#endif

/* ================================================================== */
/* Subprocess execution                                                */
/* ================================================================== */

/*
 * Run a shell command and capture its stdout.
 * Returns a malloc'd string with exit code on the first line,
 * followed by a newline, then the command output.
 * Format: "<exit_code>\n<output>"
 * Caller must free the returned string.
 *
 * On Win32 (TUI mode), pauses the reader thread before popen and restarts
 * it after pclose.  This prevents the reader thread from competing with
 * the child process for stdin and avoids console mode corruption.
 */
char *eden_run_cmd(const char *cmd) {
#ifdef _WIN32
    /* Pause reader thread before popen to avoid CRT fd-table contention.
     * ReadFile (used by reader_fn) is cancellable via CancelSynchronousIo,
     * so the thread exits cleanly — no TerminateThread needed. */
    int had_reader = 0;
    if (raw_active && reader_running && reader_thread) {
        had_reader = 1;
        reader_running = 0;
        CancelSynchronousIo(reader_thread);
        WaitForSingleObject(reader_thread, 1000);
        CloseHandle(reader_thread);
        reader_thread = NULL;
    }
#endif

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        char *err = malloc(32);
        if (err) strcpy(err, "-1\n(popen failed)");
#ifdef _WIN32
        if (had_reader) {
            eden_term_rearm();
            while (!ring_empty()) ring_pop();
            reader_running = 1;
            reader_thread = CreateThread(NULL, 0, reader_fn, NULL, 0, NULL);
        }
#endif
        return err ? err : "";
    }

    /* Reserve space for exit code prefix */
    size_t cap = 4096, len = 0;
    char *body = malloc(cap);
    if (!body) { pclose(fp); return ""; }

    char tmp[1024];
    while (fgets(tmp, sizeof(tmp), fp)) {
        size_t tl = strlen(tmp);
        if (len + tl + 1 > cap) {
            cap *= 2;
            char *nb = realloc(body, cap);
            if (!nb) break;
            body = nb;
        }
        memcpy(body + len, tmp, tl);
        len += tl;
    }
    body[len] = '\0';

    int status = pclose(fp);

#ifdef _WIN32
    int code = status;
    if (had_reader) {
        eden_term_rearm();
        while (!ring_empty()) ring_pop();
        reader_running = 1;
        reader_thread = CreateThread(NULL, 0, reader_fn, NULL, 0, NULL);
    }
#else
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    eden_term_rearm();
#endif

    /* Build result: "<code>\n<body>" */
    char prefix[24];
    int plen = snprintf(prefix, sizeof(prefix), "%d\n", code);
    char *result = malloc(plen + len + 1);
    if (!result) { free(body); return ""; }
    memcpy(result, prefix, plen);
    memcpy(result + plen, body, len + 1);
    free(body);
    return result;
}

/* ================================================================== */
/* Layer 1: Platform-specific terminal I/O                            */
/* ================================================================== */

#if defined(__MSYS__) || defined(__CYGWIN__) || (!defined(_WIN32))

#include <sys/ioctl.h>
#include <termios.h>
#include <unistd.h>

static struct termios orig_termios;
static int raw_active = 0;

int eden_term_init(void) {
    if (raw_active) return 0;
    if (tcgetattr(STDIN_FILENO, &orig_termios) == -1) return -1;
    struct termios raw = orig_termios;
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= CS8;
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw) == -1) return -1;
    raw_active = 1;
    return 0;
}

void eden_term_cleanup(void) {
    if (raw_active) {
        tcsetattr(STDIN_FILENO, TCSAFLUSH, &orig_termios);
        raw_active = 0;
    }
}

/* Re-apply raw mode after a subprocess may have reset termios. */
void eden_term_rearm(void) {
    if (!raw_active) return;
    struct termios raw;
    tcgetattr(STDIN_FILENO, &raw);
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= CS8;
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw);
}

int eden_term_width(void) {
    struct winsize ws;
    return (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) != -1) ? ws.ws_col : 80;
}

int eden_term_height(void) {
    struct winsize ws;
    return (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) != -1) ? ws.ws_row : 24;
}

static int read_byte(int timeout_ms) {
    struct termios t;
    if (tcgetattr(STDIN_FILENO, &t) == 0) {
        t.c_cc[VMIN] = 0;
        t.c_cc[VTIME] = (timeout_ms > 0) ? ((timeout_ms + 99) / 100) : 0;
        tcsetattr(STDIN_FILENO, TCSANOW, &t);
    }
    unsigned char c;
    return (read(STDIN_FILENO, &c, 1) == 1) ? (int)c : -1;
}

#else  /* _WIN32 */

/* windows.h, io.h, fcntl.h already included via forward declarations above.
 * raw_active, reader_running, reader_thread also declared above. */

#define RING_SIZE 256

static unsigned char  ring_buf[RING_SIZE];
static volatile LONG  ring_head = 0, ring_tail = 0;
static HANDLE         has_data;
static int            is_console = 0;
static HANDLE         hOut = INVALID_HANDLE_VALUE;
static DWORD          orig_out_mode = 0;
static UINT           orig_output_cp = 0;
static UINT           orig_input_cp = 0;

static int ring_empty(void) { return ring_head == ring_tail; }

static void ring_push(unsigned char c) {
    LONG h = ring_head;
    LONG next = (h + 1) % RING_SIZE;
    if (next == ring_tail) return;
    ring_buf[h] = c;
    InterlockedExchange(&ring_head, next);
    SetEvent(has_data);
}

static int ring_pop(void) {
    if (ring_empty()) return -1;
    LONG t = ring_tail;
    int c = (int)ring_buf[t];
    InterlockedExchange(&ring_tail, (t + 1) % RING_SIZE);
    if (ring_empty()) ResetEvent(has_data);
    return c;
}

static DWORD WINAPI reader_fn(LPVOID arg) {
    (void)arg;
    HANDLE hIn = GetStdHandle(STD_INPUT_HANDLE);
    DWORD ftype = GetFileType(hIn);
    if (ftype == FILE_TYPE_PIPE) {
        /* Pipe stdin (mintty / MSYS2 pty): non-blocking poll.
         * PeekNamedPipe checks for available data without blocking,
         * so the thread can exit within ~2ms when reader_running = 0. */
        while (reader_running) {
            DWORD avail = 0;
            if (PeekNamedPipe(hIn, NULL, 0, NULL, &avail, NULL) && avail > 0) {
                unsigned char c;
                DWORD nRead = 0;
                if (ReadFile(hIn, &c, 1, &nRead, NULL) && nRead == 1)
                    ring_push(c);
            } else {
                Sleep(2);
            }
        }
    } else {
        /* Console stdin (cmd.exe, Windows Terminal): use ReadFile.
         * CancelSynchronousIo can cancel this cleanly. */
        while (reader_running) {
            unsigned char c;
            DWORD nRead = 0;
            BOOL ok = ReadFile(hIn, &c, 1, &nRead, NULL);
            if (ok && nRead == 1) ring_push(c);
            else if (!reader_running) break;
            else Sleep(1);
        }
    }
    return 0;
}

static volatile int got_signal = 0;
static void signal_handler(int sig) { (void)sig; got_signal = 1; }

int eden_term_init(void) {
    if (raw_active) return 0;
    signal(SIGINT, signal_handler);
    signal(SIGBREAK, signal_handler);
    /* Set console code pages to UTF-8 before any I/O.
     * Required for ConPTY/winpty bridges (MSYS2/mintty) which interpret
     * output bytes according to the console code page. Without this,
     * multi-byte UTF-8 sequences (e.g. box-drawing chars) are garbled. */
    orig_output_cp = GetConsoleOutputCP();
    orig_input_cp = GetConsoleCP();
    SetConsoleOutputCP(65001);
    SetConsoleCP(65001);
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
    hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD m;
    is_console = GetConsoleMode(hOut, &m);
    if (is_console) {
        orig_out_mode = m;
        SetConsoleMode(hOut, m | 0x0004);
        HANDLE hIn = GetStdHandle(STD_INPUT_HANDLE);
        DWORD im;
        if (GetConsoleMode(hIn, &im))
            SetConsoleMode(hIn, (im & ~(ENABLE_LINE_INPUT|ENABLE_ECHO_INPUT|ENABLE_PROCESSED_INPUT)) | 0x0200);
    }
    has_data = CreateEvent(NULL, TRUE, FALSE, NULL);
    reader_running = 1;
    reader_thread = CreateThread(NULL, 0, reader_fn, NULL, 0, NULL);
    raw_active = 1;
    return 0;
}

void eden_term_cleanup(void) {
    if (!raw_active) return;
    reader_running = 0;
    if (reader_thread) { TerminateThread(reader_thread, 0); CloseHandle(reader_thread); reader_thread = NULL; }
    if (has_data) { CloseHandle(has_data); has_data = NULL; }
    if (is_console && hOut != INVALID_HANDLE_VALUE) SetConsoleMode(hOut, orig_out_mode);
    if (orig_output_cp) SetConsoleOutputCP(orig_output_cp);
    if (orig_input_cp) SetConsoleCP(orig_input_cp);
    signal(SIGINT, SIG_DFL);
    raw_active = 0;
}

/* Re-apply raw console mode after a subprocess may have reset it.
 * Also cancels any pending blocking _read in the reader thread so it
 * picks up the restored console mode immediately. */
void eden_term_rearm(void) {
    if (!raw_active) return;
    SetConsoleOutputCP(65001);
    SetConsoleCP(65001);
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
    if (is_console) {
        HANDLE hIn = GetStdHandle(STD_INPUT_HANDLE);
        DWORD im;
        if (GetConsoleMode(hIn, &im))
            SetConsoleMode(hIn, (im & ~(ENABLE_LINE_INPUT|ENABLE_ECHO_INPUT|ENABLE_PROCESSED_INPUT)) | 0x0200);
        DWORD m;
        if (GetConsoleMode(hOut, &m))
            SetConsoleMode(hOut, m | 0x0004);
    }
    /* Cancel any pending _read in the reader thread so it restarts
     * with the restored console mode. */
    if (reader_thread)
        CancelSynchronousIo(reader_thread);
    /* Drain stale bytes from the ring buffer */
    while (!ring_empty()) ring_pop();
}

int eden_term_width(void) {
    if (is_console) {
        CONSOLE_SCREEN_BUFFER_INFO i;
        if (GetConsoleScreenBufferInfo(hOut, &i))
            return i.srWindow.Right - i.srWindow.Left + 1;
    }
    char *e = getenv("COLUMNS");
    return e ? atoi(e) : 120;
}

int eden_term_height(void) {
    if (is_console) {
        CONSOLE_SCREEN_BUFFER_INFO i;
        if (GetConsoleScreenBufferInfo(hOut, &i))
            return i.srWindow.Bottom - i.srWindow.Top + 1;
    }
    char *e = getenv("LINES");
    return e ? atoi(e) : 30;
}

static int read_byte(int timeout_ms) {
    if (got_signal) { got_signal = 0; return 3; }
    int c = ring_pop();
    if (c >= 0) return c;
    DWORD wait = (timeout_ms > 0) ? (DWORD)timeout_ms : 0;
    if (WaitForSingleObject(has_data, wait) != WAIT_OBJECT_0) return -1;
    return ring_pop();
}

#endif /* _WIN32 */

/* ================================================================== */
/* Mouse tracking (SGR mode 1006)                                     */
/* ================================================================== */

/* Last mouse event data (read by FFI after key code indicates mouse) */
static volatile int mouse_button = 0;
static volatile int mouse_col = 0;
static volatile int mouse_row = 0;
static volatile int mouse_press = 0;  /* 1=press, 0=release */

/* Read last mouse event fields */
int eden_term_mouse_button(void) { return mouse_button; }
int eden_term_mouse_col(void)    { return mouse_col; }
int eden_term_mouse_row(void)    { return mouse_row; }
int eden_term_mouse_press(void)  { return mouse_press; }

/* Parse an SGR mouse sequence: ESC [ < button ; col ; row M/m
 * Returns 1 if successfully parsed, 0 otherwise.
 * Consumes bytes from the input. */
static int parse_sgr_mouse(void) {
    /* Already consumed ESC [ <, now read button;col;row;M/m */
    int nums[3] = {0, 0, 0};
    int ni = 0;
    while (ni < 3) {
        int c = read_byte(100);
        if (c < 0) return 0;
        if (c >= '0' && c <= '9') {
            nums[ni] = nums[ni] * 10 + (c - '0');
        } else if (c == ';') {
            ni++;
        } else if (c == 'M' || c == 'm') {
            if (ni == 2) {
                mouse_button = nums[0];
                mouse_col = nums[1];
                mouse_row = nums[2];
                mouse_press = (c == 'M') ? 1 : 0;
                return 1;
            }
            return 0;
        } else {
            return 0;
        }
    }
    /* If we got here with ni==3, read the terminator */
    {
        int c = read_byte(100);
        if (c == 'M' || c == 'm') {
            mouse_button = nums[0];
            mouse_col = nums[1];
            mouse_row = nums[2];
            mouse_press = (c == 'M') ? 1 : 0;
            return 1;
        }
    }
    return 0;
}

/* ================================================================== */
/* Shared: ANSI key parser                                            */
/* ================================================================== */

int eden_term_read_key(int timeout_ms) {
    int c = read_byte(timeout_ms);
    if (c < 0) return -1;
    if (c >= 1 && c <= 26 && c != 9 && c != 10 && c != 13) return 3000 + c;
    if (c != 27) return c;
    int b2 = read_byte(100);
    if (b2 < 0) return 27;
    if (b2 == '[') {
        int b3 = read_byte(100);
        if (b3 < 0) return 27;
        if (b3 == 'A') return 1001; if (b3 == 'B') return 1002;
        if (b3 == 'C') return 1003; if (b3 == 'D') return 1004;
        if (b3 == 'H') return 1005; if (b3 == 'F') return 1006;
        if (b3 == 'Z') return 5001;
        /* SGR mouse: ESC [ < button ; col ; row M/m */
        if (b3 == '<') {
            if (parse_sgr_mouse()) return 7001;  /* mouse event */
            return 27;
        }
        if (b3 >= '0' && b3 <= '9') {
            int b4 = read_byte(100);
            if (b4 == '~') {
                if (b3=='3') return 1009; if (b3=='5') return 1007; if (b3=='6') return 1008;
            } else if (b4 >= '0' && b4 <= '9') {
                int b5 = read_byte(100);
                if (b5 == '~') {
                    int code = (b3-'0')*10 + (b4-'0');
                    switch(code) {
                        case 11: return 2001; case 12: return 2002;
                        case 13: return 2003; case 14: return 2004;
                        case 15: return 2005; case 17: return 2006;
                        case 18: return 2007; case 19: return 2008;
                        case 20: return 2009; case 21: return 2010;
                        case 23: return 2011; case 24: return 2012;
                    }
                }
            }
        }
    } else if (b2 == 'O') {
        int b3 = read_byte(100);
        if (b3=='P') return 2001; if (b3=='Q') return 2002;
        if (b3=='R') return 2003; if (b3=='S') return 2004;
    }
    return 27;
}

/* ================================================================== */
/* Paste drain: read all available printable bytes with short timeout  */
/* Returns malloc'd string of available chars (caller frees).         */
/* Used by Idris TUI to detect paste bursts.                          */
/* ================================================================== */

char *eden_term_drain_paste(int timeout_ms) {
    int cap = 1024, len = 0;
    char *buf = (char *)malloc(cap);
    if (!buf) return "";
    while (1) {
        int c = read_byte(timeout_ms > 0 ? timeout_ms : 5);
        if (c < 0) break;
        /* Skip escape sequences during paste */
        if (c == 27) {
            int b2 = read_byte(5);
            if (b2 < 0) break;
            if (b2 == '[') {
                int b3 = read_byte(5);
                if (b3 >= '0' && b3 <= '9') {
                    int b4 = read_byte(5);
                    if (b4 >= '0' && b4 <= '9') read_byte(5);
                }
            } else if (b2 == 'O') {
                read_byte(5);
            }
            continue;
        }
        /* Collapse newlines to spaces for single-line composer */
        if (c == 10 || c == 13) c = ' ';
        /* Only accept printable ASCII + space */
        if (c >= 32 && c <= 126) {
            if (len + 2 > cap) {
                cap *= 2;
                char *nb = realloc(buf, cap);
                if (!nb) break;
                buf = nb;
            }
            buf[len++] = (char)c;
        }
    }
    buf[len] = '\0';
    return buf;
}

/* Raw fd write — bypasses stdio buffering */
#ifdef _WIN32
#define RAW_WRITE(buf, len) _write(1, (buf), (len))
#else
#define RAW_WRITE(buf, len) write(STDOUT_FILENO, (buf), (len))
#endif

void eden_term_enable_mouse(void) {
    const char *seq = "\x1b[?1000h\x1b[?1006h";
    RAW_WRITE(seq, (int)strlen(seq));
}

void eden_term_disable_mouse(void) {
    const char *seq = "\x1b[?1000l\x1b[?1006l";
    RAW_WRITE(seq, (int)strlen(seq));
}

void eden_term_write(char *s) {
    if (s) {
        int len = (int)strlen(s);
        if (len > 0) RAW_WRITE(s, len);
    }
}
void eden_term_flush(void) {
    /* No-op: raw write goes directly to fd */
}

/* ================================================================== */
/* Layer 2: Cell-buffer screen compositor                             */
/*                                                                    */
/* Maintains two grids (front/back). Idris writes to the back buffer  */
/* via eden_screen_set(). eden_screen_present() diffs back vs front,  */
/* emits only changed cells, then swaps.                              */
/* ================================================================== */

typedef struct {
    int      ch;               /* Unicode codepoint (supports box-drawing) */
    unsigned char fr, fg, fb;  /* foreground RGB */
    unsigned char br, bg, bb;  /* background RGB */
    unsigned char bold;
} Cell;

static Cell *buf_front = NULL;  /* what's on the terminal now */
static Cell *buf_back  = NULL;  /* what we want on the terminal */
static int   scr_w = 0, scr_h = 0;
static int   screen_inited = 0;

static Cell blank_cell(void) {
    Cell c;
    c.ch = ' ';
    c.fr = 255; c.fg = 217; c.fb = 138;  /* amber fg */
    c.br = 18;  c.bg = 8;   c.bb = 10;   /* dark bg */
    c.bold = 0;
    return c;
}

static int cell_eq(const Cell *a, const Cell *b) {
    return a->ch == b->ch
        && a->fr == b->fr && a->fg == b->fg && a->fb == b->fb
        && a->br == b->br && a->bg == b->bg && a->bb == b->bb
        && a->bold == b->bold;
}

/* Initialize or resize the screen buffer.
 * No-op if size hasn't changed (preserves front buffer for diffing). */
void eden_screen_init(int w, int h) {
    if (screen_inited && w == scr_w && h == scr_h) return;

    if (buf_front) free(buf_front);
    if (buf_back)  free(buf_back);
    scr_w = w;
    scr_h = h;
    int n = w * h;
    buf_front = (Cell *)malloc(n * sizeof(Cell));
    buf_back  = (Cell *)malloc(n * sizeof(Cell));
    Cell bl = blank_cell();
    for (int i = 0; i < n; i++) {
        buf_front[i] = bl;
        buf_back[i]  = bl;
    }
    /* Force full repaint on first present by making front differ */
    for (int i = 0; i < n; i++) buf_front[i].ch = 0;
    screen_inited = 1;
}

/* Set a cell in the back buffer. Row/col are 0-based. */
void eden_screen_set(int row, int col, int ch,
                     int fr, int fg, int fb,
                     int br, int bg, int bb,
                     int bold) {
    if (!screen_inited) return;
    if (row < 0 || row >= scr_h || col < 0 || col >= scr_w) return;
    Cell *c = &buf_back[row * scr_w + col];
    c->ch = ch;
    c->fr = (unsigned char)fr; c->fg = (unsigned char)fg; c->fb = (unsigned char)fb;
    c->br = (unsigned char)br; c->bg = (unsigned char)bg; c->bb = (unsigned char)bb;
    c->bold = (unsigned char)bold;
}

/* Write a UTF-8 string into the screen buffer, decoding codepoints.
 * Returns the number of characters (cells) written. */
int eden_screen_put_utf8(int row, int col, int maxW,
                         int fr, int fg, int fb,
                         int br, int bg, int bb,
                         int bold, const char *s) {
    if (!screen_inited || !s) return 0;
    int cx = col;
    const unsigned char *p = (const unsigned char *)s;
    while (*p && cx < col + maxW) {
        int cp = 0;
        if (*p < 0x80) {
            cp = *p++;
        } else if ((*p & 0xE0) == 0xC0) {
            cp = (*p & 0x1F) << 6;
            p++;
            if ((*p & 0xC0) == 0x80) cp |= (*p++ & 0x3F);
        } else if ((*p & 0xF0) == 0xE0) {
            cp = (*p & 0x0F) << 12;
            p++;
            if ((*p & 0xC0) == 0x80) { cp |= (*p++ & 0x3F) << 6; }
            if ((*p & 0xC0) == 0x80) { cp |= (*p++ & 0x3F); }
        } else if ((*p & 0xF8) == 0xF0) {
            cp = (*p & 0x07) << 18;
            p++;
            if ((*p & 0xC0) == 0x80) { cp |= (*p++ & 0x3F) << 12; }
            if ((*p & 0xC0) == 0x80) { cp |= (*p++ & 0x3F) << 6; }
            if ((*p & 0xC0) == 0x80) { cp |= (*p++ & 0x3F); }
        } else {
            p++; /* skip invalid byte */
            continue;
        }
        if (row >= 0 && row < scr_h && cx >= 0 && cx < scr_w) {
            Cell *c = &buf_back[row * scr_w + cx];
            c->ch = cp;
            c->fr = (unsigned char)fr; c->fg = (unsigned char)fg; c->fb = (unsigned char)fb;
            c->br = (unsigned char)br; c->bg = (unsigned char)bg; c->bb = (unsigned char)bb;
            c->bold = (unsigned char)bold;
        }
        cx++;
    }
    return cx - col;
}

/* Count the number of Unicode codepoints in a UTF-8 string.
 * This gives the display width (assuming all codepoints are 1 cell wide). */
int eden_utf8_strlen(const char *s) {
    if (!s) return 0;
    int count = 0;
    const unsigned char *p = (const unsigned char *)s;
    while (*p) {
        if (*p < 0x80)       p += 1;
        else if ((*p & 0xE0) == 0xC0) p += 2;
        else if ((*p & 0xF0) == 0xE0) p += 3;
        else if ((*p & 0xF8) == 0xF0) p += 4;
        else p += 1; /* skip invalid */
        count++;
    }
    return count;
}

/* Extract a substring by codepoint offset and length from a UTF-8 string.
 * Returns a malloc'd string that the caller must free.
 * If offset+len exceeds the string, returns what's available. */
char *eden_utf8_substr(const char *s, int offset, int len) {
    if (!s || offset < 0 || len < 0) {
        char *e = malloc(1);
        if (e) e[0] = '\0';
        return e ? e : "";
    }
    const unsigned char *p = (const unsigned char *)s;
    /* Skip 'offset' codepoints */
    for (int i = 0; i < offset && *p; i++) {
        if (*p < 0x80)       p += 1;
        else if ((*p & 0xE0) == 0xC0) p += 2;
        else if ((*p & 0xF0) == 0xE0) p += 3;
        else if ((*p & 0xF8) == 0xF0) p += 4;
        else p += 1;
    }
    const unsigned char *start = p;
    /* Count 'len' codepoints */
    for (int i = 0; i < len && *p; i++) {
        if (*p < 0x80)       p += 1;
        else if ((*p & 0xE0) == 0xC0) p += 2;
        else if ((*p & 0xF0) == 0xE0) p += 3;
        else if ((*p & 0xF8) == 0xF0) p += 4;
        else p += 1;
    }
    int byte_len = (int)(p - start);
    char *result = malloc(byte_len + 1);
    if (!result) return "";
    memcpy(result, start, byte_len);
    result[byte_len] = '\0';
    return result;
}

/* Find the codepoint position of the last space within the first maxW codepoints.
 * Returns 0 if no space found. */
int eden_utf8_last_space(const char *s, int maxW) {
    if (!s) return 0;
    int pos = 0, last_space = 0;
    const unsigned char *p = (const unsigned char *)s;
    while (*p && pos < maxW) {
        if (*p == ' ') last_space = pos + 1; /* 1-based so 0 means "not found" */
        if (*p < 0x80)       p += 1;
        else if ((*p & 0xE0) == 0xC0) p += 2;
        else if ((*p & 0xF0) == 0xE0) p += 3;
        else if ((*p & 0xF8) == 0xF0) p += 4;
        else p += 1;
        pos++;
    }
    return last_space;
}

/* Clear back buffer to blanks. */
void eden_screen_clear(void) {
    if (!screen_inited) return;
    Cell bl = blank_cell();
    int n = scr_w * scr_h;
    for (int i = 0; i < n; i++) buf_back[i] = bl;
}

/* Draw a nebula starfield pattern into the screen buffer.
 * Deterministic hash places dots/colons with varied colors. */
void eden_screen_nebula(int row, int col, int w, int h,
                        int bgr, int bgg, int bgb) {
    if (!screen_inited) return;
    /* Color palette: muted, violet, ember, ice, rose */
    static const unsigned char pal[][3] = {
        {230,171,90}, {168,144,255}, {255,174,87}, {141,220,255}, {255,122,215}
    };
    for (int ri = 0; ri < h; ri++) {
        for (int ci = 0; ci < w; ci++) {
            int r = row + ri, c2 = col + ci;
            if (r < 0 || r >= scr_h || c2 < 0 || c2 >= scr_w) continue;
            unsigned hv = (unsigned)(ri * 7 + ci * 13 + 37);
            unsigned hv2 = (unsigned)(ri * 11 + ci * 3 + 19);
            int ch = 0, pi = 0;
            /* Structured row patterns: colons every ~4 rows, dots every ~3 rows */
            if (ri % 4 == 0 && ci % 10 == 3) { ch = ':'; pi = 2; }
            else if (ri % 3 == 1 && ci % 8 == 5) { ch = '.'; pi = 0; }
            /* Hash-based scatter */
            else if (hv % 29 == 0) { ch = '.'; pi = 0; }
            else if (hv % 37 == 0) { ch = '.'; pi = 1; }
            else if (hv % 47 == 0) { ch = ':'; pi = 2; }
            else if (hv % 59 == 0) { ch = ':'; pi = 3; }
            else if (hv2 % 43 == 0) { ch = '.'; pi = 4; }
            else if (hv2 % 61 == 0) { ch = '.'; pi = 0; }
            else continue;
            Cell *cell = &buf_back[r * scr_w + c2];
            cell->ch = ch;
            cell->fr = pal[pi][0]; cell->fg = pal[pi][1]; cell->fb = pal[pi][2];
            cell->br = (unsigned char)bgr; cell->bg = (unsigned char)bgg; cell->bb = (unsigned char)bgb;
            cell->bold = 0;
        }
    }
}

/* Diff back vs front, emit ANSI for changed cells, swap buffers.
 * Output is built into a single buffer and written in one fwrite(). */
void eden_screen_present(void) {
    if (!screen_inited) return;
    int n = scr_w * scr_h;

    /* Worst case: each cell could need ~40 bytes of ANSI.
     * Plus sync markers and cursor hide/show. */
    int cap = n * 54 + 256;
    char *out = (char *)malloc(cap);
    int pos = 0;

    #define EMIT(...) pos += snprintf(out + pos, cap - pos, __VA_ARGS__)

    /* Begin synchronized update + hide cursor */
    EMIT("\x1b[?2026h\x1b[?25l");

    int last_row = -1, last_col = -1;
    int last_fr = -1, last_fg2 = -1, last_fb = -1;
    int last_br = -1, last_bg2 = -1, last_bb = -1;
    int last_bold = -1;

    for (int i = 0; i < n; i++) {
        if (cell_eq(&buf_back[i], &buf_front[i])) continue;

        int r = i / scr_w;
        int c = i % scr_w;
        Cell *cell = &buf_back[i];

        /* Move cursor if not contiguous */
        if (r != last_row || c != last_col) {
            EMIT("\x1b[%d;%dH", r + 1, c + 1);
        }

        /* Emit style changes only when needed */
        int need_bold = (cell->bold != last_bold);
        int need_fg = (cell->fr != last_fr || cell->fg != last_fg2 || cell->fb != last_fb);
        int need_bg = (cell->br != last_br || cell->bg != last_bg2 || cell->bb != last_bb);

        if (need_bold && !cell->bold) {
            /* Reset bold — need full SGR reset then re-apply colors */
            EMIT("\x1b[0m");
            need_fg = 1;
            need_bg = 1;
            last_bold = 0;
        }
        if (need_bold && cell->bold) {
            EMIT("\x1b[1m");
            last_bold = 1;
        }
        if (need_fg) {
            EMIT("\x1b[38;2;%d;%d;%dm", cell->fr, cell->fg, cell->fb);
            last_fr = cell->fr; last_fg2 = cell->fg; last_fb = cell->fb;
        }
        if (need_bg) {
            EMIT("\x1b[48;2;%d;%d;%dm", cell->br, cell->bg, cell->bb);
            last_br = cell->br; last_bg2 = cell->bg; last_bb = cell->bb;
        }

        /* Emit character as UTF-8 */
        {
            int cp = cell->ch;
            if (cp < 0x80) {
                if (pos < cap - 1) out[pos++] = (char)cp;
            } else if (cp < 0x800) {
                if (pos < cap - 2) {
                    out[pos++] = (char)(0xC0 | (cp >> 6));
                    out[pos++] = (char)(0x80 | (cp & 0x3F));
                }
            } else if (cp < 0x10000) {
                if (pos < cap - 3) {
                    out[pos++] = (char)(0xE0 | (cp >> 12));
                    out[pos++] = (char)(0x80 | ((cp >> 6) & 0x3F));
                    out[pos++] = (char)(0x80 | (cp & 0x3F));
                }
            } else {
                if (pos < cap - 4) {
                    out[pos++] = (char)(0xF0 | (cp >> 18));
                    out[pos++] = (char)(0x80 | ((cp >> 12) & 0x3F));
                    out[pos++] = (char)(0x80 | ((cp >> 6) & 0x3F));
                    out[pos++] = (char)(0x80 | (cp & 0x3F));
                }
            }
        }

        last_row = r;
        last_col = c + 1;  /* cursor advances after write */
    }

    /* End synchronized update */
    EMIT("\x1b[0m\x1b[?2026l");

    #undef EMIT

    /* Skip if nothing changed */
    if (pos <= 30) {  /* only sync markers, no actual cell data */
        free(out);
        return;
    }

    /* Single atomic write to fd — bypasses stdio buffering entirely */
    RAW_WRITE(out, pos);
    free(out);

    /* Swap: copy back -> front */
    memcpy(buf_front, buf_back, n * sizeof(Cell));
}
