import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np

from utils.auth import check_authentication
from utils.ui import display_logo, load_css, show_data_freshness
from utils.chart_helpers import create_chart, render_chart
from utils.table import style_table

from services.position_service import load_accounts
from persevera_tools.data.providers.ws_xp import XPWSProvider


st.set_page_config(
    page_title="Zeragem de Caixa · XPCV | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Zeragem de Caixa · XPCV")

def get_balance(df: pd.DataFrame) -> pd.DataFrame:
    
    with st.spinner("Carregando saldo das contas...", show_time=True):
        provider = XPWSProvider()

        df_xp_accounts_data = []
        for index, row in df_xp_accounts.iterrows():
            df = provider.get_data("consolidated_position_d0", customer_code=row['Nr Conta'])

            # Busca saldo no Trinity
            saldo_trinity = 0
            for item in df['posicaoDetalhada.fundos.itens'][0]:
                if 'Trinity' in item['nomeFundo']:
                    saldo_trinity = float(item['valorAtual'])
                    break

            data = {
                'Portfolio': row['Portfolio'],
                'Conta': row['Nr Conta'],
                'Saldo Disponível': df['posicaoDetalhada.financeiro.valorDisponivel'].values[0],
                'Saldo Trinity': saldo_trinity
            }
            df_xp_accounts_data.append(data)

        df_xp_accounts_data = pd.DataFrame(df_xp_accounts_data)
    return df_xp_accounts_data

with st.spinner("Carregando contas sob gestão...", show_time=True):
    st.session_state.df_accounts = load_accounts()

show_data_freshness("accounts", label="Contas sob gestão", ttl_minutes=60)

df_accounts = st.session_state.df_accounts

if df_accounts is not None:
    df_xp_accounts = df_accounts[df_accounts['Custodiante'] == 'XPCV']

    df_xp_accounts_data = get_balance(df_xp_accounts)
    df_xp_accounts_data['Elegivel para Zeragem'] = (df_xp_accounts_data['Saldo Disponível'] > 100) & (df_xp_accounts_data['Saldo Trinity'] > 0)
    df_xp_accounts_data.sort_values(by=['Elegivel para Zeragem', 'Saldo Disponível'], ascending=False, inplace=True)

    st.dataframe(
        style_table(
            df_xp_accounts_data,
            numeric_cols_format_as_float=['Saldo Disponível', 'Saldo Trinity'],
            highlight_row_by_column='Elegivel para Zeragem',
            highlight_row_if_value_equals=True,
            highlight_color='lightblue',
        ),
        hide_index=True,
    )
