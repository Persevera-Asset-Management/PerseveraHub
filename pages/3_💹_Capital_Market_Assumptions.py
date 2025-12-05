import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from persevera_tools.data import get_series
from configs.pages.capital_market_assumptions import CAPITAL_MARKET_ASSUMPTIONS
from utils.table import get_performance_table

st.set_page_config(
    page_title="Capital Market Assumptions | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Capital Market Assumptions")

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        df = get_series(codes, start_date=start_date, field='close')
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def _weekly_returns(df):
    df = df.resample('W').last()
    return df.pct_change(fill_method=None)

def calculate_returns(df, annualized=True):
    weekly_returns = _weekly_returns(df)
    returns = weekly_returns.mean()
    if annualized:
        returns = (1 + returns) ** 52 - 1
    return returns * 100

def calculate_volatility(df, annualized=True):
    weekly_returns = _weekly_returns(df)
    volatility = weekly_returns.std()
    if annualized:
        volatility = volatility * np.sqrt(52)
    return volatility * 100

def calculate_skewness(df):
    return _weekly_returns(df).skew()

def calculate_kurtosis(df):
    return _weekly_returns(df).kurt()

codes = list(CAPITAL_MARKET_ASSUMPTIONS.keys()) 

years = 15
with st.spinner(f"Carregando {years} anos de dados..."):
    start_date = pd.to_datetime(date.today() - timedelta(days=years*365))
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    data = load_data(codes, start_date_str)

performance_table = get_performance_table(data)
returns = calculate_returns(data)
volatility = calculate_volatility(data)
skewness = calculate_skewness(data)
kurtosis = calculate_kurtosis(data)
stats = pd.DataFrame({
    'Retorno': returns,
    'Volatilidade': volatility,
    'Assimetria': skewness,
    'Curtose': kurtosis,
})

stats.index, performance_table.index = list(CAPITAL_MARKET_ASSUMPTIONS.values()), list(CAPITAL_MARKET_ASSUMPTIONS.values())
stats.index.name, performance_table.index.name = 'Classe de Ativos', 'Classe de Ativos'
performance_table.drop(columns=['code'], inplace=True)

st.markdown("##### Performance Acumulada")
st.dataframe(
    style_table(
        performance_table,
        numeric_cols_format_as_float=list(performance_table.columns),
    )
)

st.markdown("##### Longo Prazo")
st.dataframe(
    style_table(
        stats,
        numeric_cols_format_as_float=['Retorno', 'Volatilidade', 'Assimetria', 'Curtose'],
    )
)

cols = st.columns(2)

with cols[0]:
    chart_stats = create_chart(
        data=stats.reset_index(),
        columns=['Retorno'],
        x_column='Volatilidade',
        chart_type='scatter',
        point_name_column='Classe de Ativos',
        title="Retorno vs Volatilidade",
        y_axis_title="Retorno (%)",
        x_axis_title="Volatilidade (%)",
        show_legend=False,
        zoom_type='xy',
        show_point_name_labels=True,
        tooltip_point_format=(
            '<b>{point.name}</b><br/>'
            'Risco: {point.x:.2f}%<br/>'
            'Retorno: {point.y:.2f}%'
        ),
    )
    hct.streamlit_highcharts(chart_stats)

with cols[1]:
    chart_stats = create_chart(
        data=stats.reset_index(),
        columns=['Assimetria'],
        x_column='Curtose',
        chart_type='scatter',
        point_name_column='Classe de Ativos',
        title="Assimetria vs Curtose",
        y_axis_title="Assimetria",
        x_axis_title="Curtose",
        show_legend=False,
        zoom_type='xy',
        show_point_name_labels=True,
        tooltip_point_format=(
            '<b>{point.name}</b><br/>'
            'Curtose: {point.x:.2f}<br/>'
            'Assimetria: {point.y:.2f}'
        ),
    )
    hct.streamlit_highcharts(chart_stats)