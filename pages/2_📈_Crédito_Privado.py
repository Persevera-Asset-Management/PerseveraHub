import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from persevera_tools.data.private_credit import get_emissions, calculate_spread
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
import streamlit_highcharts as hct
import numpy as np

st.set_page_config(
    page_title="Crédito Privado | Persevera",
    page_icon="🗓️",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

# Common meetings header with navigation links
st.title("Crédito Privado")

@st.cache_data(ttl=3600)
def load_data(start_date):
    try:
        return get_emissions(start_date=start_date, selected_fields=['code', 'empresa', 'data_emissao', 'data_vencimento', 'indice', 'juros_criterio_novo_taxa', 'valor_nominal_na_emissao', 'quantidade_emitida'])
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.sidebar:
    st.header("Parâmetros")
    start_date = st.date_input("Data Inicial", datetime.now() - timedelta(days=4*365), format="DD/MM/YYYY")
    start_date_str = start_date.strftime('%Y-%m-%d')

# Load data with progress indicator
with st.spinner("Carregando dados de mercado..."):
    data = load_data(start_date=start_date_str)
    spread = calculate_spread("DI", start_date=start_date_str, calculate_distribution=True)

if data.empty or spread.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:
    # Create tabs for different regions
    tabs = st.tabs(["Emissões", "Spread"])
    
    # Tab 1: Emissões
    with tabs[0]:
        st.header("Emissões")
        df_emissions = data.reset_index().groupby([pd.Grouper(key="data_emissao", freq="MS"), 'indice'])['volume_emissao'].sum().reset_index().pivot(
            index='data_emissao', columns='indice', values='volume_emissao'
        )

        chart_emissions_options = create_chart(
            data=df_emissions,
            columns=df_emissions.columns.tolist(),
            names=df_emissions.columns.tolist(),
            chart_type='column',
            stacking='normal',
            title="Emissões de Debentures",
            y_axis_title="Volume Emitido (R$)",
            decimal_precision=0
        )
        hct.streamlit_highcharts(chart_emissions_options)

        st.subheader("Detalhamento das Emissões Registradas")
        st.dataframe(
            style_table(
                data.sort_index(ascending=False).reset_index(),
                column_names=['Data de Emissão', 'Ticker', 'Nome', 'Data de Vencimento', 'Índice', 'Juros (%)', 'Valor Nominal na Emissão', 'Quantidade Emitida', 'Volume Emitido'],
                date_cols=['Data de Emissão', 'Data de Vencimento'],
                percent_cols=['Juros (%)'],
                currency_cols=['Valor Nominal na Emissão', 'Quantidade Emitida', 'Volume Emitido'],
            ),
            hide_index=True
        )

    # Tab 2: Spread
    with tabs[1]:
        st.header("CDI+")

        row_1 = st.columns(2)
        with row_1[0]:
            chart_spread = create_chart(
                data=spread,
                columns=["median", "mean", "weighted_mean"],
                names=["Mediana", "Média", "Média Ponderada"],
                chart_type='line',
                title="Evolução do Spread CDI+",
                y_axis_title="Spread (%)",
                decimal_precision=3
            )
            hct.streamlit_highcharts(chart_spread)

        with row_1[1]:
            chart_distribution = create_chart(
                data=spread,
                columns=['count_yield_0_50bp', 'count_yield_50_75bp', 'count_yield_75_100bp',
                         'count_yield_100_150bp', 'count_yield_150_250bp',
                         'count_yield_above_250bp'],
                names=["0-50bp", "50-75bp", "75-100bp", "100-150bp", "150-250bp", "Acima de 250bp"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ por Intervalo",
                y_axis_title="Percentual de Ativos",
                decimal_precision=0
            )
            hct.streamlit_highcharts(chart_distribution)
    
        row_2 = st.columns(2)
        with row_2[0]:
            chart_average_count = create_chart(
                data=spread,
                columns=['count_above_mean', 'count_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ (Contagem de Ativos)",
                y_axis_title="Percentual de Ativos",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_count)

        with row_2[1]:
            chart_average_volume = create_chart(
                data=spread,
                columns=['volume_above_mean', 'volume_under_mean'],
                names=["Acima da Média", "Abaixo da Média"],
                chart_type='area',
                stacking='percent',
                title="Distribuição do Spread CDI+ (Volume Emitido)",
                y_axis_title="Percentual de Ativos",
                decimal_precision=0,
            )
            hct.streamlit_highcharts(chart_average_volume)
