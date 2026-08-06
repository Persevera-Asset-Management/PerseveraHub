"""Shared performance tearsheet for Streamlit views.

Renders a consistent equity / stats / drawdown / rolling / monthly block
so Portfolio Backtester, Factor Investing, RVQM and similar pages stay aligned.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
import streamlit as st
import streamlit_highcharts as hct

from persevera_tools.quant_research.metrics import (
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_drawdown,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
)

from utils.chart_helpers import create_chart
from utils.table import get_monthly_returns_table, style_table

PERCENT_STAT_COLS = [
    "Retorno Total",
    "Retorno Anualizado",
    "Volatilidade Anual",
    "Máx. Drawdown",
    "Melhor Dia",
    "Pior Dia",
    "Melhor Mês",
    "Pior Mês",
]

ROLLING_WINDOW_OPTIONS: dict[str, int] = {
    "21d (1m)": 21,
    "63d (3m)": 63,
    "126d (6m)": 126,
    "252d (12m)": 252,
}
DEFAULT_ROLLING_WINDOW = 252


def _as_frame(data: pd.DataFrame | pd.Series, default_name: str = "series") -> pd.DataFrame:
    if isinstance(data, pd.Series):
        name = data.name if data.name is not None else default_name
        return data.to_frame(name=name)
    return data.copy()


def _levels_from_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Wealth index (base 1) from simple returns, preserving leading NaNs."""
    levels = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)
    for col in returns.columns:
        series = returns[col]
        valid = series.first_valid_index()
        if valid is None:
            levels[col] = np.nan
            continue
        tail = series.loc[valid:]
        wealth = (1 + tail.fillna(0.0)).cumprod()
        levels.loc[wealth.index, col] = wealth
    return levels


def _returns_from_levels(levels: pd.DataFrame) -> pd.DataFrame:
    return levels.pct_change(fill_method=None)


def resolve_levels_and_returns(
    levels: pd.DataFrame | pd.Series | None = None,
    returns: pd.DataFrame | pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Accept exactly one of levels or returns; derive the other.

    Raises
    ------
    ValueError
        If both are missing, both are provided, or the provided frame is empty.
    """
    has_levels = levels is not None
    has_returns = returns is not None
    if has_levels == has_returns:
        raise ValueError("Provide exactly one of `levels` or `returns`.")

    if has_levels:
        levels_df = _as_frame(levels)
        if levels_df.empty:
            raise ValueError("`levels` is empty.")
        return levels_df, _returns_from_levels(levels_df)

    returns_df = _as_frame(returns)
    if returns_df.empty:
        raise ValueError("`returns` is empty.")
    return _levels_from_returns(returns_df), returns_df


def compute_drawdown(levels: pd.DataFrame | pd.Series) -> pd.DataFrame:
    """Drawdown (%) from price / NAV / index levels."""
    df = _as_frame(levels)
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            out[col] = np.nan
            continue
        out[col] = calculate_drawdown(series) * 100
    return out


def compute_performance_stats(
    levels: pd.Series,
    *,
    label: str,
    risk_free_rate: float = 0.0,
    returns: pd.Series | None = None,
    include_extremes: bool = True,
    include_n_obs: bool = False,
) -> dict:
    """Canonical performance metrics for a single series (levels = price/NAV/index)."""
    clean = levels.dropna()
    if clean.empty:
        row = {
            "Portfólio": label,
            "Retorno Total": np.nan,
            "Retorno Anualizado": np.nan,
            "Volatilidade Anual": np.nan,
            "Sharpe Ratio": np.nan,
            "Máx. Drawdown": np.nan,
        }
        if include_extremes:
            row.update(
                {
                    "Melhor Dia": np.nan,
                    "Pior Dia": np.nan,
                    "Melhor Mês": np.nan,
                    "Pior Mês": np.nan,
                }
            )
        if include_n_obs:
            row["Observações"] = 0
        return row

    rets = (
        returns.reindex(clean.index).dropna()
        if returns is not None
        else clean.pct_change(fill_method=None).dropna()
    )

    row = {
        "Portfólio": label,
        "Retorno Total": (clean.iloc[-1] / clean.iloc[0] - 1) * 100,
        "Retorno Anualizado": calculate_annualized_return(clean) * 100,
        "Volatilidade Anual": calculate_annualized_volatility(clean, frequency="daily") * 100,
        "Sharpe Ratio": calculate_sharpe_ratio(clean, risk_free_rate=risk_free_rate),
        "Máx. Drawdown": calculate_max_drawdown(clean) * 100,
    }

    if include_extremes:
        monthly = (
            rets.resample("ME").apply(lambda x: (1 + x).prod() - 1)
            if not rets.empty
            else pd.Series(dtype=float)
        )
        row.update(
            {
                "Melhor Dia": rets.max() * 100 if not rets.empty else np.nan,
                "Pior Dia": rets.min() * 100 if not rets.empty else np.nan,
                "Melhor Mês": monthly.max() * 100 if not monthly.empty else np.nan,
                "Pior Mês": monthly.min() * 100 if not monthly.empty else np.nan,
            }
        )

    if include_n_obs:
        row["Observações"] = int(len(clean))

    return row


def compute_stats_table(
    levels: pd.DataFrame,
    *,
    risk_free_rate: float = 0.0,
    returns: pd.DataFrame | None = None,
    include_extremes: bool = True,
    include_n_obs: bool = False,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Stats table with one row per series (index = Portfólio)."""
    cols = list(columns) if columns is not None else list(levels.columns)
    rows = []
    for col in cols:
        if col not in levels.columns:
            continue
        series_returns = returns[col] if returns is not None and col in returns.columns else None
        rows.append(
            compute_performance_stats(
                levels[col],
                label=str(col),
                risk_free_rate=risk_free_rate,
                returns=series_returns,
                include_extremes=include_extremes,
                include_n_obs=include_n_obs,
            )
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("Portfólio")


def _to_cumulative_return(levels: pd.DataFrame) -> pd.DataFrame:
    """Cumulative return (%) from the first valid point of each column."""
    out = pd.DataFrame(index=levels.index)
    for col in levels.columns:
        series = levels[col]
        first = series.first_valid_index()
        if first is None or series.loc[first] == 0:
            out[col] = np.nan
        else:
            out[col] = (series / series.loc[first] - 1.0) * 100
    return out


def compute_rolling_returns(levels: pd.DataFrame | pd.Series, window: int) -> pd.DataFrame:
    """Trailing return (%) over ``window`` observations for each series."""
    if window <= 0:
        raise ValueError("window must be a positive integer")
    df = _as_frame(levels)
    return df.pct_change(periods=window, fill_method=None) * 100


def _color_returns_cell(val) -> str:
    if pd.isna(val):
        return ""
    if val > 0:
        intensity = min(val / 8.0, 1.0)
        r = int(198 * (1 - intensity) + 26 * intensity)
        g = int(239 * (1 - intensity) + 122 * intensity)
        b = int(198 * (1 - intensity) + 49 * intensity)
        text = "white" if intensity > 0.6 else "black"
    else:
        intensity = min(abs(val) / 8.0, 1.0)
        r = int(255 * (1 - intensity) + 192 * intensity)
        g = int(199 * (1 - intensity) + 0 * intensity)
        b = int(206 * (1 - intensity) + 0 * intensity)
        text = "white" if intensity > 0.6 else "black"
    return f"background-color: rgb({r},{g},{b}); color: {text}"


def _render_stats_dataframe(stats_df: pd.DataFrame, *, transpose: bool) -> None:
    if stats_df.empty:
        st.warning("Nenhuma estatística de performance disponível.")
        return

    st.markdown("##### Estatísticas de Performance")
    if transpose:
        display = stats_df.T
        st.dataframe(
            style_table(
                display,
                numeric_cols_format_as_float=list(display.columns),
            ),
            width="stretch",
        )
        return

    percent_cols = [c for c in PERCENT_STAT_COLS if c in stats_df.columns]
    float_cols = [c for c in stats_df.columns if c not in percent_cols]
    st.dataframe(
        style_table(
            stats_df,
            percent_cols=percent_cols or None,
            numeric_cols_format_as_float=float_cols or None,
        ),
        width="stretch",
    )


def _render_equity_chart(
    chart_df: pd.DataFrame,
    *,
    key: str,
    title: str,
    y_axis_title: str,
    decimal_precision: int,
) -> None:
    hct.streamlit_highcharts(
        create_chart(
            data=chart_df,
            columns=list(chart_df.columns),
            names=list(chart_df.columns),
            chart_type="line",
            title=title,
            y_axis_title=y_axis_title,
            decimal_precision=decimal_precision,
        ),
        key=key,
    )


def _render_drawdown_chart(
    drawdown_df: pd.DataFrame,
    *,
    key: str,
    decimal_precision: int = 2,
) -> None:
    if drawdown_df.empty or drawdown_df.dropna(how="all").empty:
        st.warning("Sem dados para o gráfico de drawdown.")
        return
    hct.streamlit_highcharts(
        create_chart(
            data=drawdown_df,
            columns=list(drawdown_df.columns),
            names=list(drawdown_df.columns),
            chart_type="area",
            title="Drawdown",
            y_axis_title="Drawdown (%)",
            decimal_precision=decimal_precision,
        ),
        key=key,
    )


def _render_correlation_chart(
    returns: pd.DataFrame,
    *,
    key: str,
) -> None:
    corr_df = returns.dropna(how="all")
    if corr_df.shape[1] < 2:
        st.warning(
            "Há somente um portfólio e nenhum benchmark. Não é possível calcular a correlação."
        )
        return
    corr_matrix = corr_df.corr()
    corr_matrix = corr_matrix.where(np.tril(np.ones(corr_matrix.shape)).astype(np.bool_))
    hct.streamlit_highcharts(
        create_chart(
            data=corr_matrix,
            columns=list(corr_matrix.columns),
            names=list(corr_matrix.columns),
            chart_type="heatmap",
            title="Correlação",
            y_axis_title="Portfólio",
        ),
        key=key,
    )


def _resolve_rolling_window(
    *,
    key_prefix: str,
    rolling_window: int,
    window_options: dict[str, int] | None,
) -> tuple[int, str]:
    options = window_options if window_options is not None else ROLLING_WINDOW_OPTIONS
    if not options:
        return rolling_window, f"{rolling_window}d"

    labels = list(options.keys())
    default_label = next(
        (label for label, value in options.items() if value == rolling_window),
        labels[-1],
    )
    selected_label = st.selectbox(
        "Janela do retorno móvel",
        options=labels,
        index=labels.index(default_label),
        key=f"{key_prefix}_rolling_window",
        width=220,
    )
    return options[selected_label], selected_label


def _render_rolling_returns_chart(
    rolling_df: pd.DataFrame,
    *,
    key: str,
    window_label: str,
    decimal_precision: int = 2,
) -> None:
    if rolling_df.empty or rolling_df.dropna(how="all").empty:
        st.warning("Sem dados suficientes para o retorno móvel na janela selecionada.")
        return
    hct.streamlit_highcharts(
        create_chart(
            data=rolling_df,
            columns=list(rolling_df.columns),
            names=list(rolling_df.columns),
            chart_type="line",
            title=f"Retorno Móvel ({window_label})",
            y_axis_title="Retorno (%)",
            decimal_precision=decimal_precision,
        ),
        key=key,
    )


def _resolve_monthly_column(
    columns: Sequence[str],
    *,
    key_prefix: str,
    monthly_column: str | None,
) -> str | None:
    cols = list(columns)
    if not cols:
        return None
    if monthly_column is not None and monthly_column in cols:
        default = monthly_column
    else:
        default = cols[0]
    if len(cols) == 1:
        return default
    return st.selectbox(
        "Série — retorno mensal",
        options=cols,
        index=cols.index(default),
        key=f"{key_prefix}_monthly_column",
        width=220,
    )


def _render_monthly_returns_table(
    returns: pd.Series,
    *,
    series_label: str,
) -> pd.DataFrame:
    table = get_monthly_returns_table(returns.dropna())
    if table.empty:
        st.warning("Sem dados para a tabela de retorno mensal.")
        return table
    st.markdown(f"##### Retorno Mensal — {series_label} (%)")
    styled = table.style.map(_color_returns_cell).format("{:.1f}%", na_rep="—")
    st.dataframe(styled, width="stretch")
    return table


def render_tearsheet(
    *,
    key_prefix: str,
    levels: pd.DataFrame | pd.Series | None = None,
    returns: pd.DataFrame | pd.Series | None = None,
    risk_free_rate: float = 0.0,
    show_stats: bool = True,
    show_correlation: bool = False,
    show_rolling_returns: bool = True,
    show_monthly_returns: bool = True,
    correlation_returns: pd.DataFrame | None = None,
    drawdown_columns: Sequence[str] | None = None,
    monthly_column: str | None = None,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
    rolling_window_options: dict[str, int] | None = None,
    equity_title: str | None = None,
    equity_y_axis_title: str | None = None,
    stats: pd.DataFrame | list[dict] | None = None,
    include_extremes: bool = True,
    include_n_obs: bool = False,
    stats_transpose: bool = False,
    decimal_precision: int = 2,
) -> dict:
    """Render a standardized performance tearsheet.

    Pass **exactly one** of ``levels`` or ``returns``; the other is derived.
    Equity chart always shows cumulative return (%).

    Grid (2 columns, nothing full-width)::

        Performance acumulada | Stats
        Retorno móvel         | Retorno mensal
        Drawdown              | Correlação (opcional)
    """
    empty = {
        "chart_df": pd.DataFrame(),
        "stats_df": pd.DataFrame(),
        "drawdown_df": pd.DataFrame(),
        "rolling_df": pd.DataFrame(),
        "monthly_df": pd.DataFrame(),
        "levels": pd.DataFrame(),
        "returns": pd.DataFrame(),
    }

    try:
        levels_df, returns_df = resolve_levels_and_returns(levels=levels, returns=returns)
    except ValueError as exc:
        st.warning(str(exc))
        return empty

    chart_df = _to_cumulative_return(levels_df)
    if drawdown_columns:
        dd_cols = [c for c in drawdown_columns if c in levels_df.columns]
        dd_source = levels_df[dd_cols] if dd_cols else levels_df
    else:
        dd_source = levels_df
    drawdown_df = compute_drawdown(dd_source)

    stats_df = pd.DataFrame()
    if show_stats:
        if stats is None:
            stats_df = compute_stats_table(
                levels_df,
                risk_free_rate=risk_free_rate,
                returns=returns_df,
                include_extremes=include_extremes,
                include_n_obs=include_n_obs,
            )
        elif isinstance(stats, list):
            stats_df = pd.DataFrame(stats).set_index("Portfólio") if stats else pd.DataFrame()
        else:
            stats_df = stats.copy()
            if "Portfólio" in stats_df.columns:
                stats_df = stats_df.set_index("Portfólio")

    title = equity_title or "Performance Acumulada"
    y_title = equity_y_axis_title or "Retorno (%)"
    corr_input = correlation_returns if correlation_returns is not None else returns_df

    # Row 1: Performance | Stats
    row_1 = st.columns(2)
    with row_1[0]:
        _render_equity_chart(
            chart_df,
            key=f"{key_prefix}_equity",
            title=title,
            y_axis_title=y_title,
            decimal_precision=decimal_precision,
        )
    with row_1[1]:
        if show_stats:
            _render_stats_dataframe(stats_df, transpose=stats_transpose)

    # Row 2: Retorno móvel | Retorno mensal
    rolling_df = pd.DataFrame()
    monthly_df = pd.DataFrame()
    if show_rolling_returns or show_monthly_returns:
        row_2 = st.columns(2)
        with row_2[0]:
            if show_rolling_returns:
                options = (
                    ROLLING_WINDOW_OPTIONS
                    if rolling_window_options is None
                    else rolling_window_options
                )
                if options:
                    window, window_label = _resolve_rolling_window(
                        key_prefix=key_prefix,
                        rolling_window=rolling_window,
                        window_options=options,
                    )
                else:
                    window, window_label = rolling_window, f"{rolling_window}d"
                rolling_df = compute_rolling_returns(levels_df, window)
                _render_rolling_returns_chart(
                    rolling_df,
                    key=f"{key_prefix}_rolling",
                    window_label=window_label,
                    decimal_precision=decimal_precision,
                )
        with row_2[1]:
            if show_monthly_returns:
                series_name = _resolve_monthly_column(
                    list(returns_df.columns),
                    key_prefix=key_prefix,
                    monthly_column=monthly_column,
                )
                if series_name is not None:
                    monthly_df = _render_monthly_returns_table(
                        returns_df[series_name],
                        series_label=str(series_name),
                    )

    # Row 3: Drawdown | Correlação
    row_3 = st.columns(2)
    with row_3[0]:
        _render_drawdown_chart(
            drawdown_df,
            key=f"{key_prefix}_drawdown",
            decimal_precision=decimal_precision,
        )
    with row_3[1]:
        if show_correlation and corr_input is not None:
            _render_correlation_chart(corr_input, key=f"{key_prefix}_corr")

    return {
        "chart_df": chart_df,
        "stats_df": stats_df,
        "drawdown_df": drawdown_df,
        "rolling_df": rolling_df,
        "monthly_df": monthly_df,
        "levels": levels_df,
        "returns": returns_df,
    }
