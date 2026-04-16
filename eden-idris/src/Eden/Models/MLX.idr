||| MLX backend configuration and model registry.
module Eden.Models.MLX

import Data.String

%default total

------------------------------------------------------------------------
-- JSON helper (minimal, for backend info serialization)
------------------------------------------------------------------------

jQuote : String -> String
jQuote s = "\"" ++ s ++ "\""

------------------------------------------------------------------------
-- MLX config
------------------------------------------------------------------------

public export
record MLXConfig where
  constructor MkMLXConfig
  mcDefaultModel : String
  mcMaxTokens    : Nat
  mcTemp         : Double

public export
defaultMLXConfig : MLXConfig
defaultMLXConfig = MkMLXConfig "mlx-community/Llama-3.2-3B-Instruct-4bit" 512 0.4

------------------------------------------------------------------------
-- Backend info (for observatory API)
------------------------------------------------------------------------

||| Return MLX config as key-value pairs with pre-formatted JSON values.
public export
mlxBackendInfo : MLXConfig -> List (String, String)
mlxBackendInfo cfg =
  [ ("backend", jQuote "mlx")
  , ("default_model", jQuote cfg.mcDefaultModel)
  , ("max_tokens", show cfg.mcMaxTokens)
  , ("temperature", show cfg.mcTemp)
  ]

------------------------------------------------------------------------
-- Known models
------------------------------------------------------------------------

public export
knownMLXModels : List String
knownMLXModels =
  [ "mlx-community/Llama-3.2-3B-Instruct-4bit"
  , "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
  , "mlx-community/gemma-2-9b-it-4bit"
  ]
