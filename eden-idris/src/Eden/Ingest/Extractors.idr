||| Document extraction for PDF, CSV, and plain text formats.
|||
||| PDF extraction uses the `pdftotext` command-line tool (poppler-utils).
||| CSV parsing handles quoted fields. Plain text / Markdown are read directly.
||| Provides quality scoring for PDF output.
module Eden.Ingest.Extractors

import Data.List
import Data.String
import Eden.Types
import Eden.TermIO
import System.File.ReadWrite

%default covering

------------------------------------------------------------------------
-- Format detection
------------------------------------------------------------------------

||| Detect document format from file extension.
export
detectFormat : String -> DocKind
detectFormat path =
  let ext = toLower (getExtension path)
  in if ext == "pdf" then PDF
     else if ext == "csv" then CSV
     else if ext == "md" || ext == "markdown" then Markdown
     else PlainText
  where
    ||| Extract file extension (after last dot).
    getExtension : String -> String
    getExtension s =
      let chars = unpack s
          revChars = reverse chars
          ext = takeWhile (\c => c /= '.') revChars
      in if length ext == length chars
           then ""   -- no dot found
           else pack (reverse ext)

------------------------------------------------------------------------
-- Plain text extraction
------------------------------------------------------------------------

||| Extract text from a plain text or markdown file.
||| Simply reads the file content.
export
extractPlaintext : String -> IO (Either String String)
extractPlaintext path = do
  result <- readFile path
  case result of
    Right content => pure (Right content)
    Left err      => pure (Left ("Failed to read file: " ++ path))

------------------------------------------------------------------------
-- CSV extraction
------------------------------------------------------------------------

||| Parse a single CSV field, handling quoted fields.
||| Returns (field_value, remaining_input).
parseCsvField : List Char -> (String, List Char)
parseCsvField [] = ("", [])
parseCsvField ('"' :: rest) = parseQuoted rest []
  where
    parseQuoted : List Char -> List Char -> (String, List Char)
    parseQuoted [] acc = (pack (reverse acc), [])
    parseQuoted ('"' :: '"' :: xs) acc = parseQuoted xs ('"' :: acc)
    parseQuoted ('"' :: ',' :: xs) acc = (pack (reverse acc), xs)
    parseQuoted ('"' :: xs) acc = (pack (reverse acc), xs)
    parseQuoted (x :: xs) acc = parseQuoted xs (x :: acc)
parseCsvField cs = parseUnquoted cs []
  where
    parseUnquoted : List Char -> List Char -> (String, List Char)
    parseUnquoted [] acc = (pack (reverse acc), [])
    parseUnquoted (',' :: xs) acc = (pack (reverse acc), xs)
    parseUnquoted (x :: xs) acc = parseUnquoted xs (x :: acc)

||| Parse a single CSV line into a list of fields.
parseCsvLine : String -> List String
parseCsvLine s = go (unpack s)
  where
    go : List Char -> List String
    go [] = [""]
    go cs =
      let (field, rest) = parseCsvField cs
      in case rest of
           [] => [field]
           _  => field :: go rest

||| Check if a row has any non-empty cells.
rowHasContent : List String -> Bool
rowHasContent = any (\cell => trim cell /= "")

||| Format a CSV row as readable text with pipe separators.
formatRow : List String -> String
formatRow cells = joinBy " | " (map trim cells)
  where
    joinBy : String -> List String -> String
    joinBy sep [] = ""
    joinBy sep [x] = x
    joinBy sep (x :: xs) = x ++ sep ++ joinBy sep xs

||| Extract text from a CSV file.
||| Reads the file, parses rows, and formats each row with pipe separators.
export
extractCsv : String -> IO (Either String String)
extractCsv path = do
  result <- readFile path
  case result of
    Left err => pure (Left ("Failed to read CSV: " ++ path))
    Right content =>
      let rawLines = lines content
          rows = map parseCsvLine rawLines
          nonEmpty = filter rowHasContent rows
          formatted = map formatRow nonEmpty
          text = unlines formatted
      in pure (Right text)

------------------------------------------------------------------------
-- PDF extraction
------------------------------------------------------------------------

||| Escape a file path for shell use by wrapping in double quotes.
shellQuote : String -> String
shellQuote path = "\"" ++ path ++ "\""

||| Extract text from a PDF using pdftotext (poppler-utils).
||| Tries standard mode first, falls back to layout mode.
export
extractPdf : String -> IO (Either String String)
extractPdf path = do
  -- Try standard pdftotext first
  (output, exitCode) <- runCommand ("pdftotext " ++ shellQuote path ++ " -")
  rearmTerminal
  if exitCode == 0 && trim output /= ""
    then pure (Right output)
    else do
      -- Fall back to layout mode
      (layoutOutput, layoutCode) <- runCommand ("pdftotext -layout " ++ shellQuote path ++ " -")
      rearmTerminal
      if layoutCode == 0 && trim layoutOutput /= ""
        then pure (Right layoutOutput)
        else pure (Left ("pdftotext failed for: " ++ path
                         ++ " (exit codes: " ++ show exitCode
                         ++ ", " ++ show layoutCode ++ ")"))

------------------------------------------------------------------------
-- PDF quality scoring
------------------------------------------------------------------------

||| Count occurrences of a character in a string.
countChar : Char -> String -> Nat
countChar c s = length (filter (== c) (unpack s))

||| Count words in a string (split on whitespace).
countWords : String -> Nat
countWords s = length (filter (\w => w /= "") (words s))

||| Count lines in a string.
countLines : String -> Nat
countLines s = length (lines s)

||| Count non-blank lines in a string.
countNonBlankLines : String -> Nat
countNonBlankLines s = length (filter (\l => trim l /= "") (lines l))
  where l : String
        l = s

||| Count lines shorter than a given length.
countShortLines : Nat -> String -> Nat
countShortLines threshold s =
  let ls = filter (\l => trim l /= "") (lines s)
  in length (filter (\l => length l < threshold) ls)

||| Count Unicode replacement characters (U+FFFD).
countReplacementChars : String -> Nat
countReplacementChars s = length (filter (\c => c == '\xFFFD') (unpack s))

||| Score the quality of PDF-extracted text.
||| Compares characteristics of the text to detect garbled output,
||| excessive whitespace, or very short extraction results.
||| Returns a score between 0.0 (unusable) and 1.0 (clean).
export
scorePdfQuality : String -> Double
scorePdfQuality text =
  let wc = countWords text
      nonBlank = countNonBlankLines text
      shortLines = countShortLines 24 text
      veryShortLines = countShortLines 8 text
      replacements = countReplacementChars text

      shortRatio : Double
      shortRatio = if nonBlank == 0 then 0.0
                   else cast shortLines / cast nonBlank
      veryShortRatio : Double
      veryShortRatio = if nonBlank == 0 then 0.0
                       else cast veryShortLines / cast nonBlank

      -- Start with perfect score and subtract penalties
      score : Double
      score = 1.0

      -- Penalty for replacement glyphs (garbled text)
      s1 : Double
      s1 = score - min 0.35 (cast replacements * 0.08)

      -- Penalty for very short output
      s2 : Double
      s2 = if wc < 30 then s1 - 0.22
           else if wc < 80 then s1 - 0.08
           else s1

      -- Penalty for fragmented lines
      s3 : Double
      s3 = if shortRatio > 0.4
             then s2 - min 0.18 ((shortRatio - 0.4) * 0.45 + 0.08)
             else s2

      s4 : Double
      s4 = if veryShortRatio > 0.18
             then s3 - min 0.12 ((veryShortRatio - 0.18) * 0.6 + 0.04)
             else s3

      -- Clamp to [0.0, 1.0]
      final : Double
      final = max 0.0 (min 1.0 s4)

  in final

------------------------------------------------------------------------
-- Unified extraction entry point
------------------------------------------------------------------------

||| Extract text from a document, automatically detecting the format
||| from the file extension.
||| Returns (extracted_text, detected_format) on success,
||| or an error message on failure.
export
extractDocument : String -> IO (Either String (String, DocKind))
extractDocument path =
  let fmt = detectFormat path
  in case fmt of
       PDF => do
         result <- extractPdf path
         case result of
           Right text => pure (Right (text, PDF))
           Left err   => pure (Left err)
       CSV => do
         result <- extractCsv path
         case result of
           Right text => pure (Right (text, CSV))
           Left err   => pure (Left err)
       Markdown => do
         result <- extractPlaintext path
         case result of
           Right text => pure (Right (text, Markdown))
           Left err   => pure (Left err)
       PlainText => do
         result <- extractPlaintext path
         case result of
           Right text => pure (Right (text, PlainText))
           Left err   => pure (Left err)
