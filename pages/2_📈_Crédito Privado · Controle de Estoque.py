import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM

from services.position_service import (
    load_assets,
    load_issuers,
    get_emissor_column,
    load_portfolio_from_comdinheiro,
)


st.set_page_config(
    page_title="Crédito Privado · Controle de Estoque | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Crédito Privado · Controle de Estoque")

for key in ('df', 'df_assets', 'df_issuers'):
    st.session_state.setdefault(key, None)

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_date = st.date_input("Data", format="DD/MM/YYYY", value=pd.to_datetime(date.today()), min_value=datetime(2024, 1, 1), max_value=pd.to_datetime(date.today()))
    selected_carteiras = st.multiselect("Carteiras selecionadas", options=sorted(CODIGOS_CARTEIRAS_ADM.keys()), default=sorted(CODIGOS_CARTEIRAS_ADM.keys()))
    btn_run = st.button("Executar")

    selected_status = []
    if st.session_state.df_issuers is not None:
        st.divider()
        st.subheader("Filtros")
        status_options = sorted(st.session_state.df_issuers['Status do Emissor'].dropna().unique())
        selected_status = st.multiselect("Status do Emissor", options=status_options, default=status_options)

if btn_run:
    with st.spinner("Carregando dados...", show_time=True):
        st.session_state.df = load_portfolio_from_comdinheiro(
            portfolios=tuple(sorted(selected_carteiras)),
            date_report=selected_date.strftime('%Y-%m-%d')
        )
        st.session_state.df_assets = load_assets()
        st.session_state.df_issuers = load_issuers()
        
        if "selected_asset" in st.session_state:
            st.session_state.selected_asset = ""
        st.rerun()

df_cd = st.session_state.df
df_assets = st.session_state.df_assets
df_issuers = st.session_state.df_issuers

if df_cd is not None and df_assets is not None and df_issuers is not None:
    try:
        # Transformações dos dados
        df_cd = df_cd.rename(columns={'date': 'Data', 'carteira': 'Carteira', 'ativo': 'Ativo', 'descricao': 'Descrição', 'quantidade': 'Quantidade', 'preco_unitario': 'Preço Unitário', 'saldo_bruto': 'Saldo Bruto', 'instituicao_financeira': 'Custodiante', 'tipo_ativo': 'Tipo de Ativo', 'ticker': 'Ticker'})
        strip_str = ['.pu_med', '.pu_ref', '.pu_anb', '.lastro', 'CETIP_', '_unica', '_senior1', '_subclasseA', '_classeA', '_ClasseA', '_classeB', '_classe2', 'DEB:']
        df_cd['Ticker'] = df_cd['Ticker'].str.replace(r'|'.join(strip_str), '', regex=True)
        df_cd['Ticker'] = df_cd['Ticker'].str.replace(r'_@.*$', '', regex=True)

        # df_assets = get_emissor_column(df_assets)
        df = df_cd.merge(df_assets[['Name', 'Indexador', 'Data Vencimento', 'Nome Emissor', 'Nome Devedor']], left_on='Ticker', right_on='Name', how='left')

        df = df.merge(df_issuers, left_on='Emissor', right_on='Nome Emissor', how='left')

        saldo_carteiras = df.groupby('Carteira').agg({'Saldo Bruto': 'sum'}).rename(columns={'Saldo Bruto': 'Saldo Total'})
        df = df.merge(saldo_carteiras, right_index=True, left_on='Carteira', how='left')
        df['Percentual'] = df['Saldo Bruto'] / df['Saldo Total'] * 100
        df = df[df['Tipo de Ativo'].isin(['cri', 'cra', 'debenture'])]

        if selected_status:
            df = df[df['Status do Emissor'].isin(selected_status)]

        st.dataframe(style_table(
            df[['Carteira', 'Ticker', 'Ativo', 'Indexador', 'Data Vencimento', 'Emissor', 'Quantidade', 'Preço Unitário', 'Saldo Bruto', 'Percentual', 'Custodiante']],
            date_cols=['Data Vencimento'],
            currency_cols=['Saldo Bruto', 'Preço Unitário'],
            numeric_cols_format_as_float=['Quantidade'],
            percent_cols=['Percentual'],
        ),
        hide_index=True)

    except Exception as e:
        st.error(f"Error: {str(e)}")