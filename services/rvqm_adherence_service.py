"""Cálculo de TWR e métricas de aderência das carteiras investidas à estratégia RVQM."""

from __future__ import annotations

import numpy as np
import pandas as pd

RVQM_INSTRUMENTS = ("Ação", "BDR")


def pivot_model_weights(equities_portfolio: pd.DataFrame) -> pd.DataFrame:
    """Converte a carteira-modelo (date, code, weight) em matriz de pesos normalizados."""
    weights = equities_portfolio.pivot(index="date", columns="code", values="weight")
    weights.index = pd.to_datetime(weights.index)
    return weights.div(weights.sum(axis=1), axis=0).fillna(0.0)


def filter_equity_sleeve(
    positions: pd.DataFrame,
    assets_taxonomy: pd.DataFrame,
) -> pd.DataFrame:
    """
    Filtra a sleeve de RV (Ação/BDR) nas posições históricas do ComDinheiro.

    Mantém apenas tickers com cadastro Fibery classificados como Ação ou BDR.
    """
    if positions.empty:
        return positions.copy()

    required = {"Data", "Carteira", "Ticker", "Saldo Bruto"}
    missing = required - set(positions.columns)
    if missing:
        raise ValueError(f"Colunas ausentes nas posições históricas: {sorted(missing)}")

    taxonomy = assets_taxonomy[["Name", "Classificação Instrumento"]].drop_duplicates(
        subset=["Name"]
    )
    out = positions.merge(
        taxonomy,
        left_on="Ticker",
        right_on="Name",
        how="inner",
    )

    out = out.loc[out["Classificação Instrumento"].isin(RVQM_INSTRUMENTS)].copy()
    out = out[out["Saldo Bruto"].fillna(0) != 0]
    return out.drop(columns=["Name"], errors="ignore")


def positions_to_weights(positions: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Constrói matrizes de peso (date × ticker) por carteira a partir de saldo bruto.

    Pesos são renormalizados dia a dia dentro da sleeve filtrada.
    """
    if positions.empty:
        return {}

    grouped = (
        positions.groupby(["Carteira", "Data", "Ticker"], as_index=False)["Saldo Bruto"]
        .sum()
    )
    result: dict[str, pd.DataFrame] = {}
    for carteira, chunk in grouped.groupby("Carteira"):
        weights = chunk.pivot(index="Data", columns="Ticker", values="Saldo Bruto")
        weights.index = pd.to_datetime(weights.index)
        weights = weights.sort_index()
        weights = weights.div(weights.sum(axis=1), axis=0).fillna(0.0)
        result[str(carteira)] = weights
    return result


def calculate_portfolio_twr(
    weights: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    lag_weights: bool = True,
) -> pd.Series:
    """
    Retorno diário TWR: soma(peso × retorno do ativo), opcionalmente com pesos de t-1.

    Args:
        weights: Pesos (index=date, columns=ticker), tipicamente somando 1 por dia.
        prices: Preços de fechamento alinhados por data/ticker.
        lag_weights: Se True, usa pesos do dia anterior com retorno de hoje.
    """
    if weights.empty or prices.empty:
        return pd.Series(dtype=float, name="twr")

    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index)
    asset_returns = prices.pct_change(fill_method=None)

    w = weights.copy()
    w.index = pd.to_datetime(w.index)
    w = w.reindex(asset_returns.index).ffill().fillna(0.0)
    if lag_weights:
        w = w.shift(1)

    common = w.columns.intersection(asset_returns.columns)
    if len(common) == 0:
        return pd.Series(dtype=float, name="twr")

    daily = w[common].mul(asset_returns[common]).sum(axis=1)
    daily.name = "twr"
    return daily


def calculate_active_share(
    portfolio_weights: pd.DataFrame,
    benchmark_weights: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> float:
    """Active share = 0.5 × Σ |w_p − w_b| na data mais recente comum (ou `as_of`)."""
    if portfolio_weights.empty or benchmark_weights.empty:
        return float("nan")

    pw = portfolio_weights.copy()
    bw = benchmark_weights.copy()
    pw.index = pd.to_datetime(pw.index)
    bw.index = pd.to_datetime(bw.index)

    common_dates = pw.index.intersection(bw.index)
    if common_dates.empty:
        return float("nan")

    date = pd.to_datetime(as_of) if as_of is not None else common_dates.max()
    if date not in common_dates:
        prior = common_dates[common_dates <= date]
        if prior.empty:
            return float("nan")
        date = prior.max()

    all_tickers = pw.columns.union(bw.columns)
    w_p = pw.reindex(columns=all_tickers).loc[date].fillna(0.0)
    w_b = bw.reindex(columns=all_tickers).loc[date].fillna(0.0)
    return float(0.5 * (w_p - w_b).abs().sum())


def calculate_adherence_metrics(
    portfolio_returns: pd.Series,
    strategy_returns: pd.Series,
    *,
    trading_days: int = 252,
) -> dict[str, float]:
    """Métricas de aderência a partir de retornos diários alinhados."""
    aligned = pd.concat(
        [portfolio_returns.rename("portfolio"), strategy_returns.rename("strategy")],
        axis=1,
        join="inner",
    ).dropna()

    empty = {
        "excess_return": float("nan"),
        "tracking_error": float("nan"),
        "correlation": float("nan"),
        "hit_ratio": float("nan"),
        "obs": 0.0,
    }
    if len(aligned) < 2:
        return empty

    excess = aligned["portfolio"] - aligned["strategy"]
    cum_port = float((1 + aligned["portfolio"]).prod() - 1)
    cum_strat = float((1 + aligned["strategy"]).prod() - 1)

    return {
        "excess_return": cum_port - cum_strat,
        "tracking_error": float(np.sqrt(trading_days) * excess.std(ddof=1)),
        "correlation": float(aligned["portfolio"].corr(aligned["strategy"])),
        "hit_ratio": float((np.sign(aligned["portfolio"]) == np.sign(aligned["strategy"])).mean()),
        "obs": float(len(aligned)),
    }


def build_adherence_summary(
    portfolio_returns: dict[str, pd.Series],
    strategy_returns: pd.Series,
    portfolio_weights: dict[str, pd.DataFrame],
    strategy_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Monta tabela resumo de aderência por carteira."""
    rows = []
    for name, rets in portfolio_returns.items():
        metrics = calculate_adherence_metrics(rets, strategy_returns)
        weights = portfolio_weights.get(name, pd.DataFrame())
        metrics["active_share"] = calculate_active_share(weights, strategy_weights)
        metrics["carteira"] = name
        rows.append(metrics)

    if not rows:
        return pd.DataFrame(
            columns=[
                "carteira",
                "excess_return",
                "tracking_error",
                "correlation",
                "hit_ratio",
                "active_share",
                "obs",
            ]
        )

    summary = pd.DataFrame(rows).set_index("carteira")
    return summary[
        ["excess_return", "tracking_error", "correlation", "hit_ratio", "active_share", "obs"]
    ]
