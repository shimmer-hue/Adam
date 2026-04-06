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
