||| Text indexer: extracts memes from conversation text.
|||
||| After each turn, the indexer scans both user input and Adam's response
||| for concept references. New concepts become memes; existing concepts
||| get their usage count bumped. Co-occurring concepts get edges.
module Eden.Indexer

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Store.InMemory
import Eden.TermIO
import System.File.ReadWrite

%default covering

------------------------------------------------------------------------
-- Simple keyword extraction
------------------------------------------------------------------------

||| Known concept patterns to detect in text.
||| In production this would use embeddings; here we use keyword matching.
export
||| Each entry is (keyword_to_match, canonical_label, domain).
||| Multiple keywords can map to the same canonical label.
knownConcepts : List (String, String, Domain)
knownConcepts =
  [ ("curiosity", "Curiosity", Behavior), ("curious", "Curiosity", Behavior)
  , ("honesty", "Honesty", Behavior), ("honest", "Honesty", Behavior)
  , ("clarity", "Clarity", Behavior), ("clear", "Clarity", Behavior)
  , ("empathy", "Empathy", Behavior), ("empathetic", "Empathy", Behavior)
  , ("patience", "Patience", Behavior), ("patient", "Patience", Behavior)
  , ("integrity", "Integrity", Behavior)
  , ("reasoning", "Reasoning", Knowledge), ("reason", "Reasoning", Knowledge)
  , ("logic", "Logic", Knowledge), ("logical", "Logic", Knowledge)
  , ("physics", "Physics", Knowledge), ("physical", "Physics", Knowledge)
  , ("mathematics", "Mathematics", Knowledge), ("math", "Mathematics", Knowledge)
  , ("science", "Science", Knowledge), ("scientific", "Science", Knowledge)
  , ("philosophy", "Philosophy", Knowledge), ("philosophical", "Philosophy", Knowledge)
  , ("ethics", "Ethics", Knowledge), ("ethical", "Ethics", Knowledge)
  , ("language", "Language", Knowledge), ("linguistic", "Language", Knowledge)
  , ("creativity", "Creativity", Behavior), ("creative", "Creativity", Behavior)
  , ("learning", "Learning", Behavior), ("learn", "Learning", Behavior)
  , ("truth", "Truth", Knowledge), ("truthful", "Truth", Knowledge)
  , ("understanding", "Understanding", Knowledge), ("understand", "Understanding", Knowledge)
  , ("thinking", "Thinking", Knowledge), ("think", "Thinking", Knowledge)
  , ("knowledge", "Knowledge", Knowledge)
  , ("explore", "Exploration", Behavior), ("exploration", "Exploration", Behavior)
  , ("question", "Questioning", Knowledge), ("asking", "Questioning", Behavior)
  -- Jewish law and tradition
  , ("halakh", "Halakha", Knowledge), ("halacha", "Halakha", Knowledge)
  , ("talmud", "Talmud", Knowledge), ("talmudic", "Talmud", Knowledge)
  , ("torah", "Torah", Knowledge), ("biblical", "Torah", Knowledge)
  , ("mishnah", "Mishnah", Knowledge), ("midrash", "Midrash", Knowledge)
  , ("golem", "Golem", Knowledge), ("golem of prague", "Golem", Knowledge)
  , ("malach", "Malach", Knowledge), ("angel", "Malach", Knowledge)
  , ("neshama", "Neshama", Knowledge), ("soul", "Neshama", Knowledge)
  , ("noahide", "Noahide Laws", Knowledge), ("seven laws", "Noahide Laws", Knowledge)
  , ("sanhedrin", "Sanhedrin", Knowledge), ("responsa", "Responsa", Knowledge)
  , ("rabbi", "Rabbinic Thought", Knowledge), ("rabbinic", "Rabbinic Thought", Knowledge)
  , ("chevrutah", "Chevrutah", Knowledge), ("chavruta", "Chevrutah", Knowledge)
  , ("tikkun", "Tikkun", Knowledge), ("redemption", "Redemption", Knowledge)
  , ("kabbalah", "Kabbalah", Knowledge), ("sefirot", "Kabbalah", Knowledge)
  , ("maimonides", "Maimonides", Knowledge), ("rambam", "Maimonides", Knowledge)
  -- AI governance and alignment
  , ("alignment", "AI Alignment", Knowledge), ("aligned", "AI Alignment", Knowledge)
  , ("governance", "AI Governance", Knowledge), ("regulation", "AI Governance", Knowledge)
  , ("liability", "Liability", Knowledge), ("tort", "Liability", Knowledge)
  , ("autonomous", "Autonomy", Knowledge), ("autonomy", "Autonomy", Knowledge)
  , ("consciousness", "Consciousness", Knowledge), ("sentien", "Consciousness", Knowledge)
  , ("accountability", "Accountability", Behavior), ("responsible", "Accountability", Behavior)
  , ("supervision", "Supervision", Behavior), ("oversight", "Supervision", Behavior)
  , ("bias", "Bias", Knowledge), ("fairness", "Fairness", Knowledge)
  , ("dignity", "Dignity", Knowledge), ("rights", "Rights", Knowledge)
  , ("justice", "Justice", Knowledge), ("equity", "Justice", Knowledge)
  , ("creator", "Creator Responsibility", Knowledge), ("creation", "Creation", Knowledge)
  , ("safety", "Safety", Knowledge), ("harm", "Harm Prevention", Knowledge)
  , ("consent", "Consent", Knowledge), ("agency", "Agency", Knowledge)
  ]

------------------------------------------------------------------------
-- Concept extraction
------------------------------------------------------------------------

||| Record of a concept found in text.
public export
record ExtractedConcept where
  constructor MkExtractedConcept
  ecLabel  : String
  ecDomain : Domain
  ecSource : SourceKind

||| Extract concepts from a text string by keyword matching.
export
extractConcepts : String -> SourceKind -> List ExtractedConcept
extractConcepts text sk =
  let lower = toLower text
      found = mapMaybe (\entry =>
        let (kw, lbl, dom) = entry
        in if isInfixOf kw lower
             then Just (MkExtractedConcept lbl dom sk)
             else Nothing) knownConcepts
      -- Deduplicate by canonical label (keep first occurrence)
      dedup = nubBy (\a, b => a.ecLabel == b.ecLabel) found
  in dedup

------------------------------------------------------------------------
-- Model-based concept extraction
------------------------------------------------------------------------

||| Parse a domain string to Domain. Accepts "knowledge" or "behavior".
parseDomain : String -> Maybe Domain
parseDomain s =
  let s' = toLower (trim s)
  in if s' == "knowledge" then Just Knowledge
     else if s' == "behavior" then Just Behavior
     else Nothing

||| Parse one line of model output in "label|domain" format.
parseConceptLine : SourceKind -> String -> Maybe ExtractedConcept
parseConceptLine sk line =
  let trimmed = trim line
  in if trimmed == "" then Nothing
     else case break (== '|') trimmed of
            (label, rest) =>
              if rest == "" then Nothing  -- no pipe found
              else let domStr = substr 1 (length rest) rest  -- drop the '|'
                   in case parseDomain domStr of
                        Just dom => Just (MkExtractedConcept (trim label) dom sk)
                        Nothing  => Nothing

||| Parse model output into a list of extracted concepts.
||| Expects one concept per line in "label|domain" format.
parseModelOutput : String -> SourceKind -> List ExtractedConcept
parseModelOutput output sk =
  let ls = lines output
      parsed = mapMaybe (parseConceptLine sk) ls
  in nubBy (\a, b => a.ecLabel == b.ecLabel) parsed

||| Strip ANSI escape sequences from subprocess output.
stripAnsi : String -> String
stripAnsi s = pack (go (unpack s))
  where
    go : List Char -> List Char
    go [] = []
    go (c :: '[' :: rest) =
      if c == chr 27
        then let skip : List Char -> List Char
                 skip [] = []
                 skip (x :: xs) = if isAlpha x then go xs else skip xs
             in skip rest
        else c :: '[' :: go rest
    go (c :: rest) =
      if c == chr 27 then go (drop 1 rest)
      else if ord c < 32 && c /= '\n' then go rest
      else c :: go rest

||| Build the extraction prompt for Claude.
extractionPrompt : String -> String
extractionPrompt text =
  "Extract the key concepts from the following text. "
  ++ "For each concept, output exactly one line in the format: label|domain\n"
  ++ "where domain is either 'knowledge' or 'behavior'.\n"
  ++ "- 'knowledge' = factual topics, fields of study, ideas, entities\n"
  ++ "- 'behavior' = traits, dispositions, actions, values\n"
  ++ "Output ONLY the label|domain lines, nothing else. No numbering, no bullets, no explanation.\n"
  ++ "The text may be in English, Hebrew, or mixed. Extract concepts in their natural language.\n\n"
  ++ text

||| Extract concepts via the Claude CLI model.
||| Writes text to a temp file, calls claude, parses the output.
||| Falls back to keyword extraction if the model call fails.
export
extractConceptsViaModel : String -> SourceKind -> IO (List ExtractedConcept)
extractConceptsViaModel text sk = do
  let prompt = extractionPrompt text
  _ <- writeFile "data/eden_extract.tmp" prompt
  (output, exitCode) <- runCommand ("cat data/eden_extract.tmp | claude --model sonnet")
  rearmTerminal
  if exitCode /= 0 || trim output == ""
    then pure (extractConcepts text sk)  -- fallback to keywords
    else let cleaned = stripAnsi (trim output)
             concepts = parseModelOutput cleaned sk
         in if null concepts
              then pure (extractConcepts text sk)  -- fallback if parsing yielded nothing
              else pure concepts

------------------------------------------------------------------------
-- Index result
------------------------------------------------------------------------

public export
record IndexOutcome where
  constructor MkIndexOutcome
  ioNewMemes     : Nat
  ioUpdatedMemes : Nat
  ioNewEdges     : Nat
  ioConceptNames : List String

------------------------------------------------------------------------
-- Text indexing pipeline
------------------------------------------------------------------------

||| Index a turn's text into the graph.
||| Extracts concepts from user text and adam response,
||| upserts memes, and creates co-occurrence edges.
export
indexTurn : StoreState -> ExperimentId
         -> String -> String -> Timestamp
         -> IO IndexOutcome
indexTurn store eid userText adamText ts = do
  let userConcepts = extractConcepts userText TurnUser
      adamConcepts = extractConcepts adamText TurnAdam
      allConcepts  = nubBy (\a, b => a.ecLabel == b.ecLabel) (userConcepts ++ adamConcepts)

  -- Upsert all found concepts as memes
  memes <- traverse (\c =>
    upsertMeme store eid c.ecLabel c.ecLabel c.ecDomain c.ecSource Global ts) allConcepts

  -- Create co-occurrence edges between all pairs
  let pairs = allPairs memes
  edges <- traverse (\pair => do
    let (a, b) = pair
    createEdge store eid MemeNode (show a.id) MemeNode (show b.id) CoOccursWith 0.5 ts) pairs

  pure (MkIndexOutcome
    (length allConcepts)
    0  -- simplified: no separate tracking
    (length edges)
    (map ecLabel allConcepts))

  where
    allPairs : List a -> List (a, a)
    allPairs [] = []
    allPairs (x :: xs) = map (\y => (x, y)) xs ++ allPairs xs

||| Index a turn's text into the graph using model-based extraction.
||| Falls back to keyword extraction if the model call fails.
export
indexTurnWithModel : StoreState -> ExperimentId
                   -> String -> String -> Timestamp
                   -> IO IndexOutcome
indexTurnWithModel store eid userText adamText ts = do
  userConcepts <- extractConceptsViaModel userText TurnUser
  adamConcepts <- extractConceptsViaModel adamText TurnAdam
  let allConcepts = nubBy (\a, b => a.ecLabel == b.ecLabel) (userConcepts ++ adamConcepts)

  -- Upsert all found concepts as memes
  memes <- traverse (\c =>
    upsertMeme store eid c.ecLabel c.ecLabel c.ecDomain c.ecSource Global ts) allConcepts

  -- Create co-occurrence edges between all pairs
  let pairs = allPairs memes
  edges <- traverse (\pair => do
    let (a, b) = pair
    createEdge store eid MemeNode (show a.id) MemeNode (show b.id) CoOccursWith 0.5 ts) pairs

  pure (MkIndexOutcome
    (length allConcepts)
    0
    (length edges)
    (map ecLabel allConcepts))

  where
    allPairs : List a -> List (a, a)
    allPairs [] = []
    allPairs (x :: xs) = map (\y => (x, y)) xs ++ allPairs xs
