||| Retrieval and candidate scoring for active-set assembly.
|||
||| The active set is the bounded retrieval and prompt-compilation slice.
||| It is NOT a hidden governor or planning layer.
|||
||| Similarity methods:
|||   - Jaccard: word-level set overlap (original, fast)
|||   - TFIDF: term frequency-inverse document frequency with cosine similarity
|||   - Bigram: character bigram overlap (useful for Hebrew and other scripts)
module Eden.Retrieval

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
data SimilarityMethod = Jaccard | TFIDF | Bigram

public export
Eq SimilarityMethod where
  Jaccard == Jaccard = True
  TFIDF   == TFIDF   = True
  Bigram  == Bigram  = True
  _       == _       = False

public export
Show SimilarityMethod where
  show Jaccard = "jaccard"
  show TFIDF   = "tfidf"
  show Bigram  = "bigram"

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
-- Unified similarity dispatch
------------------------------------------------------------------------

public export
computeSimilarity : SimilarityMethod -> String -> String -> Double
computeSimilarity Jaccard q t = jaccardSimilarity q t
computeSimilarity TFIDF   q t = tfidfSimilarity q t
computeSimilarity Bigram  q t = bigramSimilarity q t

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
      ns   = MkNodeState m.rewardEma m.riskEma m.evidenceN m.usageCount m.activationTau deltaSec
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
public export
assembleActiveSetWith : SimilarityMethod -> SelectionWeights -> SessionId
                     -> (deltaSec : Double) -> (k : Nat)
                     -> (query : String) -> List Meme -> List CandidateScore
assembleActiveSetWith method w curSess deltaSec k query memes =
  let memeTexts = map (\m => tokenize (m.label ++ " " ++ m.text)) memes
      simFn = case method of
        TFIDF => \mText => tfidfSimilarityCorpus query mText memeTexts
        _     => \mText => computeSimilarity method query mText
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
