import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
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
      where_filter=[">=", ["fibery/creation-date"], "$cutoffDate"],
      params={"$cutoffDate": "2026-01-01T00:00:00Z"},
      include_fibery_fields=False,
  )

  df = df[[
    "creation-date", "Portfolio",
    "Nome Ativo", "Nome Ativo Completo",
    "Classificação do Conjunto", "Classificação Instrumento",
    "Nome Emissor", "Nome Devedor", "Data de Vencimento RF",
    "Quantidade", "Valor Unitário", "Saldo",
    "Custodiante Acronimo"
  ]]
  return df

@st.cache_data
def load_accounts():
  df = read_fibery(table_name="Ops-InstFin/Conta", include_fibery_fields=False)
  df = df[df["Status Habilitação"] == "Sob Gestão"]
  df = df[["Portfolio", "Titularidade Principal", "Custodiante", "Nr Conta"]]
  df = df.dropna(subset=["Portfolio"])
  df["Nome Completo"] = df["Titularidade Principal"].str.split("|").str[1].str.strip()
  return df

@st.cache_data
def load_instruments_fgc():
  df = read_fibery(table_name="Inv-Taxonomia/Classificação Instrumento", include_fibery_fields=False)
  df = df[["Name", "Cobertura FGC"]]
  instruments_list = df[df["Cobertura FGC"]]["Name"].tolist()
  return instruments_list

@st.cache_data
def load_target_allocations():
  df = read_fibery(
    table_name="Ops-Portfolios/Parâmetro de PctPL Polinv",
    include_fibery_fields=False
  )
  df["Portfolio"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("_").str[0], df["Política de Investimento"].str.split("_").str[0])
  df["Tipo Documento"] = np.where(df["Política de Investimento"].isna(), df["Alocação Target"].str.split("_").str[1], df["Política de Investimento"].str.split("_").str[1])
  df["Data Documento"] = np.where(df["Política de Investimento"].isna(), pd.to_datetime(df["Alocação Target"].str[-10:]), pd.to_datetime(df["Política de Investimento"].str[-10:]))
  df = df[["Portfolio", "Tipo Documento", "Data Documento", "Name", "PL Min", "PL Max", "Target"]]

  df = df.groupby(['Portfolio', pd.Grouper(key='Data Documento', freq='D'), 'Name']).agg(
    **{
      'PL Min': ('PL Min', 'mean'),
      'PL Max': ('PL Max', 'mean'),
      'Target': ('Target', 'mean')
    }
  )
  return df

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=[""] + sorted(CODIGOS_CARTEIRAS_ADM.keys()))
    # btn_run = st.button("Executar")

if 'df' not in st.session_state:
    st.session_state.df = None

if 'df_target_allocations' not in st.session_state:
    st.session_state.df_target_allocations = None

if 'df_accounts' not in st.session_state:
    st.session_state.df_accounts = None

if 'instruments_fgc' not in st.session_state:
    st.session_state.instruments_fgc = None

def load_data():
    with st.spinner("Carregando dados...", show_time=True):
      st.session_state.df_positions = load_positions()
      st.session_state.instruments_fgc = load_instruments_fgc()
      st.session_state.df_target_allocations = load_target_allocations()
      st.session_state.df_accounts = load_accounts()
      st.session_state.df = st.session_state.df_positions[st.session_state.df_positions['Portfolio'] == selected_carteira]

correct_order = [
  'Caixa e Equivalentes',
  'Renda Fixa Pós-Fixada',
  'Renda Fixa Pré-Fixada',
  'Renda Fixa Atrelada à Inflação',
  'Renda Variável',
  'Retorno Total',
  'Fundos Imobiliários',
  'Investimentos Alternativos',
  'Criptomoedas',
  'Commodities',
]

if selected_carteira != "":
  load_data()

  df = st.session_state.df
  df_target_allocations = st.session_state.df_target_allocations
  df_accounts = st.session_state.df_accounts
  instruments_fgc = st.session_state.instruments_fgc

  try:
    st.subheader(selected_carteira)

    # Informações Gerais
    st.code(f"""
    {df_accounts.loc[df_accounts['Portfolio'] == selected_carteira, 'Nome Completo'].values[0]} ({selected_carteira})

    Conta(s): {', '.join(df_accounts.loc[df_accounts['Portfolio'] == selected_carteira, 'Nr Conta'].values)}
    Custodiante(s): {', '.join(df_accounts.loc[df_accounts['Portfolio'] == selected_carteira, 'Custodiante'].values)}
    """, language='markdown')
    
    # Composição Completa
    df_portfolio_positions = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto']).agg(
      **{
        'Quantidade': ('Quantidade', 'sum'),
        'Valor Unitário': ('Valor Unitário', 'mean'),
        'Saldo': ('Saldo', 'sum')
      }
    )

    df_portfolio_positions_current = df_portfolio_positions.loc[df_portfolio_positions.index.get_level_values(level=0).max()].copy()
    df_portfolio_positions_current['%'] = df_portfolio_positions_current['Saldo'] / df_portfolio_positions_current['Saldo'].sum() * 100

    with st.expander("Composição Completa", expanded=False):
      st.dataframe(
        style_table(
          df_portfolio_positions_current,
          numeric_cols_format_as_float=['Quantidade', 'Valor Unitário', 'Saldo', '%'],
        )
      )
    
    # Política de Investimentos
    if selected_carteira in df_target_allocations.index:
      df_policy_investments_current = df_target_allocations.loc[selected_carteira].dropna(subset=['PL Min', 'PL Max'])
      df_policy_investments_current = df_policy_investments_current.loc[df_policy_investments_current.index.get_level_values(level=0).max()]
      df_policy_investments_current = df_policy_investments_current.mul(100)
      df_policy_investments_current = df_policy_investments_current.reindex(correct_order)

      with st.expander("Política de Investimentos", expanded=False):
        st.dataframe(
          style_table(
            df_policy_investments_current.drop(columns='Target'),
            percent_cols=['PL Min', 'PL Max', 'Target'],
          )
        )
    else:
      st.warning("Política de Investimentos não cadastrada")

    st.markdown("Saldo Total: **R$ {0:,.2f}**".format(df_portfolio_positions_current['Saldo'].sum()))
    
    row_1 = st.columns(2)
    with row_1[0]:  # Alocação Atual
      df_portfolio_composition = df.groupby([pd.Grouper(key='creation-date', freq='D'), 'Classificação do Conjunto']).agg(**{'Saldo': ('Saldo', 'sum')})
      df_portfolio_composition_current = df_portfolio_composition.loc[df_portfolio_composition.index.get_level_values(level=0).max()]
      df_portfolio_composition_current = df_portfolio_composition_current.reindex(correct_order).dropna()

      chart_portfolio_composition = create_chart(
        data=df_portfolio_composition_current,
        columns=['Saldo'],
        names=['Saldo'],
        chart_type='donut',
        title="Alocação Atual",
        y_axis_title="%",
      )
      hct.streamlit_highcharts(chart_portfolio_composition)

    with row_1[1]:  # Alocação Alvo
      if selected_carteira in df_target_allocations.index:
        df_target_allocations_current = df_target_allocations.loc[selected_carteira].dropna(subset=['Target'])
        df_target_allocations_current = df_target_allocations_current.loc[df_target_allocations_current.index.get_level_values(level=0).max()]
        df_target_allocations_current = df_target_allocations_current * df_portfolio_positions_current['Saldo'].sum()
        df_target_allocations_current = df_target_allocations_current.reindex(correct_order)

        chart_portfolio_composition_target = create_chart(
          data=df_target_allocations_current,
          columns=['Target'],
          names=['Target'],
          chart_type='donut',
          title="Alocação Alvo",
          y_axis_title="%",
        )
        hct.streamlit_highcharts(chart_portfolio_composition_target)
      else:
        st.warning("Alocação alvo não cadastrada")      

    row_2 = st.columns(2)
    with row_2[0]:  # Distribuição de Emissores
      df_emissor = df.copy()
      df_emissor['Emissor'] = df_emissor['Nome Devedor'].fillna(df_emissor['Nome Emissor'])
      df_portfolio_positions_emissores = df_emissor.groupby([pd.Grouper(key='creation-date', freq='D'), 'Emissor']).agg(**{'Saldo': ('Saldo', 'sum')})
      df_portfolio_positions_emissores_current = df_portfolio_positions_emissores.loc[df_portfolio_positions_emissores.index.get_level_values(level=0).max()]
      df_portfolio_positions_emissores_current = df_portfolio_positions_emissores_current.sort_values(by='Saldo', ascending=False)

      chart_portfolio_positions_emissores = create_chart(
        data=df_portfolio_positions_emissores_current,
        columns=['Saldo'],
        names=['Emissor'],
        chart_type='donut',
        title="Emissores",
        y_axis_title="%",
      )
      hct.streamlit_highcharts(chart_portfolio_positions_emissores)

    with row_2[1]:  # Distribuição de Instrumentos
      df_instrument = df.copy()
      df_instrument['Instrumento'] = df_instrument['Classificação Instrumento']
      df_portfolio_positions_instruments = df_instrument.groupby([pd.Grouper(key='creation-date', freq='D'), 'Instrumento']).agg(**{'Saldo': ('Saldo', 'sum')})
      df_portfolio_positions_instruments_current = df_portfolio_positions_instruments.loc[df_portfolio_positions_instruments.index.get_level_values(level=0).max()]
      df_portfolio_positions_instruments_current = df_portfolio_positions_instruments_current.sort_values(by='Saldo', ascending=False)

      chart_portfolio_positions_instruments = create_chart(
        data=df_portfolio_positions_instruments_current,
        columns=['Saldo'],
        names=['Instrumento'],
        chart_type='donut',
        title="Instrumentos",
        y_axis_title="%",
      )
      hct.streamlit_highcharts(chart_portfolio_positions_instruments)

    row_3 = st.columns(2)
    with row_3[0]:  # Distribuição por Custodiante
      df_custodiante = df.copy()
      df_portfolio_positions_custodiante = df_custodiante.groupby([pd.Grouper(key='creation-date', freq='D'), 'Custodiante Acronimo']).agg(**{'Saldo': ('Saldo', 'sum')})
      df_portfolio_positions_custodiante_current = df_portfolio_positions_custodiante.loc[df_portfolio_positions_custodiante.index.get_level_values(level=0).max()]
      df_portfolio_positions_custodiante_current = df_portfolio_positions_custodiante_current.sort_values(by='Saldo', ascending=False)

      chart_portfolio_positions_custodiante = create_chart(
        data=df_portfolio_positions_custodiante_current,
        columns=['Saldo'],
        names=['Custodiante'],
        chart_type='donut',
        title="Custodiantes",
        y_axis_title="%",
      )
      hct.streamlit_highcharts(chart_portfolio_positions_custodiante)

    st.markdown("##### Renda Fixa")
    row_4 = st.columns(2)
    with row_4[0]:  # Vencimentos
      st.markdown("##### Vencimentos")
      df_data_vencimento_rf = df.copy()
      df_data_vencimento_rf = df_data_vencimento_rf.groupby([pd.Grouper(key='creation-date', freq='D'), 'Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto', 'Classificação Instrumento', 'Data de Vencimento RF']).agg(
        **{
          'Quantidade': ('Quantidade', 'sum'),
          'Valor Unitário': ('Valor Unitário', 'mean'),
          'Saldo': ('Saldo', 'sum')
        }
      )
      df_data_vencimento_rf_current = df_data_vencimento_rf.loc[df_data_vencimento_rf.index.get_level_values(level=0).max()].copy()
      df_data_vencimento_rf_current = df_data_vencimento_rf_current.reset_index().set_index(['Nome Ativo'])
      df_data_vencimento_rf_current['Data de Vencimento'] = pd.to_datetime(df_data_vencimento_rf_current['Data de Vencimento RF'])
      df_data_vencimento_rf_current = df_data_vencimento_rf_current.sort_values(by='Data de Vencimento', ascending=True)
      
      st.dataframe(
        style_table(
          df_data_vencimento_rf_current[['Nome Ativo Completo', 'Classificação do Conjunto', 'Classificação Instrumento', 'Data de Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo']],
          date_cols=['Data de Vencimento'],
          numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
          numeric_cols_format_as_int=['Quantidade'],
        )
      )

    with row_4[1]:  # Cobertura do FGC
      df_fgc = df.copy()
      df_fgc = df_fgc[df_fgc['Classificação Instrumento'].isin(instruments_fgc)]

      df_fgc = df_fgc.groupby([pd.Grouper(key='creation-date', freq='D'), 'Nome Emissor']).agg(**{'Saldo': ('Saldo', 'sum')})
      
      if df_fgc.index.get_level_values(level=0).max() in df_fgc.index:
        df_fgc_current = df_fgc.loc[df_fgc.index.get_level_values(level=0).max()].copy()

        chart_portfolio_positions_fgc = create_chart(
          data=df_fgc_current.sort_values(by='Saldo', ascending=False),
          columns=['Saldo'],
          names=['Nome Emissor'],
          chart_type='column',
          title="Cobertura do FGC",
          y_axis_title="Total (R$)",
          x_axis_title="Banco Emissor",
          show_legend=False,
          horizontal_line={"value": 250000, "color": "#FF0000", "width": 2, "label": {"text": "Limite por Emissor", "align": "left"}}
        )
        hct.streamlit_highcharts(chart_portfolio_positions_fgc)
      else:
        st.info("Cliente não possui ativos cobertos pelo FGC")

  except Exception as e:
    st.error(f"Ocorreu um erro ao carregar os dados: {e}")
