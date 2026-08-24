from __future__ import annotations

import pandas as pd


def score_columns(df: pd.DataFrame) -> list[str]:
    prefixes = (
        "mc_score", "tsm_score", "vrh_score", "exp_score", "mr_score",
        "man_score", "vsf_score", "tail_score", "vol_score",
    )
    return [c for c in df.columns if c in prefixes]


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = score_columns(df)
    if not cols:
        raise ValueError("No model score columns found")
    return df[cols].corr(min_periods=20)


def highly_correlated_pairs(
    corr: pd.DataFrame, threshold: float = 0.70
) -> pd.DataFrame:
    columns = ["model_a", "model_b", "correlation"]
    rows: list[dict[str, float | str]] = []
    score_names = list(corr.columns)

    for i, left in enumerate(score_names):
        for right in score_names[i + 1:]:
            value = corr.loc[left, right]
            if pd.notna(value) and abs(float(value)) >= threshold:
                rows.append(
                    {
                        "model_a": left,
                        "model_b": right,
                        "correlation": float(value),
                    }
                )

    pairs = pd.DataFrame(rows, columns=columns)
    if pairs.empty:
        return pairs

    return pairs.sort_values(
        "correlation",
        key=lambda series: series.abs(),
        ascending=False,
    ).reset_index(drop=True)


def incremental_ranking(corr: pd.DataFrame) -> pd.DataFrame:
    """Simple redundancy ranking: average absolute correlation with other model scores."""
    avg_abs = corr.abs().replace(1.0, pd.NA).mean(axis=1, skipna=True)
    return avg_abs.sort_values(ascending=False).rename("avg_abs_correlation").to_frame()
