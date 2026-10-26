"""Load and validate one ACIC 2016 simulation replication."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_DIR / "data" / "raw" / "full_data"
EXPECTED_ROWS = 4802
EXPECTED_COVARIATES = 58
REPLICATION_PATTERN = re.compile(r"^zymu_(\d+)\.csv$")
OUTCOME_COLUMNS = ("z", "y0", "y1", "mu0", "mu1")


@dataclass(frozen=True)
class ACICReplication:
    """One simulation replicate, with features separate from causal outcomes."""

    setting: int
    replication_file: str
    covariates: pd.DataFrame
    treatment: pd.Series
    observed_outcome: pd.Series
    y0: pd.Series
    y1: pd.Series
    mu0: pd.Series
    mu1: pd.Series
    realized_satt: float
    expected_satt: float


def list_replications(
    setting: int, data_dir: Path = DEFAULT_DATA_DIR
) -> list[str]:
    """Return replication filenames in numeric filename order."""
    _validate_setting(setting)
    setting_dir = Path(data_dir) / str(setting)
    if not setting_dir.is_dir():
        raise FileNotFoundError(f"ACIC setting folder not found: {setting_dir}")

    replications = [
        path.name
        for path in setting_dir.iterdir()
        if path.is_file() and REPLICATION_PATTERN.fullmatch(path.name)
    ]
    replications.sort(key=lambda name: int(REPLICATION_PATTERN.fullmatch(name).group(1)))
    if len(replications) != 100:
        raise ValueError(
            f"Expected 100 replications in setting {setting}; found {len(replications)}"
        )
    return replications


def load_replication(
    setting: int,
    replication_file: str,
    data_dir: Path = DEFAULT_DATA_DIR,
) -> ACICReplication:
    """Load one setting/replication and calculate both SATT references."""
    _validate_setting(setting)
    filename = Path(replication_file)
    if filename.is_absolute() or len(filename.parts) != 1:
        raise ValueError("replication_file must be a filename such as 'zymu_13.csv'")
    if not REPLICATION_PATTERN.fullmatch(filename.name):
        raise ValueError("replication_file must match 'zymu_<number>.csv'")

    data_dir = Path(data_dir)
    setting_dir = data_dir / str(setting)
    x_path = data_dir / "x.csv"
    outcomes_path = setting_dir / filename.name
    if not x_path.is_file():
        raise FileNotFoundError(f"Shared ACIC covariates not found: {x_path}")
    if not outcomes_path.is_file():
        raise FileNotFoundError(f"Replication file not found: {outcomes_path}")

    covariates = pd.read_csv(x_path)
    outcomes = pd.read_csv(outcomes_path)
    missing_columns = set(OUTCOME_COLUMNS).difference(outcomes.columns)
    if missing_columns:
        raise ValueError(
            f"{outcomes_path.name} is missing columns: {sorted(missing_columns)}"
        )
    if len(covariates) != EXPECTED_ROWS or len(outcomes) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} aligned rows; found {len(covariates)} covariates "
            f"and {len(outcomes)} outcome rows"
        )
    if covariates.shape[1] != EXPECTED_COVARIATES:
        raise ValueError(
            f"Expected {EXPECTED_COVARIATES} covariates; found {covariates.shape[1]}"
        )
    if covariates.isna().any().any():
        raise ValueError("Covariates contain missing values")

    numeric = outcomes.loc[:, list(OUTCOME_COLUMNS)].apply(
        pd.to_numeric, errors="coerce"
    )
    values = numeric.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Treatment or potential outcomes contain missing/non-finite values")

    treatment_values = numeric["z"].to_numpy()
    if not np.isin(treatment_values, [0, 1]).all():
        raise ValueError("Treatment column z must contain only 0 and 1")
    treatment = pd.Series(treatment_values.astype("int8"), name="z")
    treated = treatment_values == 1
    treated_n = int(treated.sum())
    if treated_n == 0:
        raise ValueError("Cannot calculate SATT: this replication has no treated units")

    y0 = numeric["y0"].rename("y0")
    y1 = numeric["y1"].rename("y1")
    mu0 = numeric["mu0"].rename("mu0")
    mu1 = numeric["mu1"].rename("mu1")
    observed = pd.Series(
        np.where(treated, y1.to_numpy(), y0.to_numpy()), name="y"
    )

    return ACICReplication(
        setting=setting,
        replication_file=filename.name,
        covariates=covariates,
        treatment=treatment,
        observed_outcome=observed,
        y0=y0,
        y1=y1,
        mu0=mu0,
        mu1=mu1,
        realized_satt=float((y1.to_numpy()[treated] - y0.to_numpy()[treated]).mean()),
        expected_satt=float((mu1.to_numpy()[treated] - mu0.to_numpy()[treated]).mean()),
    )


def _validate_setting(setting: int) -> None:
    if (
        isinstance(setting, bool)
        or not isinstance(setting, (int, np.integer))
        or not 1 <= setting <= 77
    ):
        raise ValueError("setting must be an integer from 1 to 77")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setting", type=int, required=True, help="ACIC setting, 1-77")
    parser.add_argument(
        "--replication", required=True, help="Filename, for example zymu_13.csv"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Extracted ACIC folder (default: {DEFAULT_DATA_DIR})",
    )
    args = parser.parse_args()

    data = load_replication(args.setting, args.replication, args.data_dir)
    treated_n = int(data.treatment.sum())
    print(f"Setting: {data.setting}")
    print(f"Replication: {data.replication_file}")
    print(f"Rows: {len(data.treatment)}; covariates: {data.covariates.shape[1]}")
    print(f"Treated: {treated_n}; controls: {len(data.treatment) - treated_n}")
    print(f"Realized SATT: {data.realized_satt:.8f}")
    print(f"Expected SATT: {data.expected_satt:.8f}")


if __name__ == "__main__":
    main()
