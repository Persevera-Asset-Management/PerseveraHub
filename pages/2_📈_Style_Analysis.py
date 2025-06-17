import streamlit as st
import os
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from persevera_style_analysis.core.best_subset_style_analysis import BestSubsetStyleAnalysis
from persevera_style_analysis.utils.helpers import extract_betas, compute_significance_mask
from persevera_style_analysis.utils import helpers
from persevera_tools.data import get_series, get_funds_data, get_persevera_peers
from utils.chart_helpers import create_chart
from utils.table import style_table
import streamlit_highcharts as hct
from configs.pages.style_analysis import FACTOR_OPTIONS, FACTOR_OPTIONS_SELECTED
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Style Analysis | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Style Analysis")

@st.cache_data(ttl=3600)
def load_peers():
    try:
        return get_persevera_peers()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_indicators(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()
    
@st.cache_data(ttl=3600)
def load_funds_data(fund_cnpjs, start_date):
    try:
        return get_funds_data(cnpjs=fund_cnpjs, fields=['fund_nav'], start_date=start_date)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()
    
start_date = datetime.now() - timedelta(days=180)
start_date_str = start_date.strftime('%Y-%m-%d')

peers = load_peers()

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_group = st.radio("Grupo de Fundos (pré-seleções)", options=['Nenhum'] + list(peers['persevera_group'].unique()), horizontal=True)

    # Determine default funds based on selected_group
    if selected_group and selected_group != 'Nenhum':
        default_selected_funds = peers[peers['persevera_group'] == selected_group]['short_name'].tolist()
    else:
        default_selected_funds = []
    selected_funds = st.multiselect("Fundos Selecionados", options=peers['short_name'].tolist(), default=default_selected_funds)
    selected_factors = st.multiselect("Fatores Selecionados", options=list(FACTOR_OPTIONS.values()), default=list(FACTOR_OPTIONS_SELECTED.values()))
    window_range = st.slider("Janela de Análise", min_value=10, max_value=60, value=(12, 50), step=1)
    min_window, max_window = window_range
    selection_metric = st.selectbox("Métrica de Seleção", options=['aic', 'bic', 'adjr2'], index=2)
    btn_run = st.button("Run")

if btn_run:
    start_time = time.time()
    with st.spinner("Carregando dados de mercado..."):
        factor_codes = [k for k, v in FACTOR_OPTIONS.items() if v in selected_factors]
        data_indicators = load_indicators(factor_codes, start_date=start_date_str)

    with st.spinner("Carregando dados de fundos..."):
        fund_cnpjs = peers[peers['short_name'].isin(selected_funds)]['fund_cnpj'].tolist()
        data_funds = load_funds_data(fund_cnpjs, start_date=start_date_str)
        data_funds.rename(columns=peers.set_index('fund_cnpj')['short_name'].to_dict(), inplace=True)

    with st.spinner("Reparando dados..."):
        returns = helpers.prepare_data(data_funds, data_indicators)
        returns = returns.dropna(how='any')

    with st.spinner("Iniciando análise..."):
        best_subset_analysis = BestSubsetStyleAnalysis(returns_data=returns, fund_cols=selected_funds, factor_cols=factor_codes[1:])

    with st.spinner("Executando análise para o período mais recente..."):
        best_subset_results = best_subset_analysis.run_analysis(
            min_window=min_window,
            max_window=max_window,
            selection_metric=selection_metric,
            most_recent_only=True
        )

        all_betas, all_pvalues = pd.DataFrame(), pd.DataFrame()
        all_rsquared, all_rsquared_adj, all_windows = pd.Series(), pd.Series(), pd.Series()

        # Extract betas and p-values for each fund
        for fund_name in selected_funds:
            if fund_name in best_subset_results:
                try:
                    # Get beta values and drop non-factor columns
                    beta_values = best_subset_results[fund_name].loc['beta'].drop(['date', 'fund', 'rsquared', 'rsquared_adj', 'window'], errors='ignore')
                    pvalue_values = best_subset_results[fund_name].loc['pvalue'].drop(['date', 'fund', 'rsquared', 'rsquared_adj', 'window'], errors='ignore')
                    
                    # Add to DataFrames with short name as column label
                    all_betas[fund_name] = beta_values
                    all_pvalues[fund_name] = pvalue_values
                    
                    # Get R-squared values
                    all_rsquared[fund_name] = best_subset_results[fund_name].loc['model', 'rsquared']
                    all_rsquared_adj[fund_name] = best_subset_results[fund_name].loc['model', 'rsquared_adj']
                    
                    # Get window size
                    all_windows[fund_name] = best_subset_results[fund_name].loc['model', 'window']
                except Exception as e:
                    st.error(f"Could not extract data for fund {fund_name}: {e}")

    end_time = time.time()
    execution_time = end_time - start_time

    # Display the collected data
    st.header("Resultados")
    st.code(f"""
            - Período: {returns.index.max().strftime('%Y-%m-%d')}
            - Janela de análise: {min_window} a {max_window}
            - Métrica de seleção: {selection_metric}
            - Fundos selecionados: {', '.join(selected_funds)}
            - Fatores selecionados: {', '.join(selected_factors)}
            - Tempo de execução: {execution_time:.2f} segundos
            """, language='markdown')

    # Betas
    st.subheader("Exposições a fatores de risco (Betas)")

    # Iterate over each factor (column in all_betas) to create a chart
    cols = st.columns(2)
    all_betas.dropna(how='all', inplace=True)
    for i, factor_name in enumerate(all_betas.index): # all_betas rows are factors, columns are funds
        if factor_name in FACTOR_OPTIONS:
            factor_display_name = FACTOR_OPTIONS[factor_name]
        else:
            factor_display_name = factor_name

        # Select the current column for the chart
        with cols[i % 2]:
            chart_data = all_betas.loc[[factor_name]].T
            chart_data = chart_data.merge(all_pvalues.loc[[factor_name]].T, left_index=True, right_index=True)
            chart_data.columns = ['Beta', 'P-value']
            # st.write(chart_data)

            threshold_alpha = 0.10
            chart_data = chart_data.sort_values(by='Beta', ascending=False)
            # st.write(chart_data)
            
            chart_data_adjusted = pd.DataFrame(index=chart_data.index, columns=['Beta Significante', 'Beta Não Significante'])
            chart_data_adjusted['Beta Significante'] = np.where(chart_data['P-value'] < threshold_alpha, chart_data['Beta'], 0)
            chart_data_adjusted['Beta Não Significante'] = np.where(chart_data['P-value'] >= threshold_alpha, chart_data['Beta'], 0)
            # st.write(chart_data_adjusted)

            betas_chart_options = create_chart(
                data=chart_data_adjusted,
                columns=['Beta Significante', 'Beta Não Significante'],
                names=['Beta Significante', 'Beta Não Significante'],
                chart_type='column',
                stacking='normal',
                title=factor_display_name,
                y_axis_title="Beta",
                x_axis_title="",
                decimal_precision=3
            )
            hct.streamlit_highcharts(betas_chart_options)

    # R-Squared
    st.subheader("R-Squared")
    chart_rsquared = pd.merge(all_rsquared.to_frame(name='R²'), all_rsquared_adj.to_frame(name='R² Ajustado'), left_index=True, right_index=True)
    chart_rsquared.sort_values(by='R² Ajustado', ascending=False, inplace=True)
    rsquared_chart_options = create_chart(
        data=chart_rsquared,
        columns=['R²', 'R² Ajustado'],
        names=['R²', 'R² Ajustado'],
        chart_type='column',
        title="",
        y_axis_title="R-Squared",
        x_axis_title="",
    )
    hct.streamlit_highcharts(rsquared_chart_options)

    st.subheader("Janela de análise")
    chart_windows = all_windows.sort_values(ascending=False).to_frame(name='Janela de análise')
    windows_chart_options = create_chart(
        data=chart_windows,
        columns=['Janela de análise'],
        names=['Janela de análise'],
        chart_type='column',
        title="",
        y_axis_title="Dias",
        x_axis_title="",
        decimal_precision=0
    )
    hct.streamlit_highcharts(windows_chart_options)
