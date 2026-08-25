"""Score research and analysis module for investigating score-return relationships.

This module provides visualization and analysis tools to explore how individual
scores relate to future returns across different time horizons.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

from stock_quant.consensus.perspectives import PERSPECTIVES_BY_KEY, SCORE_KEYS


def _forward_return_col(horizon: int) -> str:
    """Helper: get forward return column name for a given horizon."""
    return f"future_return_{horizon}d"


def create_score_timeseries_chart(
    df: pd.DataFrame,
    score_key: str,
    include_price: bool = True,
) -> go.Figure:
    """Create interactive chart showing score and price over time.

    Args:
        df: DataFrame with date, close, and score columns
        score_key: The score to plot
        include_price: Whether to show price on secondary y-axis

    Returns:
        Plotly figure with price and score aligned on time axis
    """
    if score_key not in df.columns:
        return go.Figure().add_annotation(text=f"Score {score_key} not found")

    df_sorted = df.sort_values("date").copy()

    if include_price and "close" in df.columns:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            row_heights=[0.7, 0.3],
        )

        fig.add_trace(
            go.Scatter(
                x=df_sorted["date"],
                y=df_sorted["close"],
                name="Price",
                mode="lines",
                line=dict(color="#3b82f6", width=2),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df_sorted["date"],
                y=df_sorted[score_key],
                name=score_key,
                mode="lines",
                line=dict(color="#8b5cf6", width=2),
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>" + f"{score_key}: %{{y:.2f}}<extra></extra>",
            ),
            row=2,
            col=1,
        )

        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text=score_key, row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df_sorted["date"],
                y=df_sorted[score_key],
                name=score_key,
                mode="lines+markers",
                line=dict(color="#8b5cf6", width=2),
                hovertemplate="<b>%{x|%Y-%m-%d}</b><br>" + f"{score_key}: %{{y:.2f}}<extra></extra>",
            )
        )
        fig.update_yaxes(title_text=score_key)
        fig.update_xaxes(title_text="Date")

    fig.update_layout(
        height=500,
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50),
        template="plotly_white",
    )

    return fig


def create_score_scatter(
    df: pd.DataFrame,
    score_key: str,
    horizon: int = 20,
    min_obs: int = 30,
) -> tuple[go.Figure, dict]:
    """Create scatter plot of score vs future return with regression line.

    Args:
        df: DataFrame with score and future_return_*d columns
        score_key: Score to plot on x-axis
        horizon: Forward return horizon (5, 20, or 60)
        min_obs: Minimum observations for correlation

    Returns:
        Tuple of (figure, statistics dict with r and p-value)
    """
    return_col = _forward_return_col(horizon)

    if score_key not in df.columns or return_col not in df.columns:
        fig = go.Figure().add_annotation(text="Data not available")
        return fig, {"correlation": np.nan, "p_value": np.nan, "n_obs": 0}

    mask = df[score_key].notna() & df[return_col].notna()
    x = df.loc[mask, score_key].values
    y = df.loc[mask, return_col].values

    if len(x) < min_obs:
        fig = go.Figure().add_annotation(text=f"Insufficient data (n={len(x)})")
        return fig, {"correlation": np.nan, "p_value": np.nan, "n_obs": len(x)}

    # Calculate correlation
    corr, p_val = stats.spearmanr(x, y)

    # Regression line
    z = np.polyfit(x, y, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x.min(), x.max(), 100)
    y_line = p(x_line)

    # Create figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            name="Observations",
            marker=dict(
                size=6,
                color="#ef4444",
                opacity=0.6,
                line=dict(width=0),
            ),
            hovertemplate=f"<b>{score_key}</b>: %{{x:.2f}}<br>" + f"Return({horizon}d): %{{y:.4f}}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="Regression",
            line=dict(color="#3b82f6", width=2, dash="dash"),
            hovertemplate="Regression<br>x: %{x:.2f}<br>y: %{y:.4f}<extra></extra>",
        )
    )

    # Add zero line for return
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

    title = f"{score_key} vs Return({horizon}d) | ρ={corr:.3f} (p={p_val:.4f}, n={len(x)})"
    fig.update_layout(
        title=title,
        xaxis_title=score_key,
        yaxis_title=f"Future Return ({horizon}d)",
        height=400,
        template="plotly_white",
        hovermode="closest",
    )

    return fig, {
        "correlation": float(corr),
        "p_value": float(p_val),
        "n_obs": len(x),
        "slope": float(z[0]),
        "intercept": float(z[1]),
    }


def create_horizon_heatmap(
    df: pd.DataFrame,
    score_keys: list[str] | None = None,
    horizons: tuple[int, ...] = (5, 10, 20, 60),
) -> go.Figure:
    """Create heatmap of score-return correlations across horizons.

    Args:
        df: DataFrame with score and future_return_*d columns
        score_keys: List of scores to include; if None, use all available
        horizons: Tuple of return horizons to analyze

    Returns:
        Plotly heatmap figure
    """
    if score_keys is None:
        score_keys = [k for k in SCORE_KEYS if k in df.columns]

    score_keys = [k for k in score_keys if k in df.columns]
    if not score_keys:
        fig = go.Figure().add_annotation(text="No scores available")
        return fig

    correlations = []
    for score_key in score_keys:
        row = []
        for horizon in horizons:
            return_col = _forward_return_col(horizon)
            if return_col not in df.columns:
                row.append(np.nan)
                continue

            mask = df[score_key].notna() & df[return_col].notna()
            if mask.sum() < 30:
                row.append(np.nan)
                continue

            corr, _ = stats.spearmanr(df.loc[mask, score_key], df.loc[mask, return_col])
            row.append(float(corr))

        correlations.append(row)

    correlations = np.array(correlations)

    horizon_labels = [f"{h}d" for h in horizons]

    fig = go.Figure(
        data=go.Heatmap(
            z=correlations,
            x=horizon_labels,
            y=score_keys,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.round(correlations, 3),
            texttemplate="%{text:.3f}",
            textfont={"size": 10},
            colorbar=dict(title="Correlation"),
            hovertemplate="<b>%{y}</b> → %{x}<br>ρ = %{z:.3f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Score-Return Correlation Across Horizons",
        xaxis_title="Forward Return Horizon",
        yaxis_title="Score",
        height=400 + len(score_keys) * 20,
        template="plotly_white",
    )

    return fig


def score_research_summary(
    df: pd.DataFrame,
    score_keys: list[str] | None = None,
    horizons: tuple[int, ...] = (5, 20, 60),
) -> pd.DataFrame:
    """Create summary statistics table for score-return relationships.

    Args:
        df: DataFrame with score and future_return_*d columns
        score_keys: List of scores to analyze
        horizons: Tuple of return horizons

    Returns:
        DataFrame with summary statistics
    """
    if score_keys is None:
        score_keys = [k for k in SCORE_KEYS if k in df.columns]

    score_keys = [k for k in score_keys if k in df.columns]

    rows = []
    for score_key in score_keys:
        perspective = PERSPECTIVES_BY_KEY.get(score_key)
        family = perspective.family if perspective else "Unknown"

        for horizon in horizons:
            return_col = _forward_return_col(horizon)
            if return_col not in df.columns:
                continue

            mask = df[score_key].notna() & df[return_col].notna()
            n_obs = int(mask.sum())

            if n_obs < 30:
                corr = p_val = np.nan
            else:
                corr, p_val = stats.spearmanr(df.loc[mask, score_key], df.loc[mask, return_col])
                corr = float(corr)
                p_val = float(p_val)

            rows.append({
                "Score": score_key,
                "Family": family,
                "Horizon": f"{horizon}d",
                "Observations": n_obs,
                "Correlation": corr,
                "P-Value": p_val,
                "Significant": "Yes" if (p_val < 0.05 and not pd.isna(p_val)) else "No",
            })

    return pd.DataFrame(rows)
