import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from persevera_tools.data import get_descriptors, get_securities_by_exchange, get_series
from persevera_tools.quant_research.matrix import corr_to_cov, find_nearest_corr
from persevera_tools.data.sma import get_equities_portfolio

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
equities_portfolio = get_equities_portfolio()
current_stocks = equities_portfolio[equities_portfolio['date'] == equities_portfolio['date'].max()].sort_values(by='code')

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_stocks = st.multiselect("Ações selecionadas", options=active_securities, default=current_stocks['code'].tolist())

data = load_data(selected_stocks, start_date=pd.to_datetime(date.today() - timedelta(days=365)), field=['price_close', 'beta']).swaplevel(axis=1)
data_equities_portfolio = load_data(list(equities_portfolio['code'].unique()), start_date=equities_portfolio['date'].min(), field='price_close')
indicators = load_indicators('br_ibovespa', start_date=equities_portfolio['date'].min())

if data.empty or len(selected_stocks) == 0:
    st.warning("Por favor, selecione ao menos uma ação para continuar.")
else:
    returns = data['price_close'].pct_change().dropna()

    tabs = st.tabs(["Composição Atual", "Track Record"])
    
    # Composição Atual
    with tabs[0]:
        st.subheader("Composição Atual")

        # Inicializa a tabela de alocação
        # betas_df = data['beta'].iloc[-1].to_frame("Bloomberg Beta")
        betas_df = current_stocks[['code', 'inv_beta']].eval('PerseveraBeta = 1 / inv_beta')

        # Permite a edição dos Betas
        with st.expander("Editar Betas", expanded=False):
            st.caption("Você pode editar os valores de Beta na tabela abaixo. As outras colunas serão recalculadas automaticamente.")
            edited_betas = st.data_editor(
                betas_df[['code', 'PerseveraBeta']].set_index('code'),
                column_config={
                    "PerseveraBeta": st.column_config.NumberColumn(
                        "PerseveraBeta",
                        help="O beta do ativo.",
                        format="%.4f",
                    )
                },
                use_container_width=True
            )

        # Recalcula a tabela de alocação com base nos betas (editados ou não)
        allocation_table = edited_betas.copy()
        allocation_table['1 / Beta'] = 1.0 / allocation_table['PerseveraBeta']
        allocation_table['Equal Weight (%)'] = 1.0 / len(allocation_table) * 100.0
        allocation_table['Final Weight (%)'] = allocation_table['1 / Beta'] / allocation_table['1 / Beta'].sum() * 100.0
        
        st.dataframe(
            style_table(
                allocation_table,
                numeric_cols_format_as_float=['PerseveraBeta', '1 / Beta'],
                percent_cols=['Equal Weight (%)', 'Final Weight (%)'],
            ),
            hide_index=False
        )
        
        st.markdown("#### Estatísticas")
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
        
        weights_df = equities_portfolio.pivot(index='date', columns='code', values='inv_beta')
        weights_df = weights_df.div(weights_df.sum(axis=1), axis=0).fillna(0)
        weights_df = weights_df.reindex(data_equities_portfolio.index)
        weights_df = weights_df.ffill()

        with st.expander("Histórico de Alocações", expanded=False):
            st.dataframe(
                style_table(
                    weights_df.replace(0, np.nan).mul(100),
                    percent_cols=weights_df.columns.tolist()
                ),
                hide_index=False
            )

        returns_equities_portfolio = weights_df.mul(data_equities_portfolio.pct_change(), axis=0).sum(axis=1)
        returns_df = pd.concat([returns_equities_portfolio, indicators.pct_change().fillna(0)], axis=1)
        returns_df.columns = ['Carteira de RV', 'Ibovespa']
        cumulative_returns_equities_portfolio = (1 + returns_df).cumprod() - 1

        col_1 = st.columns(2)
        with col_1[0]:
            # Performance acumulado
            chart_performance_options = create_chart(
                data=cumulative_returns_equities_portfolio * 100,
                columns=["Carteira de RV", "Ibovespa"],
                names=["Carteira de RV", "Ibovespa"],
                chart_type='line',
                title="Evolução da Carteira de RV",
                y_axis_title="Retorno (%)",
                decimal_precision=2
            )
            hct.streamlit_highcharts(chart_performance_options)
        
        with col_1[1]:
            # Performance diária
            chart_daily_returns_options = create_chart(
                data=returns_df * 10000,
                columns=["Carteira de RV"],
                names=["Carteira de RV"],
                chart_type='column',
                title="Retorno Diário da Carteira de RV",
                y_axis_title="Retorno (bps)",
                decimal_precision=0
            )
            hct.streamlit_highcharts(chart_daily_returns_options)
