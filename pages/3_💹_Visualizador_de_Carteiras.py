import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from datetime import datetime
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from persevera_tools.data.providers import ComdinheiroProvider
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS
from utils.auth import check_authentication

st.set_page_config(
    page_title="Visualizador de Carteiras | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Visualizador de Carteiras")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteiras = st.multiselect("Carteiras selecionadas", options=CODIGOS_CARTEIRAS, default=CODIGOS_CARTEIRAS)
    selected_date = st.date_input("Data", format="DD/MM/YYYY", value=datetime.now(), min_value=datetime(2024, 1, 1), max_value=datetime.now())
    btn_run = st.button("Run")

if 'df' not in st.session_state:
    st.session_state.df = None

if btn_run:
    with st.spinner("Carregando dados..."):
        provider = ComdinheiroProvider()
        st.session_state.df = provider.get_data(
            category='portfolio_positions',
            portfolios=selected_carteiras,
            date_report=selected_date.strftime('%Y-%m-%d')
        )
        if "selected_asset" in st.session_state:
            st.session_state.selected_asset = ""

df = st.session_state.df
if df is not None:
    try:
        # Calculo das agregações
        saldo_carteiras = df.groupby('carteira').agg(
            **{
                'saldo_bruto': ('saldo_bruto', 'sum'),
                'Percentual': ('saldo_bruto', lambda x: x.sum() / df['saldo_bruto'].sum() * 100)
            }
        ).sort_values('saldo_bruto', ascending=False)

        saldo_inst_financeiras = df.groupby('instituicao_financeira')['saldo_bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)
        saldo_tipo_ativos = df.groupby('tipo_ativo')['saldo_bruto'].sum().to_frame('Total').sort_values('Total', ascending=False)

        tabs = st.tabs(["Visão Geral", "Busca por Ativos", "Busca por Cliente"])

        with tabs[0]:
            st.subheader("Visão Geral")

            with st.expander("Dados Brutos", expanded=False):
                st.dataframe(style_table(df, currency_cols=['saldo_bruto']), hide_index=True)

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

        with tabs[1]:
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
                            ativo=('ativo', 'first'),
                            descricao=('descricao', 'first'),
                            saldo_bruto=('saldo_bruto', 'sum')
                        )
                    )
                    
                    # Percentual que o ativo representa dentro de cada Carteira
                    saldo_ativo_selecionado['pct_carteira'] = saldo_ativo_selecionado['saldo_bruto'] / total_saldo_carteira * 100

                    # Ordena pelo saldo do ativo
                    saldo_ativo_selecionado = saldo_ativo_selecionado.sort_values('saldo_bruto', ascending=False)

                    st.write(f"Saldo do Ativo Selecionado: R$ {saldo_ativo_selecionado['saldo_bruto'].sum():,.2f}")
                    st.dataframe(
                        style_table(
                            saldo_ativo_selecionado,
                            currency_cols=['saldo_bruto'],
                            percent_cols=['pct_carteira']
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

        with tabs[2]:
            st.subheader("Busca por Cliente")
            row_6 = st.columns(2)
            with row_6[0]:
                selected_carteira_cliente = st.selectbox("Selecione a Carteira", [""] + sorted(df['carteira'].unique()), key="selected_carteira_cliente")

            if selected_carteira_cliente:
                df_cliente = df[df['carteira'] == selected_carteira_cliente]
                pl_total_cliente = df_cliente['saldo_bruto'].sum()

                st.metric("PL Total da Carteira", f"R$ {pl_total_cliente:,.2f}")

                # Gráfico de alocação por tipo de ativo
                alocacao_tipo_ativo = (
                    df_cliente
                    .groupby('tipo_ativo')['saldo_bruto']
                    .sum()
                    .reset_index()
                    .sort_values('saldo_bruto', ascending=False)
                )
                alocacao_tipo_ativo['Percentual'] = (alocacao_tipo_ativo['saldo_bruto'] / pl_total_cliente) * 100
                
                chart_alocacao_tipo_ativo = create_chart(
                    data=alocacao_tipo_ativo.set_index('tipo_ativo'),
                    columns=['Percentual'],
                    names=['Percentual'],
                    chart_type='column',
                    title='Alocação por Tipo de Ativo',
                    y_axis_title='%',
                    x_axis_title='Tipo de Ativo'
                )
                hct.streamlit_highcharts(chart_alocacao_tipo_ativo)
                
                # Tabela de posições
                st.markdown("## Posições da Carteira")
                posicoes_cliente = (
                    df_cliente[[
                        'ativo', 'descricao', 'tipo_ativo', 'instituicao_financeira', 'saldo_bruto'
                    ]]
                    .sort_values('saldo_bruto', ascending=False)
                )
                st.dataframe(
                    style_table(posicoes_cliente, currency_cols=['saldo_bruto']),
                    hide_index=True,
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
