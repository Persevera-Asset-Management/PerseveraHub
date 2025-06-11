import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
import streamlit_highcharts as hct

st.set_page_config(
    page_title="Visualizador de Carteiras | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Visualizador de Carteiras")

st.write("Faça o upload do arquivo Excel exportado pelo ComDinheiro.")

uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx", "xls"])
# uploaded_file = r"C:\Users\Thales Carmo\Downloads\Relatório_Gestão_raw.xlsx"

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("Arquivo carregado com sucesso!")
        
        st.subheader("Dados Brutos")
        st.dataframe(df, hide_index=True)

        # Calculo das agregações
        saldo_carteiras = df.groupby('Carteira').agg(
            **{
                'Saldo Bruto': ('Saldo Bruto', 'sum'),
                'Percentual': ('Saldo Bruto', lambda x: x.sum() / df['Saldo Bruto'].sum() * 100)
            }
        ).sort_values('Saldo Bruto', ascending=False)

        saldo_inst_financeiras = df.groupby('Instituição Financeira do Ativo')['Saldo Bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)
        saldo_tipo_ativos = df.groupby('Tipo Ativo')['Saldo Bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)

        st.subheader("Agregação das Carteiras")

        # Gráfico de saldo bruto das carteiras
        row_1 = st.columns(2)
        with row_1[0]:
            chart_saldo_carteiras_total = create_chart(
                data=saldo_carteiras,
                columns=['Saldo Bruto'],
                names=['Saldo Bruto'],
                chart_type='column',
                title="Saldo das Carteiras",
                y_axis_title="R$",
                x_axis_title="Carteira",
            )
            hct.streamlit_highcharts(chart_saldo_carteiras_total)
        with row_1[1]:
            chart_saldo_carteiras_total = create_chart(
                data=saldo_carteiras,
                columns=['Saldo Bruto'],
                names=['Saldo Bruto'],
                chart_type='pie',
                title="Percentual de Alocação das Carteiras"
            )
            hct.streamlit_highcharts(chart_saldo_carteiras_total)

        row_2 = st.columns(2)
        with row_2[0]:
            chart_saldo_inst_financeiras = create_chart(
                data=saldo_inst_financeiras,
                columns=['Total'],
                names=['Total'],
                chart_type='pie',
                title="Saldo por Instituição Financeira",
                y_axis_title="R$",
            )
            hct.streamlit_highcharts(chart_saldo_inst_financeiras)

        with row_2[1]:
            chart_saldo_tipo_ativos = create_chart(
                data=saldo_tipo_ativos,
                columns=['Total'],
                names=['Total'],
                chart_type='pie',
                title="Saldo por Tipo de Ativo",
                y_axis_title="R$",
            )
            hct.streamlit_highcharts(chart_saldo_tipo_ativos)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
