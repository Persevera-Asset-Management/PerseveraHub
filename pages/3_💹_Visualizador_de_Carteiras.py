import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
import streamlit_highcharts as hct
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS

st.set_page_config(
    page_title="Visualizador de Carteiras | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Visualizador de Carteiras")

# Definição dos parâmetros
st.sidebar.header("Parâmetros")

with st.sidebar.form(key='visualizador_de_carteiras_form', border=False):
    selected_carteiras = st.multiselect("Carteiras selecionadas", options=CODIGOS_CARTEIRAS, default=CODIGOS_CARTEIRAS[:10])
    btn_run = st.form_submit_button("Run")

if 'df' not in st.session_state:
    st.session_state.df = None

if btn_run:
    with st.spinner("Carregando dados..."):
        provider = ComdinheiroProvider()
        st.session_state.df = provider.get_data(
            category='portfolio_positions',
            portfolios=selected_carteiras,
            date_str=datetime.now().strftime('%d%m%Y')
        )
        if "selected_asset" in st.session_state:
            st.session_state.selected_asset = ""

df = st.session_state.df
if df is not None:
    try:
        with st.expander("Dados Brutos", expanded=False):
            st.dataframe(style_table(df, currency_cols=['saldo_bruto']), hide_index=True)

        # Calculo das agregações
        saldo_carteiras = df.groupby('carteira').agg(
            **{
                'saldo_bruto': ('saldo_bruto', 'sum'),
                'Percentual': ('saldo_bruto', lambda x: x.sum() / df['saldo_bruto'].sum() * 100)
            }
        ).sort_values('saldo_bruto', ascending=False)

        saldo_inst_financeiras = df.groupby('instituicao_financeira')['saldo_bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)
        saldo_tipo_ativos = df.groupby('tipo_ativo')['saldo_bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)

        st.subheader("Agregação das Carteiras")

        # Big numbers
        row_1 = st.columns(3)
        with row_1[0]:
            st.metric("PL Total", f"R$ {saldo_carteiras['saldo_bruto'].sum():,.2f}")
        with row_1[1]:
            st.metric("PL Médio", f"R$ {saldo_carteiras['saldo_bruto'].mean():,.2f}")
        with row_1[2]:
            st.metric("PL Mediano", f"R$ {saldo_carteiras['saldo_bruto'].median():,.2f}")

        row_2 = st.columns(3)
        with row_2[0]:
            st.metric("PL Total (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['saldo_bruto'] > 1e6]['saldo_bruto'].sum():,.2f}")
        with row_2[1]:
            st.metric("PL Médio (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['saldo_bruto'] > 1e6]['saldo_bruto'].mean():,.2f}")
        with row_2[2]:
            st.metric("PL Mediano (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['saldo_bruto'] > 1e6]['saldo_bruto'].median():,.2f}")

        # saldo_bruto das carteiras
        row_3 = st.columns(2)
        with row_3[0]:
            chart_saldo_carteiras_total = create_chart(
                data=saldo_carteiras,
                columns=['saldo_bruto'],
                names=['saldo_bruto'],
                chart_type='column',
                title="Saldo das Carteiras",
                y_axis_title="R$",
                x_axis_title="Carteira",
            )
            hct.streamlit_highcharts(chart_saldo_carteiras_total)
        with row_3[1]:
            chart_saldo_carteiras_total = create_chart(
                data=saldo_carteiras,
                columns=['saldo_bruto'],
                names=['saldo_bruto'],
                chart_type='pie',
                title="Percentual de Alocação das Carteiras"
            )
            hct.streamlit_highcharts(chart_saldo_carteiras_total)

        row_4 = st.columns(2)
        with row_4[0]:
            chart_saldo_inst_financeiras = create_chart(
                data=saldo_inst_financeiras,
                columns=['Total'],
                names=['Total'],
                chart_type='pie',
                title="Saldo por Instituição Financeira",
                y_axis_title="R$",
            )
            hct.streamlit_highcharts(chart_saldo_inst_financeiras)
        with row_4[1]:
            chart_saldo_tipo_ativos = create_chart(
                data=saldo_tipo_ativos,
                columns=['Total'],
                names=['Total'],
                chart_type='pie',
                title="Saldo por Tipo de Ativo",
            )
            hct.streamlit_highcharts(chart_saldo_tipo_ativos)

        # Busca por Ativos
        st.subheader("Busca por Ativos")
        row_5 = st.columns(2)
        with row_5[0]:
            selected_asset = st.selectbox("Selecione o Ativo", [""] + sorted(df['ativo'].unique()), key="selected_asset")
            if selected_asset != "":
                total_saldo_carteira = df.groupby('carteira')['saldo_bruto'].sum()
                df_asset = df[df['ativo'] == selected_asset]

                saldo_ativo_selecionado = (
                    df_asset
                    .groupby('carteira')
                    .agg(
                        Ativo=('ativo', 'first'),
                        Descrição=('descricao', 'first'),
                        Saldo_Bruto=('saldo_bruto', 'sum')
                    )
                    .rename(columns={'saldo_bruto': 'saldo_bruto'})
                )

                # Percentual que o ativo representa dentro de cada Carteira
                saldo_ativo_selecionado['Percentual da Carteira'] = saldo_ativo_selecionado['saldo_bruto'] / total_saldo_carteira * 100

                # Ordena pelo saldo do ativo
                saldo_ativo_selecionado = saldo_ativo_selecionado.sort_values('saldo_bruto', ascending=False)

                st.write(f"Saldo do Ativo Selecionado: R$ {saldo_ativo_selecionado['saldo_bruto'].sum():,.2f}")
                st.dataframe(
                    style_table(
                        saldo_ativo_selecionado,
                        currency_cols=['saldo_bruto'],
                        percent_cols=['Percentual da Carteira']
                    )
                )
        with row_5[1]:
            if selected_asset != "":
                chart_saldo_ativos_carteiras = create_chart(
                    data=saldo_ativo_selecionado,
                    columns=['saldo_bruto'],
                    names=['saldo_bruto'],
                    chart_type='pie',
                    title="Saldo por Carteira",
                    y_axis_title="R$",
                )
                hct.streamlit_highcharts(chart_saldo_ativos_carteiras)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
