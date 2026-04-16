||| Mock model backend for testing and demos.
module Eden.Models.Mock

import Data.String
import Eden.Models.Base

%default total

||| Generate a deterministic mock response from the prompt.
public export
mockGenerate : GenerateParams -> ModelResult
mockGenerate params =
  let response = "[mock] I received your prompt ("
              ++ show (length (words params.gpConvPrompt))
              ++ " words). Here is a thoughtful response that demonstrates "
              ++ "the pipeline is working correctly."
      toks = length (words response)
  in MkModelResult "mock" response toks response "" response
