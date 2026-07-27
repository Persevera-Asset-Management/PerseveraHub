from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from services.position_service import load_funds_catalog, load_indicator_catalog
from persevera_tools.data import get_funds_data, get_series


FUND_FIELDS = [
    "fund_nav",
    "fund_total_equity",
    "fund_total_value",
    "fund_inflows",
    "fund_outflows",
    "fund_holders",
]

INDICATOR_FIELDS = [
    "close",
    "mean",
    "median",
    "weighted_mean",
    "earnings_per_share_fwd",
    "earnings_per_share_ltm",
    "price_to_earnings_fwd",
    "pct_members_above_50dma",
    "pct_members_above_100dma",
    "pct_members_above_150dma",
    "pct_members_above_200dma",
    "count_above_mean",
    "count_under_mean",
    "volume_above_mean",
    "volume_under_mean",
    "put_call_ratio",
    "weight_cta_simplify",
    "weight_cta_invesco",
    "weight_cta_kraneshares",
    "cta_vol_contribution",
]

st.title("Extração de Dados")


def _set_date_preset_years(years: int) -> None:
    st.session_state.extract_end_date = date.today()
    st.session_state.extract_start_date = date.today() - timedelta(days=365 * years)


def _set_date_preset_ytd() -> None:
    st.session_state.extract_end_date = date.today()
    st.session_state.extract_start_date = date(date.today().year, 1, 1)


@st.cache_data(ttl=3600)
def load_indicators_raw(
    codes: tuple[str, ...],
    start_date: str,
    end_date: str,
    fields: tuple[str, ...],
) -> pd.DataFrame:
    df = get_series(
        list(codes),
        start_date=start_date,
        end_date=end_date,
        field=list(fields) if len(fields) > 1 else fields[0],
    )
    if isinstance(df, pd.Series):
        name = codes[0] if len(codes) == 1 else df.name
        df = df.to_frame(name=name)
    return df


@st.cache_data(ttl=3600)
def load_funds_raw(
    cnpjs: tuple[str, ...],
    start_date: str,
    end_date: str,
    fields: tuple[str, ...],
) -> pd.DataFrame:
    return get_funds_data(
        cnpjs=list(cnpjs),
        start_date=start_date,
        end_date=end_date,
        fields=list(fields),
    )


def render_raw_table(df: pd.DataFrame, filename_prefix: str) -> None:
    if df is None or df.empty:
        st.warning("Nenhum dado retornado para os parâmetros selecionados.")
        return

    display_df = df
    st.success(f"{len(display_df):,} linhas × {len(display_df.columns)} colunas".replace(",", "."))
    st.dataframe(display_df, width="stretch", hide_index=False)


with st.spinner("Carregando catálogos...", show_time=True):
    indicator_codes = load_indicator_catalog()
    funds_catalog = load_funds_catalog()

with st.sidebar:
    st.header("Parâmetros")

    data_type = st.radio(
        "Fonte",
        ("Indicadores", "Fundos"),
        index=1,
        help="Indicadores usa get_series; Fundos usa get_funds_data.",
    )

    st.caption("Atalhos de período")
    p1, p2, p3 = st.columns(3)
    p1.button("1A", on_click=_set_date_preset_years, args=(1,), width="stretch")
    p2.button("3A", on_click=_set_date_preset_years, args=(3,), width="stretch")
    p3.button("5A", on_click=_set_date_preset_years, args=(5,), width="stretch")
    p4, p5, p6 = st.columns(3)
    p4.button("10A", on_click=_set_date_preset_years, args=(10,), width="stretch")
    p5.button("YTD", on_click=_set_date_preset_ytd, width="stretch")
    p6.button("Máx", on_click=_set_date_preset_years, args=(30,), width="stretch")

    start_date_input = st.date_input(
        "Data inicial",
        value=date.today() - timedelta(days=365 * 5),
        min_value=datetime(1900, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
        key="extract_start_date",
    )
    end_date_input = st.date_input(
        "Data final",
        value=date.today(),
        min_value=datetime(1900, 1, 1),
        max_value=date.today(),
        format="DD/MM/YYYY",
        key="extract_end_date",
    )

    if data_type == "Indicadores":
        selected_codes = st.multiselect(
            "Códigos",
            options=indicator_codes,
            placeholder="Digite para buscar um código…",
            help="Séries da tabela de indicadores.",
        )
        selected_fields = st.multiselect(
            "Campos",
            options=INDICATOR_FIELDS,
            default=["close"],
            help="Um ou mais fields a extrair via get_series.",
        )
        run_extract = st.button("Extrair dados", type="primary", width="stretch")
    else:
        if funds_catalog.empty:
            fund_options = []
            fund_labels = {}
        else:
            fund_options = funds_catalog["Name"].astype(str).tolist()
            if "Nome Completo" in funds_catalog.columns:
                fund_labels = {
                    str(row["Name"]): f"{row['Nome Completo']} ({row['Name']})"
                    for _, row in funds_catalog.iterrows()
                }
            else:
                fund_labels = {c: c for c in fund_options}

        selected_cnpjs = st.multiselect(
            "Fundos (CNPJ)",
            options=fund_options,
            format_func=lambda c: fund_labels.get(c, c),
            placeholder="Digite para buscar um fundo…",
            help="CNPJs disponíveis no catálogo de ativos.",
        )
        selected_fund_fields = st.multiselect(
            "Campos",
            options=FUND_FIELDS,
            default=["fund_nav"],
            help="Campos disponíveis em get_funds_data.",
        )
        run_extract = st.button("Extrair dados", type="primary", width="stretch")

start_date_str = start_date_input.strftime("%Y-%m-%d")
end_date_str = end_date_input.strftime("%Y-%m-%d")

if start_date_input > end_date_input:
    st.error("A data de início não pode ser posterior à data de fim.")
    st.stop()

if data_type == "Indicadores":
    if not run_extract:
        st.info("Selecione códigos e campos no sidebar e clique em **Extrair dados**.")
        st.stop()
    if not selected_codes:
        st.warning("Selecione ao menos um código de indicador.")
        st.stop()
    if not selected_fields:
        st.warning("Selecione ao menos um campo.")
        st.stop()

    with st.spinner("Extraindo indicadores...", show_time=True):
        try:
            raw = load_indicators_raw(
                tuple(selected_codes),
                start_date_str,
                end_date_str,
                tuple(selected_fields),
            )
        except Exception as e:
            st.error(f"Erro ao chamar get_series: {e}")
            st.stop()

    st.subheader("Indicadores · dados brutos")
    render_raw_table(raw, "indicadores")

else:
    if not run_extract:
        st.info("Selecione fundos e campos no sidebar e clique em **Extrair dados**.")
        st.stop()
    if not selected_cnpjs:
        st.warning("Selecione ao menos um fundo.")
        st.stop()
    if not selected_fund_fields:
        st.warning("Selecione ao menos um campo.")
        st.stop()

    with st.spinner("Extraindo dados de fundos...", show_time=True):
        try:
            raw = load_funds_raw(
                tuple(selected_cnpjs),
                start_date_str,
                end_date_str,
                tuple(selected_fund_fields),
            )
        except Exception as e:
            st.error(f"Erro ao chamar get_funds_data: {e}")
            st.stop()

    render_raw_table(raw, "fundos")
