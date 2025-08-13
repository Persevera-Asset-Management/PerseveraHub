import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import os
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.table import style_table
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from configs.pages.pilares_de_alocacao_bonds import INDICADORES

st.set_page_config(
    page_title="Pilares de Alocação (Bonds) | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title('Pilares de Alocação (Bonds)')

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", min_value=datetime(1990, 1, 1), value=datetime.today().date() - timedelta(days=365*25), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')
    selected_codes = st.multiselect("Indicadores selecionados", options=list(INDICADORES.values()), default=list(INDICADORES.values()))

@st.cache_data(ttl=3600)
def load_data(codes, start_date, field='close'):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_performance_table(df, time_frames=[5, 10, 15, 20, 25], annualize=True):
    df = df.ffill()

    def get_relative_return(years):
        start_date_calc = df.index[-1] - relativedelta(years=years)
        date_diff = (df.index[-1] - start_date_calc).days
        period_df = df.loc[start_date_calc:]
        if len(period_df) > 1:
            return (df.iloc[-1] / period_df.iloc[0]) ** (365/date_diff) - 1 if annualize else (df.iloc[-1] / period_df.iloc[0]) - 1
        return pd.Series(np.nan, index=df.columns)
    
    returns = {}
    for code in df.columns:
        for years in time_frames:
            ret = get_relative_return(years)
            returns[f'{years}Y'] = ret * 100

    return pd.DataFrame(returns)

# Chart configurations
codes = [{v: k for k, v in INDICADORES.items()}[code] for code in selected_codes]

data = load_data(codes, start_date=start_date_str)
data.dropna(thresh=data.columns.size - 2, inplace=True)

if 'us_fed_funds_effective_rate' in data.columns:
    fed_annual_rate = data['us_fed_funds_effective_rate'].ffill().bfill() / 100.0
    delta_days = data.index.to_series().diff().dt.days.fillna(0).astype(float)
    daily_factors = (1.0 + fed_annual_rate) ** (delta_days / 365.0)
    data['us_fed_funds_effective_rate'] = daily_factors.cumprod()

returns_total = get_performance_table(data, annualize=False)
returns_total = returns_total.rename(index=INDICADORES)

returns_annualized = get_performance_table(data, annualize=True)
returns_annualized = returns_annualized.rename(index=INDICADORES)

st.subheader("Performance (USD)")
cols_1 = st.columns(2)
with cols_1[0]:
    st.dataframe(style_table(returns_total, percent_cols=list(returns_total.columns), highlight_min_max_cols=list(returns_total.columns)))
with cols_1[1]:
    st.dataframe(style_table(returns_annualized, percent_cols=list(returns_annualized.columns), highlight_min_max_cols=list(returns_annualized.columns)))

cols_2 = st.columns(2)
with cols_2[0]:
    perf_acumulada_chart_options = create_chart(
        data=returns_total.T,
        columns=list(returns_total.index),
        names=list(returns_total.index),
        chart_type='column',
        title="Performance Acumulada",
        y_axis_title="Retornos (%)"
    )
    hct.streamlit_highcharts(perf_acumulada_chart_options)

with cols_2[1]:
    perf_anualizada_chart_options = create_chart(
        data=returns_annualized.T,
        columns=list(returns_annualized.index),
        names=list(returns_annualized.index),
        chart_type='column',
        title="Performance Anualizada",
        y_axis_title="Retornos (%)"
    )
    hct.streamlit_highcharts(perf_anualizada_chart_options)

st.subheader("Simulação de Carteira")
selected_codes_simulation = st.multiselect(label="Selecione dois grupos de bonds:", options=list(INDICADORES.values()), max_selections=2)
btn_simular = st.button("Simular")

if btn_simular:
    with st.spinner("Simulando carteira..."):
        if len(selected_codes_simulation) != 2:
            st.warning("Selecione exatamente dois grupos para simular.")
        else:
            codes_simulation = [{v: k for k, v in INDICADORES.items()}[code] for code in selected_codes_simulation]
            code_1, code_2 = codes_simulation
            name_1 = INDICADORES.get(code_1, code_1)
            name_2 = INDICADORES.get(code_2, code_2)

            # Usar dados preenchidos e calcular retornos diários
            base_df = data[[code_1, code_2]].ffill().bfill()
            daily_returns = base_df.pct_change().fillna(0.0)

            # Combinações de 0% a 100% em passos de 10%
            weights = np.linspace(0.0, 1.0, 11)
            portfolios_index = pd.DataFrame(index=daily_returns.index)

            for w in weights:
                port_ret = w * daily_returns[code_1] + (1.0 - w) * daily_returns[code_2]
                port_idx = (1.0 + port_ret).cumprod()
                col_label = f"{int(round(w*100))}% {name_1} + {int(round((1.0-w)*100))}% {name_2}"
                portfolios_index[col_label] = port_idx

            perf_simulacao_chart_options = create_chart(
                data=portfolios_index.sub(1).mul(100),
                columns=list(portfolios_index.columns),
                names=list(portfolios_index.columns),
                chart_type='line',
                legend_layout='vertical',
                title="Simulação de Carteiras",
                y_axis_title="Retornos (%)"
            )
            hct.streamlit_highcharts(perf_simulacao_chart_options)