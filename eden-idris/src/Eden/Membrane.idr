||| Membrane: post-generation control surface.
|||
||| NOT a planner. Acts AFTER generation to sanitize, bound, and record
||| the operator-facing response. Each transformation is a membrane event.
module Eden.Membrane

import Data.List
import Data.String
import Eden.Types

------------------------------------------------------------------------
-- Membrane result
------------------------------------------------------------------------

public export
record MembraneResult where
  constructor MkMembraneResult
  cleanedText   : String
  events        : List MembraneEventType
  reasoningText : String

------------------------------------------------------------------------
-- Individual passes
------------------------------------------------------------------------

||| Strip control characters (keep \n \r \t).
export
stripControlChars : String -> (String, Bool)
stripControlChars s =
  let cs = unpack s
      cleaned = filter (\c => c == '\n' || c == '\r' || c == '\t' || ord c >= 0x20) cs
      result = pack cleaned
  in (result, length result /= length s)

||| Check if a line starts with a scaffold label.
export
isScaffoldLabel : String -> Bool
isScaffoldLabel s =
  let t = ltrim s
  in isPrefixOf "Answer:" t
  || isPrefixOf "Basis:" t
  || isPrefixOf "Next Step:" t
  || isPrefixOf "Response:" t

||| Strip leading scaffold label from first line.
export
stripAnswerLabel : String -> (String, Bool)
stripAnswerLabel s =
  let ls = lines s
  in case ls of
       [] => (s, False)
       (first :: rest) =>
         let t = ltrim first
         in if isPrefixOf "Answer:" t
              then (ltrim (substr 7 (cast (length t)) t) ++ "\n" ++ unlines rest, True)
            else if isPrefixOf "Response:" t
              then (ltrim (substr 9 (cast (length t)) t) ++ "\n" ++ unlines rest, True)
            else (s, False)

||| Split out reasoning block (delimited by <think>...</think>).
||| Handles both formats:
|||   - "reasoning text</think>body"  (reasoning before closing tag)
|||   - "<think>reasoning</think>body" (standard think wrapper)
export
splitReasoning : String -> (String, String, Bool)
splitReasoning s =
  -- Try <think>...</think> format first
  if isPrefixOf "<think>" (ltrim s)
    then let after = ltrim (substr 7 (length s) (ltrim s))
         in case findClose (unpack after) [] of
              Just (reasoning, body) => (trim reasoning, trim body, True)
              Nothing => ("", s, False)
    else -- Try old format: reasoning</think>body
      case break (== '<') (unpack s) of
        (_, []) => ("", s, False)
        (before, rest) =>
          let restStr = pack rest
          in if isPrefixOf "</think>" restStr
               then (trim (pack before),
                     trim (substr 8 (cast (length restStr)) restStr),
                     True)
             else ("", s, False)
  where
    findClose : List Char -> List Char -> Maybe (String, String)
    findClose [] acc = Nothing
    findClose ('<' :: '/' :: 't' :: 'h' :: 'i' :: 'n' :: 'k' :: '>' :: rest) acc =
      Just (pack (reverse acc), pack rest)
    findClose (c :: rest) acc = findClose rest (c :: acc)

||| Strip support section (everything after "Basis:" or "Next Step:" line).
export
stripSupportSection : String -> (String, Bool)
stripSupportSection s =
  let ls = lines s
      kept = takeWhile (\l => not (isPrefixOf "Basis:" (ltrim l))
                            && not (isPrefixOf "Next Step:" (ltrim l))) ls
  in if length kept == length ls
     then (s, False)
     else (unlines kept, True)

||| Collapse runs of 3+ newlines into 2.
export
normalizeNewlines : String -> String
normalizeNewlines s = pack (go (unpack s))
  where
    go : List Char -> List Char
    go [] = []
    go ('\n' :: '\n' :: '\n' :: rest) = '\n' :: '\n' :: go (dropWhile (== '\n') rest)
    go (c :: rest) = c :: go rest

||| Enforce character cap (minimum 400). Adds "..." if truncated.
export
enforceCharCap : Nat -> String -> (String, Bool)
enforceCharCap cap s =
  let effectiveCap = max 400 cap
  in if length s <= effectiveCap
     then (s, False)
     else (substr 0 (cast (minus effectiveCap 1)) s ++ "...", True)

------------------------------------------------------------------------
-- Full membrane pipeline
------------------------------------------------------------------------

||| Apply the complete membrane pipeline.
||| Order: control chars -> reasoning split -> support strip ->
|||        answer label -> normalize newlines -> char cap
public export
applyMembrane : (responseCharCap : Nat) -> String -> MembraneResult
applyMembrane cap raw =
  let -- Step 1: control chars
      (s1, e1) = stripControlChars (trim raw)
      ev1 = if e1 then [ControlCharStripped] else []
      -- Step 2: reasoning split
      (reasoning, s2, e2) = splitReasoning s1
      ev2 = if e2 then [ReasoningSplit] else []
      -- Step 3: support section
      (s3, e3) = stripSupportSection s2
      ev3 = if e3 then [SupportStripped] else []
      -- Step 4: answer label
      (s4, e4) = stripAnswerLabel s3
      ev4 = if e4 then [LabelStripped] else []
      -- Step 5: normalize newlines
      s5 = normalizeNewlines (trim s4)
      -- Step 6: character cap
      (s6, e6) = enforceCharCap cap s5
      ev6 = if e6 then [Trimmed] else []
      -- Step 7: fail-closed — reject reasoning-only responses
      (s7, ev7) = if trim s6 == ""
                    then ("(Response contained only reasoning with no operator-facing content)", [Trimmed])
                    else (s6, [])
      allEvents = ev1 ++ ev2 ++ ev3 ++ ev4 ++ ev6 ++ ev7
      finalEvents = if isNil allEvents then [Passthrough] else allEvents
  in MkMembraneResult s7 finalEvents reasoning
