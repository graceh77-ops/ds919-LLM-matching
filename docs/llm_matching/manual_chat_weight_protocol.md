# Outcome-blind manual-chat weight protocol

## Purpose

Generate one reproducible set of manual-chat covariate-priority weights without
exposing the LLM to empirical outcome or matching results. This document
specifies the elicitation procedure; the prompt itself is kept separately in
[`manual_chat_weight_prompt.md`](manual_chat_weight_prompt.md).

## Isolated elicitation

1. Start a new LLM session with no prior conversation history, uploaded files,
   or project artifacts.
2. Paste the standalone prompt verbatim. Do not add pilot results, ATT
   estimates, reference-error metrics, balance results, comparator results,
   previous weights, or commentary about how any method performed.
3. Save the provider, model/version if shown, date/time, exact prompt, raw
   response, and any retries. If a format correction is necessary, repeat only
   the original prompt and a neutral request to return valid JSON in the
   specified format; record the retry.
4. Validate that the response is a JSON object with exactly the ten required
   field names, integer values from 0 through 10, and at least one positive
   value. Do not alter individual scores manually.
5. Save the validated scores separately, for example as
   `results/manual llm matching/manual_chat_weights_outcome_blind.json`, and
   save the elicitation record and raw response alongside it.
6. Freeze the new weights before running any matching evaluation. Do not revise
   them using pilot or test ATT, reference error, SMD, or comparator results.

If the isolated model does not return a valid response after the recorded
format-only retry, preserve the raw output and rerun the elicitation in a new
isolated session. Do not use matching results to resolve ambiguity.

## Existing manual weights

The original `results/manual llm matching/manual_chat_weights.json` is
preserved unchanged and is designated **exploratory**. The earlier elicitation
occurred in a conversation where pilot matching metrics were already present
in context, so it cannot be certified as outcome-blind. Keep its results
separate from results produced with the new isolated-session weights.

## Analysis separation

The new weights change only the LLM-assigned field priorities. Keep the
generalized Mahalanobis formula, cohort definition, covariate encoding,
reference-fitted preprocessing and covariance, eigenvalue floor, split
procedure, matching ratio, replacement rule, caliper setting, and evaluation
metrics fixed as documented in the analysis and LLM matching protocols.
Evaluate the new weights only after the scores and their provenance are saved.
