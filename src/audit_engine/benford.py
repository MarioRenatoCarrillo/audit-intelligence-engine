from __future__ import annotations
import numpy as np
import pandas as pd


EXPECTED = {digit: np.log10(1 + 1 / digit) for digit in range(1, 10)}


def analyze(values: pd.Series) -> tuple[pd.DataFrame, dict]:
    eligible = values[(values > 0) & values.notna()].astype(float)
    first = eligible.map(lambda x: int(str(f"{x:.12g}").replace(".", "").lstrip("0")[0]))
    observed = first.value_counts(normalize=True).reindex(range(1, 10), fill_value=0.0)
    rows = pd.DataFrame({"digit": range(1, 10), "observed": observed.values, "expected": [EXPECTED[d] for d in range(1, 10)]})
    rows["absolute_deviation"] = (rows.observed - rows.expected).abs()
    mad = float(rows.absolute_deviation.mean())
    chi_square = float((((rows.observed * len(eligible) - rows.expected * len(eligible)) ** 2) / (rows.expected * len(eligible))).sum())
    summary = {"sample_size": int(len(eligible)), "mad": mad, "chi_square": chi_square, "eligible": len(eligible) >= 500}
    return rows, summary


def digit_rarity(values: pd.Series) -> pd.Series:
    def score(value: float) -> float:
        if not value or value <= 0:
            return 0.0
        digit = int(str(f"{value:.12g}").replace(".", "").lstrip("0")[0])
        return float(1 - EXPECTED[digit])
    return values.map(score)

