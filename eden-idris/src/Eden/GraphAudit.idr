||| Model-in-the-loop graph audit pipelines.
|||
||| Four audit passes that use Claude to review and reshape the
||| knowledge graph at session start or after document ingestion:
|||
|||   1. Graph normalization — merge duplicate memes
|||   2. Behavior taxonomy audit — group behaviors into memodes
|||   3. Coherence reweave — suggest new edges for weakly-connected memes
|||   4. Document contextualization — cross-reference ingested content
|||
||| Each pipeline writes a prompt to a temp file, pipes it to the
||| Claude CLI with --print, and parses the structured response.
module Eden.GraphAudit

import Data.IORef
import Data.List
import Data.Maybe
import Data.String
import Eden.Types
import Eden.Config
import Eden.Store.InMemory
import Eden.Monad
import Eden.TermIO
import System.File.ReadWrite

%default covering

------------------------------------------------------------------------
-- Audit report record
------------------------------------------------------------------------

||| Summary of a single audit pipeline run.
public export
record AuditReport where
  constructor MkAuditReport
  arPipeline       : String
  arStatus         : String
  arCandidates     : Nat
  arProcessed      : Nat
  arMerged         : Nat
  arMemodesMade    : Nat
  arEdgesCreated   : Nat
  arErrors         : List String

||| Empty report for a given pipeline name.
emptyReport : String -> AuditReport
emptyReport name = MkAuditReport name "completed" 0 0 0 0 0 []

||| Combined report for all four pipelines.
public export
record FullAuditReport where
  constructor MkFullAuditReport
  normalization     : AuditReport
  taxonomy          : AuditReport
  coherence         : AuditReport
  contextualization : AuditReport

------------------------------------------------------------------------
-- ANSI / output sanitization (shared)
------------------------------------------------------------------------

||| Strip ANSI escape sequences and normalize whitespace.
sanitizeModelOutput : String -> String
sanitizeModelOutput s = pack (norm (stripEsc (unpack s)))
  where
    stripEsc : List Char -> List Char
    stripEsc [] = []
    stripEsc (c :: '[' :: rest) =
      if c == chr 27
        then let skip : List Char -> List Char
                 skip [] = []
                 skip (x :: xs) = if isAlpha x then stripEsc xs else skip xs
             in skip rest
        else c :: '[' :: stripEsc rest
    stripEsc (c :: rest) =
      if c == chr 27 then stripEsc (drop 1 rest)
      else c :: stripEsc rest
    norm : List Char -> List Char
    norm [] = []
    norm ('\r' :: cs) = norm cs
    norm (c :: cs) = if ord c < 32 && c /= '\n' then norm cs else c :: norm cs

------------------------------------------------------------------------
-- Pipe-based model invocation
------------------------------------------------------------------------

||| Write prompt to temp file, pipe through Claude CLI with --print,
||| rearm terminal, return sanitized output or error string.
callClaude : String -> IO (Either String String)
callClaude prompt = do
  Right () <- writeFile "data/eden_audit.tmp" prompt
    | Left err => pure (Left ("writeFile: " ++ show err))
  (output, exitCode) <- runCommand "cat data/eden_audit.tmp | claude --model sonnet --print"
  rearmTerminal
  let cleaned = sanitizeModelOutput (trim output)
  if exitCode /= 0 || cleaned == ""
    then pure (Left ("claude exit=" ++ show exitCode))
    else pure (Right cleaned)

------------------------------------------------------------------------
-- String helpers
------------------------------------------------------------------------

||| Split a string on '|' into parts.
splitPipe : String -> List String
splitPipe s = splitOn '|' (unpack s)
  where
    splitOn : Char -> List Char -> List String
    splitOn _ [] = [""]
    splitOn sep (c :: cs) =
      if c == sep
        then "" :: splitOn sep cs
        else case splitOn sep cs of
               [] => [pack [c]]
               (w :: ws) => (pack [c] ++ w) :: ws

||| Count edges involving a given node ID (as src or dst).
countNodeEdges : List Edge -> String -> Nat
countNodeEdges edges nid =
  length (filter (\e => e.srcId == nid || e.dstId == nid) edges)

------------------------------------------------------------------------
-- 1. Graph Normalization
------------------------------------------------------------------------

||| A group of memes that may be duplicates.
record DuplicateGroup where
  constructor MkDuplicateGroup
  dgLabels : List String
  dgIds    : List MemeId

||| Find groups of memes with similar canonical labels.
||| Groups by canonical prefix (first 10 chars) as a simple heuristic.
findDuplicateGroups : List Meme -> List DuplicateGroup
findDuplicateGroups memes =
  let -- Group by the first 10 chars of the canonical label
      keyed : List (String, Meme)
      keyed = map (\m => (toLower (substr 0 10 m.canonicalLabel), m)) memes
      -- Collect into groups; simple O(n^2) gather
      grouped : List (List Meme)
      grouped = gather [] keyed
      -- Keep only groups with 2+ members
      dups = filter (\g => length g >= 2) grouped
  in map (\g => MkDuplicateGroup (map (.label) g) (map (.id) g)) dups
  where
    insertInto : List (String, List Meme) -> String -> Meme -> List (String, List Meme)
    insertInto [] k v = [(k, [v])]
    insertInto ((k', vs) :: rest) k v =
      if k == k' then (k', v :: vs) :: rest
      else (k', vs) :: insertInto rest k v
    gather : List (String, List Meme) -> List (String, Meme) -> List (List Meme)
    gather acc [] = map snd acc
    gather acc ((k, m) :: rest) = gather (insertInto acc k m) rest

||| Build the normalization prompt for Claude.
buildNormalizationPrompt : List DuplicateGroup -> String
buildNormalizationPrompt groups =
  let header = "You are reviewing a knowledge graph for duplicate memes.\n"
            ++ "For each group below, decide whether to merge or keep them separate.\n"
            ++ "Output exactly one line per group:\n"
            ++ "  MERGE label1|label2|canonical_label\n"
            ++ "  KEEP label1|label2\n"
            ++ "Output ONLY these lines, nothing else.\n\n"
      body = unlines (map formatGroup groups)
  in header ++ body
  where
    formatGroup : DuplicateGroup -> String
    formatGroup g = "Group: " ++ (concat (intersperse ", " g.dgLabels))

||| Parse a MERGE line: "MERGE label1|label2|canonical" -> (labels, canonical).
parseMergeLine : String -> Maybe (List String, String)
parseMergeLine line =
  let trimmed = trim line
  in if isPrefixOf "MERGE " trimmed
       then let rest = trim (substr 6 (length trimmed) trimmed)
                parts = splitPipe rest
            in case reverse parts of
                 [] => Nothing
                 (canonical :: labelsRev) =>
                   let labels = reverse labelsRev
                   in if null labels then Nothing
                      else Just (map trim labels, trim canonical)
       else Nothing

||| Execute the graph normalization pipeline.
||| Finds potential duplicate memes, asks Claude to decide, merges as directed.
export
runGraphNormalization : EdenM AuditReport
runGraphNormalization = do
  env <- ask
  memes <- eGetMemes
  let groups = findDuplicateGroups memes
      report = emptyReport "normalization"
  if null groups
    then pure report
    else do
      let prompt = buildNormalizationPrompt groups
      result <- liftIO (callClaude prompt)
      case result of
        Left err => pure ({ arStatus := "error", arErrors := [err] } report)
        Right output => do
          let responseLines = lines output
              mergeLines = mapMaybe parseMergeLine responseLines
          -- For each merge directive, redirect edges from old memes to canonical
          mergeCount <- liftIO (processMerges env.store env.eid memes mergeLines env.ts)
          pure ({ arCandidates := length groups
                , arProcessed := length mergeLines
                , arMerged := mergeCount } report)
  where
    ||| Find meme by label (case-insensitive) in the meme list.
    findByLabel : List Meme -> String -> Maybe Meme
    findByLabel ms lbl =
      let target = toLower (trim lbl)
      in find (\m => m.canonicalLabel == target) ms

    ||| Process merge directives: for each merge, update edges to point
    ||| to the canonical meme (upserted if necessary).
    processMerges : StoreState -> ExperimentId -> List Meme
                 -> List (List String, String) -> Timestamp -> IO Nat
    processMerges st eid allMemes directives now = go 0 directives
      where
        go : Nat -> List (List String, String) -> IO Nat
        go n [] = pure n
        go n ((labels, canonical) :: rest) = do
          -- Ensure the canonical meme exists
          canonMeme <- upsertMeme st eid canonical canonical Knowledge ManualSource Global now
          -- Bump evidence on the canonical meme for each merged source
          let sourceIds = mapMaybe (\l => map (.id) (findByLabel allMemes l)) labels
          -- Create edges from merged memes to canonical (DERIVED_FROM)
          _ <- traverse (\srcId => do
            _ <- createEdge st eid MemeNode (show srcId) MemeNode (show canonMeme.id)
                   DerivedFrom 0.8 now
            pure ()) sourceIds
          go (n + 1) rest

------------------------------------------------------------------------
-- 2. Behavior Taxonomy Audit
------------------------------------------------------------------------

||| Build the taxonomy audit prompt for Claude.
buildTaxonomyPrompt : List Meme -> String
buildTaxonomyPrompt behaviorMemes =
  let header = "You are reviewing behavior-domain memes in a knowledge graph.\n"
            ++ "Group these behaviors into coherent memodes (behavioral patterns).\n"
            ++ "Each memode should contain 2-4 related behaviors.\n"
            ++ "Output exactly one line per memode:\n"
            ++ "  MEMODE memode_name|member1|member2|...\n"
            ++ "Output ONLY these lines, nothing else.\n\n"
            ++ "Behavior memes:\n"
      body = unlines (map (\m => "- " ++ m.label) behaviorMemes)
  in header ++ body

||| Parse a MEMODE line: "MEMODE name|m1|m2|..." -> (name, [members]).
parseMemodeLine : String -> Maybe (String, List String)
parseMemodeLine line =
  let trimmed = trim line
  in if isPrefixOf "MEMODE " trimmed
       then let rest = trim (substr 7 (length trimmed) trimmed)
                parts = splitPipe rest
            in case parts of
                 [] => Nothing
                 (name :: members) =>
                   let cleanMembers = filter (\s => trim s /= "") (map trim members)
                   in if length cleanMembers < 2 then Nothing
                      else Just (trim name, cleanMembers)
       else Nothing

||| Execute the behavior taxonomy audit pipeline.
||| Collects behavior memes, asks Claude to group them, materializes memodes.
export
runBehaviorTaxonomy : EdenM AuditReport
runBehaviorTaxonomy = do
  env <- ask
  memes <- eGetMemes
  let behaviorMemes = filter (\m => m.domain == Behavior) memes
      report = emptyReport "taxonomy"
  if length behaviorMemes < 2
    then pure report
    else do
      let prompt = buildTaxonomyPrompt behaviorMemes
      result <- liftIO (callClaude prompt)
      case result of
        Left err => pure ({ arStatus := "error", arErrors := [err] } report)
        Right output => do
          let responseLines = lines output
              memodeLines = mapMaybe parseMemodeLine responseLines
          -- Materialize each memode grouping
          madeCount <- materializeGroups env.store env.eid behaviorMemes memodeLines env.ts
          pure ({ arCandidates := length behaviorMemes
                , arProcessed := length memodeLines
                , arMemodesMade := madeCount } report)
  where
    ||| Find a behavior meme by label (case-insensitive).
    findBehaviorMeme : List Meme -> String -> Maybe Meme
    findBehaviorMeme ms lbl =
      let target = toLower (trim lbl)
      in find (\m => m.domain == Behavior && toLower m.label == target) ms

    ||| Materialize memode groupings from Claude's response.
    materializeGroups : StoreState -> ExperimentId -> List Meme
                     -> List (String, List String) -> Timestamp -> EdenM Nat
    materializeGroups st eid allBehavior groupings now = go 0 groupings
      where
        go : Nat -> List (String, List String) -> EdenM Nat
        go n [] = pure n
        go n ((name, memberLabels) :: rest) = do
          let memberMemes = mapMaybe (findBehaviorMeme allBehavior) memberLabels
              memberIds = map (.id) memberMemes
          if length memberIds < 2
            then go n rest  -- skip if fewer than 2 valid members
            else do
              let summary = "Behavior cluster: " ++ concat (intersperse ", " memberLabels)
              _ <- liftIO (upsertMemode st eid name summary Behavior memberIds now)
              -- Create MemberOf edges from each member to the memode
              _ <- traverse (\mid => do
                _ <- eCreateEdge MemeNode (show mid) MemodeNode name MemberOf 1.0
                pure ()) memberIds
              go (n + 1) rest

------------------------------------------------------------------------
-- 3. Coherence Reweave
------------------------------------------------------------------------

||| Find memes with few edges (structurally weak nodes).
findWeakMemes : List Meme -> List Edge -> Nat -> List Meme
findWeakMemes memes edges threshold =
  filter (\m => countNodeEdges edges (show m.id) < threshold) memes

||| Get neighbor labels for a meme from the edge list.
neighborLabels : List Meme -> List Edge -> MemeId -> List String
neighborLabels memes edges mid =
  let midStr = show mid
      neighborIds = map (\e => if e.srcId == midStr then e.dstId else e.srcId)
                        (filter (\e => e.srcId == midStr || e.dstId == midStr) edges)
      neighborMemes = mapMaybe (\nid => find (\m => show m.id == nid) memes) neighborIds
  in map (.label) neighborMemes

||| Build the coherence reweave prompt for Claude.
buildReweavePrompt : List (Meme, List String) -> String
buildReweavePrompt weakWithNeighbors =
  let header = "You are reviewing a knowledge graph for structural coherence.\n"
            ++ "The following memes have few connections. Suggest new edges to strengthen the graph.\n"
            ++ "Output exactly one line per suggested edge:\n"
            ++ "  EDGE source_label|target_label|relation_type|weight\n"
            ++ "relation_type must be one of: SUPPORTS, RELATES_TO, INFLUENCES, CO_OCCURS_WITH, DERIVED_FROM\n"
            ++ "weight must be a decimal between 0.0 and 1.0\n"
            ++ "Output ONLY these lines, nothing else.\n\n"
      body = unlines (map formatEntry weakWithNeighbors)
  in header ++ body
  where
    formatEntry : (Meme, List String) -> String
    formatEntry (m, neighbors) =
      "- " ++ m.label ++ " (domain=" ++ show m.domain ++ ")"
      ++ case neighbors of
           [] => " [no neighbors]"
           ns => " neighbors: " ++ concat (intersperse ", " ns)

||| Parse an edge type string to EdgeType.
parseEdgeType : String -> Maybe EdgeType
parseEdgeType s =
  let s' = toUpper (trim s)
  in if s' == "SUPPORTS" then Just Supports
     else if s' == "REINFORCES" then Just Reinforces
     else if s' == "REFINES" then Just Refines
     else if s' == "RELATES_TO" then Just RelatesTo
     else if s' == "INFLUENCES" then Just Influences
     else if s' == "CO_OCCURS_WITH" then Just CoOccursWith
     else if s' == "DERIVED_FROM" then Just DerivedFrom
     else if s' == "CONTRADICTS" then Just ContradictsEdge
     else if s' == "CONTEXTUALIZES_DOCUMENT" then Just ContextualizesDocument
     else if s' == "FED_BACK_BY" then Just FedBackBy
     else if s' == "OCCURS_IN" then Just OccursIn
     else Nothing

||| Parse an EDGE line: "EDGE src|dst|type|weight" -> parsed tuple.
parseEdgeLine : String -> Maybe (String, String, EdgeType, Double)
parseEdgeLine line =
  let trimmed = trim line
  in if isPrefixOf "EDGE " trimmed
       then let rest = trim (substr 5 (length trimmed) trimmed)
                parts = splitPipe rest
            in case parts of
                 [src, dst, relType, wStr] =>
                   case parseEdgeType relType of
                     Nothing => Nothing
                     Just et => Just (trim src, trim dst, et, fromMaybe 0.5 (parseDouble wStr))
                 _ => Nothing
       else Nothing

||| Execute the coherence reweave pipeline.
||| Finds structurally weak memes, asks Claude for edge suggestions, creates them.
export
runCoherenceReweave : EdenM AuditReport
runCoherenceReweave = do
  env <- ask
  memes <- eGetMemes
  allEdges <- liftIO (readIORef env.store.edges)
  let expEdges = filter (\e => e.experimentId == env.eid) allEdges
      weakMemes = findWeakMemes memes expEdges 2
      report = emptyReport "coherence"
  if null weakMemes
    then pure report
    else do
      let weakWithNeighbors = map (\m => (m, neighborLabels memes expEdges m.id))
                                  (take 20 weakMemes) -- limit to 20 to keep prompt manageable
          prompt = buildReweavePrompt weakWithNeighbors
      result <- liftIO (callClaude prompt)
      case result of
        Left err => pure ({ arStatus := "error", arErrors := [err] } report)
        Right output => do
          let responseLines = lines output
              edgeDirectives = mapMaybe parseEdgeLine responseLines
          -- Create each suggested edge
          edgeCount <- createSuggestedEdges env.store env.eid memes edgeDirectives env.ts
          pure ({ arCandidates := length weakMemes
                , arProcessed := length edgeDirectives
                , arEdgesCreated := edgeCount } report)
  where
    ||| Find a meme by label (case-insensitive).
    findMemeByLabel : List Meme -> String -> Maybe Meme
    findMemeByLabel ms lbl =
      let target = toLower (trim lbl)
      in find (\m => toLower m.label == target) ms

    ||| Create edges from Claude's suggestions, validating that source
    ||| and target memes actually exist.
    createSuggestedEdges : StoreState -> ExperimentId -> List Meme
                        -> List (String, String, EdgeType, Double) -> Timestamp -> EdenM Nat
    createSuggestedEdges st eid allMemes directives now = go 0 directives
      where
        go : Nat -> List (String, String, EdgeType, Double) -> EdenM Nat
        go n [] = pure n
        go n ((srcLabel, dstLabel, et, w) :: rest) = do
          case (findMemeByLabel allMemes srcLabel, findMemeByLabel allMemes dstLabel) of
            (Just src, Just dst) => do
              _ <- eCreateEdge MemeNode (show src.id) MemeNode (show dst.id) et w
              go (n + 1) rest
            _ => go n rest  -- skip if either meme not found

------------------------------------------------------------------------
-- 4. Document Contextualization
------------------------------------------------------------------------

||| Build the document contextualization prompt.
buildContextualizationPrompt : String -> String -> List Meme -> String
buildContextualizationPrompt docTitle sampleText existingMemes =
  let header = "A document titled \"" ++ docTitle ++ "\" has been ingested into the knowledge graph.\n"
            ++ "Below are sample excerpts from the document and a summary of existing graph memes.\n"
            ++ "Identify connections between the new content and existing memes.\n"
            ++ "Output exactly one line per connection:\n"
            ++ "  EDGE new_concept|existing_label|relation_type|weight\n"
            ++ "relation_type must be one of: SUPPORTS, RELATES_TO, INFLUENCES, CO_OCCURS_WITH, DERIVED_FROM\n"
            ++ "weight must be a decimal between 0.0 and 1.0\n"
            ++ "Output ONLY these lines, nothing else.\n\n"
            ++ "Document excerpts:\n" ++ substr 0 2000 sampleText ++ "\n\n"
            ++ "Existing graph memes:\n"
      memeList = unlines (map (\m => "- " ++ m.label ++ " (" ++ show m.domain ++ ")") (take 50 existingMemes))
  in header ++ memeList

||| Execute the document contextualization pipeline.
||| After a document is ingested, finds cross-references with existing graph.
export
runDocumentContextualization : String -> String -> EdenM AuditReport
runDocumentContextualization docTitle sampleText = do
  env <- ask
  memes <- eGetMemes
  let report = emptyReport "contextualization"
  if null memes
    then pure report
    else do
      let prompt = buildContextualizationPrompt docTitle sampleText memes
      result <- liftIO (callClaude prompt)
      case result of
        Left err => pure ({ arStatus := "error", arErrors := [err] } report)
        Right output => do
          let responseLines = lines output
              edgeDirectives = mapMaybe parseEdgeLine responseLines
          -- Create new memes for concepts not yet in graph, then create edges
          edgeCount <- createContextEdges env.store env.eid memes edgeDirectives env.ts
          pure ({ arCandidates := length memes
                , arProcessed := length edgeDirectives
                , arEdgesCreated := edgeCount } report)
  where
    ||| Find or create a meme for a label.
    findOrCreateMeme : StoreState -> ExperimentId -> List Meme -> String
                    -> Timestamp -> IO Meme
    findOrCreateMeme st eid ms lbl now =
      let target = toLower (trim lbl)
      in case find (\m => toLower m.label == target) ms of
           Just existing => pure existing
           Nothing => upsertMeme st eid lbl lbl Knowledge IngestSource Global now

    ||| Create cross-reference edges from the contextualization directives.
    createContextEdges : StoreState -> ExperimentId -> List Meme
                      -> List (String, String, EdgeType, Double) -> Timestamp -> EdenM Nat
    createContextEdges st eid allMemes directives now = go 0 directives
      where
        go : Nat -> List (String, String, EdgeType, Double) -> EdenM Nat
        go n [] = pure n
        go n ((srcLabel, dstLabel, et, w) :: rest) = do
          -- Source might be a new concept from the document
          srcMeme <- liftIO (findOrCreateMeme st eid allMemes srcLabel now)
          -- Destination should be an existing meme
          case find (\m => toLower m.label == toLower (trim dstLabel)) allMemes of
            Nothing => go n rest  -- skip if target not found
            Just dstMeme => do
              _ <- eCreateEdge MemeNode (show srcMeme.id) MemeNode (show dstMeme.id) et w
              go (n + 1) rest

------------------------------------------------------------------------
-- Full audit pipeline
------------------------------------------------------------------------

||| Run all four graph audit pipelines.
||| Call at session start (without document args) for the first three.
export
runFullGraphAudit : EdenM FullAuditReport
runFullGraphAudit = do
  normReport <- runGraphNormalization
  taxReport  <- runBehaviorTaxonomy
  cohReport  <- runCoherenceReweave
  let ctxReport = emptyReport "contextualization"  -- no document context at session start
  pure (MkFullAuditReport normReport taxReport cohReport ctxReport)

||| Run the session-start audit (normalization + taxonomy + coherence).
export
runSessionStartAudit : EdenM FullAuditReport
runSessionStartAudit = runFullGraphAudit

||| Run a post-ingest audit (all four pipelines including contextualization).
export
runPostIngestAudit : String -> String -> EdenM FullAuditReport
runPostIngestAudit docTitle sampleText = do
  normReport <- runGraphNormalization
  taxReport  <- runBehaviorTaxonomy
  cohReport  <- runCoherenceReweave
  ctxReport  <- runDocumentContextualization docTitle sampleText
  pure (MkFullAuditReport normReport taxReport cohReport ctxReport)
