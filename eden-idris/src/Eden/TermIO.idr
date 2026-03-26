||| Terminal I/O primitives requiring C FFI.
|||
||| Raw mode, terminal size, non-blocking key reading.
||| Uses POSIX termios on macOS/Linux, Windows console API via MSYS2.
module Eden.TermIO

import Data.IORef
import Eden.Term

------------------------------------------------------------------------
-- C FFI declarations
------------------------------------------------------------------------

-- We link against a small C helper (eden_term.c) that wraps
-- platform-specific terminal calls.

%foreign "C:eden_term_init,eden_term"
prim__termInit : PrimIO Int

%foreign "C:eden_term_cleanup,eden_term"
prim__termCleanup : PrimIO ()

%foreign "C:eden_term_width,eden_term"
prim__termWidth : PrimIO Int

%foreign "C:eden_term_height,eden_term"
prim__termHeight : PrimIO Int

%foreign "C:eden_term_read_key,eden_term"
prim__readKey : Int -> PrimIO Int

%foreign "C:eden_term_write,eden_term"
prim__termWrite : String -> PrimIO ()

%foreign "C:eden_term_flush,eden_term"
prim__termFlush : PrimIO ()

%foreign "C:eden_screen_init,eden_term"
prim__screenInit : Int -> Int -> PrimIO ()

%foreign "C:eden_screen_set,eden_term"
prim__screenSet : Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> PrimIO ()

%foreign "C:eden_screen_clear,eden_term"
prim__screenClear : PrimIO ()

%foreign "C:eden_screen_nebula,eden_term"
prim__screenNebula : Int -> Int -> Int -> Int -> Int -> Int -> Int -> PrimIO ()

%foreign "C:eden_screen_present,eden_term"
prim__screenPresent : PrimIO ()

------------------------------------------------------------------------
-- Terminal size
------------------------------------------------------------------------

public export
record TermSize where
  constructor MkTermSize
  tsWidth  : Nat
  tsHeight : Nat

||| Get current terminal dimensions.
export
getTermSize : IO TermSize
getTermSize = do
  w <- primIO prim__termWidth
  h <- primIO prim__termHeight
  pure (MkTermSize (cast (max 40 w)) (cast (max 10 h)))

------------------------------------------------------------------------
-- Raw mode management
------------------------------------------------------------------------

||| Initialize raw terminal mode (no echo, no line buffering).
||| Returns True on success.
export
initRawMode : IO Bool
initRawMode = do
  result <- primIO prim__termInit
  pure (result == 0)

||| Restore terminal to normal mode.
export
cleanupTerminal : IO ()
cleanupTerminal = primIO prim__termCleanup

------------------------------------------------------------------------
-- Key input
------------------------------------------------------------------------

||| Key event representation.
public export
data KeyEvent
  = KeyChar Char
  | KeyEnter
  | KeyBackspace
  | KeyTab
  | KeyEscape
  | KeyUp
  | KeyDown
  | KeyLeft
  | KeyRight
  | KeyHome
  | KeyEnd
  | KeyPageUp
  | KeyPageDown
  | KeyDelete
  | KeyF1 | KeyF2 | KeyF3 | KeyF4
  | KeyF5 | KeyF6 | KeyF7 | KeyF8
  | KeyF9 | KeyF10 | KeyF11 | KeyF12
  | KeyCtrl Char
  | KeyShiftEnter
  | KeyNone  -- no key available (non-blocking returned empty)

||| Read a key event. timeout_ms=0 for non-blocking.
export
readKey : (timeout_ms : Int) -> IO KeyEvent
readKey timeout = do
  code <- primIO (prim__readKey timeout)
  pure (decodeKey code)
  where
    decodeKey : Int -> KeyEvent
    decodeKey c =
      if c == (-1)   then KeyNone
      else if c == 10 || c == 13  then KeyEnter
      else if c == 127 || c == 8  then KeyBackspace
      else if c == 9   then KeyTab
      else if c == 27  then KeyEscape  -- simplified; escape sequences handled in C
      -- Arrow keys encoded as 1000+direction by C helper
      else if c == 1001 then KeyUp
      else if c == 1002 then KeyDown
      else if c == 1003 then KeyRight
      else if c == 1004 then KeyLeft
      else if c == 1005 then KeyHome
      else if c == 1006 then KeyEnd
      else if c == 1007 then KeyPageUp
      else if c == 1008 then KeyPageDown
      else if c == 1009 then KeyDelete
      -- F-keys encoded as 2001-2012 by C helper
      else if c >= 2001 && c <= 2012 then
        case c of
          2001 => KeyF1;  2002 => KeyF2;  2003 => KeyF3;  2004 => KeyF4
          2005 => KeyF5;  2006 => KeyF6;  2007 => KeyF7;  2008 => KeyF8
          2009 => KeyF9;  2010 => KeyF10; 2011 => KeyF11; 2012 => KeyF12
          _    => KeyNone
      -- Ctrl+letter encoded as 3001-3026 by C helper
      else if c >= 3001 && c <= 3026 then KeyCtrl (chr (c - 3001 + ord 'a'))
      -- Shift+Enter encoded as 4001
      else if c == 4001 then KeyShiftEnter
      -- Regular printable character
      else if c >= 32 && c <= 126 then KeyChar (chr c)
      else KeyNone

------------------------------------------------------------------------
-- Output primitives
------------------------------------------------------------------------

||| Write a string directly to the terminal (no newline).
export
termWrite : String -> IO ()
termWrite s = primIO (prim__termWrite s)

||| Flush terminal output.
export
termFlush : IO ()
termFlush = primIO prim__termFlush

||| Write string and flush.
export
termPut : String -> IO ()
termPut s = do
  termWrite s
  termFlush

------------------------------------------------------------------------
-- Cell-buffer screen API
------------------------------------------------------------------------

||| RGB color triple.
public export
record RGB where
  constructor MkRGB
  r, g, b : Int

||| Initialize or resize the screen buffer.
export
screenInit : (width : Int) -> (height : Int) -> IO ()
screenInit w h = primIO (prim__screenInit w h)

||| Set a cell in the back buffer. Row/col are 0-based.
export
screenSet : (row : Int) -> (col : Int) -> (ch : Char) -> (fg : RGB) -> (bg : RGB) -> (isBold : Bool) -> IO ()
screenSet row col ch fg bg bd =
  primIO (prim__screenSet row col (ord ch) fg.r fg.g fg.b bg.r bg.g bg.b (if bd then 1 else 0))

||| Set a cell using a Unicode codepoint directly (bypasses Char 8-bit truncation in RefC).
export
screenSetCP : (row : Int) -> (col : Int) -> (codepoint : Int) -> (fg : RGB) -> (bg : RGB) -> (isBold : Bool) -> IO ()
screenSetCP row col cp fg bg bd =
  primIO (prim__screenSet row col cp fg.r fg.g fg.b bg.r bg.g bg.b (if bd then 1 else 0))

||| Fill a horizontal span with a Unicode codepoint.
export
screenFillCP : (row : Int) -> (col : Int) -> (width : Int) -> (codepoint : Int) -> (fg : RGB) -> (bg : RGB) -> IO ()
screenFillCP row col w cp fg bg = go col
  where
    go : Int -> IO ()
    go c = if c >= col + w
             then pure ()
             else do screenSetCP row c cp fg bg False
                     go (c + 1)

||| Clear back buffer to blanks.
export
screenClear : IO ()
screenClear = primIO prim__screenClear

||| Draw a nebula starfield pattern into the screen buffer.
export
screenNebula : (row : Int) -> (col : Int) -> (width : Int) -> (height : Int) -> (bg : RGB) -> IO ()
screenNebula row col w h bg = primIO (prim__screenNebula row col w h bg.r bg.g bg.b)

||| Diff back vs front and emit only changed cells. Zero flicker.
export
screenPresent : IO ()
screenPresent = primIO prim__screenPresent

||| Write a plain string into the cell buffer at (row, col) with given colors.
export
screenPutStr : (row : Int) -> (col : Int) -> (fg : RGB) -> (bg : RGB) -> (isBold : Bool) -> String -> IO ()
screenPutStr row col fg bg bd s = go col (unpack s)
  where
    go : Int -> List Char -> IO ()
    go _ [] = pure ()
    go c (x :: xs) = do
      screenSet row c x fg bg bd
      go (c + 1) xs

||| Fill a horizontal span with a character.
export
screenFill : (row : Int) -> (col : Int) -> (width : Int) -> (ch : Char) -> (fg : RGB) -> (bg : RGB) -> IO ()
screenFill row col w ch fg bg = go col
  where
    go : Int -> IO ()
    go c = if c >= col + w
             then pure ()
             else do screenSet row c ch fg bg False
                     go (c + 1)

------------------------------------------------------------------------
-- Subprocess execution (C FFI)
------------------------------------------------------------------------

-- eden_run_cmd returns "<exit_code>\n<output>".
%foreign "C:eden_run_cmd,eden_term"
prim__runCmd : String -> PrimIO String

splitFirst : Nat -> String -> (String, String)
splitFirst n s =
  if n >= length s then (s, "")
  else if substr n 1 s == "\n"
    then (substr 0 n s, substr (n + 1) (length s) s)
    else splitFirst (n + 1) s

||| Run a shell command and capture stdout. Returns (output, exitCode).
export
runCommand : String -> IO (String, Int)
runCommand cmd = do
  raw <- primIO (prim__runCmd cmd)
  let (codePart, output) = splitFirst 0 raw
  pure (output, cast (cast {to=Integer} codePart))

------------------------------------------------------------------------
-- High-level terminal setup/teardown
------------------------------------------------------------------------

||| Enter TUI mode: alt screen, raw mode, hide cursor.
export
enterTUI : IO Bool
enterTUI = do
  ok <- initRawMode
  if ok
    then do
      termPut (enterAltScreen ++ hideCursor ++ clearScreen ++ moveTo 1 1)
      pure True
    else pure False

||| Leave TUI mode: show cursor, leave alt screen, restore terminal.
export
leaveTUI : IO ()
leaveTUI = do
  termPut (showCursor ++ leaveAltScreen)
  cleanupTerminal
