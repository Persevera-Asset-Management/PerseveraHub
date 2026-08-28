import streamlit as st
import pandas as pd
from datetime import datetime
from persevera_tools.data import get_series
from utils.chart_helpers import extract_codes_from_config, organize_charts_by_context, render_chart_group_with_context
from configs.pages.comite_investimentos import CHARTS_INVESTIMENTOS_BR, CHARTS_INVESTIMENTOS_US
from configs.pages.reuniao_estrategia import CHARTS_ESTRATEGIA
from utils.table import get_performance_table, style_table

st.title('Comitê de Investimentos')

CURR_CODES = {
    "usd_twi": "TWI (DM - Trade Weighted)",
    "ars_usd": "ARS",
    "aud_usd": "AUD",
    "brl_usd": "BRL",
    "cad_usd": "CAD",
    "chf_usd": "CHF",
    "clp_usd": "CLP",
    "cnh_usd": "CNH",
    "cny_usd": "CNY",
    "cop_usd": "COP",
    "dxy_index": "DXY (DM)",
    "eur_usd": "EUR",
    "gbp_usd": "GBP",
    "idr_usd": "IDR",
    "jpm_em_currency_index": "JPM EM Currency Index",
    "jpy_usd": "JPY",
    "mxn_usd": "MXN",
    "nzd_usd": "NZD",
    "zar_usd": "ZAR",
}
CURR_NON_INVERTED = ["usd_twi", "dxy_index", "jpm_em_currency_index", "eur_usd", "gbp_usd", "nzd_usd", "aud_usd"]

@st.cache_data(ttl=7200)
def load_data(codes, start_date, field='close'):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def render_context_groups(data, chart_configs, charts_by_context, context):
    groups = list(charts_by_context.get(context, {}).keys())
    if not groups:
        return

    if len(groups) == 1:
        render_chart_group_with_context(data, chart_configs, context, groups[0], charts_by_context)
        return

    group_tabs = st.tabs(groups)
    for tab, group in zip(group_tabs, groups):
        with tab:
            render_chart_group_with_context(data, chart_configs, context, group, charts_by_context)

def load_currencies(start_date):
    data_currencies = load_data(list(CURR_CODES.keys()), start_date=start_date)
    if data_currencies.empty:
        return data_currencies

    set_inverse = list(set(CURR_CODES.keys()) - set(CURR_NON_INVERTED))
    data_currencies[set_inverse] = data_currencies[set_inverse].apply(lambda x: x**(-1))
    return data_currencies.rename(columns=CURR_CODES)

def render_mercados(data, data_valuation, data_currencies, chart_configs):
    charts_by_context = organize_charts_by_context(chart_configs)
    tabs_mercados = st.tabs(["Renda Fixa", "Moedas", "Commodities", "Renda Variável"])

    with tabs_mercados[0]:
        renda_fixa_tabs = st.tabs(["Títulos Públicos (US)", "Crédito Privado (US)", "Títulos Públicos (BR)", "Crédito Privado (BR)"])
        with renda_fixa_tabs[0]:
            render_chart_group_with_context(data, chart_configs, "Renda Fixa", "Títulos Públicos (US)", charts_by_context)
        with renda_fixa_tabs[1]:
            render_chart_group_with_context(data, chart_configs, "Renda Fixa", "Crédito Privado (US)", charts_by_context)
        with renda_fixa_tabs[2]:
            render_chart_group_with_context(data, chart_configs, "Renda Fixa", "Títulos Públicos (BR)", charts_by_context)

    with tabs_mercados[1]:
        render_chart_group_with_context(data, chart_configs, "Moedas", "Performance", charts_by_context)
        if not data_currencies.empty:
            st.dataframe(
                style_table(
                    get_performance_table(data_currencies).drop(columns=['1d']),
                    numeric_cols_format_as_float=['mtd', 'ytd', '1m', '3m', '6m', '12m', '24m', '36m'],
                    highlight_row_by_column='code',
                    highlight_row_if_value_equals='BRL',
                    highlight_color='lightblue'
                ),
                width='stretch',
                hide_index=True
            )
        render_chart_group_with_context(data, chart_configs, "Moedas", "Reservas Internacionais", charts_by_context)

    with tabs_mercados[2]:
        commodities_context = charts_by_context.get("Commodities", {})
        render_chart_group_with_context(data, chart_configs, "Commodities", "Commodities", charts_by_context)
        if "Commodities" in commodities_context:
            commodities_codes = {
                col: name
                for entry in commodities_context["Commodities"]
                for col, name in zip(entry[1]["chart_config"]["columns"], entry[1]["chart_config"]["names"])
                if col in data.columns
            }
            if commodities_codes:
                data_commodities = data[list(commodities_codes.keys())].rename(columns=commodities_codes)
                st.dataframe(
                    style_table(
                        get_performance_table(data_commodities).drop(columns=['1d']),
                        numeric_cols_format_as_float=['mtd', 'ytd', '1m', '3m', '6m', '12m', '24m', '36m'],
                    ),
                    width='stretch',
                    hide_index=True
                )

    with tabs_mercados[3]:
        if data_valuation.empty:
            st.warning("Não foi possível carregar os dados de valuation.")
        else:
            render_chart_group_with_context(data_valuation, chart_configs, "Renda Variável", "Valuation", charts_by_context)

CHARTS_BY_REGION = {
    "Brasil": CHARTS_INVESTIMENTOS_BR,
    "Estados Unidos": CHARTS_INVESTIMENTOS_US,
}

with st.sidebar:
    st.header("Parâmetros")
    selected_region = st.radio("Região", list(CHARTS_BY_REGION.keys()), index=0, horizontal=True)
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime(2010, 1, 1), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

chart_configs = CHARTS_BY_REGION[selected_region]
chart_configs_mercados = CHARTS_ESTRATEGIA
CODES = list(dict.fromkeys(
    extract_codes_from_config(chart_configs) + extract_codes_from_config(chart_configs_mercados)
))

with st.spinner("Carregando dados...", show_time=True):
    data = load_data(CODES, start_date=start_date_str)

with st.spinner("Carregando dados de valuation...", show_time=True):
    data_valuation = load_data(extract_codes_from_config(chart_configs_mercados), start_date=start_date_str, field='price_to_earnings_fwd')

with st.spinner("Carregando cotações das moedas...", show_time=True):
    data_currencies = load_currencies(start_date_str)

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    charts_by_context = organize_charts_by_context(chart_configs)

    tabs = st.tabs(["Cockpit", "Temas", "Mercados", "Micro", "Teses", "Carteiras"])

    with tabs[0]:   # Tab 1: Cockpit
        pass

    with tabs[1]:   # Tab 2: Temas
        temas = ["Crescimento", "Inflação", "Fiscal", "Política Monetária", "Liquidez", "Posicionamento", "Oferta e Demanda"]
        tabs_temas = st.tabs(temas)

        for tab, tema in zip(tabs_temas, temas):
            with tab:
                render_context_groups(data, chart_configs, charts_by_context, tema)

    with tabs[2]:   # Tab 3: Mercados
        render_mercados(data, data_valuation, data_currencies, chart_configs_mercados)

    with tabs[3]:   # Tab 4: Micro
        pass

    with tabs[4]:   # Tab 5: Teses
        pass

    with tabs[5]:   # Tab 6: Carteiras
        pass
