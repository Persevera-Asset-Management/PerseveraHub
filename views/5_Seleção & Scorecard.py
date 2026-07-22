from collections import Counter

import numpy as np
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from services.position_service import load_assets

from persevera_tools.data import get_funds_data, get_series
from persevera_tools.db.fibery import read_fibery
from persevera_tools.quant_research.metrics import (
    calculate_annualized_return,
    calculate_consistency,
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
)

from utils.chart_helpers import create_chart, render_chart
from utils.table import style_table

st.title("Fundos · Seleção & Scorecard")

# ── Metric definitions ────────────────────────────────────────────────────────

METRICS = {
    "Retorno": {
        "default_active": True,
        "key": "retorno",
        "group": "retorno",
        "default_weight": 1.0,
        "higher_is_better": True,
        "default_window": 12,
        "is_pct": True,
        "description": "Retorno acumulado no período selecionado",
    },
    "Consistência": {
        "default_active": True,
        "key": "consistencia",
        "group": "consistencia",
        "default_weight": 1.0,
        "higher_is_better": True,
        "default_window": 24,
        "is_pct": True,
        "description": "% de meses com retorno acima do CDI",
    },
    "Volatilidade": {
        "default_active": True,
        "key": "volatilidade",
        "group": "risco",
        "default_weight": 1.0,
        "higher_is_better": False,
        "default_window": 12,
        "is_pct": True,
        "description": "Volatilidade anualizada dos retornos diários",
    },
    "Max Drawdown": {
        "default_active": True,
        "key": "max_dd",
        "group": "risco",
        "default_weight": 1.0,
        "higher_is_better": False,
        "default_window": 24,
        "is_pct": True,
        "description": "Maior queda do pico ao vale no período",
    },
    "Sharpe": {
        "default_active": True,
        "key": "sharpe",
        "group": "risco_retorno",
        "default_weight": 1.0,
        "higher_is_better": True,
        "default_window": 12,
        "is_pct": False,
        "description": "Retorno excedente ao CDI / Volatilidade (anualizado)",
    },
    "Sortino": {
        "default_active": True,
        "key": "sortino",
        "group": "risco_retorno",
        "default_weight": 1.0,
        "higher_is_better": True,
        "default_window": 12,
        "is_pct": False,
        "description": "Retorno excedente ao CDI / Desvio negativo (anualizado)",
    },
    "Calmar": {
        "default_active": True,
        "key": "calmar",
        "group": "risco_retorno",
        "default_weight": 1.0,
        "higher_is_better": True,
        "default_window": 24,
        "is_pct": False,
        "description": "Retorno anualizado / |Max Drawdown|",
    },
}

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_taxonomy() -> pd.DataFrame:
    try:
        df = load_assets(instrumentos=("Fundo de Investimento", "Previdência Privada"))
        return df[["Name", "Nome Completo"]].drop_duplicates()
    except Exception:
        return pd.DataFrame(columns=["Name", "Nome Completo"])

@st.cache_data(ttl=3600)
def load_nav(cnpjs: tuple, start_date: str) -> pd.DataFrame:
    try:
        raw = get_funds_data(
            cnpjs=list(cnpjs), start_date=start_date, fields=["fund_nav"]
        )
        if raw.empty:
            return pd.DataFrame()
        if isinstance(raw.columns, pd.MultiIndex):
            lvl0 = raw.columns.get_level_values(0).unique().tolist()
            if "fund_nav" in lvl0:
                nav = raw["fund_nav"]
            else:
                swapped = raw.swaplevel(axis=1)
                lvl0_s = swapped.columns.get_level_values(0).unique().tolist()
                nav = swapped["fund_nav"] if "fund_nav" in lvl0_s else raw.droplevel(0, axis=1)
        else:
            nav = raw
        nav = nav.replace(0, np.nan).sort_index()
        if not isinstance(nav.index, pd.DatetimeIndex):
            nav.index = pd.to_datetime(nav.index)
        return nav
    except Exception as e:
        st.error(f"Erro ao carregar dados de NAV: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_benchmark(start_date: str) -> pd.Series:
    try:
        raw = get_series(["br_cdi_index"], start_date=start_date, field="close")
        series = raw.iloc[:, 0] if isinstance(raw, pd.DataFrame) else raw
        if not isinstance(series.index, pd.DatetimeIndex):
            series.index = pd.to_datetime(series.index)
        return series.rename("CDI")
    except Exception:
        return pd.Series(dtype=float, name="CDI")

# ── Metric computation ────────────────────────────────────────────────────────

def compute_metrics(nav_series: pd.Series, cdi_series: pd.Series, metric_params: dict) -> dict:
    result = {}
    nav = nav_series.dropna()
    if len(nav) < 10:
        return {m: np.nan for m in metric_params}

    end_dt = nav.index.max()

    for mname, params in metric_params.items():
        key = METRICS[mname]["key"]
        window = params["window"]
        start_dt = end_dt - relativedelta(months=window)
        pnav = nav.loc[start_dt:]

        if len(pnav) < 5:
            result[mname] = np.nan
            continue

        try:
            if key == "retorno":
                result[mname] = float(pnav.iloc[-1] / pnav.iloc[0] - 1)

            elif key == "consistencia":
                result[mname] = calculate_consistency(pnav, cdi_series.loc[start_dt:end_dt].dropna())

            elif key == "volatilidade":
                result[mname] = calculate_annualized_volatility(pnav, frequency="daily")

            elif key == "max_dd":
                result[mname] = abs(calculate_max_drawdown(pnav))

            elif key == "sharpe":
                rf = calculate_annualized_return(cdi_series.loc[start_dt:end_dt].dropna())
                result[mname] = calculate_sharpe_ratio(pnav, risk_free_rate=rf)

            elif key == "sortino":
                rf = calculate_annualized_return(cdi_series.loc[start_dt:end_dt].dropna())
                result[mname] = calculate_sortino_ratio(pnav, risk_free_rate=rf)

            elif key == "calmar":
                result[mname] = calculate_calmar_ratio(pnav)

            else:
                result[mname] = np.nan

        except Exception:
            result[mname] = np.nan

    return result

def compute_scores(raw: pd.DataFrame, metric_params: dict) -> pd.Series:
    """Percentile-rank weighted score with equal-weight-by-group normalization.

    Each metric is ranked percentile within its peers. Within a group, the
    contribution is the average of the ranked metrics weighted by their
    individual weights. Groups themselves each contribute equally to the
    final score (25% each for 4 groups), regardless of how many metrics
    are active per group.
    """
    score = pd.Series(0.0, index=raw.index)

    # Build group → {mname: weight} mapping for active metrics only
    groups: dict[str, dict[str, float]] = {}
    for mname, params in metric_params.items():
        w = params["weight"]
        if w == 0 or mname not in raw.columns:
            continue
        group = METRICS[mname]["group"]
        groups.setdefault(group, {})[mname] = w

    n_groups = len(groups)
    if n_groups == 0:
        return score

    for group_metrics in groups.values():
        group_w = sum(group_metrics.values())
        group_score = pd.Series(0.0, index=raw.index)
        for mname, w in group_metrics.items():
            col = pd.to_numeric(raw[mname], errors="coerce")
            ranked = col.rank(pct=True, na_option="keep")
            if not METRICS[mname]["higher_is_better"]:
                ranked = 1 - ranked
            group_score += ranked.fillna(0.5) * (w / group_w)
        score += group_score / n_groups

    return (score * 100).round(1)

# ── CNPJ parsing ──────────────────────────────────────────────────────────────

def parse_cnpjs(text: str) -> list:
    if not text or not text.strip():
        return []
    lines = text.replace(",", "\n").replace(";", "\n").split("\n")
    return [ln.strip() for ln in lines if ln.strip()]

def build_labels(cnpj_list: list, mapping: dict) -> dict:
    raw = {c: mapping.get(c, c) for c in cnpj_list}
    counts = Counter(raw.values())
    return {c: (f"{n} ({c})" if counts[n] > 1 else n) for c, n in raw.items()}

def cumulative_return_pct(nav_df: pd.DataFrame) -> pd.DataFrame:
    """Cumulative return (%) from the first row; NaNs before inception stay NaN."""
    if nav_df.empty or len(nav_df) < 2:
        return pd.DataFrame(index=nav_df.index)
    rets = nav_df.ffill().pct_change(fill_method=None)
    cum = (1 + rets).cumprod()
    cum.iloc[0] = 1.0
    return (cum - 1) * 100

def common_start_date(nav_df: pd.DataFrame) -> pd.Timestamp | None:
    """Earliest date on which every column has a valid observation."""
    if nav_df.empty:
        return None
    starts = [nav_df[c].first_valid_index() for c in nav_df.columns]
    starts = [s for s in starts if s is not None]
    return max(starts) if starts else None

def render_perf_chart(data: pd.DataFrame, columns: list, key: str) -> None:
    valid = [c for c in columns if c in data.columns]
    if not valid or data[valid].dropna(how="all").empty:
        st.info("Dados insuficientes para exibir o gráfico.")
        return
    chart_obj = create_chart(
        data=data,
        columns=valid,
        names=valid,
        chart_type="line",
        title="",
        y_axis_title="%",
        enable_fullscreen_on_dblclick=True,
    )
    render_chart(chart_obj, key=key)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Parâmetros")

    st.subheader("1 · Fundos")
    cnpj_text = st.text_area(
        "CNPJs (um por linha ou separados por vírgula):",
        height=170,
        placeholder="11.111.111/0001-11\n22.222.222/0001-22\n...",
        help="Formato: XX.XXX.XXX/XXXX-XX",
    )

    st.subheader("2 · Período de Análise")
    three_years_ago = (pd.Timestamp.today() - relativedelta(years=3)).date()
    today = pd.Timestamp.today().date()
    d_start = st.date_input("Início", value=three_years_ago, format="DD/MM/YYYY")
    d_end = st.date_input("Fim", value=today, format="DD/MM/YYYY")

    st.subheader("3 · Métricas e Pesos")
    st.caption("Peso 0 exclui a métrica do score. A janela define o lookback de cálculo.")

    active_params: dict = {}
    for mname, meta in METRICS.items():
        is_default = meta["default_active"]
        with st.expander(f"{'✅' if is_default else '◻️'} {mname}", expanded=is_default):
            enabled = st.checkbox(
                "Incluir no score", value=is_default, key=f"en_{meta['key']}"
            )
            if enabled:
                col1, col2 = st.columns(2)
                w = col1.number_input(
                    "Peso",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(meta["default_weight"]),
                    step=0.5,
                    key=f"w_{meta['key']}",
                )
                win = col2.number_input(
                    "Janela (m)",
                    min_value=1,
                    max_value=60,
                    value=int(meta["default_window"]),
                    step=1,
                    key=f"win_{meta['key']}",
                )
                direction = "↑ maior melhor" if meta["higher_is_better"] else "↓ menor melhor"
                st.caption(f"{direction} · {meta['description']}")
                active_params[mname] = {"window": int(win), "weight": float(w)}

    run = st.button("▶ Calcular Score", type="primary", width='stretch')

# ── Validation ────────────────────────────────────────────────────────────────

cnpjs = parse_cnpjs(cnpj_text)

if not cnpjs:
    st.info(
        "Insira os CNPJs dos fundos na barra lateral para iniciar a análise.\n\n"
        "Formato esperado: `XX.XXX.XXX/XXXX-XX`, um por linha ou separados por vírgula."
    )
    st.stop()

if not run:
    st.info(
        f"**{len(cnpjs)} CNPJ(s)** inserido(s). "
        "Configure as métricas e pesos na barra lateral e clique em **▶ Calcular Score**."
    )
    st.stop()

if not active_params:
    st.warning("Selecione pelo menos uma métrica na barra lateral.")
    st.stop()

if d_start >= d_end:
    st.error("A data inicial deve ser anterior à data final.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────

with st.spinner("Carregando dados...", show_time=True):
    nav_raw = load_nav(tuple(cnpjs), str(d_start))
    cdi_raw = load_benchmark(str(d_start))
    taxonomy = load_taxonomy()

if nav_raw.empty:
    st.error(
        "Não foi possível carregar dados de NAV para os CNPJs informados. "
        "Verifique os CNPJs e tente novamente."
    )
    st.stop()

nav = nav_raw.loc[str(d_start): str(d_end)]
cdi = (
    cdi_raw.loc[str(d_start): str(d_end)]
    if not cdi_raw.empty
    else pd.Series(dtype=float, name="CDI")
)

# Build deduplicated display labels
cnpj_to_name = (
    taxonomy.set_index("Name")["Nome Completo"].to_dict()
    if not taxonomy.empty
    else {}
)
labels = build_labels(list(nav.columns), cnpj_to_name)
nav_lb = nav.rename(columns=labels)

# ── Summary header ────────────────────────────────────────────────────────────

found = len(nav.columns)
not_found_count = len([c for c in cnpjs if c not in nav.columns])
period_str = (
    f"{nav.index.min().strftime('%m/%Y')} – {nav.index.max().strftime('%m/%Y')}"
    if found > 0
    else "—"
)

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Fundos Encontrados", found)
mc2.metric("Não Encontrados", not_found_count)
mc3.metric("Métricas Ativas", len(active_params))
mc4.metric("Período dos Dados", period_str)

if not_found_count > 0:
    missing = [c for c in cnpjs if c not in nav.columns]
    st.warning(f"Dados não encontrados para {not_found_count} CNPJ(s): {', '.join(missing)}")

# ── Compute metrics ───────────────────────────────────────────────────────────

with st.spinner("Calculando métricas...", show_time=True):
    rows = []
    for cnpj, label in labels.items():
        if cnpj not in nav.columns:
            continue
        m = compute_metrics(nav[cnpj], cdi, active_params)
        m["Fundo"] = label
        rows.append(m)

if not rows:
    st.error("Nenhum fundo com dados suficientes para calcular as métricas.")
    st.stop()

raw_df = pd.DataFrame(rows).set_index("Fundo")

# Convert raw values to percentage for display.
# Max Drawdown is stored as a positive absolute value internally;
# multiply by -100 so the table shows it as a negative percentage (e.g., -16.00%).
disp = raw_df.copy()
for mname in active_params:
    if mname in disp.columns and METRICS[mname]["is_pct"]:
        multiplier = -100 if METRICS[mname]["key"] == "max_dd" else 100
        disp[mname] = disp[mname] * multiplier

# Score and rank
scores = compute_scores(raw_df, active_params)
disp.insert(0, "Score", scores)
disp.sort_values("Score", ascending=False, inplace=True)
disp.insert(0, "Rank", range(1, len(disp) + 1))

# ── Scorecard table ───────────────────────────────────────────────────────────

pct_cols = [m for m in active_params if METRICS[m]["is_pct"] and m in disp.columns]
float_cols = [m for m in active_params if not METRICS[m]["is_pct"] and m in disp.columns]

st.dataframe(
    style_table(
        disp,
        percent_cols=pct_cols,
        numeric_cols_format_as_float=["Score"] + float_cols,
        numeric_cols_format_as_int=["Rank"],
        highlight_quartile=["Score"] + pct_cols + float_cols,
        color_negative_positive_cols=pct_cols + float_cols,
        center_align_cols=["Rank"],
    ),
    width='stretch',
)

# ── Performance chart ─────────────────────────────────────────────────────────

st.subheader("Performance Acumulada")

all_labels = list(nav_lb.columns)
top5 = [lbl for lbl in disp.index[:5] if lbl in all_labels]

chart_col1, chart_col2 = st.columns([5, 1])
with chart_col1:
    selected_for_chart = st.multiselect(
        "Selecione fundos para o gráfico:",
        options=all_labels,
        default=top5,
        key="perf_select",
    )
with chart_col2:
    show_cdi = st.checkbox("Incluir CDI", value=True, key="show_cdi")

if not selected_for_chart:
    st.info("Selecione fundos para exibir o gráfico de performance.")
else:
    cdi_aligned = (
        cdi.reindex(nav_lb.index, method="ffill")
        if show_cdi and not cdi.empty
        else None
    )

    tab_labels = ["Comparativo"] + selected_for_chart
    tabs = st.tabs(tab_labels)

    # ── Comparativo: common start across selected funds (+ CDI if shown) ──
    with tabs[0]:
        funds_nav = nav_lb[selected_for_chart].copy()
        common_cols = list(selected_for_chart)
        if cdi_aligned is not None:
            funds_nav = funds_nav.join(cdi_aligned, how="left")
            common_cols = selected_for_chart + ["CDI"]

        start = common_start_date(funds_nav[selected_for_chart])
        if start is None:
            st.info("Dados insuficientes para o comparativo.")
        else:
            sliced = funds_nav.loc[start:, common_cols].dropna(how="all")
            # Drop rows where any fund is still missing (align to full overlap)
            sliced = sliced.dropna(subset=selected_for_chart, how="any")
            if cdi_aligned is not None and "CDI" in sliced.columns:
                sliced["CDI"] = sliced["CDI"].ffill()

            if len(sliced) < 2:
                st.info("Período comum insuficiente entre os fundos selecionados.")
            else:
                st.caption(
                    f"Período comum a partir de **{start.strftime('%d/%m/%Y')}** "
                    "(início do fundo mais recente entre os selecionados)."
                )
                render_perf_chart(
                    cumulative_return_pct(sliced),
                    common_cols,
                    key="scorecard_perf_common",
                )

    # ── Individual: rebase from each fund's own inception ──
    for i, label in enumerate(selected_for_chart):
        with tabs[i + 1]:
            series = nav_lb[[label]].copy()
            first = series[label].first_valid_index()
            if first is None:
                st.info(f"Sem dados de NAV para {label}.")
                continue

            indiv = series.loc[first:].copy()
            cols = [label]
            if cdi_aligned is not None:
                indiv = indiv.join(cdi_aligned.loc[first:], how="left")
                indiv["CDI"] = indiv["CDI"].ffill()
                cols = [label, "CDI"]

            indiv = indiv.dropna(subset=[label])
            if len(indiv) < 2:
                st.info(f"Dados insuficientes para {label}.")
                continue

            st.caption(
                f"Desde a inception em **{first.strftime('%d/%m/%Y')}**."
            )
            render_perf_chart(
                cumulative_return_pct(indiv[cols]),
                cols,
                key=f"scorecard_perf_indiv_{i}",
            )
