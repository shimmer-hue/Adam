||| EDEN TUI application.
|||
||| Matches Python Textual layout: action strip, status panels,
||| dialogue tape, memgraph, reasoning tabs, composer, footer.
||| Includes help modal, config modal, atlas/archive browser,
||| session profile wiring, graph audit, and paste handling.
module Eden.TUI

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard
import Eden.Retrieval
import Eden.Budget
import Eden.Inference
import Eden.Membrane
import Eden.Hum
import Eden.Models.Base
import Eden.Models.Mock
import Eden.Storage
import Eden.Store.InMemory
import Eden.Runtime
import Eden.Indexer
import Eden.Trace
import Eden.SemanticRelations
import Eden.OntologyProjection
import Eden.Monad
import Eden.Pipeline
import Eden.Term
import Eden.TermIO
import Eden.Export
import Eden.SQLite
import Eden.Session
import Eden.GraphAudit

------------------------------------------------------------------------
-- Palette
------------------------------------------------------------------------
colAmber : RGB
colAmber = MkRGB 255 217 138
colText : RGB
colText = MkRGB 255 241 210
colMuted : RGB
colMuted = MkRGB 230 171 90
colBg : RGB
colBg = MkRGB 18 8 10
colPanel : RGB
colPanel = MkRGB 33 16 20
colNeon : RGB
colNeon = MkRGB 132 255 208
colIce : RGB
colIce = MkRGB 141 220 255
colRose : RGB
colRose = MkRGB 255 122 215
colEmber : RGB
colEmber = MkRGB 255 174 87
colViolet : RGB
colViolet = MkRGB 168 144 255
colActBg : RGB
colActBg = MkRGB 7 35 45
colActBd : RGB
colActBd = MkRGB 142 243 255
colModalBg : RGB
colModalBg = MkRGB 24 12 16
colModalBd : RGB
colModalBd = MkRGB 255 217 138

------------------------------------------------------------------------
-- UI Mode
------------------------------------------------------------------------
public export
data UIMode
  = Normal
  | HelpModal
  | ConfigModal Nat
  | AtlasModal Nat Nat

------------------------------------------------------------------------
-- UI State
------------------------------------------------------------------------
public export
record UIState where
  constructor MkUIState
  uiEnv        : EdenEnv
  uiBackend    : IORef Backend
  uiModelPath  : Maybe String
  uiTurnIdx    : IORef Nat
  uiComposer   : IORef String
  uiDialogue   : IORef (List (String, String))
  uiFeedback   : IORef (Maybe String)
  uiLastActive : IORef (List CandidateScore)
  uiLastHum    : IORef (Maybe HumPayload)
  uiLastBudget : IORef (Maybe BudgetEstimate)
  uiLastProj   : IORef (List MemeProjection)
  uiFocusPanel : IORef Nat
  uiScrollOff  : IORef Nat
  uiQuit       : IORef Bool
  uiWidth      : IORef Int
  uiHeight     : IORef Int
  uiMode       : IORef UIMode
  uiSessMeta   : SessionMetaStore
  uiSessProf   : IORef SessionProfile

------------------------------------------------------------------------
-- Rendering primitives
------------------------------------------------------------------------
putText : Int -> Int -> RGB -> RGB -> Bool -> Int -> String -> IO ()
putText row col fg bg bd maxW s = go col (unpack s)
  where
    go : Int -> List Char -> IO ()
    go c [] = pure ()
    go c (x :: xs) =
      if c >= col + maxW then pure ()
      else do screenSet row c x fg bg bd
              go (c + 1) xs

clearRow : Int -> Int -> Int -> RGB -> IO ()
clearRow row col w bg = screenFill row col w ' ' colText bg

clearRect : Int -> Int -> Int -> Int -> RGB -> IO ()
clearRect r h c w bg = go r
  where go : Int -> IO ()
        go row = if row >= r + h then pure ()
                 else do clearRow row c w bg; go (row + 1)

-- Box drawing codepoints
cpTL : Int; cpTL = 9484
cpTR : Int; cpTR = 9488
cpBL : Int; cpBL = 9492
cpBR : Int; cpBR = 9496
cpH  : Int; cpH  = 9472
cpV  : Int; cpV  = 9474

drawBox : Int -> Int -> Int -> Int -> RGB -> IO ()
drawBox r c w h bc = do
  screenSetCP r c cpTL bc colBg False
  screenFillCP r (c+1) (w-2) cpH bc colBg
  screenSetCP r (c+w-1) cpTR bc colBg False
  screenSetCP (r+h-1) c cpBL bc colBg False
  screenFillCP (r+h-1) (c+1) (w-2) cpH bc colBg
  screenSetCP (r+h-1) (c+w-1) cpBR bc colBg False
  sides (r+1) (r+h-1) c (c+w-1) bc
  where
    sides : Int -> Int -> Int -> Int -> RGB -> IO ()
    sides row rEnd l ri bc2 =
      if row >= rEnd then pure ()
      else do screenSetCP row l cpV bc2 colBg False
              screenSetCP row ri cpV bc2 colBg False
              sides (row+1) rEnd l ri bc2

drawBoxBg : Int -> Int -> Int -> Int -> RGB -> RGB -> IO ()
drawBoxBg r c w h bc bg = do
  clearRect r h c w bg
  screenSetCP r c cpTL bc bg False
  screenFillCP r (c+1) (w-2) cpH bc bg
  screenSetCP r (c+w-1) cpTR bc bg False
  screenSetCP (r+h-1) c cpBL bc bg False
  screenFillCP (r+h-1) (c+1) (w-2) cpH bc bg
  screenSetCP (r+h-1) (c+w-1) cpBR bc bg False
  sidesBg (r+1) (r+h-1) c (c+w-1) bc bg
  where
    sidesBg : Int -> Int -> Int -> Int -> RGB -> RGB -> IO ()
    sidesBg row rEnd l ri bc2 bg2 =
      if row >= rEnd then pure ()
      else do screenSetCP row l cpV bc2 bg2 False
              screenSetCP row ri cpV bc2 bg2 False
              sidesBg (row+1) rEnd l ri bc2 bg2

boxTitle : Int -> Int -> String -> RGB -> IO ()
boxTitle r c title fg = putText r (c+2) fg colBg True (cast (length title)) title

boxTitleBg : Int -> Int -> String -> RGB -> RGB -> IO ()
boxTitleBg r c title fg bg = putText r (c+2) fg bg True (cast (length title)) title

showD : Double -> String
showD d = let i = cast {to=Integer} (d * 100.0)
          in show (cast {to=Double} i / 100.0)

------------------------------------------------------------------------
-- Centered section title with horizontal rules
------------------------------------------------------------------------
sectionTitle : Int -> Int -> Int -> String -> RGB -> IO ()
sectionTitle row col w title fg = do
  let tl = cast {to=Int} (length title) + 2
  let ts = col + (w `div` 2) - (tl `div` 2)
  screenFillCP row col (ts - col) cpH fg colBg
  putText row ts fg colBg False tl (" " ++ title ++ " ")
  screenFillCP row (ts + tl) (col + w - ts - tl) cpH fg colBg

------------------------------------------------------------------------
-- Action strip
------------------------------------------------------------------------
colActHi : RGB
colActHi = MkRGB 4 22 27

colActHiBg : RGB
colActHiBg = MkRGB 152 244 255

actionLine : Int -> Int -> Int -> Nat -> Bool -> String -> IO ()
actionLine row col maxW num sel label = do
  let n = if num < 10 then "0" ++ show num else show num
  let fg = if sel then colActHi else colIce
  let bg = if sel then colActHiBg else colActBg
  clearRow row col maxW bg
  putText row col fg bg sel maxW ("[ " ++ n ++ " " ++ label ++ " ]")

drawActions : Int -> Int -> Int -> IO ()
drawActions r c w = do
  let h = 10
  clearRect r h c w colActBg
  drawBox r c w h colActBd
  boxTitle r c " Actions " colNeon
  let hw = (w - 4) `div` 2
  let rc = c + 2 + hw + 1
  actionLine (r+1) (c+2) hw  1 True  "Review Last Reply"
  actionLine (r+2) (c+2) hw  2 False "Open Conversation Log"
  actionLine (r+3) (c+2) hw  3 False "Open Conversation Atlas"
  actionLine (r+4) (c+2) hw  4 False "Tune Session"
  actionLine (r+5) (c+2) hw  5 False "Start New Session"
  actionLine (r+6) (c+2) hw  6 False "Continue Latest"
  actionLine (r+7) (c+2) hw  7 False "Prepare Local Model"
  actionLine (r+1) rc hw  8 False "Open Browser Observatory"
  actionLine (r+2) rc hw  9 False "Export Artifacts"
  actionLine (r+3) rc hw 10 False "Open Utilities Deck"
  actionLine (r+4) rc hw 11 False "Help"
  actionLine (r+5) rc hw 12 False "Ingest PDF / Doc"
  actionLine (r+6) rc hw 13 False "Toggle Aperture Drawer"
  actionLine (r+7) rc hw 14 False "Toggle Runtime Chyron"
  -- Status hint line
  clearRow (r+8) (c+1) (w-2) colActBg
  putText (r+8) (c+2) colMuted colActBg False (w-4) "digits jump | left/right move | Enter runs"

------------------------------------------------------------------------
-- Status panels (right of actions)
------------------------------------------------------------------------
drawPanel : Int -> Int -> Int -> Int -> String -> RGB -> List String -> IO ()
drawPanel r c w h title bc lns = do
  clearRect r h c w colBg
  drawBox r c w h bc
  boxTitle r c (" " ++ title ++ " ") bc
  writeLns (r+1) lns (c+1) (w-2) (r+h-1)
  where
    writeLns : Int -> List String -> Int -> Int -> Int -> IO ()
    writeLns row [] c' w' rEnd = pure ()
    writeLns row (l :: ls) c' w' rEnd =
      if row >= rEnd then pure ()
      else do putText row c' colText colBg False w' l
              writeLns (row+1) ls c' w' rEnd

drawStatusPanels : UIState -> Int -> Int -> Int -> IO ()
drawStatusPanels ui r c tw = do
  be <- readIORef ui.uiBackend
  idx <- readIORef ui.uiTurnIdx
  counts <- runEden ui.uiEnv eGraphCounts
  active <- readIORef ui.uiLastActive
  prof <- readIORef ui.uiSessProf
  let pw = tw `div` 3
  drawPanel r c pw 10 "Context" colAmber
    ["No estimate", "yet", "Type to arm.", "Deck=F6"]
  drawPanel r (c+pw) pw 10 "Live Turn Status" colAmber
    [ "Adam status", "phase=start"
    , "Start here: type", "below, press Enter"
    , "to send, or press F9"
    , "model=" ++ show be, "mode=" ++ show prof.spMode
    , "items=" ++ show (length active) ++ " review=clear"]
  let aLns = case active of
        [] => ["Aperture snapshot", "No active set yet. Type in", "the compose or ingest a", "document to arm the scan.", "Press F8 for the wide", "aperture drawer."]
        _  => map (\x => x.label ++ " " ++ showD x.regard) (take 6 active)
  drawPanel r (c+pw+pw) (tw-pw-pw) 10 "Aperture / Active Set" colAmber aLns

------------------------------------------------------------------------
-- Runtime status line
------------------------------------------------------------------------
drawRuntimeLine : UIState -> Int -> Int -> IO ()
drawRuntimeLine ui row w = do
  be <- readIORef ui.uiBackend
  idx <- readIORef ui.uiTurnIdx
  prof <- readIORef ui.uiSessProf
  clearRow row 0 w colPanel
  putText row 1 colIce colPanel False (w-1)
    ("runtime=Adam / " ++ show be ++ " mode=" ++ show prof.spMode
     ++ " budget=" ++ show prof.spBudget ++ " session=active focus=composer")

------------------------------------------------------------------------
-- Dialogue tape (bordered)
------------------------------------------------------------------------
drawDialogue : UIState -> Int -> Int -> Int -> Int -> IO ()
drawDialogue ui r c w h = do
  clearRect r h c w colBg
  entries <- readIORef ui.uiDialogue
  let ch = h - 3
  let cs = r + 2
  case entries of
    [] => do
      putText cs (c+2) colMuted colBg False (w-4)
        "Start here: type in the composer below and press Enter to send."
      if cs + 1 < cs + ch
        then putText (cs+1) (c+2) colMuted colBg False (w-4)
               "Press F9 first if you want to ingest a document with a framing note."
        else pure ()
    _  => drawEntries cs 0 (reverse entries) cs ch (c+1) (w-2)
  -- Draw box borders AFTER content so they're never overwritten
  drawBox r c w h colRose
  boxTitle r c " Dialogue Tape " colRose
  sectionTitle (r+1) (c+1) (w-2) "Adam Dialogue" colAmber
  where
    -- Break a string into lines of at most maxW characters
    wrapLines : Nat -> String -> List String
    wrapLines maxW s =
      if length s <= maxW then [s]
      else substr 0 maxW s :: wrapLines maxW (substr maxW (length s) s)

    -- Render wrapped lines starting at row, return next row
    putWrapped : Int -> Int -> Int -> Int -> RGB -> List String -> IO Int
    putWrapped row limit c' cw fg [] = pure row
    putWrapped row limit c' cw fg (l :: ls) =
      if row >= limit then pure row
      else do clearRow row c' cw colBg
              putText row (c'+1) fg colBg False (cw-1) l
              putWrapped (row+1) limit c' cw fg ls

    drawEntries : Int -> Nat -> List (String, String) -> Int -> Int -> Int -> Int -> IO ()
    drawEntries row idx [] s ch c' cw = pure ()
    drawEntries row idx ((u, a) :: rest) s ch c' cw =
      if row + 1 >= s + ch
        then pure ()
        else do
          -- User line (single line with tag)
          clearRow row c' cw colBg
          let tag = "[you T" ++ show idx ++ "] "
          let tl = cast (length tag)
          putText row (c'+1) colAmber colBg True (cw-1) tag
          putText row (c' + 1 + tl) colText colBg False (cw - 1 - tl) u
          -- Adam response: first line has tag, continuation lines indented
          let ar = row + 1
          let at = "[adam T" ++ show idx ++ "] "
          let al = cast (length at)
          let tw = max 1 (cw - 1 - al)
          let pad = pack (replicate (length at) ' ')
          let lines = wrapLines (cast tw) a
          clearRow ar c' cw colBg
          putText ar (c'+1) colRose colBg False (cw-1) at
          case lines of
            [] => drawEntries (ar + 1) (idx+1) rest s ch c' cw
            (first :: more) => do
              putText ar (c' + 1 + al) colText colBg False tw first
              endRow <- putWrapped (ar+1) (s+ch) c' cw colText
                          (map (\l => pad ++ l) more)
              drawEntries endRow (idx+1) rest s ch c' cw

------------------------------------------------------------------------
-- Memgraph (simplified scatter)
------------------------------------------------------------------------
drawMemgraph : UIState -> Int -> Int -> Int -> Int -> IO ()
drawMemgraph ui r c w h = do
  sectionTitle r c w "Memgraph Bus" colMuted
  clearRect (r+1) (h-1) c w colBg
  -- Nebula starfield background (C FFI for codegen budget)
  screenNebula (r+1) c w (h-1) colBg
  -- Session anchor @ in center
  let cy = r + 1 + (h-1) `div` 2
  let cx = c + w `div` 2
  screenSet cy cx '@' colIce colBg False
  -- Plot memes
  memes <- runEden ui.uiEnv eGetMemes
  plotMemes (r+1) c w (h-1) memes
  where
    plotMemes : Int -> Int -> Int -> Int -> List Meme -> IO ()
    plotMemes rs c' w' sh [] = pure ()
    plotMemes rs c' w' sh (m :: ms) = do
      let ry = cast {to=Int} (m.rewardEma * cast {to=Double} (max 1 (sh - 1)))
      let rx = cast {to=Int} (m.riskEma * cast {to=Double} (max 1 (w' - 1)))
      let pr = rs + max 0 (sh - 1 - ry)
      let pc = c' + min (w' - 1) (max 0 rx)
      let ch = case m.domain of Knowledge => 'o'; Behavior => '^'
      let ptCol = case m.domain of Knowledge => colNeon; Behavior => colRose
      screenSet pr pc ch ptCol colBg False
      plotMemes rs c' w' sh ms

------------------------------------------------------------------------
-- Tab bar + Reasoning
------------------------------------------------------------------------
drawTabBar : Int -> Int -> Int -> IO ()
drawTabBar row col w = do
  clearRow row col w colPanel
  let tw = w `div` 3
  screenSetCP row (col+1) 9679 colAmber colPanel False
  putText row (col+3) colAmber colPanel True (tw-3) "Reasoning"
  putText row (col+tw) colMuted colPanel False tw "  Chain-Like"
  putText row (col+tw+tw) colMuted colPanel False (w-tw-tw) "  Hum Live"

drawReasoning : UIState -> Int -> Int -> Int -> Int -> IO ()
drawReasoning ui r c w h = do
  sectionTitle r c w "Reasoning" colMuted
  clearRect (r+1) (h-1) c w colBg
  putText (r+1) (c+1) colNeon colBg True (w-1) "Response material"
  if h > 2 then putText (r+2) (c+1) colMuted colBg False (w-1) "No operator-facing answer is persisted yet."
           else pure ()
  if h > 4 then do putText (r+4) (c+1) colAmber colBg True (w-1) "Reasoning signal"
                   if h > 5 then putText (r+5) (c+1) colMuted colBg False (w-1) "No model-emitted reasoning artifact was captured for this turn."
                            else pure ()
           else pure ()
  if h > 7 then do putText (r+7) (c+1) colIce colBg True (w-1) "Runtime condition"
                   if h > 8 then putText (r+8) (c+1) colMuted colBg False (w-1) "- state=persisted profile=pending mode=pending -> pending"
                            else pure ()
                   if h > 9 then putText (r+9) (c+1) colMuted colBg False (w-1) "- pressure=n/a response_cap=n/a retrieval_depth=n/a"
                            else pure ()
                   if h > 10 then putText (r+10) (c+1) colMuted colBg False (w-1) "- lane=quiet focus=none yet reasoning_chars=0"
                             else pure ()
                   if h > 11 then putText (r+11) (c+1) colMuted colBg False (w-1) "- feedback=no explicit feedback yet"
                             else pure ()
           else pure ()
  if h > 13 then putText (r+13) (c+1) colNeon colBg True (w-1) "Membrane record"
            else pure ()

------------------------------------------------------------------------
-- Composer (bordered)
------------------------------------------------------------------------
drawComposer : UIState -> Int -> Int -> Int -> Int -> IO ()
drawComposer ui r c w h = do
  clearRect r h c w colBg
  drawBox r c w h colAmber
  text <- readIORef ui.uiComposer
  fb <- readIORef ui.uiFeedback
  case fb of
    Just msg => do
      boxTitle r c " >> Composer " colEmber
      putText (r+1) (c+2) colEmber colBg False (w-4) msg
    Nothing =>
      if text == ""
        then do
          boxTitle r c " >> Composer " colNeon
          putText (r+1) (c+2) colMuted colBg False (w-4)
            "Message Adam here. ?/h=help  /config  /atlas  /archive. Enter sends."
          if h > 2
            then putText (r+2) (c+2) colMuted colBg False (w-4) "F9 ingests a document first if needed."
            else pure ()
        else do
          boxTitle r c " >> Composer " colNeon
          putText (r+1) (c+2) colText colBg False (w-4) text

------------------------------------------------------------------------
-- Footer
------------------------------------------------------------------------
fItem : Int -> Int -> String -> String -> IO ()
fItem row col key label = do
  putText row col colAmber colPanel True (cast (length key)) key
  putText row (col + cast (length key)) colText colPanel False (cast (length label)) label

drawFooter : Int -> Int -> IO ()
drawFooter row w = do
  clearRow row 0 w colPanel
  fItem row 1 "Aq" " Quit  "
  fItem row 9 "f1" " Help  "
  fItem row 17 "As" " Send  "
  fItem row 25 "f2" " Export  "
  fItem row 35 "f3" " Observatory  "
  fItem row 51 "f4" " Motion  "
  fItem row 61 "f5" " New Session  "
  fItem row 77 "f8" " Aperture  "
  fItem row 89 "f9" " Ingest  "
  fItem row 99 "f10" " Archive  "
  fItem row 111 "f11" " Runtime Chyron  "
  fItem row 131 "Ap" " palette"

------------------------------------------------------------------------
-- Help modal overlay
------------------------------------------------------------------------
drawHelpModal : Int -> Int -> IO ()
drawHelpModal scrW scrH = do
  let mw = min 72 (scrW - 4)
  let mh = min 28 (scrH - 4)
  let mr = max 1 ((scrH - mh) `div` 2)
  let mc = max 1 ((scrW - mw) `div` 2)
  drawBoxBg mr mc mw mh colModalBd colModalBg
  boxTitleBg mr mc " EDEN/Adam Help " colAmber colModalBg
  let cw = mw - 4
  let cc = mc + 2
  let r0 = mr + 1
  putText r0 cc colNeon colModalBg True cw "Keybindings"
  putText (r0+1) cc colAmber colModalBg True cw "  Ctrl+Q / F12"
  putText (r0+1) (cc+16) colText colModalBg False (cw-16) "Quit"
  putText (r0+2) cc colAmber colModalBg True cw "  Esc"
  putText (r0+2) (cc+16) colText colModalBg False (cw-16) "Dismiss modal / Quit"
  putText (r0+3) cc colAmber colModalBg True cw "  Enter"
  putText (r0+3) (cc+16) colText colModalBg False (cw-16) "Send message to Adam"
  putText (r0+4) cc colAmber colModalBg True cw "  Backspace"
  putText (r0+4) (cc+16) colText colModalBg False (cw-16) "Delete last character"
  putText (r0+5) cc colAmber colModalBg True cw "  Ctrl+S"
  putText (r0+5) (cc+16) colText colModalBg False (cw-16) "Open config modal"
  putText (r0+7) cc colNeon colModalBg True cw "Feedback (after Adam responds)"
  putText (r0+8) cc colAmber colModalBg True cw "  a"
  putText (r0+8) (cc+16) colText colModalBg False (cw-16) "Accept response"
  putText (r0+9) cc colAmber colModalBg True cw "  r"
  putText (r0+9) (cc+16) colText colModalBg False (cw-16) "Reject response"
  putText (r0+10) cc colAmber colModalBg True cw "  e"
  putText (r0+10) (cc+16) colText colModalBg False (cw-16) "Edit response"
  putText (r0+11) cc colAmber colModalBg True cw "  s"
  putText (r0+11) (cc+16) colText colModalBg False (cw-16) "Skip feedback"
  putText (r0+13) cc colNeon colModalBg True cw "Commands (type in composer)"
  putText (r0+14) cc colIce colModalBg False cw "  /help      Show this help screen"
  putText (r0+15) cc colIce colModalBg False cw "  /quit      Quit the TUI"
  putText (r0+16) cc colIce colModalBg False cw "  /config    Session configuration"
  putText (r0+17) cc colIce colModalBg False cw "  /stats     Show graph statistics"
  putText (r0+18) cc colIce colModalBg False cw "  /memes     List all memes"
  putText (r0+19) cc colIce colModalBg False cw "  /regard    Show regard scores"
  putText (r0+20) cc colIce colModalBg False cw "  /hum       Show hum status"
  putText (r0+21) cc colIce colModalBg False cw "  /export    Export graph JSON"
  putText (r0+22) cc colIce colModalBg False cw "  /atlas     Browse conversation archive"
  putText (r0+23) cc colIce colModalBg False cw "  /archive   Browse conversation archive"
  if r0+25 < mr+mh-1
    then putText (r0+25) cc colMuted colModalBg False cw "Press any key to dismiss"
    else pure ()

------------------------------------------------------------------------
-- Config modal overlay
------------------------------------------------------------------------
showConfigItems : UIState -> Nat -> Int -> Int -> Int -> Int -> IO ()
showConfigItems ui cursor r0 cc cw rEnd = do
  be <- readIORef ui.uiBackend
  prof <- readIORef ui.uiSessProf
  let items : List (String, String)
      items = [ ("Backend",          show be)
              , ("Inference Mode",   show prof.spMode)
              , ("Token Budget",     show prof.spBudget)
              , ("Retrieval Depth",  show prof.spRetrDepth)
              , ("Max Output",       show prof.spMaxOutput)
              , ("Temperature",      showD prof.spTemp)
              , ("Response Cap",     show prof.spRespCap)
              , ("History Turns",    show prof.spHistTurns)
              , ("Low Motion",       show prof.spLowMotion)
              , ("Debug",            show prof.spDebug)
              ]
  drawItemsAt r0 cc cw 0 cursor items rEnd
  where
    drawItemsAt : Int -> Int -> Int -> Nat -> Nat -> List (String, String) -> Int -> IO ()
    drawItemsAt row cc' cw' idx cur [] rEnd' = pure ()
    drawItemsAt row cc' cw' idx cur ((lbl, val) :: rest) rEnd' =
      if row >= rEnd' then pure ()
      else do
        let sel = idx == cur
        let fg = if sel then colAmber else colText
        let marker = if sel then "> " else "  "
        putText row cc' fg colModalBg sel cw' (marker ++ lbl ++ ": " ++ val)
        drawItemsAt (row+1) cc' cw' (idx+1) cur rest rEnd'

drawConfigModal : UIState -> Nat -> Int -> Int -> IO ()
drawConfigModal ui cursor scrW scrH = do
  let mw = min 64 (scrW - 4)
  let mh = min 18 (scrH - 4)
  let mr = max 1 ((scrH - mh) `div` 2)
  let mc = max 1 ((scrW - mw) `div` 2)
  drawBoxBg mr mc mw mh colModalBd colModalBg
  boxTitleBg mr mc " Session Config " colNeon colModalBg
  let cw = mw - 4
  let cc = mc + 2
  let r0 = mr + 1
  showConfigItems ui cursor r0 cc cw (mr+mh-2)
  let hintRow = mr + mh - 2
  putText hintRow cc colMuted colModalBg False cw "Up/Down=navigate  Enter=toggle  Esc=dismiss"

------------------------------------------------------------------------
-- Atlas/Archive modal overlay
------------------------------------------------------------------------
drawAtlasItems : Int -> Int -> Int -> Nat -> Nat -> List (String, String, String, String) -> Int -> IO ()
drawAtlasItems row cc cw idx cur [] rEnd = pure ()
drawAtlasItems row cc cw idx cur ((sid, title, tc, created) :: rest) rEnd =
  if row >= rEnd then pure ()
  else do
    let sel = idx == cur
    let fg = if sel then colAmber else colText
    let marker = if sel then "> " else "  "
    let line = marker ++ padRight 20 (substr 0 18 sid) ++ " "
                      ++ padRight 18 (substr 0 16 title) ++ " "
                      ++ padRight 6 tc ++ " "
                      ++ substr 0 20 created
    putText row cc fg colModalBg sel cw line
    drawAtlasItems (row+1) cc cw (idx+1) cur rest rEnd

drawAtlasModal : UIState -> Nat -> Nat -> Int -> Int -> IO ()
drawAtlasModal ui cursor soff scrW scrH = do
  let mw = min 80 (scrW - 4)
  let mh = min 22 (scrH - 4)
  let mr = max 1 ((scrH - mh) `div` 2)
  let mc = max 1 ((scrW - mw) `div` 2)
  drawBoxBg mr mc mw mh colModalBd colModalBg
  boxTitleBg mr mc " Conversation Atlas " colViolet colModalBg
  let cw = mw - 4
  let cc = mc + 2
  let r0 = mr + 1
  -- Load sessions from store
  sessions <- readIORef ui.uiEnv.store.sessions
  turns <- readIORef ui.uiEnv.store.turns
  let mkItem : Session -> (String, String, String, String)
      mkItem sess = (show sess.id, sess.title,
                     show (length (filter (\t => t.sessionId == sess.id) turns)),
                     show sess.createdAt)
  let items = map mkItem sessions
  case items of
    [] => do
      putText r0 cc colMuted colModalBg False cw "No sessions found."
      putText (r0+2) cc colMuted colModalBg False cw "Start a conversation to create a session."
    _ => do
      putText r0 cc colIce colModalBg True cw "ID                    Title              Turns  Created"
      sectionTitle (r0+1) cc cw "" colMuted
      let visibleH = mh - 5
      let visible = take (cast visibleH) (drop soff items)
      drawAtlasItems (r0+2) cc cw 0 (minus cursor soff) visible (mr+mh-2)
  let hintRow = mr + mh - 2
  putText hintRow cc colMuted colModalBg False cw "Up/Down=navigate  Esc=dismiss"

------------------------------------------------------------------------
-- Full frame render
------------------------------------------------------------------------
renderFrame : UIState -> IO ()
renderFrame ui = do
  ts <- getTermSize
  let w = cast {to=Int} ts.tsWidth
  let h = cast {to=Int} ts.tsHeight
  writeIORef ui.uiWidth w
  writeIORef ui.uiHeight h
  screenInit w h
  screenClear

  let actH = 10
  let actW = (w * 55) `div` 100
  let stC = actW + 1
  let stW = w - stC
  let rlRow = actH
  let bStart = actH + 1
  let fRow = h - 1
  let compH = 4
  let compRow = fRow - compH
  let bH = compRow - bStart
  let lW = (w * 60) `div` 100
  let rC = lW + 1
  let rW = w - rC
  let mgH = bH `div` 3
  let tRow = bStart + mgH
  let rsRow = tRow + 1
  let rsH = bH - mgH - 1

  let deckH = fRow - bStart  -- total left column height

  drawActions 0 0 actW
  drawStatusPanels ui 0 stC stW
  drawRuntimeLine ui rlRow w
  -- Outer amber border (chat_deck) wrapping dialogue + composer
  drawBox bStart 0 lW deckH colAmber
  -- Dialogue tape (rose border) inside chat_deck
  drawDialogue ui (bStart + 1) 1 (lW - 2) (bH - 2)
  drawMemgraph ui bStart rC rW mgH
  drawTabBar tRow rC rW
  drawReasoning ui rsRow rC rW rsH
  -- Composer inside chat_deck at bottom
  drawComposer ui compRow 1 (lW - 2) compH
  drawFooter fRow w

  -- Render modal overlays on top
  mode <- readIORef ui.uiMode
  case mode of
    Normal => pure ()
    HelpModal => drawHelpModal w h
    ConfigModal cur => drawConfigModal ui cur w h
    AtlasModal cur soff => drawAtlasModal ui cur soff w h

  screenPresent

------------------------------------------------------------------------
-- Command parsing
------------------------------------------------------------------------
isCommand : String -> Maybe String
isCommand s =
  let t = trim s
  in if isPrefixOf "/" t then Just (toLower t) else Nothing

------------------------------------------------------------------------
-- Input handling: Normal mode
------------------------------------------------------------------------
parseVerdict : Char -> Maybe Verdict
parseVerdict 'a' = Just Accept
parseVerdict 'r' = Just Reject
parseVerdict 'e' = Just Edit
parseVerdict 's' = Just Skip
parseVerdict _   = Nothing

handleNormalKey : UIState -> KeyEvent -> IO ()
handleNormalKey ui KeyF12 = writeIORef ui.uiQuit True
handleNormalKey ui (KeyCtrl 'q') = writeIORef ui.uiQuit True
handleNormalKey ui (KeyCtrl 'c') = writeIORef ui.uiQuit True
handleNormalKey ui (KeyCtrl 's') = writeIORef ui.uiMode (ConfigModal 0)
handleNormalKey ui KeyEscape = writeIORef ui.uiQuit True
handleNormalKey ui KeyEnter = do
  text <- readIORef ui.uiComposer
  if text == ""
    then pure ()
    else case isCommand text of
      Just "/quit" => writeIORef ui.uiQuit True
      Just "/help" => do
        writeIORef ui.uiComposer ""
        writeIORef ui.uiMode HelpModal
      Just "/config" => do
        writeIORef ui.uiComposer ""
        writeIORef ui.uiMode (ConfigModal 0)
      Just "/atlas" => do
        writeIORef ui.uiComposer ""
        writeIORef ui.uiMode (AtlasModal 0 0)
      Just "/archive" => do
        writeIORef ui.uiComposer ""
        writeIORef ui.uiMode (AtlasModal 0 0)
      Just "/stats" => do
        writeIORef ui.uiComposer ""
        counts <- runEden ui.uiEnv eGraphCounts
        writeIORef ui.uiFeedback (Just
          ("memes=" ++ show counts.memeCount
          ++ " memodes=" ++ show counts.memodeCount
          ++ " edges=" ++ show counts.edgeCount
          ++ " turns=" ++ show counts.turnCount
          ++ " feedback=" ++ show counts.feedbackCount))
      Just "/memes" => do
        writeIORef ui.uiComposer ""
        memes <- runEden ui.uiEnv eGetMemes
        let labels = map (\m => m.label ++ "[" ++ show m.domain ++ "]") (take 10 memes)
        writeIORef ui.uiFeedback (Just (concat (intersperse ", " labels)))
      Just "/regard" => do
        writeIORef ui.uiComposer ""
        memes <- runEden ui.uiEnv eGetMemes
        let labels = map (\m =>
              let ns = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau 0.0
                  gm = MkGraphMetrics 0.5 0.4 0.3
                  rb = regardBreakdown defaultRegardWeights ns gm
              in m.label ++ "=" ++ showD rb.totalRegard) (take 8 memes)
        writeIORef ui.uiFeedback (Just (concat (intersperse " " labels)))
      Just "/hum" => do
        writeIORef ui.uiComposer ""
        hum <- runEden ui.uiEnv mBuildHum
        writeIORef ui.uiFeedback (Just
          ("hum: status=" ++ show hum.hpStatus
          ++ " turns=" ++ show hum.metrics.turnsCovered
          ++ " motifs=" ++ show hum.metrics.recurringItems))
      Just "/export" => do
        writeIORef ui.uiComposer ""
        path <- writeGraphExport ui.uiEnv.store ui.uiEnv.eid
        writeIORef ui.uiFeedback (Just ("exported: " ++ path))
      _ => do
        -- Normal message: execute turn
        idx <- readIORef ui.uiTurnIdx
        writeIORef ui.uiTurnIdx (idx + 1)
        writeIORef ui.uiComposer ""
        writeIORef ui.uiFeedback (Just "Adam is thinking...")
        renderFrame ui
        be <- readIORef ui.uiBackend
        let mp = ui.uiModelPath
        tr <- runEden ui.uiEnv (mExecuteTurnWith be mp idx text)
        entries <- readIORef ui.uiDialogue
        writeIORef ui.uiDialogue ((text, tr.mrResponse) :: entries)
        activeSet <- runEden ui.uiEnv (mRetrieve text)
        writeIORef ui.uiLastActive activeSet
        projs <- runEden ui.uiEnv mProject
        writeIORef ui.uiLastProj projs
        writeIORef ui.uiFeedback Nothing
        renderFrame ui
        fbKey <- readKey 10000
        case fbKey of
          KeyChar c => case parseVerdict c of
            Just v => do
              let turnId = MkId {a=TurnTag} ("turn-" ++ show (idx + 3))
              runEden ui.uiEnv (mProcessFeedback turnId v "")
              writeIORef ui.uiFeedback (Just ("recorded: " ++ show v))
              hum <- runEden ui.uiEnv mBuildHum
              writeHumFile hum
              writeIORef ui.uiLastHum (Just hum)
            Nothing => writeIORef ui.uiFeedback (Just "skipped")
          _ => writeIORef ui.uiFeedback (Just "skipped")
        renderFrame ui
        -- Brief pause so user sees feedback result, then clear it
        _ <- readKey 1500
        writeIORef ui.uiFeedback Nothing
handleNormalKey ui KeyBackspace = do
  text <- readIORef ui.uiComposer
  case strM text of
    StrNil => pure ()
    StrCons _ _ =>
      let l = length text
      in writeIORef ui.uiComposer (substr 0 (cast (minus l 1)) text)
handleNormalKey ui (KeyChar c) = do
  text <- readIORef ui.uiComposer
  -- Check for help shortcut: ? or h when composer is empty
  if text == "" && (c == '?' || c == 'h')
    then writeIORef ui.uiMode HelpModal
    else do
      let newText = text ++ singleton c
      writeIORef ui.uiComposer newText
      -- Paste detection: drain any rapid input burst
      pasted <- drainPaste 10
      if pasted == ""
        then pure ()
        else do
          cur <- readIORef ui.uiComposer
          writeIORef ui.uiComposer (cur ++ pasted)
handleNormalKey ui KeyF1 = writeIORef ui.uiMode HelpModal
handleNormalKey _ _ = pure ()

------------------------------------------------------------------------
-- Input handling: Help modal
------------------------------------------------------------------------
handleHelpKey : UIState -> KeyEvent -> IO ()
handleHelpKey ui _ = writeIORef ui.uiMode Normal

------------------------------------------------------------------------
-- Input handling: Config modal
------------------------------------------------------------------------
handleConfigKey : UIState -> Nat -> KeyEvent -> IO ()
handleConfigKey ui cursor KeyEscape = writeIORef ui.uiMode Normal
handleConfigKey ui cursor (KeyCtrl 'q') = writeIORef ui.uiQuit True
handleConfigKey ui cursor KeyUp =
  if cursor > 0
    then writeIORef ui.uiMode (ConfigModal (minus cursor 1))
    else pure ()
handleConfigKey ui cursor KeyDown =
  if cursor < 9
    then writeIORef ui.uiMode (ConfigModal (cursor + 1))
    else pure ()
handleConfigKey ui cursor KeyEnter = do
  be <- readIORef ui.uiBackend
  prof <- readIORef ui.uiSessProf
  case cursor of
    0 => do
      let newBe = case be of Mock => Claude; Claude => MLX; MLX => Mock
      writeIORef ui.uiBackend newBe
    1 => do
      let newMode = case prof.spMode of
            Manual => RuntimeAuto; RuntimeAuto => AdamAuto; AdamAuto => Manual
      writeIORef ui.uiSessProf ({ spMode := newMode } prof)
      updateSessionProfile ui.uiSessMeta ui.uiEnv.sid "mode" (show newMode)
    2 => do
      let newBudget = case prof.spBudget of
            Tight => Balanced; Balanced => Wide; Wide => Tight
      writeIORef ui.uiSessProf ({ spBudget := newBudget } prof)
      updateSessionProfile ui.uiSessMeta ui.uiEnv.sid "budget_mode" (show newBudget)
    3 => do
      let nd = if prof.spRetrDepth >= 20 then 4 else prof.spRetrDepth + 1
      writeIORef ui.uiSessProf ({ spRetrDepth := nd } prof)
    4 => do
      let no = if prof.spMaxOutput >= 4096 then 256 else prof.spMaxOutput + 256
      writeIORef ui.uiSessProf ({ spMaxOutput := no } prof)
    5 => do
      let nt = if prof.spTemp >= 1.95 then 0.1 else prof.spTemp + 0.1
      writeIORef ui.uiSessProf ({ spTemp := nt } prof)
    6 => do
      let nr = if prof.spRespCap >= 10000 then 500 else prof.spRespCap + 500
      writeIORef ui.uiSessProf ({ spRespCap := nr } prof)
    7 => do
      let nh = if prof.spHistTurns >= 20 then 1 else prof.spHistTurns + 1
      writeIORef ui.uiSessProf ({ spHistTurns := nh } prof)
    8 => writeIORef ui.uiSessProf ({ spLowMotion := not prof.spLowMotion } prof)
    9 => writeIORef ui.uiSessProf ({ spDebug := not prof.spDebug } prof)
    _ => pure ()
handleConfigKey ui _ _ = pure ()

------------------------------------------------------------------------
-- Input handling: Atlas modal
------------------------------------------------------------------------
handleAtlasKey : UIState -> Nat -> Nat -> KeyEvent -> IO ()
handleAtlasKey ui cursor soff KeyEscape = writeIORef ui.uiMode Normal
handleAtlasKey ui cursor soff (KeyCtrl 'q') = writeIORef ui.uiQuit True
handleAtlasKey ui cursor soff KeyUp = do
  if cursor > 0
    then do
      let nc = minus cursor 1
      let ns = if nc < soff then nc else soff
      writeIORef ui.uiMode (AtlasModal nc ns)
    else pure ()
handleAtlasKey ui cursor soff KeyDown = do
  sessions <- readIORef ui.uiEnv.store.sessions
  let maxIdx = minus (length sessions) 1
  if cursor < maxIdx
    then do
      let nc = cursor + 1
      h <- readIORef ui.uiHeight
      let visH = cast {to=Nat} (max 1 (h - 10))
      let ns = if nc >= soff + visH then soff + 1 else soff
      writeIORef ui.uiMode (AtlasModal nc ns)
    else pure ()
handleAtlasKey ui cursor soff KeyEnter = do
  sessions <- readIORef ui.uiEnv.store.sessions
  case drop cursor sessions of
    (sess :: _) => do
      turns <- readIORef ui.uiEnv.store.turns
      let tc = length (filter (\t => t.sessionId == sess.id) turns)
      writeIORef ui.uiFeedback (Just
        ("Session: " ++ sess.title ++ " (" ++ show sess.id ++ ") "
        ++ show tc ++ " turns"))
      writeIORef ui.uiMode Normal
    [] => pure ()
handleAtlasKey ui _ _ _ = pure ()

------------------------------------------------------------------------
-- Top-level key dispatch
------------------------------------------------------------------------
handleKey : UIState -> KeyEvent -> IO ()
handleKey ui key = do
  mode <- readIORef ui.uiMode
  case mode of
    Normal => handleNormalKey ui key
    HelpModal => handleHelpKey ui key
    ConfigModal cur => handleConfigKey ui cur key
    AtlasModal cur soff => handleAtlasKey ui cur soff key

------------------------------------------------------------------------
-- Main loop
------------------------------------------------------------------------
tuiLoop : UIState -> IO ()
tuiLoop ui = do
  key <- readKey 500
  case key of
    KeyNone => do
      quit <- readIORef ui.uiQuit
      if quit
        then pure ()
        else tuiLoop ui
    k => do
      handleKey ui k
      quit <- readIORef ui.uiQuit
      if quit
        then pure ()
        else do
          renderFrame ui
          tuiLoop ui

------------------------------------------------------------------------
-- Entry point
------------------------------------------------------------------------
export
runTUIWith : Backend -> Maybe String -> String -> IO ()
runTUIWith be mp principles = do
  store <- newStore
  ts <- currentTimestamp

  -- Open SQLite database
  mdb <- openDB "data/eden.db"
  case mdb of
    Just db => writeIORef store.dbHandle (Just db)
    Nothing => pure ()

  -- Load or create experiment
  case mdb of
    Just db => do _ <- loadFromDB db store; pure ()
    Nothing => pure ()
  exps <- readIORef store.experiments
  eid <- case exps of
    (e :: _) => pure e.id
    [] => do
      exp <- createExperiment store "tui" "tui" Blank ts
      _ <- upsertMeme store exp.id "Curiosity" "Drive to explore" Behavior SeedSource Global ts
      _ <- upsertMeme store exp.id "Honesty" "Truthful communication" Behavior SeedSource Global ts
      _ <- upsertMeme store exp.id "Clarity" "Clear explanations" Behavior SeedSource Global ts
      pure exp.id
  let agentId = MkId {a=AgentTag} "adam-01"
  sess <- createSession store eid agentId "TUI session" ts
  turns <- readIORef store.turns
  env <- newEdenEnv store eid sess.id ts principles

  -- Session metadata and profile
  sessMeta <- newSessionMetaStore
  sessProf <- getSessionProfile sessMeta sess.id
  sessProfRef <- newIORef sessProf

  -- UI state refs
  turnIdx <- newIORef (the Nat 0)
  composer <- newIORef ""
  dialogue <- newIORef (the (List (String, String)) [])
  feedback <- newIORef (the (Maybe String) Nothing)
  lastActive <- newIORef (the (List CandidateScore) [])
  lastHum <- newIORef (the (Maybe HumPayload) Nothing)
  lastBudget <- newIORef (the (Maybe BudgetEstimate) Nothing)
  lastProj <- newIORef (the (List MemeProjection) [])
  focusPanel <- newIORef (the Nat 0)
  scrollOff <- newIORef (the Nat 0)
  quit <- newIORef False
  uiW <- newIORef (the Int 120)
  uiH <- newIORef (the Int 30)
  uiModeRef <- newIORef Normal
  beRef <- newIORef be

  let ui = MkUIState env beRef mp turnIdx composer dialogue feedback
                     lastActive lastHum lastBudget lastProj
                     focusPanel scrollOff quit uiW uiH uiModeRef
                     sessMeta sessProfRef

  -- Run graph audit at session start (normalization + taxonomy)
  _ <- runEden env runSessionStartAudit

  ok <- enterTUI
  if ok
    then do renderFrame ui; tuiLoop ui; leaveTUI
            -- Close DB on exit
            mdb2 <- readIORef store.dbHandle
            case mdb2 of
              Just db => do closeDB db; pure ()
              Nothing => pure ()
            putStrLn "Goodbye."
    else putStrLn "Failed to initialize terminal."

export
runTUI : IO ()
runTUI = runTUIWith Mock Nothing "You are a curious, honest thinker."
