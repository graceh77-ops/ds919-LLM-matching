# ACIC 2016 LLM Field-Weight Protocol

## Purpose

Elicit a priori matching-priority scores for the 58 ACIC covariate fields, then
compare LLM-weighted generalized Mahalanobis matching with identity
generalized Mahalanobis, PSM, and PCA Mahalanobis. These scores are not
estimated causal effects or empirically learned feature importance.

## Elicitation

1. Use the standalone [weight prompt](weight_prompt.md) in a new chat with no
   prior project conversation. Do not supply ACIC replication data, treatment
   rates, simulation setting parameters, potential outcomes, true SATTs,
   matching results, or previous LLM weights.
2. Elicit one vector per model/session. Save the exact prompt, raw response,
   date, provider, model/version as displayed, interface or API, and any
   generation settings in a run record. Do not edit the returned values. A
   retry is a separate elicitation with its own record.
3. Validate that the response is JSON containing exactly `x_1` through `x_58`,
   with one integer score from 0 to 10 per field and at least one nonzero
   score. Save the validated object as `weights.json` in that elicitation's
   own results folder.
4. Keep every valid vector. Do not choose among vectors based on matching
   performance. Decide and record how many independent elicitation runs to
   compare before looking at evaluation results.

## Matching use

The ACIC runner accepts a saved vector with `--weights-json PATH`. Each score
is mapped to every encoded column from its source field, then the expanded
diagonal vector is normalized to mean 1. This means a categorical field with
more contrasts receives more total matrix weight under the primary mapping.
The runner uses the same vector for every replication in a run; it does not
call an LLM during matching. The current runner supports field-level mapping;
column-normalized allocation remains a planned sensitivity analysis.

Treat each independently elicited vector as a separate method specification.
Evaluate vectors on the same preselected ACIC replications and report the
distribution across both simulation replications and elicitation runs. Do not
select a vector after inspecting outcomes or benchmark errors.

## Current status

The prompt and field dictionary are prepared. No ACIC LLM weights have been
elicited. The runner can load a validated field-weight JSON; the initial pilot
therefore included only identity Mahalanobis, PSM, and PCA Mahalanobis.
