import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart
from utils.table import style_table
from services.position_service import load_indicator_catalog, load_funds_catalog

from persevera_tools.data import get_series, get_funds_data
from persevera_tools.quant_research.metrics import (
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
)

# Edite este dicionário para adicionar/remover benchmarks disponíveis.
# Formato: "Nome exibido no multiselect": "ticker_na_base"
BENCHMARK_OPTIONS: dict[str, str] = {
    "CDI": "br_cdi_index",
    "IBOV": "br_ibovespa",
    "BRL/USD": "brl_usd",
    "S&P 500 (USD)": "us_sp500",
}

RESULT_KEY = "pb_backtest_results"
_CNPJ_DIGITS_RE = re.compile(r"\D+")


def _is_cnpj(code: str) -> bool:
    """True when the code has exactly 14 digits (formatted or raw CNPJ)."""
    digits = _CNPJ_DIGITS_RE.sub("", str(code))
    return len(digits) == 14


def _cnpj_digits(code: str) -> str:
    return _CNPJ_DIGITS_RE.sub("", str(code))


_PAREN_CNPJ_RE = re.compile(r"\(([^)]+)\)\s*$")


@st.cache_data(ttl=3600)
def _build_asset_catalog() -> tuple[tuple[str, ...], dict[str, str]]:
    """Build catalog codes + pretty labels for the multiselect.

    Options stored/returned are canonical codes (série or CNPJ as in the DB).
    ``code_to_label`` is only for display via ``format_func``.
    """
    codes: list[str] = []
    code_to_label: dict[str, str] = {}

    for code in load_indicator_catalog():
        code = str(code).strip()
        if not code:
            continue
        codes.append(code)
        code_to_label.setdefault(code, code)

    funds = load_funds_catalog()
    if not funds.empty and "Name" in funds.columns:
        for _, row in funds.iterrows():
            cnpj = str(row["Name"]).strip()
            if not cnpj:
                continue
            nome = str(row.get("Nome Completo", "") or "").strip()
            codes.append(cnpj)
            code_to_label[cnpj] = f"{nome} ({cnpj})" if nome else cnpj

    return tuple(sorted(dict.fromkeys(codes), key=str.lower)), code_to_label


def _resolve_ticker(value: str, code_to_label: dict[str, str] | None = None) -> str:
    """Normalize cell values to canonical codes (CNPJ / série).

    Accepts bare codes, or legacy labels like ``Nome (CNPJ)``.
    """
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    if code_to_label and text in code_to_label:
        return text
    match = _PAREN_CNPJ_RE.search(text)
    if match:
        maybe_cnpj = match.group(1).strip()
        if _is_cnpj(maybe_cnpj):
            return maybe_cnpj
    return text


def _ensure_range_index(df: pd.DataFrame) -> pd.DataFrame:
    """RangeIndex is required for hide_index + num_rows='dynamic' in data_editor."""
    return df.reset_index(drop=True)


def _bump_table_editor() -> None:
    """Remount data_editor after external structural edits."""
    st.session_state["pb_table_editor_version"] = (
        st.session_state.get("pb_table_editor_version", 0) + 1
    )


def _editor_key() -> str:
    return f"portfolio_table_editor_{st.session_state.get('pb_table_editor_version', 0)}"


def _append_assets_to_table(table: pd.DataFrame, selected_codes: list[str]) -> pd.DataFrame:
    """Append catalog codes (série/CNPJ) to the (already edited) portfolio table."""
    table = _ensure_range_index(table.copy())
    existing_codes = {
        _resolve_ticker(v) for v in table["Ticker"].tolist() if str(v).strip()
    }
    new_rows = []
    for raw in selected_codes:
        code = _resolve_ticker(raw)
        if not code or code in existing_codes:
            continue
        new_rows.append({col: (code if col == "Ticker" else 0.0) for col in table.columns})
        existing_codes.add(code)

    if not new_rows:
        return table

    non_empty = table[table["Ticker"].astype(str).str.strip() != ""]
    return _ensure_range_index(
        pd.concat([non_empty, pd.DataFrame(new_rows)], ignore_index=True)
    )


def _align_data_columns(data: pd.DataFrame, codes: list[str]) -> pd.DataFrame:
    """Rename fund columns when CNPJ punctuation differs from requested codes."""
    if data.empty:
        return data
    col_by_digits = {
        _cnpj_digits(c): c for c in data.columns if _is_cnpj(str(c))
    }
    rename: dict[str, str] = {}
    for code in codes:
        if code in data.columns:
            continue
        if _is_cnpj(code):
            src = col_by_digits.get(_cnpj_digits(code))
            if src is not None and src not in rename:
                rename[src] = code
    return data.rename(columns=rename) if rename else data


def _normalize_columns(df: pd.DataFrame | pd.Series, single_name: str | None = None) -> pd.DataFrame:
    """Normalize get_series / get_funds_data output to a flat-column DataFrame."""
    if isinstance(df, pd.Series):
        name = single_name or (df.name if df.name and df.name != "close" else "series")
        return df.to_frame(name=name)
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)
    return out.dropna(how="all", axis="columns")


def _split_codes(codes: list[str]) -> tuple[list[str], list[str]]:
    series_codes, fund_cnpjs = [], []
    for code in codes:
        (fund_cnpjs if _is_cnpj(code) else series_codes).append(code)
    return series_codes, fund_cnpjs


@st.cache_data(ttl=3600)
def load_data(
    series_codes: tuple[str, ...],
    fund_cnpjs: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Load prices for series tickers and fund NAVs separately; return (data, warnings)."""
    frames: list[pd.DataFrame] = []
    warnings: list[str] = []

    if series_codes:
        try:
            raw = get_series(
                list(series_codes),
                start_date=start_date,
                end_date=end_date,
                field=["close"],
            )
            indicators = _normalize_columns(
                raw,
                single_name=series_codes[0] if len(series_codes) == 1 else None,
            )
            if indicators.empty:
                warnings.append(
                    f"Nenhum dado de série retornado para: {', '.join(series_codes)}"
                )
            else:
                frames.append(indicators)
        except Exception as e:
            warnings.append(f"Falha ao carregar séries ({', '.join(series_codes)}): {e}")

    if fund_cnpjs:
        try:
            raw_funds = get_funds_data(
                cnpjs=list(fund_cnpjs),
                start_date=start_date,
                end_date=end_date,
                fields=["fund_nav"],
            )
            funds = _normalize_columns(raw_funds)
            if funds.empty:
                warnings.append(
                    f"Nenhum NAV retornado para CNPJs: {', '.join(fund_cnpjs)}"
                )
            else:
                frames.append(funds)
        except TypeError:
            # Alguns backends ainda não aceitam end_date em get_funds_data
            try:
                raw_funds = get_funds_data(
                    cnpjs=list(fund_cnpjs),
                    start_date=start_date,
                    fields=["fund_nav"],
                )
                funds = _normalize_columns(raw_funds)
                if not funds.empty:
                    funds = funds.loc[:end_date] if end_date else funds
                    frames.append(funds)
                else:
                    warnings.append(
                        f"Nenhum NAV retornado para CNPJs: {', '.join(fund_cnpjs)}"
                    )
            except Exception as e:
                warnings.append(f"Falha ao carregar fundos ({', '.join(fund_cnpjs)}): {e}")
        except Exception as e:
            warnings.append(f"Falha ao carregar fundos ({', '.join(fund_cnpjs)}): {e}")

    if not frames:
        return pd.DataFrame(), tuple(warnings)

    data = pd.concat(frames, axis=1)
    data = data.loc[:, ~data.columns.duplicated()]
    return data, tuple(warnings)


def _compute_stats(index: pd.Series, returns: pd.Series, label: str, risk_free_rate: float) -> dict:
    monthly_returns = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    return {
        "Portfólio": label,
        "Retorno Total": (index.iloc[-1] / index.iloc[0] - 1) * 100,
        "Retorno Anualizado": calculate_annualized_return(index) * 100,
        "Volatilidade Anual": calculate_annualized_volatility(index, frequency="daily") * 100,
        "Sharpe Ratio": calculate_sharpe_ratio(index, risk_free_rate=risk_free_rate),
        "Máx. Drawdown": calculate_max_drawdown(index) * 100,
        "Melhor Dia": returns.max() * 100,
        "Pior Dia": returns.min() * 100,
        "Melhor Mês": monthly_returns.max() * 100,
        "Pior Mês": monthly_returns.min() * 100,
    }


def _format_date(ts) -> str:
    if ts is None or (isinstance(ts, float) and np.isnan(ts)) or pd.isna(ts):
        return "—"
    return pd.Timestamp(ts).strftime("%d/%m/%Y")


def _build_coverage_table(
    data: pd.DataFrame,
    asset_codes: list[str],
    benchmark_labels: list[str],
    code_to_label: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, str | None, str | None]:
    """Build coverage table and identify the portfolio asset that starts latest."""
    code_to_label = code_to_label or {}
    rows: list[dict] = []
    asset_first_dates: dict[str, pd.Timestamp] = {}

    for code in asset_codes:
        display = code_to_label.get(code, code)
        if code not in data.columns:
            rows.append(
                {
                    "Ativo": display,
                    "_code": code,
                    "Tipo": "Fundo" if _is_cnpj(code) else "Série",
                    "Data mínima": "—",
                    "Data máxima": "—",
                    "Limitante": "",
                    "_first": pd.Timestamp.max,
                }
            )
            continue
        series = data[code]
        first = series.first_valid_index()
        last = series.last_valid_index()
        first_ts = pd.Timestamp(first) if first is not None else None
        if first_ts is not None:
            asset_first_dates[code] = first_ts
        rows.append(
            {
                "Ativo": display,
                "_code": code,
                "Tipo": "Fundo" if _is_cnpj(code) else "Série",
                "Data mínima": _format_date(first),
                "Data máxima": _format_date(last),
                "Limitante": "",
                "_first": first_ts if first_ts is not None else pd.Timestamp.max,
            }
        )

    for label in benchmark_labels:
        bm_ticker = BENCHMARK_OPTIONS[label]
        if bm_ticker not in data.columns:
            rows.append(
                {
                    "Ativo": label,
                    "_code": bm_ticker,
                    "Tipo": "Benchmark",
                    "Data mínima": "—",
                    "Data máxima": "—",
                    "Limitante": "",
                    "_first": pd.Timestamp.max,
                }
            )
            continue
        series = data[bm_ticker]
        first = series.first_valid_index()
        rows.append(
            {
                "Ativo": label,
                "_code": bm_ticker,
                "Tipo": "Benchmark",
                "Data mínima": _format_date(first),
                "Data máxima": _format_date(series.last_valid_index()),
                "Limitante": "",
                "_first": pd.Timestamp(first) if first is not None else pd.Timestamp.max,
            }
        )

    limiting_code: str | None = None
    limiting_date_str: str | None = None
    if asset_first_dates:
        limiting_code = max(asset_first_dates, key=asset_first_dates.get)
        limiting_date_str = _format_date(asset_first_dates[limiting_code])
        for row in rows:
            if row.get("_code") == limiting_code:
                row["Limitante"] = "Sim"

    coverage_df = pd.DataFrame(rows)
    if not coverage_df.empty:
        coverage_df["_is_limiting"] = coverage_df["Limitante"].ne("Sim").astype(int)
        coverage_df = (
            coverage_df.sort_values(["_is_limiting", "_first", "Ativo"], ascending=[True, False, True])
            .drop(columns=["_first", "_is_limiting", "_code"])
            .reset_index(drop=True)
        )

    limiting_display = (
        code_to_label.get(limiting_code, limiting_code) if limiting_code else None
    )
    return coverage_df, limiting_display, limiting_date_str


def _render_results(results: dict) -> None:
    chart_df = results["chart_df"]
    portfolio_stats = results["portfolio_stats"]
    portfolio_returns_df = results["portfolio_returns_df"]
    benchmark_returns_dict = results["benchmark_returns_dict"]
    coverage_df = results.get("coverage_df")
    limiting_code = results.get("limiting_code")
    limiting_date = results.get("limiting_date")

    for msg in results.get("warnings", []):
        st.warning(msg)

    if coverage_df is not None and not coverage_df.empty:
        with st.expander("Cobertura de dados", expanded=False):
            if limiting_code and limiting_date:
                st.info(
                    f"**Ativo limitante:** {limiting_code} — histórico começa em **{limiting_date}**. "
                    "Antes dessa data, o backtest long-only redistribui pesos entre os ativos já disponíveis."
                )
            st.dataframe(coverage_df, hide_index=True, width="stretch")

    row_1 = st.columns(2)
    with row_1[0]:
        chart = create_chart(
            data=chart_df,
            columns=list(chart_df.columns),
            names=list(chart_df.columns),
            chart_type="line",
            title="Equity Curve",
            y_axis_title="Índice",
        )
        hct.streamlit_highcharts(chart, key="equity_curve")

    with row_1[1]:
        if portfolio_stats:
            st.markdown("##### Estatísticas de Performance")
            stats_df = pd.DataFrame(portfolio_stats).set_index("Portfólio")
            st.dataframe(
                style_table(
                    stats_df,
                    percent_cols=[
                        "Retorno Total",
                        "Retorno Anualizado",
                        "Volatilidade Anual",
                        "Máx. Drawdown",
                        "Melhor Dia",
                        "Pior Dia",
                        "Melhor Mês",
                        "Pior Mês",
                    ],
                    numeric_cols_format_as_float=["Sharpe Ratio"],
                ),
                width="stretch",
            )
        else:
            st.warning("Nenhum portfólio foi calculado com sucesso.")

    row_2 = st.columns(2)
    with row_2[0]:
        drawdown_df = pd.DataFrame(index=chart_df.index)
        for col in chart_df.columns:
            cumulative = chart_df[col]
            running_max = cumulative.expanding().max()
            drawdown_df[col] = (cumulative - running_max) / running_max * 100

        chart_drawdown = create_chart(
            data=drawdown_df,
            columns=list(drawdown_df.columns),
            names=list(drawdown_df.columns),
            chart_type="area",
            title="Drawdown",
            y_axis_title="Drawdown (%)",
        )
        hct.streamlit_highcharts(chart_drawdown, key="drawdown")

    with row_2[1]:
        corr_df = portfolio_returns_df.copy()
        for bm_label, bm_rets in benchmark_returns_dict.items():
            corr_df[bm_label] = bm_rets

        if len(corr_df.columns) > 1:
            corr_matrix = corr_df.corr()
            corr_matrix = corr_matrix.where(np.tril(np.ones(corr_matrix.shape)).astype(np.bool_))
            chart_corr = create_chart(
                data=corr_matrix,
                columns=list(corr_matrix.columns),
                names=list(corr_matrix.columns),
                chart_type="heatmap",
                title="Correlação",
                y_axis_title="Portfólio",
            )
            hct.streamlit_highcharts(chart_corr, key="correlacao")
        else:
            st.warning(
                "Há somente um portfólio e nenhum benchmark. Não é possível calcular a correlação."
            )


st.title("Portfolio Backtester")

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input(
        "Data Inicial",
        min_value=datetime(2000, 1, 1),
        max_value=datetime.today(),
        value=datetime(2010, 1, 1),
        format="DD/MM/YYYY",
    )
    end_date = st.date_input(
        "Data Final",
        min_value=datetime(2000, 1, 1),
        max_value=datetime.today(),
        value=datetime.today(),
        format="DD/MM/YYYY",
    )
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    risk_free_rate = st.number_input(
        "Taxa Livre de Risco (% a.a.)",
        min_value=0.0,
        max_value=50.0,
        value=10.75,
        step=0.25,
        format="%.2f",
    ) / 100
    selected_benchmarks = st.multiselect(
        "Benchmarks",
        options=list(BENCHMARK_OPTIONS.keys()),
    )

st.markdown(
    "Busque e selecione **séries** ou **fundos** do catálogo, defina os **pesos em %** "
    "para cada portfólio. Pesos **positivos** são normalizados para somar 100%. "
    "Use pesos **negativos** para posições vendidas — nesse caso os valores são usados como "
    "alocação absoluta (ex: −50, −50, +200)."
)

with st.spinner("Carregando catálogo de ativos...", show_time=True):
    asset_codes, code_to_label = _build_asset_catalog()

if "num_portfolios" not in st.session_state:
    st.session_state["num_portfolios"] = 1

if "portfolio_table" not in st.session_state:
    st.session_state["portfolio_table"] = pd.DataFrame({"Ticker": [""], "Portfolio 1 (%)": [0.0]})
else:
    st.session_state["portfolio_table"] = _ensure_range_index(st.session_state["portfolio_table"])

if "pb_add_ms_version" not in st.session_state:
    st.session_state["pb_add_ms_version"] = 0

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("➕ Adicionar Portfolio"):
        st.session_state["num_portfolios"] += 1
        new_col_name = f"Portfolio {st.session_state['num_portfolios']} (%)"
        st.session_state["portfolio_table"][new_col_name] = 0.0
        st.session_state["portfolio_table"] = _ensure_range_index(
            st.session_state["portfolio_table"]
        )
        _bump_table_editor()
        st.rerun()

with col2:
    if st.button("➖ Remover Portfolio") and st.session_state["num_portfolios"] > 1:
        col_to_remove = f"Portfolio {st.session_state['num_portfolios']} (%)"
        if col_to_remove in st.session_state["portfolio_table"].columns:
            st.session_state["portfolio_table"] = _ensure_range_index(
                st.session_state["portfolio_table"].drop(columns=[col_to_remove])
            )
        st.session_state["num_portfolios"] -= 1
        _bump_table_editor()
        st.rerun()

with st.form("portfolio_form"):
    add_col, add_btn_col = st.columns([4, 1])
    with add_col:
        assets_to_add = st.multiselect(
            "Adicionar ativos ao portfólio",
            options=list(asset_codes),
            format_func=lambda c: code_to_label.get(c, c),
            default=[],
            placeholder="Digite para buscar série ou fundo…",
            help="Séries e fundos do catálogo. Fundos entram na tabela só com o CNPJ.",
            key=f"pb_assets_to_add_{st.session_state['pb_add_ms_version']}",
        )
    with add_btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        add_assets = st.form_submit_button("➕ Adicionar", width="stretch")

    weight_col_config = {
        col: st.column_config.NumberColumn(col, format="%.1f")
        for col in st.session_state["portfolio_table"].columns
        if col != "Ticker"
    }
    column_config = {
        "Ticker": st.column_config.TextColumn(
            "Ativo",
            help="Código da série ou CNPJ do fundo (como na base).",
        ),
        **weight_col_config,
    }
    edited_df = st.data_editor(
        _ensure_range_index(st.session_state["portfolio_table"]),
        hide_index=True,
        column_config=column_config,
        width="stretch",
        key=_editor_key(),
        num_rows="dynamic",
    )
    run_backtest = st.form_submit_button("Rodar Backtest", type="primary")

# Só sincroniza a tabela quando o form é submetido — assim deletes entram no estado.
if add_assets or run_backtest:
    synced = _ensure_range_index(edited_df)
    # Normaliza labels legados "Nome (CNPJ)" → CNPJ
    synced["Ticker"] = synced["Ticker"].map(_resolve_ticker)
    st.session_state["portfolio_table"] = synced

if add_assets:
    st.session_state["portfolio_table"] = _append_assets_to_table(
        st.session_state["portfolio_table"],
        list(assets_to_add or []),
    )
    st.session_state["pb_add_ms_version"] += 1
    _bump_table_editor()
    st.rerun()

if run_backtest:
    if end_date < start_date:
        st.error("A data final deve ser maior ou igual à data inicial.")
        st.stop()

    df_input = st.session_state["portfolio_table"].copy()
    df_input["Ticker"] = df_input["Ticker"].map(_resolve_ticker)
    df_input = df_input[df_input["Ticker"] != ""]

    if df_input.empty:
        st.warning("Informe ao menos um ticker/CNPJ para rodar o backtest.")
        st.stop()

    weight_columns = [col for col in df_input.columns if col != "Ticker"]
    if not weight_columns:
        st.warning("Nenhum portfólio configurado.")
        st.stop()

    tickers = list(df_input["Ticker"].unique())
    benchmark_tickers = [BENCHMARK_OPTIONS[label] for label in selected_benchmarks]
    asset_series, fund_cnpjs = _split_codes(tickers)
    series_codes = list(dict.fromkeys(asset_series + benchmark_tickers))

    run_warnings: list[str] = []

    with st.spinner("Carregando dados dos ativos...", show_time=True):
        data, load_warnings = load_data(
            tuple(series_codes),
            tuple(fund_cnpjs),
            start_date_str,
            end_date_str,
        )
    run_warnings.extend(load_warnings)

    if data.empty:
        st.warning(
            "Não foi possível carregar os dados. Verifique os tickers/CNPJs informados "
            "ou tente novamente mais tarde."
        )
        for msg in run_warnings:
            st.warning(msg)
        st.stop()

    data = data.ffill(limit=1)
    if end_date_str:
        data = data.loc[:end_date_str]

    data = _align_data_columns(data, tickers + benchmark_tickers)

    available_tickers = [t for t in tickers if t in data.columns]
    missing_tickers = [t for t in tickers if t not in data.columns]
    if missing_tickers:
        missing_labels = [code_to_label.get(t, t) for t in missing_tickers]
        run_warnings.append(
            f"Sem dados para: {', '.join(missing_labels)}. "
            "Esses ativos serão ignorados no backtest."
        )

    coverage_df, limiting_code, limiting_date = _build_coverage_table(
        data, tickers, selected_benchmarks, code_to_label=code_to_label
    )

    close_prices = data[available_tickers] if available_tickers else pd.DataFrame()
    if close_prices.empty:
        st.warning("Não há dados de preços disponíveis para os ativos informados.")
        for msg in run_warnings:
            st.warning(msg)
        st.stop()

    prices = close_prices.dropna(how="all")
    if prices.empty:
        st.warning("Não há histórico suficiente para calcular o backtest.")
        st.stop()

    returns = prices.pct_change(fill_method=None)

    result_df = pd.DataFrame(index=prices.index)
    portfolio_returns_df = pd.DataFrame(index=prices.index)
    portfolio_stats: list[dict] = []

    for weight_col in weight_columns:
        portfolio_name = weight_col.replace(" (%)", "")

        try:
            weights_raw = df_input.set_index("Ticker")[weight_col].astype(float)
            if weights_raw.index.duplicated().any():
                weights_raw = weights_raw.groupby(level=0).sum()
        except Exception:
            run_warnings.append(
                f"Não foi possível ler os pesos para '{portfolio_name}'. Verifique os valores."
            )
            continue

        weights_raw = weights_raw[weights_raw != 0]
        if weights_raw.empty:
            run_warnings.append(
                f"'{portfolio_name}' não possui pesos válidos (diferentes de zero)."
            )
            continue

        is_leveraged = (weights_raw < 0).any()
        weights = weights_raw.reindex(available_tickers).fillna(0.0)
        if is_leveraged:
            weights = weights / 100
        else:
            weight_sum = weights.sum()
            if weight_sum == 0:
                run_warnings.append(f"'{portfolio_name}' ficou com soma de pesos zero.")
                continue
            weights = weights / weight_sum

        weights_matrix = pd.DataFrame(
            np.tile(weights.values, (len(returns), 1)),
            index=returns.index,
            columns=returns.columns,
        )
        valid_mask = returns.notna()
        weights_matrix = weights_matrix.where(valid_mask, 0.0)

        if not is_leveraged:
            row_sums = weights_matrix.sum(axis=1)
            weights_matrix = weights_matrix.div(row_sums.replace(0, np.nan), axis=0).fillna(0.0)

        portfolio_returns = (returns.fillna(0.0) * weights_matrix).sum(axis=1)
        portfolio_index = (1 + portfolio_returns).cumprod() * 100

        result_df[portfolio_name] = portfolio_index
        portfolio_returns_df[portfolio_name] = portfolio_returns

        try:
            portfolio_stats.append(
                _compute_stats(portfolio_index, portfolio_returns, portfolio_name, risk_free_rate)
            )
        except Exception as e:
            run_warnings.append(f"Erro ao calcular estatísticas para '{portfolio_name}': {e}")

    if result_df.empty:
        st.warning("Nenhum portfólio foi calculado com sucesso.")
        for msg in run_warnings:
            st.warning(msg)
        st.stop()

    benchmark_returns_dict: dict[str, pd.Series] = {}
    chart_df = result_df.copy()

    for label in selected_benchmarks:
        bm_ticker = BENCHMARK_OPTIONS[label]
        if bm_ticker not in data.columns:
            run_warnings.append(f"Benchmark '{label}' ({bm_ticker}) não encontrado nos dados.")
            continue

        bm_raw = data[bm_ticker].reindex(result_df.index).ffill()
        bm_first_valid = bm_raw.first_valid_index()
        if bm_first_valid is None:
            run_warnings.append(f"Benchmark '{label}' não possui dados no período selecionado.")
            continue

        bm_index = bm_raw / bm_raw[bm_first_valid] * 100
        bm_returns = bm_raw.pct_change(fill_method=None)
        benchmark_returns_dict[label] = bm_returns
        chart_df[label] = bm_index

        try:
            portfolio_stats.append(
                _compute_stats(bm_index, bm_returns, label, risk_free_rate)
            )
        except Exception as e:
            run_warnings.append(f"Erro ao calcular estatísticas do benchmark '{label}': {e}")

    st.session_state[RESULT_KEY] = {
        "chart_df": chart_df,
        "portfolio_stats": portfolio_stats,
        "portfolio_returns_df": portfolio_returns_df,
        "benchmark_returns_dict": benchmark_returns_dict,
        "coverage_df": coverage_df,
        "limiting_code": limiting_code,
        "limiting_date": limiting_date,
        "warnings": run_warnings,
    }

if RESULT_KEY in st.session_state:
    _render_results(st.session_state[RESULT_KEY])
