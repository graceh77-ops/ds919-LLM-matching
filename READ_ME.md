# Evaluating LLM-Assisted Matching

This project compares LLM-assisted covariate weighting with conventional
matching methods. The current application is maternal smoking during pregnancy
and birth weight in the 2024 CDC Natality Public Use File. The project evaluates
matching procedures; it does not establish a definitive causal effect.

The core question is whether covariate weights suggested by an LLM can improve
matching and treatment-effect estimation compared with standard approaches.
The analysis focuses on singleton births and uses pregnancy smoking as the
treatment and infant birth weight as the outcome.

## Project roadmap

1. **Prepare the Natality analysis cohort.** Apply the documented eligibility
   rules, assemble the selected covariates, and complete data-quality checks.
2. **Set consistent reference estimators and matching comparators.** Use
   reference-cohort AIPW-ATT as the primary comparison estimate, with IPW and
   outcome regression as separate reference sensitivities. Identity
   Mahalanobis and PSM are matching comparators, like the LLM-weighted methods.
3. **Obtain LLM covariate weights in stages.** Start with a manual chat
   interface, then use DeepSeek, and later use an advanced API/model. The LLM 
   provides weights; the analysis design and matching rules are set separately.
4. **Compare matching approaches.** Apply LLM weights and conventional
   comparators to the same cohort and preprocessing, then assess effect
   estimates alongside balance and overlap diagnostics.
5. **Evaluate against the reference estimate.** Use repeated,
   treatment-stratified 99% reference / 1% test splits. Report error relative
   to the reference-cohort AIPW-ATT estimate, not as error against the unknown
   true causal effect. Differences between the reference and test cohorts may
   contribute to this error.
6. **Consider extensions later.** Additional Natality years may increase the
   available sample after harmonization. ACIC 2016 remains a possible separate
   benchmark for future discussion.

## Start here

- [LLM matching protocol](docs/llm_matching/protocol_LLM_matching.md): staged
  manual and API workflow, reference comparison, methods, and evaluation.
- [Natality analysis protocol](docs/maternal_smoking_birthweight/protocal_maternal_smoking_dataset.md):
  study population, variables, matching distance, and analysis decisions.
- [Covariate review](docs/maternal_smoking_birthweight/covariate_review.md):
  candidate variables, rationale, and coding decisions.
- [Data reference](docs/maternal_smoking_birthweight/data_reference.md): source
  file and extraction details.

## Current status

The 2024 Natality extraction, initial full-data QC, and analysis-cohort
preparation are complete. The project has manual-chat and DeepSeek weight records. The matching workflow uses reference-cohort AIPW-ATT as its primary pseudo-reference estimate. The first implementation check passed on the existing 10,000-row pilot workflow; full-cohort AIPW results have not yet been generated. 

Raw and processed data are local project inputs and must not be committed to
Git. See `.gitignore` for the repository rules.
