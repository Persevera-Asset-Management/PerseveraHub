import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime, date
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.db.fibery import read_fibery
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication

st.set_page_config(
    page_title="Controle de Posições | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Controle de Posições")

@st.cache_data
def load_positions():
    df = read_fibery(
      table_name="Inv-Asset Allocation/Posição",
      include_fibery_fields=False
    )
    df = df[["creation-date", "Name", "Portfolio", "Classificação do Conjunto", "Ativo Nome Completo", "Quantidade", "Valor Unitário", "Saldo"]]
    return df

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=sorted(CODIGOS_CARTEIRAS_ADM.keys()))
    btn_run = st.button("Executar")

if 'df' not in st.session_state:
    st.session_state.df = None

if btn_run:
    with st.spinner("Carregando dados...", show_time=True):
        st.session_state.df_positions = load_positions()
        st.session_state.df = st.session_state.df_positions[st.session_state.df_positions['Portfolio'] == selected_carteira]

df = st.session_state.df
if df is not None:
    try:
      st.subheader(selected_carteira)
      
      row_1 = st.columns(2)
      with row_1[0]:
        # Posição Atual
        st.markdown("##### Posição Atual")
        df_portfolio_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Name', 'Ativo Nome Completo', 'Classificação do Conjunto']).agg(
          **{
              'Quantidade': ('Quantidade', 'sum'),
              'Valor Unitário': ('Valor Unitário', 'mean'),
              'Saldo': ('Saldo', 'sum')
          }
        )

        df_portfolio_positions_current = df_portfolio_positions.loc[df_portfolio_positions.index.get_level_values(level=0).max()]
        st.dataframe(
          style_table(
            df_portfolio_positions_current,
            numeric_cols_format_as_float=['Quantidade', 'Valor Unitário', 'Saldo'],
          )
        )

      with row_1[1]:
        # Composição do Portfolio
        st.markdown("##### Composição do Portfolio")
        df_portfolio_composition = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Classificação do Conjunto']).agg(**{'Saldo': ('Saldo', 'sum')})
        df_portfolio_composition_current = df_portfolio_composition.loc[df_portfolio_composition.index.get_level_values(level=0).max()]
        correct_order = [
          'Caixa e Equivalentes',
          'Renda Fixa Pós-Fixado',
          'Renda Fixa Pré-Fixados',
          'Renda Fixa Atrelada à Inflação',
          'Renda Fixa em Moeda Estrangeira',
          'Renda Variável Nacional',
          'Renda Variável Internacional',
          'Retorno Total',
          'Fundos Imobiliários',
          'Investimentos Alternativos',
          'Criptomoedas',
          'Commodities',
        ]

        df_portfolio_composition_current = df_portfolio_composition_current.reindex(correct_order).dropna()

        chart_portfolio_composition = create_chart(
            data=df_portfolio_composition_current,
            columns=['Saldo'],
            names=['Saldo'],
            chart_type='pie',
            title="Percentual de Alocação das Classes",
            y_axis_title="R$",
        )
        hct.streamlit_highcharts(chart_portfolio_composition)

    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
