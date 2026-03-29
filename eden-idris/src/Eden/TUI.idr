||| EDEN TUI application.
|||
||| Matches Python Textual layout: action strip, status panels,
||| dialogue tape, memgraph, reasoning tabs, composer, footer.
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

------------------------------------------------------------------------
-- Globals (avoids UIState field additions that crash codegen)
------------------------------------------------------------------------
gBackend : IORef Backend
gBackend = unsafePerformIO (newIORef Mock)
gModelPath : IORef (Maybe String)
gModelPath = unsafePerformIO (newIORef Nothing)

------------------------------------------------------------------------
-- UI State
------------------------------------------------------------------------
public export
record UIState where
  constructor MkUIState
  uiEnv        : EdenEnv
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

boxTitle : Int -> Int -> String -> RGB -> IO ()
boxTitle r c title fg = putText r (c+2) fg colBg True (cast (length title)) title

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
  be <- readIORef gBackend
  idx <- readIORef ui.uiTurnIdx
  counts <- runEden ui.uiEnv eGraphCounts
  active <- readIORef ui.uiLastActive
  let pw = tw `div` 3
  drawPanel r c pw 10 "Context" colAmber
    ["No estimate", "yet", "Type to arm.", "Deck=F6"]
  drawPanel r (c+pw) pw 10 "Live Turn Status" colAmber
    [ "Adam status", "phase=start"
    , "Start here: type", "below, press Enter"
    , "to send, or press F9"
    , "model=" ++ show be, "reasoning=quiet"
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
  be <- readIORef gBackend
  idx <- readIORef ui.uiTurnIdx
  clearRow row 0 w colPanel
  putText row 1 colIce colPanel False (w-1)
    ("runtime=Adam / " ++ show be ++ " stage=n/a session=arming profile=pending focus=compos...")

------------------------------------------------------------------------
-- Dialogue tape (bordered)
------------------------------------------------------------------------
drawDialogue : UIState -> Int -> Int -> Int -> Int -> IO ()
drawDialogue ui r c w h = do
  clearRect r h c w colBg
  drawBox r c w h colRose
  boxTitle r c " Dialogue Tape " colRose
  sectionTitle (r+1) (c+1) (w-2) "Adam Dialogue" colAmber
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
    _  => drawEntries cs 0 (take (cast (natDiv (cast ch) 2)) (reverse entries)) cs ch (c+1) (w-2)
  where
    drawEntries : Int -> Nat -> List (String, String) -> Int -> Int -> Int -> Int -> IO ()
    drawEntries row idx [] s ch c' cw = pure ()
    drawEntries row idx ((u, a) :: rest) s ch c' cw =
      if row >= s + ch then pure ()
      else do
        clearRow row c' cw colBg
        let tag = "[you T" ++ show idx ++ "] "
        putText row (c'+1) colAmber colBg True (cw-1) tag
        putText row (c' + 1 + cast (length tag)) colText colBg False (cw - 1 - cast (length tag)) u
        if row+1 < s + ch
          then do
            clearRow (row+1) c' cw colBg
            let at = "[adam T" ++ show idx ++ "] "
            putText (row+1) (c'+1) colRose colBg False (cw-1) at
            putText (row+1) (c' + 1 + cast (length at)) colText colBg False (cw - 1 - cast (length at)) a
            drawEntries (row+2) (idx+1) rest s ch c' cw
          else pure ()

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
  screenSetCP row (col+1) 9679 colAmber colPanel False  -- ● bullet
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
  boxTitle r c " >> Composer " colNeon
  text <- readIORef ui.uiComposer
  if text == ""
    then do
      putText (r+1) (c+2) colMuted colBg False (w-4)
        "Message Adam here. Ask a question, continue the session, or correct the draft. Enter sends."
      if h > 2
        then putText (r+2) (c+2) colMuted colBg False (w-4) "F9 ingests a document first if needed."
        else pure ()
    else putText (r+1) (c+2) colText colBg False (w-4) text

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
  screenPresent

------------------------------------------------------------------------
-- Input handling
------------------------------------------------------------------------
parseVerdict : Char -> Maybe Verdict
parseVerdict 'a' = Just Accept
parseVerdict 'r' = Just Reject
parseVerdict 'e' = Just Edit
parseVerdict 's' = Just Skip
parseVerdict _   = Nothing

handleKey : UIState -> KeyEvent -> IO ()
handleKey ui KeyF12 = writeIORef ui.uiQuit True
handleKey ui (KeyCtrl 'q') = writeIORef ui.uiQuit True
handleKey ui (KeyCtrl 'c') = writeIORef ui.uiQuit True
handleKey ui KeyEscape = writeIORef ui.uiQuit True
handleKey ui KeyEnter = do
  text <- readIORef ui.uiComposer
  if text == ""
    then pure ()
    else do
    idx <- readIORef ui.uiTurnIdx
    writeIORef ui.uiTurnIdx (idx + 1)
    writeIORef ui.uiFeedback (Just "generating...")
    renderFrame ui
    be <- readIORef gBackend
    mp <- readIORef gModelPath
    tr <- runEden ui.uiEnv (mExecuteTurnWith be mp idx text)
    entries <- readIORef ui.uiDialogue
    writeIORef ui.uiDialogue ((text, tr.mrResponse) :: entries)
    writeIORef ui.uiComposer ""
    activeSet <- runEden ui.uiEnv (mRetrieve text)
    writeIORef ui.uiLastActive activeSet
    projs <- runEden ui.uiEnv mProject
    writeIORef ui.uiLastProj projs
    writeIORef ui.uiFeedback (Just "feedback? (a/r/e/s)")
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
handleKey ui KeyBackspace = do
  text <- readIORef ui.uiComposer
  case strM text of
    StrNil => pure ()
    StrCons _ _ =>
      let l = length text
      in writeIORef ui.uiComposer (substr 0 (cast (minus l 1)) text)
handleKey ui (KeyChar c) = do
  text <- readIORef ui.uiComposer
  writeIORef ui.uiComposer (text ++ singleton c)
handleKey ui KeyF1 =
  writeIORef ui.uiFeedback (Just "EDEN/Adam TUI | Esc/Ctrl+Q=quit | Enter=send")
handleKey _ _ = pure ()

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
runTUIWith : Backend -> Maybe String -> IO ()
runTUIWith be mp = do
  writeIORef gBackend be
  writeIORef gModelPath mp
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
  env <- newEdenEnv store eid sess.id ts
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
  let ui = MkUIState env turnIdx composer dialogue feedback
                     lastActive lastHum lastBudget lastProj
                     focusPanel scrollOff quit uiW uiH
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
runTUI = runTUIWith Mock Nothing
