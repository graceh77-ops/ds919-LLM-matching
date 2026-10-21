# Analysis Protocol

## Research question

Among 2024 U.S. live births represented in the Natality file, what is the
effect of maternal smoking during pregnancy on birth weight?

## Target population

- Primary pilot population: singleton live births in the 2024 Natality file.
- Sensitivity population: all eligible live births, including multiple births.
- Verify the exact plurality code and file coverage using the 2024 User Guide.

## Treatment

- Exposure: maternal smoking during pregnancy.
- Use the CDC-provided pregnancy smoking classification (`CIG_REC`) for the
  primary analysis after verifying its value labels and unknown-value rules.
- Retain trimester-specific smoking variables to describe the exposure and
  check the classification.
- Do not treat unknown or unreported smoking status as nonsmoking.

## Outcome

- Birth weight in grams (`DBWT`).
- Follow the User Guide's rules for unknown or invalid values.
- Report the number of records excluded because birth weight is unavailable.

## Target causal effect

- Primary estimand: ATT among treated births that can be matched to comparable
  nonsmoking births.
- Interpret this as the effect for the matched smoking group, not automatically
  for every birth or every pregnant person.
- Report how many treated records were not matched.

## Covariates

- Start with the provisional primary candidate set in `covariate_screening.md`.
- Do not use variables that may occur after smoking exposure begins in the
  primary matching set unless the causal diagram and timing review support it.
- Report missingness for each selected covariate and the number of records
  removed by the missing-data rule.

## Identification assumptions and diagnostics

- No unmeasured confounding after adjustment for the selected covariates.
- Overlap: comparable treated and control records exist across covariate
  patterns.
- Consistency: treatment and outcome are defined clearly enough for the
  comparison.
- Check covariate balance and overlap after matching.
- Treat these assumptions as limitations; they cannot all be verified from
  balance statistics alone.

## Decisions still to confirm

- Confirm singleton-only primary population.
- Confirm CDC smoking classification and missing-value handling.
- Confirm the final primary covariate set.
- Confirm the matching algorithm and caliper after the data format is checked.