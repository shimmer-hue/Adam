||| Retrieval and candidate scoring for active-set assembly.
|||
||| The active set is the bounded retrieval and prompt-compilation slice.
||| It is NOT a hidden governor or planning layer.
|||
||| Similarity methods:
|||   - Jaccard: word-level set overlap (original, fast)
|||   - TFIDF: term frequency-inverse document frequency with cosine similarity
|||   - Bigram: character bigram overlap (useful for Hebrew and other scripts)
|||   - Embedding: cosine similarity over semantic feature vectors (via Claude CLI)
module Eden.Retrieval

import Data.IORef
import Data.List
import Data.String
import Eden.Types
import Eden.Config
import Eden.Regard

%default total

------------------------------------------------------------------------
-- Similarity method selection
------------------------------------------------------------------------

||| Available similarity computation methods.
public export
data SimilarityMethod = Jaccard | TFIDF | Bigram | Embedding

public export
Eq SimilarityMethod where
  Jaccard   == Jaccard   = True
  TFIDF     == TFIDF     = True
  Bigram    == Bigram    = True
  Embedding == Embedding = True
  _         == _         = False

public export
Show SimilarityMethod where
  show Jaccard   = "jaccard"
  show TFIDF     = "tfidf"
  show Bigram    = "bigram"
  show Embedding = "embedding"

------------------------------------------------------------------------
-- Stopword filtering
------------------------------------------------------------------------

||| Common English stopwords that carry little semantic content.
stopwords : List String
stopwords =
  [ "the", "a", "an", "is", "are", "was", "were", "be", "been", "being"
  , "have", "has", "had", "do", "does", "did", "will", "would", "shall"
  , "should", "may", "might", "must", "can", "could"
  , "i", "me", "my", "we", "our", "you", "your", "he", "him", "his"
  , "she", "her", "it", "its", "they", "them", "their"
  , "this", "that", "these", "those"
  , "in", "on", "at", "to", "for", "of", "with", "by", "from", "as"
  , "into", "about", "between", "through", "during", "before", "after"
  , "and", "but", "or", "nor", "not", "so", "yet", "both", "either"
  , "if", "then", "else", "when", "where", "while", "because", "since"
  , "what", "which", "who", "whom", "how", "why"
  , "all", "each", "every", "some", "any", "no", "more", "most", "very"
  , "just", "also", "than", "too", "only"
  ]

||| Check whether a word is a stopword.
isStopword : String -> Bool
isStopword w = elem w stopwords

||| Filter stopwords from a word list.
filterStopwords : List String -> List String
filterStopwords = filter (not . isStopword)

------------------------------------------------------------------------
-- Basic stemming
------------------------------------------------------------------------

||| Check if a string ends with a given suffix.
endsWithSuffix : String -> String -> Bool
endsWithSuffix s suffix =
  let slen = length s
      suflen = length suffix
  in if suflen > slen then False
     else substr (minus slen suflen) suflen s == suffix

||| Strip a suffix from the end of a string.
stripSuffix : String -> String -> String
stripSuffix s suffix =
  let slen = length s
      suflen = length suffix
  in substr 0 (minus slen suflen) s

||| Basic English stemmer: strips common suffixes.
||| Not a full Porter stemmer, but effective for retrieval improvement.
public export
stemWord : String -> String
stemWord w =
  if length w < 4 then w
  else if endsWithSuffix w "tion" && length w > 6 then stripSuffix w "tion"
  else if endsWithSuffix w "sion" && length w > 6 then stripSuffix w "sion"
  else if endsWithSuffix w "ment" && length w > 6 then stripSuffix w "ment"
  else if endsWithSuffix w "ness" && length w > 6 then stripSuffix w "ness"
  else if endsWithSuffix w "able" && length w > 6 then stripSuffix w "able"
  else if endsWithSuffix w "ible" && length w > 6 then stripSuffix w "ible"
  else if endsWithSuffix w "less" && length w > 6 then stripSuffix w "less"
  else if endsWithSuffix w "ious" && length w > 6 then stripSuffix w "ious"
  else if endsWithSuffix w "eous" && length w > 6 then stripSuffix w "eous"
  else if endsWithSuffix w "ing" && length w > 5 then stripSuffix w "ing"
  else if endsWithSuffix w "ous" && length w > 5 then stripSuffix w "ous"
  else if endsWithSuffix w "ive" && length w > 5 then stripSuffix w "ive"
  else if endsWithSuffix w "ful" && length w > 5 then stripSuffix w "ful"
  else if endsWithSuffix w "ity" && length w > 5 then stripSuffix w "ity"
  else if endsWithSuffix w "est" && length w > 5 then stripSuffix w "est"
  else if endsWithSuffix w "ly" && length w > 4 then stripSuffix w "ly"
  else if endsWithSuffix w "ed" && length w > 4 then stripSuffix w "ed"
  else if endsWithSuffix w "er" && length w > 4 then stripSuffix w "er"
  else if endsWithSuffix w "al" && length w > 4 then stripSuffix w "al"
  else w

------------------------------------------------------------------------
-- Text normalization
------------------------------------------------------------------------

||| Normalize a word: lowercase and stem.
public export
normWord : String -> String
normWord w = stemWord (toLower w)

||| Tokenize text into normalized, filtered words.
public export
tokenize : String -> List String
tokenize text =
  let raw = map normWord (words text)
  in filterStopwords (filter (\w => length w > 1) raw)

------------------------------------------------------------------------
-- Term-overlap similarity (Jaccard)
------------------------------------------------------------------------

wordOverlap : List String -> List String -> Nat
wordOverlap qs ms = length (filter (\w => elem w ms) qs)

||| Jaccard similarity: |intersection| / |union|.
public export
jaccardSimilarity : String -> String -> Double
jaccardSimilarity query memeText =
  let qWords = nub (tokenize query)
      mWords = nub (tokenize memeText)
      unionSize = length (nub (qWords ++ mWords))
  in if unionSize == 0 then 0.0
     else cast (wordOverlap qWords mWords) / cast unionSize

||| Legacy alias for backward compatibility.
public export
termSimilarity : String -> String -> Double
termSimilarity = jaccardSimilarity

------------------------------------------------------------------------
-- Character bigrams (n-gram overlap)
------------------------------------------------------------------------

||| Extract character bigrams from a string.
public export
bigrams : String -> List (Char, Char)
bigrams s = go (unpack (toLower s))
  where
    go : List Char -> List (Char, Char)
    go [] = []
    go [_] = []
    go (a :: b :: rest) = (a, b) :: go (b :: rest)

bigramElem : (Char, Char) -> List (Char, Char) -> Bool
bigramElem _ [] = False
bigramElem (a, b) ((c, d) :: rest) =
  if a == c && b == d then True
  else bigramElem (a, b) rest

bigramNub : List (Char, Char) -> List (Char, Char)
bigramNub [] = []
bigramNub (x :: xs) =
  if bigramElem x xs then bigramNub xs
  else x :: bigramNub xs

||| Bigram Jaccard similarity for Hebrew and similar scripts.
public export
bigramSimilarity : String -> String -> Double
bigramSimilarity query memeText =
  let qBigrams = bigramNub (bigrams query)
      mBigrams = bigramNub (bigrams memeText)
      intersection = length (filter (\bg => bigramElem bg mBigrams) qBigrams)
      unionSize = length (bigramNub (qBigrams ++ mBigrams))
  in if unionSize == 0 then 0.0
     else cast intersection / cast unionSize

------------------------------------------------------------------------
-- TF-IDF similarity
------------------------------------------------------------------------

termCount : String -> List String -> Nat
termCount _ [] = 0
termCount term (w :: ws) =
  if term == w then S (termCount term ws)
  else termCount term ws

tf : String -> List String -> Double
tf term doc =
  let docLen = length doc
  in if docLen == 0 then 0.0
     else cast (termCount term doc) / cast docLen

idf : String -> List (List String) -> Double
idf term corpus =
  let n = length corpus
      df = length (filter (\doc => termCount term doc > 0) corpus)
  in if df == 0 || n == 0 then 0.0
     else log (cast n / cast df)

tfidfWeight : String -> List String -> List (List String) -> Double
tfidfWeight term doc corpus = tf term doc * idf term corpus

dotProduct : List Double -> List Double -> Double
dotProduct [] _ = 0.0
dotProduct _ [] = 0.0
dotProduct (a :: as) (b :: bs) = a * b + dotProduct as bs

magnitude : List Double -> Double
magnitude v = sqrt (dotProduct v v)

cosineSim : List Double -> List Double -> Double
cosineSim v1 v2 =
  let magA = magnitude v1
      magB = magnitude v2
  in if magA == 0.0 || magB == 0.0 then 0.0
     else dotProduct v1 v2 / (magA * magB)

||| Cosine similarity using TF-IDF vectors.
public export
tfidfSimilarity : String -> String -> Double
tfidfSimilarity query memeText =
  let qTokens  = tokenize query
      mTokens  = tokenize memeText
      corpus   = [qTokens, mTokens]
      allTerms = nub (qTokens ++ mTokens)
      qVec     = map (\t => tfidfWeight t qTokens corpus) allTerms
      mVec     = map (\t => tfidfWeight t mTokens corpus) allTerms
  in cosineSim qVec mVec

||| Multi-document TF-IDF similarity with full corpus IDF.
public export
tfidfSimilarityCorpus : String -> String -> List (List String) -> Double
tfidfSimilarityCorpus query memeText corpus =
  let qTokens    = tokenize query
      mTokens    = tokenize memeText
      fullCorpus = qTokens :: corpus
      allTerms   = nub (qTokens ++ mTokens)
      qVec       = map (\t => tfidfWeight t qTokens fullCorpus) allTerms
      mVec       = map (\t => tfidfWeight t mTokens fullCorpus) allTerms
  in cosineSim qVec mVec

------------------------------------------------------------------------
-- Embedding-based similarity
------------------------------------------------------------------------

||| Cosine similarity over two embedding vectors.
||| Returns 0.0 for empty or mismatched vectors.
public export
embeddingSimilarity : List Double -> List Double -> Double
embeddingSimilarity v1 v2 =
  let magA = magnitude v1
      magB = magnitude v2
  in if magA == 0.0 || magB == 0.0 then 0.0
     else dotProduct v1 v2 / (magA * magB)

||| The 64 semantic dimensions used for Claude-generated embeddings.
||| Each dimension is rated from -1.0 to 1.0 by the model.
public export
embeddingDimensions : List String
embeddingDimensions =
  [ "concreteness", "emotionality", "formality", "technicality"
  , "abstractness", "urgency", "certainty", "subjectivity"
  , "complexity", "novelty", "positivity", "negativity"
  , "agency", "temporality", "spatiality", "causality"
  , "morality", "aesthetics", "sociality", "cognition"
  , "embodiment", "spirituality", "humor", "irony"
  , "narrative", "analytical", "poetic", "pragmatic"
  , "philosophical", "scientific", "political", "personal"
  , "universal", "cultural", "historical", "futuristic"
  , "relational", "hierarchical", "cyclical", "linear"
  , "visual", "auditory", "tactile", "olfactory"
  , "emotional_intensity", "intellectual_depth", "accessibility", "ambiguity"
  , "assertiveness", "receptivity", "playfulness", "gravity"
  , "intimacy", "distance", "warmth", "coolness"
  , "tradition", "innovation", "stability", "dynamism"
  , "simplicity", "richness", "precision", "evocativeness"
  , "groundedness", "transcendence", "vulnerability", "resilience"
  ]

||| Build the prompt to send to Claude for embedding generation.
||| Asks Claude to output exactly 64 comma-separated floats.
public export
embeddingPrompt : String -> String
embeddingPrompt text =
  "Rate the following text on these 64 semantic dimensions from -1.0 to 1.0. "
  ++ "Output ONLY a comma-separated list of 64 floating point numbers, nothing else. "
  ++ "Dimensions: " ++ joinDims embeddingDimensions ++ ". "
  ++ "Text: " ++ text
  where
    joinDims : List String -> String
    joinDims [] = ""
    joinDims [x] = x
    joinDims (x :: rest) = x ++ ", " ++ joinDims rest

||| Parse a comma-separated string of doubles into a list.
||| Tolerates whitespace around values. Returns empty list on parse failure.
public export
parseEmbeddingOutput : String -> List Double
parseEmbeddingOutput s =
  let cleaned = pack (filter (\c => c /= '\n' && c /= '\r') (unpack s))
      parts = splitOn ',' cleaned
  in mapMaybe parseDouble' parts
  where
    splitOn : Char -> String -> List String
    splitOn sep str = go (unpack str) [] []
      where
        go : List Char -> List Char -> List String -> List String
        go []        acc toks = reverse (pack (reverse acc) :: toks)
        go (c :: cs) acc toks =
          if c == sep
            then go cs [] (pack (reverse acc) :: toks)
            else go cs (c :: acc) toks
    parseDouble' : String -> Maybe Double
    parseDouble' str =
      let trimmed = trim str
      in if trimmed == "" then Nothing
         else Just (cast {to=Double} trimmed)

||| Embedding cache: maps keys to embedding vectors.
||| Backed by an IORef association list.
public export
record EmbeddingCache where
  constructor MkEmbeddingCache
  ecEntries : IORef (List (String, List Double))

||| Create a fresh empty embedding cache.
export
newEmbeddingCache : IO EmbeddingCache
newEmbeddingCache = do
  ref <- newIORef []
  pure (MkEmbeddingCache ref)

||| Look up a cached embedding by key.
export
lookupEmbedding : EmbeddingCache -> String -> IO (Maybe (List Double))
lookupEmbedding cache key = do
  entries <- readIORef cache.ecEntries
  pure (lookup key entries)

||| Store an embedding in the cache.
export
cacheEmbedding : EmbeddingCache -> String -> List Double -> IO ()
cacheEmbedding cache key vec = do
  entries <- readIORef cache.ecEntries
  let filtered = filter (\p => fst p /= key) entries
  writeIORef cache.ecEntries ((key, vec) :: filtered)

||| Re-rank a list of TF-IDF-scored candidates using embedding similarity.
||| Takes the query embedding and a list of (candidate, embedding) pairs.
||| The embedding similarity is blended with the original TF-IDF score:
|||   blended = 0.6 * embeddingSim + 0.4 * originalSim
||| Then re-scores the candidate with the blended similarity.
public export
rerankWithEmbeddings : List Double -> List (CandidateScore, List Double) -> List CandidateScore
rerankWithEmbeddings queryEmb pairs =
  let reranked = map (\p =>
        let cs = fst p
            mEmb = snd p
            embSim = embeddingSimilarity queryEmb mEmb
            blended = 0.6 * embSim + 0.4 * cs.semanticSimilarity
        in { semanticSimilarity := blended
           , selection := cs.selection - cs.semanticSimilarity + blended
           } cs) pairs
  in sortBy (\a, b => compare b.selection a.selection) reranked

------------------------------------------------------------------------
-- Unified similarity dispatch
------------------------------------------------------------------------

public export
computeSimilarity : SimilarityMethod -> String -> String -> Double
computeSimilarity Jaccard   q t = jaccardSimilarity q t
computeSimilarity TFIDF     q t = tfidfSimilarity q t
computeSimilarity Bigram    q t = bigramSimilarity q t
computeSimilarity Embedding q t = tfidfSimilarity q t  -- fallback; real embeddings need IO

public export
defaultSimilarityMethod : SimilarityMethod
defaultSimilarityMethod = TFIDF

------------------------------------------------------------------------
-- Selection scoring
------------------------------------------------------------------------

public export
selectionScore : SelectionWeights
             -> (sim : Double) -> (act : Double) -> (reg : Double)
             -> (sb : Double)  -> (ef : Double)
             -> (sp : Double)  -> (mp : Double)
             -> Double
selectionScore w sim act reg sb ef sp mp =
  bounded (-12.0) 12.0
    ( w.wSemantic     * sim
    + w.wActivation   * act
    + w.wRegard       * reg
    + w.wSessionBias  * sb
    + w.wFeedback     * ef
    - w.wScopePenalty * sp
    - w.wMembrane     * mp
    )

------------------------------------------------------------------------
-- Component helpers
------------------------------------------------------------------------

public export
calcSessionBias : Scope -> SessionId -> Double
calcSessionBias (SessionScoped sid) current =
  if sid == current then 1.0 else 0.0
calcSessionBias Global              _       = 0.0

public export
calcExplicitFeedback : (rewardEma : Double) -> (riskEma : Double) -> (fc : Nat) -> Double
calcExplicitFeedback rw rk fc =
  if fc == 0 then 0.0
  else let raw   = rw - rk
           t     = if raw > 3.0 then 1.0
                   else if raw < (-3.0) then (-1.0)
                   else raw / (1.0 + abs raw)
           scale = dmin 1.0 (log (cast fc + 1.0) / log 5.0)
       in t * scale

public export
calcScopePenalty : Scope -> SessionId -> Double
calcScopePenalty (SessionScoped sid) current =
  if sid == current then 0.0 else 1.0
calcScopePenalty Global              _       = 0.0

public export
calcMembranePenalty : (conflicts : Nat) -> Double
calcMembranePenalty conflicts =
  if conflicts == 0 then 0.0
  else dmin 1.5 (log (cast conflicts + 1.0) / log 3.0)

------------------------------------------------------------------------
-- Score a single candidate
------------------------------------------------------------------------

public export
scoreCandidate : SelectionWeights -> SessionId
              -> (sim : Double) -> (deltaSec : Double) -> (tau : Double)
              -> (regardVal : Double) -> (scope : Scope)
              -> (rw : Double) -> (rk : Double)
              -> (fc : Nat) -> (mc : Nat)
              -> Double
scoreCandidate w curSess sim deltaSec tau reg scope rw rk fc mc =
  let act = activationDecay deltaSec tau
      sb  = calcSessionBias scope curSess
      ef  = calcExplicitFeedback rw rk fc
      sp  = calcScopePenalty scope curSess
      mp  = calcMembranePenalty mc
  in selectionScore w sim act reg sb ef sp mp

------------------------------------------------------------------------
-- Candidate construction from a meme
------------------------------------------------------------------------

public export
buildCandidateScore : SelectionWeights -> SessionId
                   -> (sim : Double) -> (deltaSec : Double)
                   -> Meme -> CandidateScore
buildCandidateScore w curSess sim deltaSec m =
  let act  = activationDecay deltaSec m.activationTau
      ns   = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau deltaSec m.feedbackCount m.editEma m.contradictionCount m.membraneConflicts
      gm   = MkGraphMetrics 0.5 0.4 0.3
      rb   = regardBreakdown defaultRegardWeights ns gm
      reg  = rb.totalRegard
      sb   = calcSessionBias m.scope curSess
      ef   = calcExplicitFeedback m.rewardEma m.riskEma m.feedbackCount
      sp   = calcScopePenalty m.scope curSess
      mp   = calcMembranePenalty m.membraneConflicts
      sel  = selectionScore w sim act reg sb ef sp mp
  in MkCandidateScore
       { nodeKind           = MemeNode
       , nodeId             = show m.id
       , label              = m.label
       , domain             = m.domain
       , scope              = m.scope
       , sourceKind         = m.sourceKind
       , semanticSimilarity = sim
       , activationVal      = act
       , regard             = reg
       , sessionBias        = sb
       , explicitFeedback   = ef
       , scopePenalty        = sp
       , membranePenalty    = mp
       , selection          = sel
       , text               = m.text
       , provenance         = show m.sourceKind
       }

------------------------------------------------------------------------
-- Active-set selection (top-k)
------------------------------------------------------------------------

public export
selectTopK : (k : Nat) -> List CandidateScore -> List CandidateScore
selectTopK k candidates =
  let sorted = sortBy (\a, b => compare b.selection a.selection) candidates
  in take k sorted

------------------------------------------------------------------------
-- Active-set assembly from memes
------------------------------------------------------------------------

||| Score all memes and select the top k, using the given similarity method.
||| For the Embedding method, this function uses TF-IDF as a pre-filter;
||| actual embedding re-ranking requires IO and is done via assembleActiveSetEmbedding.
public export
assembleActiveSetWith : SimilarityMethod -> SelectionWeights -> SessionId
                     -> (deltaSec : Double) -> (k : Nat)
                     -> (query : String) -> List Meme -> List CandidateScore
assembleActiveSetWith method w curSess deltaSec k query memes =
  let memeTexts = map (\m => tokenize (m.label ++ " " ++ m.text)) memes
      -- For Embedding method, use TF-IDF as pre-filter (re-ranking happens in IO)
      simFn = case method of
        TFIDF     => \mText => tfidfSimilarityCorpus query mText memeTexts
        Embedding => \mText => tfidfSimilarityCorpus query mText memeTexts
        _         => \mText => computeSimilarity method query mText
      candidates = map (\m => buildCandidateScore w curSess
                          (simFn (m.label ++ " " ++ m.text))
                          deltaSec m) memes
  in selectTopK k candidates

||| Score all memes and select the top k (backward-compatible signature).
public export
assembleActiveSet : SelectionWeights -> SessionId
                 -> (deltaSec : Double) -> (k : Nat)
                 -> (query : String) -> List Meme -> List CandidateScore
assembleActiveSet = assembleActiveSetWith defaultSimilarityMethod

------------------------------------------------------------------------
-- Embedding-aware active-set assembly (IO)
------------------------------------------------------------------------

||| Pre-filter expansion factor: how many TF-IDF candidates to consider
||| before embedding re-ranking (3x the final k).
public export
embeddingPrefilterFactor : Nat
embeddingPrefilterFactor = 3

||| Assemble the active set using embedding re-ranking.
||| 1. TF-IDF pre-filter selects top (k * prefilterFactor) candidates
||| 2. Embeddings are computed for the query and each pre-filtered candidate
||| 3. Candidates are re-ranked by blended embedding + TF-IDF similarity
||| 4. Final top-k is selected from the re-ranked set
|||
||| The getOrComputeEmbedding callback handles caching and CLI calls.
||| Falls back to pure TF-IDF if embeddings are empty/unavailable.
export
assembleActiveSetEmbedding : SelectionWeights -> SessionId
                          -> (deltaSec : Double) -> (k : Nat)
                          -> (query : String) -> List Meme
                          -> (getOrComputeEmbedding : String -> String -> IO (List Double))
                          -> IO (List CandidateScore)
assembleActiveSetEmbedding w curSess deltaSec k query memes getEmb = do
  -- Step 1: TF-IDF pre-filter (wider than final k)
  let preK = k * embeddingPrefilterFactor
      preFiltered = assembleActiveSetWith TFIDF w curSess deltaSec preK query memes
  -- Step 2: Get query embedding
  queryEmb <- getEmb "query" query
  if length queryEmb == 0
    then pure (selectTopK k preFiltered)  -- fallback to TF-IDF only
    else do
      -- Step 3: Get embeddings for each candidate, pair them
      pairs <- traverse (\cs => do
        emb <- getEmb cs.nodeId (cs.label ++ " " ++ cs.text)
        pure (cs, emb)) preFiltered
      -- Step 4: Re-rank and take top-k
      let reranked = rerankWithEmbeddings queryEmb pairs
      pure (take k reranked)
