import pandas as pd

import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from utils.data_transformers import apply_transformations

from persevera_tools.data import get_series


st.set_page_config(
    page_title="B3 · Fluxo de Investidores | Persevera",
    page_icon="🪙",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('B3 · Fluxo de Investidores')

FLUXO_DE_INVESTIMENTOS = {
    "br_b3_financial_institutions_net": "Inst. Financeiras",
    "br_b3_foreign_investors_net": "Investidores Estrangeiros",
    "br_b3_individual_investors_net": "Pessoa Física",
    "br_b3_institutional_investors_net": "Investidores Institucionais",
    "br_b3_others_net": "Outros",
}

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


def format_currency(value: float) -> str:
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e6:
        return f"{sign}R$ {abs_val / 1e6:.1f}B"
    if abs_val >= 1e3:
        return f"{sign}R$ {abs_val / 1e3:.1f}M"
    return f"{sign}R$ {abs_val:,.0f}"


with st.spinner("Carregando dados...", show_time=True):
    data = load_data(list(FLUXO_DE_INVESTIMENTOS.keys()), start_date='2015-01-01')

if data.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    latest_date = data.index.max()

    _period_options = {
        "Ano Atual (YTD)": latest_date.replace(month=1, day=1),
        "30 Dias":         latest_date - pd.DateOffset(days=30),
        "6 Meses":         latest_date - pd.DateOffset(months=6),
        "1 Ano":           latest_date - pd.DateOffset(years=1),
        "2 Anos":          latest_date - pd.DateOffset(years=2),
    }

    with st.sidebar:
        st.header("Parâmetros")
        selected_period = st.radio("Período (Saldo Diário):", list(_period_options.keys()))

    period_start = _period_options[selected_period]

    st.markdown("Data mais recente: **{0:%Y-%m-%d}**".format(latest_date))

    # --- KPI Cards ---
    st.subheader("Indicadores Chave")

    monthly_flow = data.groupby(pd.Grouper(level=0, freq='ME')).sum().iloc[-1]
    yearly_flow = data.groupby(pd.Grouper(level=0, freq='YE')).sum().iloc[-1]

    kpi_cols = st.columns(len(FLUXO_DE_INVESTIMENTOS))
    for i, (code, name) in enumerate(FLUXO_DE_INVESTIMENTOS.items()):
        monthly_val = monthly_flow.get(code, 0.0)
        yearly_val = yearly_flow.get(code, 0.0)
        with kpi_cols[i]:
            st.metric(
                label=name,
                value=f"{format_currency(monthly_val)} no mês",
                delta=f"{format_currency(yearly_val)} no ano",
                delta_color="normal",
            )

    # --- Charts ---
    tabs = st.tabs(list(FLUXO_DE_INVESTIMENTOS.values()))
    for tab, (code, name) in zip(tabs, FLUXO_DE_INVESTIMENTOS.items()):
        with tab:
            cols = st.columns(2)
            with cols[0]:
                group_data = data[code].loc[period_start:].to_frame('Fluxo Diário')
                group_data['Fluxo Acumulado'] = group_data['Fluxo Diário'].expanding().sum()
                chart_options = create_chart(
                    data=group_data[['Fluxo Acumulado', 'Fluxo Diário']],
                    columns=('Fluxo Acumulado', 'Fluxo Diário'),
                    chart_type='dual_axis_line_column',
                    title=f'Saldo Diário: {name}',
                    y_axis_title=("Fluxo Acumulado (R$)", "Fluxo Diário (R$)"),
                    decimal_precision=0,
                )
                hct.streamlit_highcharts(chart_options)

            with cols[1]:
                by_year_data = apply_transformations(
                    data,
                    [{"type": "accumulated_by_year", "column": code, "frequency": "D"}],
                )
                by_year_data = by_year_data.rename(
                    columns=lambda c: c.replace(f"{code}_", "")
                )
                by_year_chart_options = create_chart(
                    data=by_year_data,
                    columns=by_year_data.columns.tolist(),
                    names=by_year_data.columns.tolist(),
                    chart_type='spline',
                    title=f'Acumulado por Ano: {name}',
                    y_axis_title="Fluxo Acumulado no Ano (R$)",
                    decimal_precision=0,
                )
                hct.streamlit_highcharts(by_year_chart_options)
