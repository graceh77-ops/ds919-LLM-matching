# Manual chat-interface weight record

## Elicitation record

- Date: 2026-10-22
- Stage: manual chat-interface elicitation; no API was used.
- Interface/model: ChatGPT chat interface, GPT-6 family. Exact serving build and sampling settings were not exposed in this session.
- Retries: none recorded.
- Manual edits to returned scores: none.
- Outcome values or pilot matching metrics provided during elicitation: none.

## Prompt specification

The weights were elicited in this conversation after clarifying that the LLM, rather than the researcher, should propose relative priorities. The following is a transparent reconstruction of the task specification, not a verbatim saved prompt from an earlier message:

> Assign relative matching-priority scores from 0 to 10 for each of these ten prespecified pre-treatment fields in a 2024 Natality study of maternal smoking during pregnancy and infant birth weight: MAGER (maternal age), MRACEHISP (race/Hispanic origin as social context), MEDUC (maternal education), CIG0_R (pre-pregnancy smoking), PRIORLIVE and PRIORDEAD (prior pregnancy history), BMI_R (pre-pregnancy BMI), RF_PDIAB and RF_PHYPE (pre-pregnancy conditions), and SEX (prognostic for birth weight, but not an established confounder). Base scores on plausible relevance to treatment assignment and/or outcome prognosis, without using outcome values. Return one nonnegative score per field and a brief rationale. Scores are relative and need not sum to 1.

## Returned field scores

The returned values are recorded in [`manual_chat_weights.json`](manual_chat_weights.json):

| Field | Score |
|---|---:|
| MAGER | 8 |
| MRACEHISP | 7 |
| MEDUC | 8 |
| CIG0_R | 10 |
| PRIORLIVE | 6 |
| PRIORDEAD | 4 |
| BMI_R | 8 |
| RF_PDIAB | 6 |
| RF_PHYPE | 6 |
| SEX | 4 |

These are relative scores, not probabilities. The matching code rescales the ten field scores to mean 1 before constructing the diagonal matrix. In the primary mapping, a field score is repeated over every encoded column from that field. A column-normalized allocation is also computed as a prespecified sensitivity method to assess the effect of fields represented by multiple columns.

## Pilot run

The weighted pilot is run on the same 10,000-row development subset, split fraction, and seed as the identity pilot. It is a one-split development check, not a final comparison. The outputs are `manual_chat_pilot_matching.csv` and `manual_chat_pilot_summary.csv`.
