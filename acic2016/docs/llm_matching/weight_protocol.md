# ACIC 2016 LLM Field-Weight Protocol

## Purpose

Elicit relative matching-priority scores for the 58 ACIC covariate fields and
compare the resulting generalized Mahalanobis method with identity generalized
Mahalanobis, propensity score matching (PSM), and PCA Mahalanobis. The scores
are elicited judgments; they are not treatment-effect estimates or empirical
feature-importance estimates.

## Elicitation procedure

- Use the standalone [weight prompt](weight_prompt.md). The DeepSeek script
  sends one user message containing only the prompt; it does not include
  replication data, treatment rates, simulation settings, potential outcomes,
  SATTs, matching results, prior weights, or earlier chat history.
- Each API request is a distinct elicitation. Save its exact prompt, raw
  response, validated weights, provider/model, timestamp, prompt hash, and
  generation settings. Do not edit scores. A retry or prompt revision gets a
  separate run folder.
- Accept only JSON with exactly `x_1` through `x_58`, integer scores from 0 to
  10, and at least one positive score.
- Keep elicitation vectors separate. Do not average them or select among them
  based on matching performance. For a comparison across vectors, prespecify
  which eligible vectors and replications will be evaluated before examining
  their matching results.

The current prompt describes the hypothetical birthweight-to-IQ study and the
58 fields using provisional semantic labels. It does not explicitly define
simulated `z` and `y`, what `z = 1` means, most category encodings, category
meanings, or exact measurement units. Interpret its scores as priorities for
the fields as described in that prompt, not as importance scores for verified
clinical confounders. The mapping limitations are documented in the
[covariate mapping evidence audit](../covariate_mapping_evidence.md).

## API implementation

Run from the repository root after setting `DEEPSEEK_API_KEY` in the current
PowerShell session:

```powershell
python .\acic2016\src\get_deepseek_weights.py
```

The script uses the DeepSeek chat-completions endpoint with one non-streaming
request, JSON-object response format, temperature 0, thinking disabled, and a
2,048-token limit. It does not retry automatically or overwrite an existing
timestamped run. Each run is saved under
`acic2016/results/llm_weights/deepseek_api/` with the exact prompt, raw API
response, raw model text, validated `weights.json`, and `record.json`.

## Matching use

Pass the selected saved vector to the ACIC runner with `--weights-json PATH`.
The runner maps each field score to all encoded columns derived from that
field, then normalizes the expanded diagonal vector to mean 1. Consequently,
categorical fields with more encoded contrasts receive more total matrix
weight under this primary allocation. The runner uses one fixed vector across
replications in a run and does not call the API during matching.

The identity-matrix, PSM, PCA, and LLM-weighted methods use the same 79-column
covariate representation, matching rules, and within-replication cohort.
LLM weights, treatment, and covariates determine matching. The current loader
does read potential outcomes and calculate SATT references before matching;
however, matching-coordinate construction and match selection use only
covariates and treatment. Observed outcomes are used to calculate matched ATT
after matches are selected. Keep outcome values out of weight elicitation,
preprocessing, and matching.

## Elicitation records and current selection

Three successful DeepSeek runs are currently retained:

| Run folder | Prompt SHA-256 | Status for comparison |
|---|---|---|
| `first_trial_20261026T231410Z` | `a811ea2b98202a71527ae2703c7d4e793ec010060e1e8f74b89570e0ca308cf9` | Earlier prompt version |
| `second_trial_20261026T231852Z` | `a811ea2b98202a71527ae2703c7d4e793ec010060e1e8f74b89570e0ca308cf9` | Separate API call with the same prompt content as the first run |
| `20261026T234904Z` | `c38f5ea080fdd3c37661b53790f70360b83f7901f1744ebcc564b9edb4825a3d` | Latest prompt version; used in the first LLM-weighted pilot |

The pilot used
`results/llm_weights/deepseek_api/20261026T234904Z/weights.json`. Its exact
prompt and API metadata are preserved alongside it. The first two runs are
kept as separate elicitation records and are not silently treated as the same
prompt version as the latest run.

## Status

The DeepSeek API elicitation and one LLM-weighted matching pilot are complete.
Both the initial pilot without LLM weights and the LLM-weighted pilot used
setting 1, replication `zymu_13.csv`. The LLM-weighted pilot outputs are in
[`results/run1_20261027T000241Z/`](../../results/run1_20261027T000241Z/);
the earlier no-LLM pilot is in `results/pilot_run/`. The full 77-setting,
100-replication evaluation has not been run.
