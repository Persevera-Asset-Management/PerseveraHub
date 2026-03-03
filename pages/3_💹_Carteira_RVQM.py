import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table, get_performance_table
from utils.auth import check_authentication
from persevera_tools.data import get_descriptors, get_series
from services.position_service import load_equities_portfolio


st.set_page_config(
    page_title="Carteira RVQM | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Carteira RVQM")

@st.cache_data(ttl=3600)
def load_data(codes, start_date, field):
    try:
        if isinstance(field, list):
            return get_descriptors(codes, start_date=start_date, descriptors=field)
        else:
            return get_descriptors(codes, start_date=start_date, descriptors=[field])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_indicators(codes, start_date):
    try:
        return get_series(codes, start_date=start_date)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


with st.spinner("Carregando composição da carteira..."):
    equities_portfolio = load_equities_portfolio()
    securities_list = list(equities_portfolio['code'].unique())

with st.spinner("Carregando preços das ações selecionadas..."):
    prices = load_data(securities_list, start_date=equities_portfolio['date'].min(), field=['price_close'])

with st.spinner("Carregando indicadores..."):
    indicators = load_indicators(['br_ibovespa', 'br_smll', 'br_cdi_index'], start_date=equities_portfolio['date'].min())

if prices.empty or len(securities_list) == 0:
    st.warning("Nenhum dado disponível para exibir.")
else:
    weights_df = equities_portfolio.pivot(index='date', columns='code', values='weight')
    weights_df = weights_df.div(weights_df.sum(axis=1), axis=0).fillna(0)
    weights_df = weights_df.reindex(prices.index)
    weights_df = weights_df.ffill()

    with st.expander("Histórico de Alocações", expanded=False):
        weights_history_table = weights_df.replace(0, np.nan).mul(100)
        weights_history_table.index = weights_history_table.index.strftime('%Y-%m-%d')
        st.dataframe(
            style_table(
                weights_history_table,
                percent_cols=weights_df.columns.tolist()
            ),
            hide_index=False
        )

    returns_equities_portfolio = weights_df.mul(prices.pct_change(), axis=0).sum(axis=1)
    returns_df = pd.concat([returns_equities_portfolio, indicators.pct_change().fillna(0)], axis=1)
    returns_df.columns = ['Carteira', 'Ibovespa', 'SMLL', 'CDI']
    cumulative_returns = (1 + returns_df).cumprod() - 1

    # Date Range Selection
    min_date_val = cumulative_returns.index.min().date()
    max_date_val = cumulative_returns.index.max().date()

    if 'start_date' not in st.session_state:
        st.session_state.start_date = pd.to_datetime(min_date_val)
    else:
        if not isinstance(st.session_state.start_date, pd.Timestamp):
            st.session_state.start_date = pd.to_datetime(st.session_state.start_date)
        if st.session_state.start_date.date() < min_date_val:
            st.session_state.start_date = pd.to_datetime(min_date_val)
        elif st.session_state.start_date.date() > max_date_val:
            st.session_state.start_date = pd.to_datetime(max_date_val)

    if 'end_date' not in st.session_state:
        st.session_state.end_date = pd.to_datetime(max_date_val)
    else:
        if not isinstance(st.session_state.end_date, pd.Timestamp):
            st.session_state.end_date = pd.to_datetime(st.session_state.end_date)
        if st.session_state.end_date.date() > max_date_val:
            st.session_state.end_date = pd.to_datetime(max_date_val)
        elif st.session_state.end_date.date() < min_date_val:
            st.session_state.end_date = pd.to_datetime(min_date_val)

    if st.session_state.start_date > st.session_state.end_date:
        st.session_state.start_date = st.session_state.end_date

    cols_date = st.columns(2)
    with cols_date[0]:
        start_date_input = st.date_input(
            "Data Inicial",
            format="DD/MM/YYYY",
            value=st.session_state.start_date.date(),
            min_value=min_date_val,
            max_value=max_date_val,
            key='start_date_picker'
        )
    with cols_date[1]:
        end_date_input = st.date_input(
            "Data Final",
            format="DD/MM/YYYY",
            value=st.session_state.end_date.date(),
            min_value=min_date_val,
            max_value=max_date_val,
            key='end_date_picker'
        )

    st.session_state.start_date = pd.to_datetime(start_date_input)
    st.session_state.end_date = pd.to_datetime(end_date_input)

    if st.session_state.start_date > st.session_state.end_date:
        st.warning("Data inicial deve ser anterior à data final.")
        st.stop()

    performance_table = get_performance_table(
        series=cumulative_returns.add(1)
    )

    if not performance_table.empty:
        st.dataframe(
            style_table(
                performance_table.set_index('index'),
                numeric_cols_format_as_float=['mtd', 'ytd', '3m', '6m', '12m', '24m', '36m'],
                highlight_quartile=['mtd', 'ytd', '3m', '6m', '12m', '24m', '36m'],
                highlight_color='lightblue'
            ),
            use_container_width=True
        )

    col_1 = st.columns(2)
    with col_1[0]:
        chart_performance_options = create_chart(
            data=cumulative_returns * 100,
            columns=["Carteira", "Ibovespa", "SMLL", "CDI"],
            names=["Carteira", "Ibovespa", "SMLL", "CDI"],
            chart_type='line',
            title="Performance Acumulada",
            y_axis_title="Retorno (%)",
            decimal_precision=2
        )
        hct.streamlit_highcharts(chart_performance_options)

    with col_1[1]:
        chart_daily_returns_options = create_chart(
            data=returns_df * 10000,
            columns=["Carteira", "Ibovespa"],
            names=["Carteira", "Ibovespa"],
            chart_type='column',
            title="Retorno Diário",
            y_axis_title="Retorno (bps)",
            decimal_precision=0
        )
        hct.streamlit_highcharts(chart_daily_returns_options)
