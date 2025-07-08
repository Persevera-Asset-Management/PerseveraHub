import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.data import get_descriptors, get_securities_by_exchange
from persevera_tools.quant_research.matrix import corr_to_cov, find_nearest_corr
from configs.pages.carteira_rv import ACOES_RV
from utils.auth import check_authentication

st.set_page_config(
    page_title="Carteira de RV | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Carteira de RV")

@st.cache_data(ttl=3600)
def load_active_securities():
    try:
        codes = get_securities_by_exchange(exchange='BZ')
        return list(codes.values())
    except Exception as e:
        st.error(f"Error loading active securities: {str(e)}")
        return []

def create_allocation_table(data):
    table = data.swaplevel(axis=1)['beta'].iloc[-1].to_frame("Bloomberg Beta")
    table['1 / Beta'] = 1.0 / table['Bloomberg Beta']
    table['Equal Weight (%)'] = 1.0 / len(table) * 100.0
    table['Final Weight (%)'] = table['1 / Beta'] / table['1 / Beta'].sum() * 100.0
    return table

def calculate_portfolio_volatility(weights, returns):
    weights_decimal = weights.to_numpy() / 100.0
    cov_matrix_annual = returns.cov() * 252
    portfolio_variance = np.dot(weights_decimal.T, np.dot(cov_matrix_annual, weights_decimal))
    return np.sqrt(portfolio_variance)

active_securities = load_active_securities()

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_stocks = st.multiselect("Ações selecionadas", options=active_securities, default=ACOES_RV)

data = get_descriptors(selected_stocks, start_date=datetime.now() - timedelta(days=365), descriptors=['price_close', 'beta'])
data = data.swaplevel(axis=1)

if data.empty or len(selected_stocks) == 0:
    st.warning("Por favor, selecione ao menos uma ação para continuar.")
else:
    returns = data['price_close'].pct_change().dropna()

    tabs = st.tabs(["Composição Atual", "Track Record"])
    
    # Composição Atual
    with tabs[0]:
        st.subheader("Composição Atual")

        # Inicializa a tabela de alocação
        betas_df = data['beta'].iloc[-1].to_frame("Bloomberg Beta")

        # Permite a edição dos Betas
        with st.expander("Editar Betas", expanded=False):
            st.caption("Você pode editar os valores de Beta na tabela abaixo. As outras colunas serão recalculadas automaticamente.")
            edited_betas = st.data_editor(
                betas_df,
                column_config={
                    "Bloomberg Beta": st.column_config.NumberColumn(
                        "Bloomberg Beta",
                        help="O beta do ativo.",
                        format="%.4f",
                    )
                },
                use_container_width=True
            )

        # Recalcula a tabela de alocação com base nos betas (editados ou não)
        allocation_table = edited_betas.copy()
        allocation_table['1 / Beta'] = 1.0 / allocation_table['Bloomberg Beta']
        allocation_table['Equal Weight (%)'] = 1.0 / len(allocation_table) * 100.0
        allocation_table['Final Weight (%)'] = allocation_table['1 / Beta'] / allocation_table['1 / Beta'].sum() * 100.0
        
        st.dataframe(style_table(allocation_table, numeric_cols_format_as_float=['Bloomberg Beta', '1 / Beta'], percent_cols=['Equal Weight (%)', 'Final Weight (%)']))
        
        st.subheader("Estatísticas")
        portfolio_volatility_inv_beta = calculate_portfolio_volatility(allocation_table['Final Weight (%)'], returns)
        portfolio_volatility_equal_weight = calculate_portfolio_volatility(allocation_table['Equal Weight (%)'], returns)
        
        col_1 = st.columns(2)
        with col_1[0]:
            st.metric("Volatilidade Anualizada Estimada (1 / Beta)", f"{portfolio_volatility_inv_beta:.2%}")
        with col_1[1]:
            st.metric("Volatilidade Anualizada Estimada (Equal Weight)", f"{portfolio_volatility_equal_weight:.2%}")

        correlation_matrix = returns.corr()
        correlation_matrix = correlation_matrix.where(np.tril(np.ones(correlation_matrix.shape)).astype(np.bool_))
        correlation_matrix = correlation_matrix.sort_index(ascending=False)

        heatmap = create_chart(
            data=correlation_matrix,
            chart_type='heatmap',
            title='Correlação dos Ativos',
        )
        hct.streamlit_highcharts(heatmap, height=500)

    # Track Record
    with tabs[1]:
        st.subheader("Track Record")
