# Outcome-blind manual-chat weight protocol

## Purpose

This procedure is reusable, but the linked prompt and its ten covariates are
specific to the CDC Natality application. A different dataset needs a new
outcome-blind prompt and matching weight schema.

Generate one reproducible set of manual-chat covariate-priority weights without
exposing the LLM to empirical outcome or matching results. This document
specifies the elicitation procedure; the prompt itself is kept separately in
[`llm_prompt_covariate_weights.md`](llm_prompt_covariate_weights.md).

## Isolated elicitation

1. Start a new LLM session with no prior conversation history, uploaded files,
   or project details.
2. Paste the standalone prompt verbatim. Do not add any other information.
3. Save the provider, model/version if shown, date/time, exact prompt, raw
   response, and any retries. If a format correction is necessary, repeat only
   the original prompt and a neutral request to return valid JSON in the
   specified format; record the retry.
4. Validate that the response is a JSON object with exactly the ten required
   field names, integer values from 0 through 10, and at least one positive
   value. Do not alter individual scores manually.
5. From the repository root, run `Set-Location "cdc natality"`. Save the
   validated scores in
   `results/matching results/manual_chat_weights_outcome.json`. Save the
   elicitation record in
   `results/matching results/manual_chat_weight_record_outcome.md`.
6. Freeze the new weights before running any matching evaluation. Do not revise
   them using pilot or test ATT, reference error, SMD, or comparator results.

If the isolated model does not return a valid response after the recorded
format-only retry, preserve the raw output and rerun the elicitation in a new
isolated session. Do not use matching results to resolve ambiguity.

## Analysis separation

The new weights change only the LLM-assigned field priorities. Keep the
generalized Mahalanobis formula, cohort definition, covariate encoding,
test-sample-fitted matching preprocessing and covariance, eigenvalue floor,
split procedure, matching ratio, replacement rule, caliper setting, and
evaluation metrics fixed as documented in the analysis and LLM matching
protocols. 
Evaluate the new weights only after the scores and their provenance are saved.
