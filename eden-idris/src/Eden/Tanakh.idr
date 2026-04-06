||| Hebrew text processing: gematria, notarikon, temurah, and text utilities.
|||
||| Implements the core hermeneutic operations from the Python TanakhService
||| as pure functions over Unicode codepoints.
|||
||| Hebrew Unicode block:
|||   Letters: U+05D0 (aleph) to U+05EA (tav), 27 codepoints
|||   Final letter forms interleaved: U+05DA, U+05DD, U+05DF, U+05E3, U+05E5
|||   Nikkud (vowel points + cantillation): U+0591 to U+05C7
module Eden.Tanakh

import Data.List
import Data.String

%default total

------------------------------------------------------------------------
-- Unicode constants
------------------------------------------------------------------------

||| First Hebrew letter codepoint (aleph).
hebrewAleph : Int
hebrewAleph = 0x05D0

||| Last Hebrew letter codepoint (tav).
hebrewTav : Int
hebrewTav = 0x05EA

||| Start of nikkud/cantillation range.
nikkudStart : Int
nikkudStart = 0x0591

||| End of nikkud/cantillation range.
nikkudEnd : Int
nikkudEnd = 0x05C7

------------------------------------------------------------------------
-- Character classification
------------------------------------------------------------------------

||| Check if a character is a Hebrew letter (aleph through tav,
||| including final letter forms which fall within the range).
public export
isHebrew : Char -> Bool
isHebrew c =
  let cp = ord c
  in cp >= hebrewAleph && cp <= hebrewTav

||| Check if a character is a nikkud (vowel point or cantillation mark).
public export
isNikkud : Char -> Bool
isNikkud c =
  let cp = ord c
  in cp >= nikkudStart && cp <= nikkudEnd

||| Check if a character is a Hebrew final letter form.
||| Final forms: kaf sofit (05DA), mem sofit (05DD), nun sofit (05DF),
|||              pe sofit (05E3), tsadi sofit (05E5).
public export
isFinalForm : Char -> Bool
isFinalForm c =
  let cp = ord c
  in cp == 0x05DA || cp == 0x05DD || cp == 0x05DF
     || cp == 0x05E3 || cp == 0x05E5

------------------------------------------------------------------------
-- Strip nikkud
------------------------------------------------------------------------

||| Remove all nikkud (vowel points and cantillation marks) from a string.
||| Preserves consonantal letters and non-Hebrew characters.
public export
stripNikkud : String -> String
stripNikkud = pack . filter (not . isNikkud) . unpack

------------------------------------------------------------------------
-- Final-to-standard normalization
------------------------------------------------------------------------

||| Normalize a final letter form to its standard (medial) form.
||| Non-final letters are returned unchanged.
|||
||| Unicode layout (finals precede their standard forms):
|||   U+05DA kaf sofit   -> U+05DB kaf
|||   U+05DD mem sofit   -> U+05DE mem
|||   U+05DF nun sofit   -> U+05E0 nun
|||   U+05E3 pe sofit    -> U+05E4 pe
|||   U+05E5 tsadi sofit -> U+05E6 tsadi
public export
normalizeFinal : Char -> Char
normalizeFinal c =
  let cp = ord c
  in if cp == 0x05DA then chr 0x05DB  -- kaf sofit -> kaf
     else if cp == 0x05DD then chr 0x05DE  -- mem sofit -> mem
     else if cp == 0x05DF then chr 0x05E0  -- nun sofit -> nun
     else if cp == 0x05E3 then chr 0x05E4  -- pe sofit -> pe
     else if cp == 0x05E5 then chr 0x05E6  -- tsadi sofit -> tsadi
     else c

------------------------------------------------------------------------
-- Gematria (mispar hechrachi — standard numerical values)
------------------------------------------------------------------------

||| Standard gematria value for a Hebrew letter codepoint.
||| After normalizeFinal, the 22 standard letters have these codepoints:
|||   aleph  05D0=1, bet   05D1=2,  gimel  05D2=3,  dalet 05D3=4,
|||   he     05D4=5, vav   05D5=6,  zayin  05D6=7,  chet  05D7=8,
|||   tet    05D8=9, yod   05D9=10, kaf    05DB=20, lamed 05DC=30,
|||   mem    05DE=40, nun  05E0=50, samekh 05E1=60, ayin  05E2=70,
|||   pe     05E4=80, tsadi 05E6=90, qof   05E7=100, resh 05E8=200,
|||   shin   05E9=300, tav  05EA=400.
||| Returns 0 for non-Hebrew characters and for final-form codepoints
||| (call normalizeFinal first).
gematriaTable : Int -> Int
gematriaTable cp =
  if      cp == 0x05D0 then 1
  else if cp == 0x05D1 then 2
  else if cp == 0x05D2 then 3
  else if cp == 0x05D3 then 4
  else if cp == 0x05D4 then 5
  else if cp == 0x05D5 then 6
  else if cp == 0x05D6 then 7
  else if cp == 0x05D7 then 8
  else if cp == 0x05D8 then 9
  else if cp == 0x05D9 then 10
  else if cp == 0x05DB then 20
  else if cp == 0x05DC then 30
  else if cp == 0x05DE then 40
  else if cp == 0x05E0 then 50
  else if cp == 0x05E1 then 60
  else if cp == 0x05E2 then 70
  else if cp == 0x05E4 then 80
  else if cp == 0x05E6 then 90
  else if cp == 0x05E7 then 100
  else if cp == 0x05E8 then 200
  else if cp == 0x05E9 then 300
  else if cp == 0x05EA then 400
  else 0

||| Standard gematria value for a Hebrew letter.
||| Returns 0 for non-Hebrew characters.
||| Final forms are normalized to their standard counterparts.
public export
letterValue : Char -> Int
letterValue c = gematriaTable (ord (normalizeFinal c))

||| Compute the gematria (numerical value) of a word or phrase.
||| Non-Hebrew characters are skipped.
public export
gematria : String -> Int
gematria = foldl (\acc, c => acc + letterValue c) 0 . unpack

------------------------------------------------------------------------
-- Hebrew letter names
------------------------------------------------------------------------

||| Return the English transliteration name of a Hebrew letter.
||| Returns "" for non-Hebrew characters.
||| Final forms are normalized before lookup.
public export
hebrewLetterName : Char -> String
hebrewLetterName c =
  let cp = ord (normalizeFinal c)
  in if      cp == 0x05D0 then "Aleph"
     else if cp == 0x05D1 then "Bet"
     else if cp == 0x05D2 then "Gimel"
     else if cp == 0x05D3 then "Dalet"
     else if cp == 0x05D4 then "He"
     else if cp == 0x05D5 then "Vav"
     else if cp == 0x05D6 then "Zayin"
     else if cp == 0x05D7 then "Chet"
     else if cp == 0x05D8 then "Tet"
     else if cp == 0x05D9 then "Yod"
     else if cp == 0x05DB then "Kaf"
     else if cp == 0x05DC then "Lamed"
     else if cp == 0x05DE then "Mem"
     else if cp == 0x05E0 then "Nun"
     else if cp == 0x05E1 then "Samekh"
     else if cp == 0x05E2 then "Ayin"
     else if cp == 0x05E4 then "Pe"
     else if cp == 0x05E6 then "Tsadi"
     else if cp == 0x05E7 then "Qof"
     else if cp == 0x05E8 then "Resh"
     else if cp == 0x05E9 then "Shin"
     else if cp == 0x05EA then "Tav"
     else ""

------------------------------------------------------------------------
-- Notarikon (acronym analysis)
------------------------------------------------------------------------

||| Extract Hebrew letters from a string.
hebrewLetters : String -> List Char
hebrewLetters = filter isHebrew . unpack

||| Split text into words and extract their Hebrew letters.
||| Returns a list of (raw word, hebrew letters in word) pairs.
||| Words with no Hebrew letters are excluded.
tokenizeHebrewWords : String -> List (String, List Char)
tokenizeHebrewWords s =
  let ws = words s
  in mapMaybe (\w =>
       let letters = hebrewLetters w
       in case letters of
            [] => Nothing
            _  => Just (w, letters)
     ) ws

||| Roshei teivot: extract the first Hebrew letter of each word.
public export
rosheiTeivot : String -> String
rosheiTeivot s =
  let tokens = tokenizeHebrewWords s
      firsts = mapMaybe (\p => head' (snd p)) tokens
  in pack firsts

||| Sofei teivot: extract the last Hebrew letter of each word.
public export
sofeiTeivot : String -> String
sofeiTeivot s =
  let tokens = tokenizeHebrewWords s
      lasts  = mapMaybe (\p => last' (snd p)) tokens
  in pack lasts

------------------------------------------------------------------------
-- Temurah — At-Bash cipher
------------------------------------------------------------------------

||| The 22 standard Hebrew letters in canonical order (no final forms).
||| Used as the basis for At-Bash mirror pairing.
standardLetters : List Int
standardLetters =
  [ 0x05D0, 0x05D1, 0x05D2, 0x05D3, 0x05D4, 0x05D5, 0x05D6
  , 0x05D7, 0x05D8, 0x05D9, 0x05DB, 0x05DC, 0x05DE, 0x05E0
  , 0x05E1, 0x05E2, 0x05E4, 0x05E6, 0x05E7, 0x05E8, 0x05E9
  , 0x05EA
  ]

||| At-Bash lookup table: maps a standard letter codepoint to its mirror.
||| Aleph(1st) <-> Tav(22nd), Bet(2nd) <-> Shin(21st), etc.
atBashTable : Int -> Int
atBashTable cp =
  -- Pair 1: aleph <-> tav
  if      cp == 0x05D0 then 0x05EA
  else if cp == 0x05EA then 0x05D0
  -- Pair 2: bet <-> shin
  else if cp == 0x05D1 then 0x05E9
  else if cp == 0x05E9 then 0x05D1
  -- Pair 3: gimel <-> resh
  else if cp == 0x05D2 then 0x05E8
  else if cp == 0x05E8 then 0x05D2
  -- Pair 4: dalet <-> qof
  else if cp == 0x05D3 then 0x05E7
  else if cp == 0x05E7 then 0x05D3
  -- Pair 5: he <-> tsadi
  else if cp == 0x05D4 then 0x05E6
  else if cp == 0x05E6 then 0x05D4
  -- Pair 6: vav <-> pe
  else if cp == 0x05D5 then 0x05E4
  else if cp == 0x05E4 then 0x05D5
  -- Pair 7: zayin <-> ayin
  else if cp == 0x05D6 then 0x05E2
  else if cp == 0x05E2 then 0x05D6
  -- Pair 8: chet <-> samekh
  else if cp == 0x05D7 then 0x05E1
  else if cp == 0x05E1 then 0x05D7
  -- Pair 9: tet <-> nun
  else if cp == 0x05D8 then 0x05E0
  else if cp == 0x05E0 then 0x05D8
  -- Pair 10: yod <-> mem
  else if cp == 0x05D9 then 0x05DE
  else if cp == 0x05DE then 0x05D9
  -- Pair 11: kaf <-> lamed
  else if cp == 0x05DB then 0x05DC
  else if cp == 0x05DC then 0x05DB
  -- Not a standard letter
  else cp

||| At-Bash substitution for a single character.
||| Final forms are normalized first, then substituted.
||| Non-Hebrew characters pass through unchanged.
public export
atBash : Char -> Char
atBash c =
  if isHebrew c
    then chr (atBashTable (ord (normalizeFinal c)))
    else c

||| Apply At-Bash cipher to an entire string.
||| Non-Hebrew characters (including nikkud and spaces) pass through unchanged.
public export
atBashStr : String -> String
atBashStr = pack . map atBash . unpack

------------------------------------------------------------------------
-- Convenience: combined analysis
------------------------------------------------------------------------

||| Result of a combined Hebrew text analysis.
public export
record HebrewAnalysis where
  constructor MkHebrewAnalysis
  inputText      : String
  strippedText   : String
  gematriaValue  : Int
  rosheiResult   : String
  sofeiResult    : String
  atBashResult   : String
  letterCount    : Nat

||| Perform a combined analysis on Hebrew text: strip nikkud, compute
||| gematria, extract notarikon (roshei and sofei teivot), and apply At-Bash.
public export
analyzeHebrew : String -> HebrewAnalysis
analyzeHebrew input =
  let stripped = stripNikkud input
  in MkHebrewAnalysis
       input
       stripped
       (gematria stripped)
       (rosheiTeivot stripped)
       (sofeiTeivot stripped)
       (atBashStr stripped)
       (length (hebrewLetters stripped))

||| Format a HebrewAnalysis as a human-readable summary string.
public export
showAnalysis : HebrewAnalysis -> String
showAnalysis a =
  unlines [ "Hebrew Analysis"
          , "  Input:    " ++ a.inputText
          , "  Stripped: " ++ a.strippedText
          , "  Letters:  " ++ show a.letterCount
          , "  Gematria: " ++ show a.gematriaValue
          , "  Roshei:   " ++ a.rosheiResult
          , "  Sofei:    " ++ a.sofeiResult
          , "  At-Bash:  " ++ a.atBashResult
          ]

------------------------------------------------------------------------
-- Multiple gematria schemes
------------------------------------------------------------------------

||| Gematria calculation schemes.
||| - Standard: mispar hechrachi (standard values, finals normalized)
||| - Gadol: final letter forms retain full hundreds values
||| - Katan: each letter reduced to single digit (1-9)
||| - Ordinal: positional value (aleph=1, bet=2, ..., tav=22)
public export
data GematriaScheme = Standard | Gadol | Katan | Ordinal

public export
Show GematriaScheme where
  show Standard = "standard"
  show Gadol    = "gadol"
  show Katan    = "katan"
  show Ordinal  = "ordinal"

public export
Eq GematriaScheme where
  Standard == Standard = True
  Gadol    == Gadol    = True
  Katan    == Katan    = True
  Ordinal  == Ordinal  = True
  _        == _        = False

||| Gematria gadol: final letter forms at their full extended values.
||| kaf sofit=500, mem sofit=600, nun sofit=700, pe sofit=800, tsadi sofit=900.
||| Standard letters use their normal values.
gematriaGadolValue : Char -> Int
gematriaGadolValue c =
  let cp = ord c
  in if      cp == 0x05DA then 500   -- kaf sofit
     else if cp == 0x05DD then 600   -- mem sofit
     else if cp == 0x05DF then 700   -- nun sofit
     else if cp == 0x05E3 then 800   -- pe sofit
     else if cp == 0x05E5 then 900   -- tsadi sofit
     else gematriaTable (ord (normalizeFinal c))

||| Gematria katan: reduce each standard letter value to a single digit.
||| 1-9 -> 1-9, 10-90 -> 1-9, 100-400 -> 1-4.
gematriaKatanValue : Char -> Int
gematriaKatanValue c =
  let v = letterValue c
  in if v == 0 then 0
     else let reduced = if v >= 100 then v `div` 100
                        else if v >= 10 then v `div` 10
                        else v
          in reduced

||| Gematria ordinal: positional value in the alphabet.
||| aleph=1, bet=2, ..., tav=22.
gematriaOrdinalTable : Int -> Int
gematriaOrdinalTable cp =
  if      cp == 0x05D0 then 1   -- aleph
  else if cp == 0x05D1 then 2   -- bet
  else if cp == 0x05D2 then 3   -- gimel
  else if cp == 0x05D3 then 4   -- dalet
  else if cp == 0x05D4 then 5   -- he
  else if cp == 0x05D5 then 6   -- vav
  else if cp == 0x05D6 then 7   -- zayin
  else if cp == 0x05D7 then 8   -- chet
  else if cp == 0x05D8 then 9   -- tet
  else if cp == 0x05D9 then 10  -- yod
  else if cp == 0x05DB then 11  -- kaf
  else if cp == 0x05DC then 12  -- lamed
  else if cp == 0x05DE then 13  -- mem
  else if cp == 0x05E0 then 14  -- nun
  else if cp == 0x05E1 then 15  -- samekh
  else if cp == 0x05E2 then 16  -- ayin
  else if cp == 0x05E4 then 17  -- pe
  else if cp == 0x05E6 then 18  -- tsadi
  else if cp == 0x05E7 then 19  -- qof
  else if cp == 0x05E8 then 20  -- resh
  else if cp == 0x05E9 then 21  -- shin
  else if cp == 0x05EA then 22  -- tav
  else 0

gematriaOrdinalValue : Char -> Int
gematriaOrdinalValue c = gematriaOrdinalTable (ord (normalizeFinal c))

||| Compute the gematria value of a single character under a given scheme.
public export
letterValueWith : GematriaScheme -> Char -> Int
letterValueWith Standard c = letterValue c
letterValueWith Gadol    c = gematriaGadolValue c
letterValueWith Katan    c = gematriaKatanValue c
letterValueWith Ordinal  c = gematriaOrdinalValue c

||| Compute the gematria of a word or phrase under a given scheme.
||| Non-Hebrew characters are skipped.
public export
gematriaWith : GematriaScheme -> String -> Int
gematriaWith scheme = foldl (\acc, c => acc + letterValueWith scheme c) 0 . unpack

||| Compute gematria gadol of a word or phrase.
||| Final letter forms use extended values (500-900).
public export
gematriaGadol : String -> Int
gematriaGadol = gematriaWith Gadol

||| Compute gematria katan of a word or phrase.
||| Each letter is reduced to a single digit (1-9).
public export
gematriaKatan : String -> Int
gematriaKatan = gematriaWith Katan

||| Compute gematria ordinal of a word or phrase.
||| Each letter is valued by its position: aleph=1 through tav=22.
public export
gematriaOrdinal : String -> Int
gematriaOrdinal = gematriaWith Ordinal

------------------------------------------------------------------------
-- Gematria equivalence search
------------------------------------------------------------------------

||| Check if two strings have equal gematria under the standard scheme.
public export
areGematriaEqual : String -> String -> Bool
areGematriaEqual a b = gematria a == gematria b

||| Check if two strings have equal gematria under a given scheme.
public export
areGematriaEqualWith : GematriaScheme -> String -> String -> Bool
areGematriaEqualWith scheme a b = gematriaWith scheme a == gematriaWith scheme b

||| Find all strings in a corpus that have a given gematria value
||| under the standard scheme.
public export
findEquivalent : Int -> List String -> List String
findEquivalent target = filter (\s => gematria s == target)

||| Find all strings in a corpus that have a given gematria value
||| under a specified scheme.
public export
findEquivalentWith : GematriaScheme -> Int -> List String -> List String
findEquivalentWith scheme target = filter (\s => gematriaWith scheme s == target)

------------------------------------------------------------------------
-- Enhanced analysis: per-word and per-letter breakdowns
------------------------------------------------------------------------

||| Compute gematria for each word in a phrase, returning (word, value) pairs.
||| Words with no Hebrew letters are excluded.
public export
wordGematria : String -> List (String, Int)
wordGematria s =
  let ws = words s
  in mapMaybe (\w =>
       let letters = hebrewLetters w
       in case letters of
            [] => Nothing
            _  => Just (w, gematria w)
     ) ws

||| Compute gematria for each word under a given scheme.
public export
wordGematriaWith : GematriaScheme -> String -> List (String, Int)
wordGematriaWith scheme s =
  let ws = words s
  in mapMaybe (\w =>
       let letters = hebrewLetters w
       in case letters of
            [] => Nothing
            _  => Just (w, gematriaWith scheme w)
     ) ws

||| Per-letter breakdown: for each Hebrew letter in a string, return
||| (character, letter name, standard gematria value).
||| Non-Hebrew characters are skipped.
public export
letterBreakdown : String -> List (Char, String, Int)
letterBreakdown s =
  let chars = filter isHebrew (unpack s)
  in map (\c => (c, hebrewLetterName c, letterValue c)) chars

||| Per-letter breakdown under a given scheme.
public export
letterBreakdownWith : GematriaScheme -> String -> List (Char, String, Int)
letterBreakdownWith scheme s =
  let chars = filter isHebrew (unpack s)
  in map (\c => (c, hebrewLetterName c, letterValueWith scheme c)) chars

------------------------------------------------------------------------
-- Scene compiler types (foundation for 3D visualization)
------------------------------------------------------------------------

||| Spatial coordinate in scene space.
public export
record Vec3 where
  constructor MkVec3
  vx : Double
  vy : Double
  vz : Double

||| A passage with its analysis attached.
public export
record AnalyzedPassage where
  constructor MkAnalyzedPassage
  apText       : String
  apAnalysis   : HebrewAnalysis
  apScheme     : GematriaScheme
  apGadolVal   : Int
  apKatanVal   : Int
  apOrdinalVal : Int

||| A scene element: an analyzed passage with spatial placement.
public export
record SceneElement where
  constructor MkSceneElement
  sePassage  : AnalyzedPassage
  sePosition : Vec3
  seScale    : Double
  seLayer    : Nat

||| A compiled scene: passages analyzed and placed for visualization.
public export
record Scene where
  constructor MkScene
  scTitle      : String
  scElements   : List SceneElement
  scTotalGem   : Int
  scPassageCount : Nat

||| Analyze a passage under all gematria schemes.
public export
analyzePassage : String -> AnalyzedPassage
analyzePassage text =
  MkAnalyzedPassage
    text
    (analyzeHebrew text)
    Standard
    (gematriaGadol text)
    (gematriaKatan text)
    (gematriaOrdinal text)

||| Simple layout: place passages along a vertical axis, spaced by index.
placeElements : List AnalyzedPassage -> List SceneElement
placeElements passages = go 0 passages
  where
    go : Nat -> List AnalyzedPassage -> List SceneElement
    go _ []        = []
    go n (p :: ps) =
      let y = cast {to=Double} n * 2.0
          pos = MkVec3 0.0 y 0.0
      in MkSceneElement p pos 1.0 n :: go (S n) ps

||| Compile a list of passage strings into a scene.
||| Each passage is analyzed under all gematria schemes and placed
||| in a linear vertical layout for frontend consumption.
public export
compileScene : String -> List String -> Scene
compileScene title passages =
  let analyzed = map analyzePassage passages
      elements = placeElements analyzed
      totalGem = foldl (\acc, p => acc + p.apAnalysis.gematriaValue) 0 analyzed
  in MkScene title elements totalGem (length passages)

------------------------------------------------------------------------
-- Scene JSON serialization
------------------------------------------------------------------------

||| Minimal JSON helpers (self-contained to keep Tanakh pure/importless).
scJsonStr : String -> String
scJsonStr s = "\"" ++ s ++ "\""

scJsonNum : Double -> String
scJsonNum d =
  let i = cast {to=Integer} (d * 1000.0)
  in show (cast {to=Double} i / 1000.0)

scJsonInt : Int -> String
scJsonInt = show

scJsonNat : Nat -> String
scJsonNat = show

scJsonObj : List (String, String) -> String
scJsonObj fields =
  "{" ++ joinFields fields ++ "}"
  where
    joinFields : List (String, String) -> String
    joinFields [] = ""
    joinFields [(k, v)] = scJsonStr k ++ ": " ++ v
    joinFields ((k, v) :: rest) = scJsonStr k ++ ": " ++ v ++ ", " ++ joinFields rest

scJsonArr : List String -> String
scJsonArr items = "[" ++ joinItems items ++ "]"
  where
    joinItems : List String -> String
    joinItems [] = ""
    joinItems [x] = x
    joinItems (x :: rest) = x ++ ", " ++ joinItems rest

||| Serialize a Vec3 to JSON.
vec3ToJson : Vec3 -> String
vec3ToJson v = scJsonObj
  [ ("x", scJsonNum v.vx)
  , ("y", scJsonNum v.vy)
  , ("z", scJsonNum v.vz)
  ]

||| Serialize an AnalyzedPassage to JSON.
passageToJson : AnalyzedPassage -> String
passageToJson p = scJsonObj
  [ ("text",         scJsonStr p.apText)
  , ("gematria",     scJsonInt p.apAnalysis.gematriaValue)
  , ("gadol",        scJsonInt p.apGadolVal)
  , ("katan",        scJsonInt p.apKatanVal)
  , ("ordinal",      scJsonInt p.apOrdinalVal)
  , ("letter_count", scJsonNat p.apAnalysis.letterCount)
  , ("roshei",       scJsonStr p.apAnalysis.rosheiResult)
  , ("sofei",        scJsonStr p.apAnalysis.sofeiResult)
  , ("atbash",       scJsonStr p.apAnalysis.atBashResult)
  ]

||| Serialize a SceneElement to JSON.
elementToJson : SceneElement -> String
elementToJson se = scJsonObj
  [ ("passage",  passageToJson se.sePassage)
  , ("position", vec3ToJson se.sePosition)
  , ("scale",    scJsonNum se.seScale)
  , ("layer",    scJsonNat se.seLayer)
  ]

||| Serialize a Scene to JSON for frontend consumption.
public export
sceneToJSON : Scene -> String
sceneToJSON sc = scJsonObj
  [ ("title",         scJsonStr sc.scTitle)
  , ("passage_count", scJsonNat sc.scPassageCount)
  , ("total_gematria", scJsonInt sc.scTotalGem)
  , ("elements",      scJsonArr (map elementToJson sc.scElements))
  ]

------------------------------------------------------------------------
-- Enhanced HebrewAnalysis with multi-scheme results
------------------------------------------------------------------------

||| Extended analysis including all gematria schemes.
public export
record HebrewAnalysisExt where
  constructor MkHebrewAnalysisExt
  haeBase     : HebrewAnalysis
  haeGadol    : Int
  haeKatan    : Int
  haeOrdinal  : Int
  haeWords    : List (String, Int)
  haeLetters  : List (Char, String, Int)

||| Perform extended analysis on Hebrew text including all gematria schemes,
||| per-word breakdown, and per-letter breakdown.
public export
analyzeHebrewExt : String -> HebrewAnalysisExt
analyzeHebrewExt input =
  let base = analyzeHebrew input
      stripped = base.strippedText
  in MkHebrewAnalysisExt
       base
       (gematriaGadol stripped)
       (gematriaKatan stripped)
       (gematriaOrdinal stripped)
       (wordGematria stripped)
       (letterBreakdown stripped)

||| Format an extended analysis as a human-readable summary.
public export
showAnalysisExt : HebrewAnalysisExt -> String
showAnalysisExt a =
  let base = a.haeBase
      wordLines = map (\p => "    " ++ fst p ++ " = " ++ show (snd p)) a.haeWords
      letterLines = map (\t =>
        let c = fst t
            nm = fst (snd t)
            v = snd (snd t)
        in "    " ++ singleton c ++ " (" ++ nm ++ ") = " ++ show v) a.haeLetters
  in unlines ([ "Hebrew Analysis (Extended)"
              , "  Input:       " ++ base.inputText
              , "  Stripped:    " ++ base.strippedText
              , "  Letters:     " ++ show base.letterCount
              , "  Standard:    " ++ show base.gematriaValue
              , "  Gadol:       " ++ show a.haeGadol
              , "  Katan:       " ++ show a.haeKatan
              , "  Ordinal:     " ++ show a.haeOrdinal
              , "  Roshei:      " ++ base.rosheiResult
              , "  Sofei:       " ++ base.sofeiResult
              , "  At-Bash:     " ++ base.atBashResult
              , "  Word breakdown:"
              ] ++ wordLines
              ++ ["  Letter breakdown:"]
              ++ letterLines)
