||| Document ingestion pipeline.
|||
||| Reads file content, chunks it, indexes concepts from each chunk,
||| and materializes memodes. This is the Idris2 equivalent of
||| eden/ingest/pipeline.py.
module Eden.Ingest.Pipeline

import Data.IORef
import Data.List
import Data.List1
import Data.String
import System
import System.File.ReadWrite
import Eden.Types
import Eden.Config
import Eden.Ingest
import Eden.Ingest.Extractors
import Eden.Indexer
import Eden.Store.InMemory
import Eden.TermIO

------------------------------------------------------------------------
-- Chunking
------------------------------------------------------------------------

||| Split text into chunks of approximately `maxLen` characters,
||| breaking at paragraph boundaries where possible.
export
chunkText : String -> Nat -> List RawChunk
chunkText text maxLen =
  let paragraphs = split (\c => c == '\n') text
      chunks = buildChunks (toList paragraphs) 0 "" 0
  in chunks
  where
    buildChunks : List String -> Nat -> String -> Nat -> List RawChunk
    buildChunks [] idx acc _ =
      let trimmed = trim acc
      in if trimmed == "" then []
         else [MkRawChunk trimmed Nothing idx]
    buildChunks (p :: ps) idx acc accLen =
      let pLen = length p
          newLen = accLen + pLen + 1
      in if newLen > maxLen && accLen > 0
           then MkRawChunk (trim acc) Nothing idx
                :: buildChunks (p :: ps) (idx + 1) "" 0
           else buildChunks ps idx (acc ++ p ++ "\n") newLen

------------------------------------------------------------------------
-- Quality flags
------------------------------------------------------------------------

||| Assess quality flags for a set of chunks.
export
assessFlags : List RawChunk -> List QualityFlag
assessFlags chunks =
  let cnt = length chunks
      shortCount = length (filter (\c => length c.rcText < MinChunkLength) chunks)
      emptyCount = length (filter (\c => trim c.rcText == "") chunks)
  in (if shortCount * 2 > cnt then [ShortChunks] else [])
  ++ (if emptyCount > 0 then [EmptyChunks] else [])

------------------------------------------------------------------------
-- MLX Adam-identity contextualization (§6.2)
------------------------------------------------------------------------

||| Sort chunks by text length (longest first) and take the first n.
sampleLongestChunks : Nat -> List RawChunk -> List RawChunk
sampleLongestChunks n chunks =
  let sorted = sortBy (\a, b => compare (length b.rcText) (length a.rcText)) chunks
  in take n sorted

||| Select the top behavior memes by usage count.
topBehaviorMemes : Nat -> List Meme -> List Meme
topBehaviorMemes n memes =
  let behaviorOnly = filter (\m => m.domain == Behavior) memes
      sorted = sortBy (\a, b => compare b.usageCount a.usageCount) behaviorOnly
  in take n sorted

||| Build the Adam-identity contextualization prompt.
buildCtxPrompt : List RawChunk -> List Meme -> String
buildCtxPrompt chunks memes =
  let chunkTexts = unlines (map (\c => c.rcText) chunks)
      memeLabels = unlines (map (\m => "- " ++ m.label) memes)
  in "You are Adam, a memetic persona runtime. A document has been ingested into your knowledge graph.\n"
  ++ "Below are sample excerpts and your existing behavior patterns.\n"
  ++ "Propose behavior-domain contextualization memes: how should this document's content relate to your behavioral patterns?\n"
  ++ "Do NOT restate factual content. Propose behavioral patterns this content activates or modifies.\n"
  ++ "Output JSON only: [{\"label\": \"short label\", \"text\": \"behavioral pattern description\"}]\n\n"
  ++ "Document excerpts:\n" ++ chunkTexts ++ "\n\n"
  ++ "Existing behavior patterns:\n" ++ memeLabels

||| Simple JSON field extractor: find value for a key like "label" or "text".
||| Looks for "key": "value" patterns. Returns the value string or Nothing.
extractJsonField : String -> String -> Maybe String
extractJsonField key input =
  let needle = "\"" ++ key ++ "\""
  in case isInfixOf needle input of
       False => Nothing
       True  =>
         -- Find the needle position manually
         let chars = unpack input
         in findField (unpack needle) chars
  where
    matchPrefix : List Char -> List Char -> Bool
    matchPrefix [] _ = True
    matchPrefix _ [] = False
    matchPrefix (p :: ps) (c :: cs) = p == c && matchPrefix ps cs

    -- Skip whitespace and colon after key, then extract quoted value
    skipToValue : List Char -> Maybe String
    skipToValue [] = Nothing
    skipToValue ('"' :: rest) = Just (pack (takeWhile (\c => c /= '"') rest))
    skipToValue (' ' :: rest) = skipToValue rest
    skipToValue (':' :: rest) = skipToValue rest
    skipToValue _             = Nothing

    findField : List Char -> List Char -> Maybe String
    findField _      []        = Nothing
    findField needle (c :: cs) =
      if matchPrefix needle (c :: cs)
        then skipToValue (drop (length needle) (c :: cs))
        else findField needle cs

||| Parse the MLX JSON output into (label, text) pairs.
||| Uses simple string scanning for "label" and "text" fields.
parseCtxJson : String -> List (String, String)
parseCtxJson output =
  -- Split on '{' to isolate individual objects
  let segments = split (\c => c == '{') output
      objects = toList segments
  in mapMaybe parseOneObject objects
  where
    parseOneObject : String -> Maybe (String, String)
    parseOneObject s =
      case (extractJsonField "label" s, extractJsonField "text" s) of
        (Just lbl, Just txt) =>
          if trim lbl /= "" && trim txt /= ""
            then Just (trim lbl, trim txt)
            else Nothing
        _ => Nothing

||| Strip ANSI escape sequences from subprocess output.
stripAnsiCtx : String -> String
stripAnsiCtx s = pack (go (unpack s))
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

||| Run the MLX Adam-identity contextualization pass (§6.2).
||| Samples up to 5 document chunks (longest first), takes up to 10
||| existing behavior memes (by usage count), calls the local MLX model
||| to propose behavior-domain contextualization memes, then creates
||| memes and ContextualizesDocument edges in the graph.
||| Gracefully returns an empty list on any failure.
export
runMLXContextualization : StoreState -> ExperimentId -> DocumentId
                       -> List RawChunk -> List Meme -> Timestamp -> IO (List Meme)
runMLXContextualization store eid docId chunks allMemes ts = do
  let sampled = sampleLongestChunks 5 chunks
      topBehavior = topBehaviorMemes 10 allMemes
  -- If no chunks to sample, skip
  if null sampled
    then pure []
    else do
      let prompt = buildCtxPrompt sampled topBehavior
      writeResult <- writeFile "data/eden_ctx.tmp" prompt
      case writeResult of
        Left _ => pure []  -- file write failed
        Right () => do
          let model = "mlx-community/Llama-3.2-3B-Instruct-4bit"
              cmd = "cat data/eden_ctx.tmp | python3 -c \"from mlx_lm import load,generate;m,t=load('"
                    ++ model ++ "');import sys;p=sys.stdin.read();print(generate(m,t,prompt=p,max_tokens=512))\""
          (output, exitCode) <- runCommand cmd
          rearmTerminal
          if exitCode /= 0 || trim output == ""
            then pure []
            else do
              let cleaned = stripAnsiCtx (trim output)
                  parsed = parseCtxJson cleaned
              if null parsed
                then pure []
                else do
                  -- Create behavior memes and ContextualizesDocument edges
                  newMemes <- traverse (\pair => do
                    let (lbl, txt) = pair
                    m <- upsertMeme store eid lbl txt Behavior IngestSource Global ts
                    _ <- createEdge store eid MemeNode (show m.id)
                           DocumentNode (show docId) ContextualizesDocument 0.5 ts
                    pure m) parsed
                  pure newMemes

------------------------------------------------------------------------
-- Ingest pipeline
------------------------------------------------------------------------

||| Ingest a text document into the graph.
||| Chunks the text, indexes concepts from each chunk,
||| creates document and chunk records, materializes memodes.
export
ingestText : StoreState -> ExperimentId
          -> String -> String -> String -> Timestamp
          -> IO IngestResult
ingestText store eid docPath title content ts = do
  -- 1. Create document record
  doc <- createDocument store eid docPath PlainText title "" ts

  -- 2. Chunk the content
  let chunks = chunkText content MaxChunkLength
      flags  = assessFlags chunks
      (qScore, qState) = assessQuality (length chunks) 0 flags

  -- 3. Index concepts from each chunk
  allConcepts <- traverse indexChunkConcepts chunks

  let totalConcepts = concat allConcepts
      uniqueLabels = nub (map ecLabel totalConcepts)
      memeCount = length uniqueLabels

  -- 4. Create co-occurrence edges within each chunk
  traverse_ createChunkEdges chunks

  -- 5. Materialize memodes
  memodes <- materializeMemodes store eid ts

  -- 6. §6.2: MLX Adam-identity contextualization pass (env-gated)
  mlxEnv <- getEnv "EDEN_ENABLE_MLX_INGEST"
  let mlxEnabled = case mlxEnv of
                     Just "1"    => True
                     Just "true" => True
                     _           => False
  ctxMemes <- runCtxPass mlxEnabled doc.id chunks
  let ctxNote = if null ctxMemes then []
                else ["mlx contextualization: " ++ show (length ctxMemes) ++ " behavior memes"]

  -- 7. Build result
  let (finalScore, finalState) = assessQuality (length chunks) memeCount flags
  pure (MkIngestResult
    doc.id
    (length chunks)
    (memeCount + length ctxMemes)
    (length memodes)
    Ingested
    (["ingested " ++ show (length chunks) ++ " chunks"] ++ ctxNote)
    "text"
    finalScore
    finalState
    flags)

  where
    ignore : IO a -> IO ()
    ignore act = do _ <- act; pure ()

    allPairs : List a -> List (a, a)
    allPairs [] = []
    allPairs (x :: xs) = map (\y => (x, y)) xs ++ allPairs xs

    upsertConceptMeme : ExtractedConcept -> IO ()
    upsertConceptMeme ec =
      ignore (upsertMeme store eid ec.ecLabel ec.ecLabel ec.ecDomain IngestSource Global ts)

    indexChunkConcepts : RawChunk -> IO (List ExtractedConcept)
    indexChunkConcepts c = do
      let concepts = extractConcepts c.rcText IngestSource
      traverse_ upsertConceptMeme concepts
      pure concepts

    createPairEdge : (ExtractedConcept, ExtractedConcept) -> IO ()
    createPairEdge (a, b) =
      ignore (createEdge store eid MemeNode a.ecLabel MemeNode b.ecLabel CoOccursWith 0.3 ts)

    createChunkEdges : RawChunk -> IO ()
    createChunkEdges c = do
      let concepts = extractConcepts c.rcText IngestSource
      traverse_ createPairEdge (allPairs concepts)

    runCtxPass : Bool -> DocumentId -> List RawChunk -> IO (List Meme)
    runCtxPass False _ _ = pure []
    runCtxPass True did cs = do
      graphMemes <- readIORef store.memes
      runMLXContextualization store eid did cs graphMemes ts

||| Ingest a text document using model-based concept extraction.
||| Falls back to keyword extraction if the model call fails.
export
ingestTextWithModel : StoreState -> ExperimentId
                    -> String -> String -> String -> Timestamp
                    -> IO IngestResult
ingestTextWithModel store eid docPath title content ts = do
  -- 1. Create document record
  doc <- createDocument store eid docPath PlainText title "" ts

  -- 2. Chunk the content
  let chunks = chunkText content MaxChunkLength
      flags  = assessFlags chunks
      (qScore, qState) = assessQuality (length chunks) 0 flags

  -- 3. Index concepts from each chunk via model
  allConcepts <- traverse indexChunkConceptsModel chunks

  let totalConcepts = concat allConcepts
      uniqueLabels = nub (map ecLabel totalConcepts)
      memeCount = length uniqueLabels

  -- 4. Create co-occurrence edges within each chunk
  traverse_ createChunkEdgesModel chunks

  -- 5. Materialize memodes
  memodes <- materializeMemodes store eid ts

  -- 6. §6.2: MLX Adam-identity contextualization pass (env-gated)
  mlxEnv <- getEnv "EDEN_ENABLE_MLX_INGEST"
  let mlxEnabled = case mlxEnv of
                     Just "1"    => True
                     Just "true" => True
                     _           => False
  ctxMemes <- runCtxPass mlxEnabled doc.id chunks
  let ctxNote : List String
      ctxNote = if null ctxMemes then []
                else ["mlx contextualization: " ++ show (length ctxMemes) ++ " behavior memes"]

  -- 7. Build result
  let (finalScore, finalState) = assessQuality (length chunks) memeCount flags
  pure (MkIngestResult
    doc.id
    (length chunks)
    (memeCount + length ctxMemes)
    (length memodes)
    Ingested
    (["ingested " ++ show (length chunks) ++ " chunks (model)"] ++ ctxNote)
    "text"
    finalScore
    finalState
    flags)

  where
    ignore : IO a -> IO ()
    ignore act = do _ <- act; pure ()

    allPairs : List a -> List (a, a)
    allPairs [] = []
    allPairs (x :: xs) = map (\y => (x, y)) xs ++ allPairs xs

    upsertConceptMeme : ExtractedConcept -> IO ()
    upsertConceptMeme ec =
      ignore (upsertMeme store eid ec.ecLabel ec.ecLabel ec.ecDomain IngestSource Global ts)

    indexChunkConceptsModel : RawChunk -> IO (List ExtractedConcept)
    indexChunkConceptsModel c = do
      concepts <- extractConceptsViaModel c.rcText IngestSource
      traverse_ upsertConceptMeme concepts
      pure concepts

    createPairEdge : (ExtractedConcept, ExtractedConcept) -> IO ()
    createPairEdge (a, b) =
      ignore (createEdge store eid MemeNode a.ecLabel MemeNode b.ecLabel CoOccursWith 0.3 ts)

    createChunkEdgesModel : RawChunk -> IO ()
    createChunkEdgesModel c = do
      concepts <- extractConceptsViaModel c.rcText IngestSource
      traverse_ createPairEdge (allPairs concepts)

    runCtxPass : Bool -> DocumentId -> List RawChunk -> IO (List Meme)
    runCtxPass False _ _ = pure []
    runCtxPass True did cs = do
      graphMemes <- readIORef store.memes
      runMLXContextualization store eid did cs graphMemes ts

------------------------------------------------------------------------
-- File-based ingest (multi-format)
------------------------------------------------------------------------

||| Extract the filename from a path string.
pathFileName : String -> String
pathFileName path =
  let chars = unpack path
      revChars = reverse chars
      nameRev = takeWhile (\c => c /= '/' && c /= '\\') revChars
  in pack (reverse nameRev)

||| Ingest a file of any supported format (PDF, CSV, TXT, Markdown).
||| Uses `extractDocument` to detect format and extract text,
||| then delegates to `ingestText` for chunking and indexing.
export
ingestFile : StoreState -> ExperimentId -> String -> Timestamp
          -> IO IngestResult
ingestFile store eid path ts = do
  result <- extractDocument path
  case result of
    Left err =>
      -- Create a failed result
      pure (MkIngestResult
        (MkId "")
        0 0 0
        Failed
        ["extraction failed: " ++ err]
        "none"
        0.0
        QualityFailed
        [LowExtraction])
    Right (content, fmt) => do
      let title = pathFileName path
          parser = show fmt
      -- For PDF, compute quality score
      let qNote = case fmt of
                    PDF => let q = scorePdfQuality content
                           in if q < 0.3
                                then ["pdf quality score: " ++ show q ++ " (degraded)"]
                                else ["pdf quality score: " ++ show q]
                    _   => []
      -- Delegate to ingestText for chunking and concept extraction
      ir <- ingestText store eid path title content ts
      -- Return result with format-specific parser info and notes
      pure ({ irParser := parser
            , irNotes  := ir.irNotes ++ qNote
            } ir)
