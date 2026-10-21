# Data Layout Notes

- Dataset: 2024 CDC Natality U.S. Birth Data
- Extracted filename: Nat2024PublicUS.c20250512.r20250708.txt
- TXT file size: 4.6G
- Number of records: 3,638,436
- Shortest record length: 1345
- Longest record length: 1345
- User Guide record length: 1330
- Notes: Record contents not edited. Raw files remain under `data/raw/2024/`.


## Raw file inspection

- File: `Nat2024PublicUS.c20250512.r20250708.txt`
- Checked with: `src/inspect_natality.py`
- Number of records: 3,638,436
- Record length(s): 1345
- Cross-check: Python results and Git Bash results match
- Interpretation: All records are of the same length