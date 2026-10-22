# Primary Covariate Missingness Review

## Scope

- Input: `data\processed\2024\extracted_natality.csv`
- Singleton analysis cohort rows before covariate handling: 3,506,582
- Proposed primary covariates assessed: `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, `SEX`
- This report profiles unknown codes, blanks, and unexpected values. It does not apply a missing-data rule or alter the cohort.

## Primary covariate value status

Unknown/not-stated codes and blank values are shown separately. Reporting and imputation flags are descriptive audits; their values are not automatically treated as missing covariates.

| Field | Observed | Unknown code | Blank | Unexpected code | Coding note |
|---|---:|---:|---:|---:|---|
| `MAGER` | 3,506,582 | 0 | 0 | 0 | Valid age codes 12-50; 12 represents 10-12 years |
| `MRACEHISP` | 3,474,923 | 31,659 | 0 | 0 | Code 8 is unknown or not stated |
| `MEDUC` | 3,445,193 | 61,389 | 0 | 0 | Code 9 is unknown or not stated |
| `CIG0_R` | 3,505,992 | 590 | 0 | 0 | Code 6 is unknown or not stated |
| `PRIORLIVE` | 3,500,527 | 6,055 | 0 | 0 | Code 99 is unknown or not stated |
| `PRIORDEAD` | 3,496,518 | 10,064 | 0 | 0 | Code 99 is unknown or not stated |
| `BMI_R` | 3,426,845 | 79,737 | 0 | 0 | Code 9 is unknown or not stated |
| `RF_PDIAB` | 3,502,216 | 4,366 | 0 | 0 | U or blank is unknown/not stated |
| `RF_PHYPE` | 3,502,216 | 4,366 | 0 | 0 | U or blank is unknown/not stated |
| `SEX` | 3,506,582 | 0 | 0 | 0 | Blank or other value is unknown/unexpected |

## Observed value distributions

### `MAGER`

- `12`: 51
- `13`: 317
- `14`: 1,336
- `15`: 4,070
- `16`: 9,890
- `17`: 19,861
- `18`: 36,651
- `19`: 63,846
- `20`: 84,721
- `21`: 100,632
- `22`: 120,341
- `23`: 136,654
- `24`: 152,426
- `25`: 166,019
- `26`: 179,247
- `27`: 192,125
- `28`: 205,514
- `29`: 216,034
- `30`: 221,376
- `31`: 224,472
- `32`: 221,269
- `33`: 209,588
- `34`: 195,488
- `35`: 172,019
- `36`: 145,049
- `37`: 116,485
- `38`: 93,202
- `39`: 71,606
- `40`: 52,629
- `41`: 36,604
- `42`: 24,246
- `43`: 14,436
- `44`: 8,291
- `45`: 4,254
- `46`: 2,258
- `47`: 1,280
- `48`: 708
- `49`: 550
- `50`: 1,037

### `MRACEHISP`

- `1`: 1,718,585
- `2`: 450,454
- `3`: 23,086
- `4`: 221,078
- `5`: 10,027
- `6`: 88,058
- `7`: 963,635
- `8`: 31,659

### `MEDUC`

- `1`: 117,987
- `2`: 274,356
- `3`: 932,764
- `4`: 573,256
- `5`: 280,391
- `6`: 780,806
- `7`: 372,778
- `8`: 112,855
- `9`: 61,389

### `CIG0_R`

- `0`: 3,401,798
- `1`: 32,345
- `2`: 33,061
- `3`: 32,393
- `4`: 4,946
- `5`: 1,449
- `6`: 590

### `PRIORLIVE`

- `00`: 1,425,280
- `01`: 1,089,848
- `02`: 559,507
- `03`: 245,789
- `04`: 97,935
- `05`: 42,064
- `06`: 19,438
- `07`: 9,723
- `08`: 5,126
- `09`: 2,695
- `10`: 1,565
- `11`: 837
- `12`: 428
- `13`: 160
- `14`: 80
- `15`: 28
- `16`: 18
- `17`: 2
- `18`: 4
- `99`: 6,055

### `PRIORDEAD`

- `00`: 3,457,734
- `01`: 32,621
- `02`: 3,924
- `03`: 963
- `04`: 414
- `05`: 212
- `06`: 112
- `07`: 97
- `08`: 95
- `09`: 154
- `10`: 107
- `11`: 46
- `12`: 37
- `17`: 1
- `18`: 1
- `99`: 10,064

### `BMI_R`

- `1`: 90,172
- `2`: 1,282,774
- `3`: 960,447
- `4`: 587,718
- `5`: 293,523
- `6`: 212,211
- `9`: 79,737

### `RF_PDIAB`

- `N`: 3,456,521
- `U`: 4,366
- `Y`: 45,695

### `RF_PHYPE`

- `N`: 3,386,780
- `U`: 4,366
- `Y`: 115,436

### `SEX`

- `F`: 1,714,100
- `M`: 1,792,482

## Reporting and imputation flag distributions

Flags are reported as coded in the cohort. For reporting flags, `0` means non-reporting and `1` means reporting where defined by the User Guide. Age/race/sex imputation flags describe processing, not missing covariate values.

### `MAGE_IMPFLG`

- `[blank]`: 3,506,241
- `1`: 341

### `MAGE_REPFLG`

- `[blank]`: 3,506,504
- `1`: 78

### `MRACEIMP`

- `[blank]`: 3,214,116
- `1`: 292,466

### `F_MHISP`

- `0`: 8,874
- `1`: 3,497,708

### `F_MEDUC`

- `0`: 8,874
- `1`: 3,497,708

### `F_M_HT`

- `0`: 8,874
- `1`: 3,497,708

### `F_PWGT`

- `0`: 8,874
- `1`: 3,497,708

### `F_CIGS_0`

- `0`: 8,874
- `1`: 3,497,708

### `F_RF_PDIAB`

- `0`: 8,874
- `1`: 3,497,708

### `F_RF_PHYPER`

- `0`: 8,874
- `1`: 3,497,708

### `IMP_SEX`

- `[blank]`: 3,506,516
- `1`: 66

## Covariate-by-flag cross-checks

These tables check whether a selected covariate value appears alongside a non-reporting or imputation flag. The flag-aware scenario requires the selected item to be reported where a reporting flag applies, including Hispanic origin, education, pre-pregnancy smoking, height and weight used for BMI, diabetes, and hypertension. Imputation flags are reviewed but do not by themselves make a value missing.

### `MAGER` by `MAGE_IMPFLG`

| Covariate status | `[blank]` | `1` |
|---|---:|---:|
| observed | 3,506,241 | 341 |
| unknown code | 0 | 0 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `MAGER` by `MAGE_REPFLG`

| Covariate status | `[blank]` | `1` |
|---|---:|---:|
| observed | 3,506,504 | 78 |
| unknown code | 0 | 0 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `MRACEHISP` by `MRACEIMP`

| Covariate status | `[blank]` | `1` |
|---|---:|---:|
| observed | 3,203,958 | 270,965 |
| unknown code | 10,158 | 21,501 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `MRACEHISP` by `F_MHISP`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,756 | 3,466,167 |
| unknown code | 118 | 31,541 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `MEDUC` by `F_MEDUC`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,574 | 3,436,619 |
| unknown code | 300 | 61,089 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `CIG0_R` by `F_CIGS_0`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,874 | 3,497,118 |
| unknown code | 0 | 590 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `BMI_R` by `F_M_HT`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,620 | 3,418,225 |
| unknown code | 254 | 79,483 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `BMI_R` by `F_PWGT`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,620 | 3,418,225 |
| unknown code | 254 | 79,483 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `RF_PDIAB` by `F_RF_PDIAB`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,853 | 3,493,363 |
| unknown code | 21 | 4,345 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `RF_PHYPE` by `F_RF_PHYPER`

| Covariate status | `0` | `1` |
|---|---:|---:|
| observed | 8,853 | 3,493,363 |
| unknown code | 21 | 4,345 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

### `SEX` by `IMP_SEX`

| Covariate status | `[blank]` | `1` |
|---|---:|---:|
| observed | 3,506,516 | 66 |
| unknown code | 0 | 0 |
| blank | 0 | 0 |
| unexpected code | 0 | 0 |

## Gestational-age sensitivity-variable profile

Gestational age is not part of the proposed primary set. `COMBGEST` is detailed weeks; `GESTREC10` is the coarser 10-category recode. Their flags describe imputation/source and should be reviewed before the sensitivity analysis.

### `COMBGEST`

- `17`: 77
- `18`: 139
- `19`: 352
- `20`: 752
- `21`: 952
- `22`: 1,346
- `23`: 1,987
- `24`: 2,644
- `25`: 2,983
- `26`: 3,324
- `27`: 4,057
- `28`: 5,570
- `29`: 6,817
- `30`: 9,232
- `31`: 12,118
- `32`: 17,738
- `33`: 27,081
- `34`: 50,494
- `35`: 76,178
- `36`: 146,617
- `37`: 385,099
- `38`: 586,186
- `39`: 1,090,456
- `40`: 628,698
- `41`: 252,001
- `42`: 89,227
- `43`: 47,703
- `44`: 26,086
- `45`: 13,730
- `46`: 8,406
- `47`: 6,969
- `99`: 1,563

### `GESTREC10`

- `01`: 568
- `02`: 18,045
- `03`: 33,737
- `04`: 44,819
- `05`: 273,289
- `06`: 971,285
- `07`: 1,090,456
- `08`: 628,698
- `09`: 252,001
- `10`: 192,121
- `99`: 1,563

### `COMPGST_IMP`

- `[blank]`: 3,449,669
- `1`: 56,913

### `OBGEST_FLG`

- `[blank]`: 3,336,106
- `1`: 170,476

## Complete-case scenarios

These are descriptive scenarios: retain a record only when every proposed primary covariate has an observed, recognized value. The flag-aware scenario also requires a reporting flag for fields where CDC supplies one. CDC-imputed ages, races, and sex remain observed values in these counts; their imputation flags are reported separately.

- Complete cases: 3,344,587 (95.38%)
- Records excluded by this strict rule: 161,995 (4.62%)
- Complete cases when required reporting flags must also equal `1`: 3,336,235 (95.14%)
- Records excluded by the flag-aware scenario: 170,347 (4.86%)

| Treatment | Code-based complete | Code-based excluded | Flag-aware complete | Flag-aware excluded |
|---|---:|---:|---:|---:|
| `Y` | 79,399 | 4,027 | 79,378 | 4,048 |
| `N` | 3,265,188 | 157,968 | 3,256,857 | 166,299 |

## Interpretation and next decision

The flag-aware complete-case rule was selected for the primary analysis cohort and applied in `prepare_analysis_data.py`. The code-based complete-case count is shown as an eligibility comparison only. Reporting flags are eligibility checks, not matching covariates; CDC-imputed age, race, and sex values remain eligible and their imputation flags are retained for audit.
