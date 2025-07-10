import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS
from utils.auth import check_authentication

st.set_page_config(
    page_title="Atribuição de Performance | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Atribuição de Performance")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox("Carteira selecionada", options=CODIGOS_CARTEIRAS)
    selected_report_date = st.date_input("Data do Relatório", format="DD/MM/YYYY", value=datetime.now(), min_value=datetime(2024, 1, 1), max_value=datetime.now())
    selected_inception_date = st.date_input("Data de Início (Inception)", format="DD/MM/YYYY", value=datetime.now(), min_value=datetime(2024, 1, 1), max_value=datetime.now())
    btn_run = st.button("Gerar Relatório")

if 'table_data' not in st.session_state:
    st.session_state.table_data = None

if btn_run:
    with st.spinner("Carregando dados..."):
        provider = ComdinheiroProvider()
        table_data = provider.get_data(
            category='portfolio_statement',
            portfolio=selected_carteira,
            date_inception=selected_inception_date.strftime('%Y-%m-%d'),
            date_report=selected_report_date.strftime('%Y-%m-%d'),
        )
        st.session_state.table_data = table_data

table_data = st.session_state.table_data
if table_data is not None:
    try:
        classes_ativos = [
            'Previdência',
            'Ações/ETFs',
            'Ação/ETF',
            'Títulos Públicos',
            'Título Público',
            'Fundos',
            'Genérico',
            'Ativo Genérico',
            'Debêntures',
            'Debênture',
            'CRI/CRA',
            'Caixa',
            'Caixa Bloqueado',
            'Clube Invest.',
            'Fundo Offshore',
            'International Bond',
            'Mercado Futuro',
            'Opção',
            'Renda Fixa (CDB/LCI/LCA...)',
            'Renda Fixa',
            'Total',
        ]

        movimentacoes = table_data['Movimentações - no Mês'].apply(lambda x: pd.to_numeric(x, errors='coerce') if x.name in ['Quantidade', 'Valor Bruto'] else x)
        rentabilidade_acumulada = table_data['Rentabilidade Ativos por Classe']
        rentabilidade_acumulada['Classe'] = rentabilidade_acumulada['Ativo'].apply(lambda x: x if np.isin(x ,classes_ativos) else None).ffill()
        rentabilidade_acumulada = rentabilidade_acumulada.drop_duplicates().set_index(['Ativo', 'Classe']).apply(lambda x: pd.to_numeric(x, errors='coerce'))
        posicao_consolidada = table_data['Posição Consolidada - No Mês'].set_index('Ativo').apply(lambda x: pd.to_numeric(x, errors='coerce')).groupby('Ativo').sum()
        rentabilidade_acumulada_consolidada = pd.merge(rentabilidade_acumulada, posicao_consolidada, on='Ativo', how='outer').fillna(0)
        rentabilidade_acumulada_consolidada['Contribuição'] = rentabilidade_acumulada_consolidada['no Mês'] * rentabilidade_acumulada_consolidada['%'] / 100

        with st.expander("Dados Brutos"):
            st.dataframe(rentabilidade_acumulada_consolidada)

        with st.expander("Movimentações"):
            st.dataframe(movimentacoes, hide_index=True)

        contribuicao_classes = rentabilidade_acumulada_consolidada.filter(classes_ativos, axis=0)
        contribuicao_ativos = rentabilidade_acumulada_consolidada[~rentabilidade_acumulada_consolidada.index.isin(classes_ativos)]

        contribuicao_classes.at['Taxa de Administração', 'Contribuição'] = 100 - rentabilidade_acumulada_consolidada[~rentabilidade_acumulada_consolidada.index.isin(classes_ativos)]['%'].sum()
        contribuicao_classes = pd.concat([contribuicao_classes.iloc[:-2], contribuicao_classes.iloc[-1].to_frame().T, contribuicao_classes.iloc[-2].to_frame().T])

        contribuicao_ativos.at['Taxa de Administração', 'Contribuição'] = 100 - rentabilidade_acumulada_consolidada[~rentabilidade_acumulada_consolidada.index.isin(classes_ativos)]['%'].sum()
        contribuicao_ativos = contribuicao_ativos.sort_values(by='Contribuição', ascending=False)

        row_1 = st.columns(4)
        with row_1[0]:
            st.metric("Contribuição Calculada (Classes)", f"{contribuicao_classes.iloc[:-1]['Contribuição'].sum():,.2f}%", help="Soma das contribuições calculadas a partir das classes de ativos")
        with row_1[1]:
            st.metric("Contribuição Calculada (Ativos)", f"{contribuicao_ativos['Contribuição'].sum():,.2f}%", help="Soma das contribuições calculadas a partir dos ativos")
        with row_1[2]:
            st.metric("Contribuição Real (ComDinheiro)", f"{contribuicao_classes.at['Total', 'Contribuição']:,.2f}%")
        with row_1[3]:
            st.metric("Diferença", f"{contribuicao_ativos['Contribuição'].sum() - contribuicao_classes.at['Total', 'Contribuição']:,.2f}%")

        contribuicao_classes['Contribuição'] = contribuicao_classes['Contribuição'].mul(100)
        contribuicao_ativos['Contribuição'] = contribuicao_ativos['Contribuição'].mul(100)

        chart_contribuicao_classes = create_chart(
            data=contribuicao_classes,
            columns=['Contribuição'],
            names=['Contribuição'],
            chart_type='column',
            title="Contribuição das Classes",
            y_axis_title="bps",
            x_axis_title="Classe",
            )
        hct.streamlit_highcharts(chart_contribuicao_classes)

        chart_contribuicao_ativos = create_chart(
            data=contribuicao_ativos,
            columns=['Contribuição'],
            names=['Contribuição'],
            chart_type='column',
            title="Contribuição dos Ativos",
            y_axis_title="bps",
            x_axis_title="Ativo",
            )
        hct.streamlit_highcharts(chart_contribuicao_ativos)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
