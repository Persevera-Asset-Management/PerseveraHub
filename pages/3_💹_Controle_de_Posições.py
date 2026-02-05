import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
from utils.chart_helpers import create_chart, render_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from configs.pages.visualizador_de_carteiras import CODIGOS_CARTEIRAS_ADM
from utils.auth import check_authentication
from services.position_service import (
    load_positions,
    load_target_allocations,
    load_accounts,
    load_instruments_fgc,
    get_latest_date_data,
    get_emissor_column,
    ASSET_CLASSES_ORDER,
)

st.set_page_config(
    page_title="Controle de Posições | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Controle de Posições")

# Definição dos parâmetros
with st.sidebar:
    st.header("Parâmetros")
    selected_carteira = st.selectbox(
        "Carteira selecionada",
        options=[""] + sorted(CODIGOS_CARTEIRAS_ADM.keys())
    )


def load_data():
    """Carrega todos os dados necessários para a página."""
    with st.spinner("Carregando dados...", show_time=True):
        df_positions = load_positions(include_custodiante=True, include_vencimento_rf=True)
        st.session_state.df_positions = df_positions
        st.session_state.instruments_fgc = load_instruments_fgc()
        st.session_state.df_target_allocations = load_target_allocations(include_limits=True)
        st.session_state.df_accounts = load_accounts()
        st.session_state.df = df_positions[df_positions['Portfolio'] == selected_carteira]


if selected_carteira != "":
    load_data()

    df = st.session_state.df
    df_target_allocations = st.session_state.df_target_allocations
    df_accounts = st.session_state.df_accounts
    instruments_fgc = st.session_state.instruments_fgc

    try:
        st.subheader(selected_carteira)

        # Informações Gerais
        account_info = df_accounts[df_accounts['Portfolio'] == selected_carteira]
        st.code(f"""
        {account_info['Nome Completo'].values[0]} ({selected_carteira})

        Conta(s): {', '.join(account_info['Nr Conta'].values)}
        Custodiante(s): {', '.join(account_info['Custodiante'].values)}
        """, language='markdown')

        # Composição Completa
        df_portfolio_positions = df.groupby(
            [pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Nome Ativo Completo', 'Classificação do Conjunto']
        ).agg(**{
            'Quantidade': ('Quantidade', 'sum'),
            'Valor Unitário': ('Valor Unitário', 'mean'),
            'Saldo': ('Saldo', 'sum')
        })

        df_portfolio_positions_current = get_latest_date_data(df_portfolio_positions).copy()
        df_portfolio_positions_current['%'] = (
            df_portfolio_positions_current['Saldo'] / df_portfolio_positions_current['Saldo'].sum() * 100
        )

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
            df_policy_investments_current = get_latest_date_data(df_policy_investments_current)
            df_policy_investments_current = df_policy_investments_current.mul(100)
            df_policy_investments_current = df_policy_investments_current.reindex(ASSET_CLASSES_ORDER)

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

        tabs = st.tabs(["Alocação Atual", "Alocação Hierárquica", "Emissores", "Instrumentos", "Custodiantes", "Vencimentos e FGC"])

        with tabs[0]: # Alocação Atual

            cols = st.columns(2)
            with cols[0]:
                df_portfolio_composition = df.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Classificação do Conjunto']
                ).agg(**{'Saldo': ('Saldo', 'sum')})
                df_portfolio_composition_current = get_latest_date_data(df_portfolio_composition)
                df_portfolio_composition_current = df_portfolio_composition_current.reindex(ASSET_CLASSES_ORDER).dropna()

                chart_portfolio_composition = create_chart(
                    data=df_portfolio_composition_current,
                    columns=['Saldo'],
                    names=['Saldo'],
                    chart_type='donut',
                    title="Alocação Atual",
                    y_axis_title="%",
                )
                hct.streamlit_highcharts(chart_portfolio_composition)
            
            with cols[1]:
                if selected_carteira in df_target_allocations.index:
                    df_target_allocations_current = df_target_allocations.loc[selected_carteira].dropna(subset=['Target'])
                    df_target_allocations_current = get_latest_date_data(df_target_allocations_current)
                    df_target_allocations_current = df_target_allocations_current * df_portfolio_positions_current['Saldo'].sum()
                    df_target_allocations_current = df_target_allocations_current.reindex(ASSET_CLASSES_ORDER)

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

        with tabs[1]: # Alocação Hierárquica
            df_inner_chart = df_portfolio_composition_current.reset_index()
            df_outer_chart = df_portfolio_positions_current.reset_index()
            category_order = {cat: i for i, cat in enumerate(df_inner_chart['Classificação do Conjunto'])}
            df_outer_chart['_cat_order'] = df_outer_chart['Classificação do Conjunto'].map(category_order)
            df_outer_chart = df_outer_chart.sort_values(
                by=['_cat_order', 'Saldo'],
                ascending=[True, False]  # Categoria na ordem, Saldo decrescente
            ).drop(columns=['_cat_order'])

            options_nested = create_chart(
                data=df_outer_chart,
                columns='Saldo',
                x_column='Nome Ativo Completo',  # Ativos individuais no anel externo
                chart_type='nested_pie',
                title='Alocação Hierárquica',
                inner_data=df_inner_chart,
                inner_y_column='Saldo',
                inner_x_column='Classificação do Conjunto',  # Classes no anel interno
                inner_series_name='Classes',
                names='Ativos',
                inner_size="55%",
                outer_inner_size="55%",
                center_hole_size="30%",
                outer_parent_column='Classificação do Conjunto',  # Liga anel externo ao interno
                enable_fullscreen_on_dblclick=True,
            )

            render_chart(options_nested)

        with tabs[2]: # Emissores
            df_emissor = get_emissor_column(df)
            df_portfolio_positions_emissores = df_emissor.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Emissor']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_emissores_current = get_latest_date_data(df_portfolio_positions_emissores)
            df_portfolio_positions_emissores_current = df_portfolio_positions_emissores_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_emissores = create_chart(
                data=df_portfolio_positions_emissores_current,
                columns=['Saldo'],
                names=['Emissor'],
                chart_type='donut',
                title="Emissores",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_emissores)

        with tabs[3]: # Instrumentos
            df_instrument = df.copy()
            df_instrument['Instrumento'] = df_instrument['Classificação Instrumento']
            df_portfolio_positions_instruments = df_instrument.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Instrumento']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_instruments_current = get_latest_date_data(df_portfolio_positions_instruments)
            df_portfolio_positions_instruments_current = df_portfolio_positions_instruments_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_instruments = create_chart(
                data=df_portfolio_positions_instruments_current,
                columns=['Saldo'],
                names=['Instrumento'],
                chart_type='donut',
                title="Instrumentos",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_instruments)

        with tabs[4]: # Custodiantes
            df_custodiante = df.copy()
            df_portfolio_positions_custodiante = df_custodiante.groupby(
                [pd.Grouper(key='Data Posição', freq='D'), 'Custodiante Acronimo']
            ).agg(**{'Saldo': ('Saldo', 'sum')})
            df_portfolio_positions_custodiante_current = get_latest_date_data(df_portfolio_positions_custodiante)
            df_portfolio_positions_custodiante_current = df_portfolio_positions_custodiante_current.sort_values(
                by='Saldo', ascending=False
            )

            chart_portfolio_positions_custodiante = create_chart(
                data=df_portfolio_positions_custodiante_current,
                columns=['Saldo'],
                names=['Custodiante'],
                chart_type='donut',
                title="Custodiantes",
                y_axis_title="%",
            )
            hct.streamlit_highcharts(chart_portfolio_positions_custodiante)

        with tabs[5]: # Vencimentos e FGC
            cols = st.columns(2)
            with cols[0]:
                st.markdown("##### Vencimentos")
                df_data_vencimento_rf = df.copy()
                df_data_vencimento_rf = df_data_vencimento_rf.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Nome Ativo', 'Nome Ativo Completo',
                    'Classificação do Conjunto', 'Classificação Instrumento', 'Data de Vencimento RF']
                ).agg(**{
                    'Quantidade': ('Quantidade', 'sum'),
                    'Valor Unitário': ('Valor Unitário', 'mean'),
                    'Saldo': ('Saldo', 'sum')
                })
                df_data_vencimento_rf_current = get_latest_date_data(df_data_vencimento_rf).copy()
                df_data_vencimento_rf_current = df_data_vencimento_rf_current.reset_index().set_index(['Nome Ativo'])
                df_data_vencimento_rf_current['Data de Vencimento'] = pd.to_datetime(
                    df_data_vencimento_rf_current['Data de Vencimento RF']
                )
                df_data_vencimento_rf_current = df_data_vencimento_rf_current.sort_values(
                    by='Data de Vencimento', ascending=True
                )

                st.dataframe(
                    style_table(
                        df_data_vencimento_rf_current[[
                            'Nome Ativo Completo', 'Classificação do Conjunto', 'Classificação Instrumento',
                            'Data de Vencimento', 'Quantidade', 'Valor Unitário', 'Saldo'
                        ]],
                        date_cols=['Data de Vencimento'],
                        numeric_cols_format_as_float=['Valor Unitário', 'Saldo'],
                        numeric_cols_format_as_int=['Quantidade'],
                    )
                )

            with cols[1]:
                df_fgc = df.copy()
                df_fgc = df_fgc[df_fgc['Classificação Instrumento'].isin(instruments_fgc)]

                df_fgc = df_fgc.groupby(
                    [pd.Grouper(key='Data Posição', freq='D'), 'Nome Emissor']
                ).agg(**{'Saldo': ('Saldo', 'sum')})

                if len(df_fgc) > 0:
                    df_fgc_current = get_latest_date_data(df_fgc).copy()

                    chart_portfolio_positions_fgc = create_chart(
                        data=df_fgc_current.sort_values(by='Saldo', ascending=False),
                        columns=['Saldo'],
                        names=['Nome Emissor'],
                        chart_type='column',
                        title="Cobertura do FGC",
                        y_axis_title="Total (R$)",
                        x_axis_title="Banco Emissor",
                        show_legend=False,
                        horizontal_line={
                            "value": 250000,
                            "color": "#FF0000",
                            "width": 2,
                            "label": {"text": "Limite por Emissor", "align": "left"}
                        }
                    )
                    hct.streamlit_highcharts(chart_portfolio_positions_fgc)
                else:
                    st.info("Cliente não possui ativos cobertos pelo FGC")

    except KeyError as e:
        st.error(f"Erro ao acessar dados: campo {e} não encontrado")
    except IndexError as e:
        st.error(f"Erro ao acessar dados: índice inválido - {e}")
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
