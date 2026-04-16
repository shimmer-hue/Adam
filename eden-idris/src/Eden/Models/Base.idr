||| Base model types: GenerateParams and ModelResult.
module Eden.Models.Base

%default total

------------------------------------------------------------------------
-- Generate parameters
------------------------------------------------------------------------

public export
record GenerateParams where
  constructor MkGenerateParams
  gpSystemPrompt : String
  gpConvPrompt   : String
  gpMaxTokens    : Nat
  gpTemp         : Double
  gpTopP         : Double
  gpRepPen       : Double

------------------------------------------------------------------------
-- Model result
------------------------------------------------------------------------

public export
record ModelResult where
  constructor MkModelResult
  mrBackend       : String
  mrText          : String
  mrTokenEstimate : Nat
  mrRawOutput     : String
  mrStopReason    : String
  mrCleanedText   : String
