import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
import streamlit_highcharts as hct

st.set_page_config(
    page_title="Visualizador de Carteiras | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Visualizador de Carteiras")

uploaded_file = st.file_uploader("Faça o upload do arquivo Excel exportado pelo ComDinheiro", type=["xlsx", "xls"], accept_multiple_files=False)
# uploaded_file = r"C:\Users\ThalesCarmo\Downloads\Relatório_Gestão_raw.xlsx"

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("Arquivo carregado com sucesso!")
        
        with st.expander("Dados Brutos", expanded=False):
            st.dataframe(style_table(df, currency_cols=['Saldo Bruto']), hide_index=True)

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

        # Big numbers
        row_1 = st.columns(3)
        with row_1[0]:
            st.metric("PL Total", f"R$ {saldo_carteiras['Saldo Bruto'].sum():,.2f}")
        with row_1[1]:
            st.metric("PL Médio", f"R$ {saldo_carteiras['Saldo Bruto'].mean():,.2f}")
        with row_1[2]:
            st.metric("PL Mediano", f"R$ {saldo_carteiras['Saldo Bruto'].median():,.2f}")

        row_2 = st.columns(3)
        with row_2[0]:
            st.metric("PL Total (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['Saldo Bruto'] > 1e6]['Saldo Bruto'].sum():,.2f}")
        with row_2[1]:
            st.metric("PL Médio (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['Saldo Bruto'] > 1e6]['Saldo Bruto'].mean():,.2f}")
        with row_2[2]:
            st.metric("PL Mediano (acima de R$ 1MM)", f"R$ {saldo_carteiras[saldo_carteiras['Saldo Bruto'] > 1e6]['Saldo Bruto'].median():,.2f}")

        # Saldo bruto das carteiras
        row_3 = st.columns(2)
        with row_3[0]:
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
        with row_3[1]:
            chart_saldo_carteiras_total = create_chart(
                data=saldo_carteiras,
                columns=['Saldo Bruto'],
                names=['Saldo Bruto'],
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
            selected_asset = st.selectbox("Selecione o Ativo", [""] + sorted(df['Ativo'].unique()))
            if selected_asset != "":
                total_saldo_carteira = df.groupby('Carteira')['Saldo Bruto'].sum()
                df_asset = df[df['Ativo'] == selected_asset]

                saldo_ativo_selecionado = (
                    df_asset
                    .groupby('Carteira')
                    .agg(
                        Ativo=('Ativo', 'first'),
                        Descrição=('Descrição', 'first'),
                        Saldo_Bruto=('Saldo Bruto', 'sum')
                    )
                    .rename(columns={'Saldo_Bruto': 'Saldo Bruto'})
                )

                # Percentual que o ativo representa dentro de cada Carteira
                saldo_ativo_selecionado['Percentual da Carteira'] = saldo_ativo_selecionado['Saldo Bruto'] / total_saldo_carteira * 100

                # Ordena pelo saldo do ativo
                saldo_ativo_selecionado = saldo_ativo_selecionado.sort_values('Saldo Bruto', ascending=False)

                st.write(f"Saldo do Ativo Selecionado: R$ {saldo_ativo_selecionado['Saldo Bruto'].sum():,.2f}")
                st.dataframe(
                    style_table(
                        saldo_ativo_selecionado,
                        currency_cols=['Saldo Bruto'],
                        percent_cols=['Percentual da Carteira']
                    )
                )
        with row_5[1]:
            if selected_asset != "":
                chart_saldo_ativos_carteiras = create_chart(
                    data=saldo_ativo_selecionado,
                    columns=['Saldo Bruto'],
                    names=['Saldo Bruto'],
                    chart_type='pie',
                    title="Saldo por Carteira",
                    y_axis_title="R$",
                )
                hct.streamlit_highcharts(chart_saldo_ativos_carteiras)

    except Exception as e:
        st.error(f"Ocorreu um erro ao ler o arquivo: {e}")
