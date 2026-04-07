||| Browser automation: open URLs in the system default browser.
|||
||| Platform-aware: tries start (Windows/MSYS2), open (macOS),
||| and xdg-open (Linux) in order. Non-fatal on failure.
module Eden.Browser

import System

------------------------------------------------------------------------
-- Public API
------------------------------------------------------------------------

||| Open a URL in the system default browser.
|||
||| Tries platform-specific commands in order:
|||   1. start (Windows/MSYS2)
|||   2. open (macOS)
|||   3. xdg-open (Linux/X11)
|||
||| Returns True if the command succeeded, False otherwise.
||| Failure is non-fatal: the URL is printed to stdout as fallback.
export
openBrowser : HasIO io => String -> io Bool
openBrowser url = do
  result <- liftIO (system ("start \"\" \"" ++ url ++ "\" 2>/dev/null"))
  if result == 0
    then pure True
    else do
      result2 <- liftIO (system ("open \"" ++ url ++ "\" 2>/dev/null"))
      if result2 == 0
        then pure True
        else do
          result3 <- liftIO (system ("xdg-open \"" ++ url ++ "\" 2>/dev/null"))
          if result3 == 0
            then pure True
            else do
              liftIO (putStrLn ("  Open in browser: " ++ url))
              pure False

||| Open the observatory web UI at the given host and port.
export
openObservatory : HasIO io => String -> Nat -> io Bool
openObservatory host port =
  openBrowser ("http://" ++ host ++ ":" ++ show port)
