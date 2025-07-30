import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from persevera_tools.data import get_securities_by_exchange, get_descriptors
from persevera_tools.quant_research.metrics import calculate_sqn

from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication

st.set_page_config(
    page_title="SQN Scanner | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("SQN Scanner")

with st.sidebar:
    st.header("Configurações")
    lookback_days = st.slider("Período de Análise (dias)", min_value=30, max_value=200, value=100, step=10)
    min_liquidity = st.number_input("Liquidez Mínima (R$)", min_value=0., value=8e6, step=1e6, format="%.0f")

@st.cache_data(ttl=3600)
def load_data(start_date, descriptors_list):
    try:
        codes = get_securities_by_exchange(exchange='BZ').values()
        return get_descriptors(list(codes), start_date=start_date, descriptors=descriptors_list)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data
def process_data(df, min_liquidity, lookback_days):
    """
    Filters the most liquid assets and calculates the SQN.
    """
    df_swapped = df.swaplevel(0, axis=1)
    most_liquid = df_swapped["median_dollar_volume_traded_21d"].dropna(how='all', axis='rows').iloc[-1]
    most_liquid = most_liquid[most_liquid > min_liquidity]

    price_close = df_swapped["price_close"][most_liquid.index]
    df_sqn_history = price_close.apply(calculate_sqn, period=lookback_days, axis=0)
    
    df_sqn = df_sqn_history.tail(10).T
    df_sqn = df_sqn[sorted(df_sqn.columns, reverse=True)]
    df_sqn = df_sqn.sort_values(by=df_sqn.columns[0], ascending=False)
    df_sqn = df_sqn.dropna(how='all', axis='rows')
    
    return df_sqn, df_sqn_history, price_close


if 'df' not in st.session_state:
    st.session_state.df = None

start_date = pd.to_datetime(date.today() - timedelta(days=365*5))
df = load_data(start_date=start_date, descriptors_list=["price_close", "median_dollar_volume_traded_21d"])

if df.empty:
    st.warning("Não foi possível carregar os dados.")
    st.stop()
else:
    df_sqn, df_sqn_history, price_close = process_data(df, min_liquidity, lookback_days)

    st.dataframe(
        style_table(
            df=df_sqn,
            column_names=[col.strftime('%Y-%m-%d') for col in df_sqn.columns],
            numeric_cols_format_as_float=[col.strftime('%Y-%m-%d') for col in df_sqn.columns]
        )
    )

    st.subheader("Análise de Retornos Futuros por SQN")

    # Add a selectbox to choose the stock
    row_1 = st.columns(2)
    with row_1[0]:
        selected_stock = st.selectbox(
            "Selecione um ativo para análise de retorno futuro",
            options=df_sqn.index
        )

    if selected_stock:
        # Calculate forward returns for the selected stock
        price_stock = price_close[selected_stock].dropna()
        forward_periods = [5, 10, 20, 30, 60]
        forward_returns = pd.DataFrame({
            f'{p}d Fwd': price_stock.pct_change(p).shift(-p) * 100 for p in forward_periods
        })

        # Get SQN for the selected stock
        sqn_stock = df_sqn_history[selected_stock]

        # Combine SQN and forward returns
        combined_df = pd.concat([sqn_stock.rename('SQN'), forward_returns], axis=1)

        # Define SQN bins
        bins = [-np.inf, -2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0, np.inf]
        labels = ["SQN < -2.0", "-2.0 <= SQN < -1.5", "-1.5 <= SQN < -1.0", "-1.0 <= SQN < -0.5", "-0.5 <= SQN < 0.5", "0.5 <= SQN < 1.0", "1.0 <= SQN < 1.5", "1.5 <= SQN < 2.0", "SQN >= 2.0"]
        combined_df['SQN Range'] = pd.cut(combined_df['SQN'], bins=bins, labels=labels)

        if not combined_df.empty:
            # Calculate median forward returns per SQN bin
            median_returns = combined_df.groupby('SQN Range', observed=True).median()

            # We are interested in forward returns, so drop the SQN column from the result
            median_returns = median_returns.drop(columns='SQN')
            
            # Also calculate the number of occurrences in each bin
            count_returns = combined_df.groupby('SQN Range', observed=True).count()['SQN'].rename('Observações')
            
            # Combine median returns and counts for display
            display_df = pd.concat([median_returns, count_returns], axis=1)
            
            row_2 = st.columns(2)
            with row_2[0]:
                chart_sqn_returns = create_chart(
                    data=median_returns,
                    columns=[*median_returns.columns],
                    names=[*median_returns.columns],
                    chart_type='column',
                    title=f"Retorno Mediano Futuro por Faixa de SQN - {selected_stock}",
                    y_axis_title="Retorno Mediano (%)",
                    x_axis_title="Faixa de SQN",
                )
                hct.streamlit_highcharts(chart_sqn_returns)
            with row_2[1]:
                chart_sqn_returns_count = create_chart(
                    data=display_df,
                    columns=['Observações'],
                    names=['Observações'],
                    chart_type='column',
                    title=f"Número de Observações por Faixa de SQN - {selected_stock}",
                    y_axis_title="Número de Observações",
                    x_axis_title="Faixa de SQN",
                    decimal_precision=0
                )
                hct.streamlit_highcharts(chart_sqn_returns_count)
        else:
            st.warning(f"Não há dados suficientes para a análise de {selected_stock}.")
