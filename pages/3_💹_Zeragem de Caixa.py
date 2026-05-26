import io

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime

from utils.auth import check_authentication
from utils.ui import display_logo, load_css, show_data_freshness
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

PRE_SELECTED_FUNDS = {
    '47.562.149/0001-28': 'Persevera Trinity FI RF Ref DI',
    '45.823.918/0001-79': 'Trend Cash FIC FIRF Simples',
    '27.717.359/0001-30': 'BTG CDB Plus FI RF',
}

CUSTOM_FUND_OPTION = 'Outro (informar CNPJ)'


def adjust_cnpj(cnpj: str) -> str:
    return cnpj.replace('.', '').replace('/', '').replace('-', '')


def format_cnpj(cnpj: str) -> str:
    digits = adjust_cnpj(cnpj)
    if len(digits) != 14:
        return cnpj.strip()
    return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}'


def is_valid_cnpj(cnpj: str) -> bool:
    return len(adjust_cnpj(cnpj)) == 14


def get_balance(accounts: pd.DataFrame, cnpj: str, balance_col: str) -> pd.DataFrame:
    with st.spinner('Carregando saldo das contas...', show_time=True):
        provider = XPWSProvider()
        cnpj_digits = adjust_cnpj(cnpj)

        df_xp_accounts_data = []
        for _, row in accounts.iterrows():
            df = provider.get_data('consolidated_position_d0', customer_code=row['Nr Conta'])

            fund_balance = 0
            for item in df['posicaoDetalhada.fundos.itens'][0]:
                if item['cnpj'] == cnpj_digits:
                    fund_balance = float(item['valorAtual'])
                    break

            df_xp_accounts_data.append({
                'Portfolio': row['Portfolio'],
                'Conta': row['Nr Conta'],
                'Saldo Disponível': df['posicaoDetalhada.financeiro.valorDisponivel'].values[0],
                balance_col: fund_balance,
            })

    return pd.DataFrame(df_xp_accounts_data)

if 'df_accounts' not in st.session_state or st.session_state.df_accounts is None:
    with st.spinner("Carregando contas sob gestão...", show_time=True):
        st.session_state.df_accounts = load_accounts()

show_data_freshness('accounts', label='Contas sob gestão', ttl_minutes=60)

with st.sidebar:
    st.header('Parâmetros')
    fund_options = list(PRE_SELECTED_FUNDS.values()) + [CUSTOM_FUND_OPTION]
    selected_fund = st.selectbox('Fundo para zeragem', options=fund_options)

    if selected_fund == CUSTOM_FUND_OPTION:
        custom_cnpj_input = st.text_input(
            'CNPJ do fundo',
            placeholder='XX.XXX.XXX/XXXX-XX',
            help='Informe o CNPJ do fundo de liquidez a ser utilizado na zeragem.',
        )
        fund_cnpj = format_cnpj(custom_cnpj_input) if custom_cnpj_input.strip() else ''
        fund_label = fund_cnpj or 'Fundo'
    else:
        fund_cnpj = next(cnpj for cnpj, name in PRE_SELECTED_FUNDS.items() if name == selected_fund)
        fund_label = selected_fund

df_accounts = st.session_state.df_accounts

if df_accounts is None:
    st.warning('Não foi possível carregar as contas sob gestão.')
    st.stop()

df_xp_accounts = df_accounts[df_accounts['Custodiante'] == 'XPCV']

if df_xp_accounts.empty:
    st.info('Nenhuma conta XPCV encontrada.')
    st.stop()

if selected_fund == CUSTOM_FUND_OPTION and not is_valid_cnpj(fund_cnpj):
    st.info('Informe um CNPJ válido na barra lateral para consultar os saldos.')
    st.stop()

balance_col = f'Saldo · {fund_label}'
cache_key = f'zeragem_balance_{fund_cnpj}'

if cache_key not in st.session_state:
    df_xp_accounts_data = get_balance(df_xp_accounts, fund_cnpj, balance_col)
    df_xp_accounts_data['Elegivel para Zeragem'] = (
        (df_xp_accounts_data['Saldo Disponível'] > 100) & (df_xp_accounts_data[balance_col] > 0)
    )
    df_xp_accounts_data['CNPJ do Fundo'] = fund_cnpj
    df_xp_accounts_data.sort_values(
        by=['Elegivel para Zeragem', 'Saldo Disponível'],
        ascending=False,
        inplace=True,
    )
    st.session_state[cache_key] = df_xp_accounts_data
else:
    df_xp_accounts_data = st.session_state[cache_key]

st.dataframe(
    style_table(
        df_xp_accounts_data[['Portfolio', 'Conta', 'CNPJ do Fundo', 'Saldo Disponível', balance_col, 'Elegivel para Zeragem']],
        numeric_cols_format_as_float=['Saldo Disponível', balance_col],
        highlight_row_by_column='Elegivel para Zeragem',
        highlight_row_if_value_equals=True,
        highlight_color='lightblue',
    ),
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Exportar Excel para Zeragem
# ---------------------------------------------------------------------------

df_eligible = df_xp_accounts_data[df_xp_accounts_data['Elegivel para Zeragem']].copy()

if df_eligible.empty:
    st.info('Nenhuma conta elegível para zeragem no momento.')
else:
    df_export = pd.DataFrame({
        'COD_CLIENTE': df_eligible['Conta'].values,
        'CNPJ_FUNDO': df_eligible['CNPJ do Fundo'].apply(adjust_cnpj).values,
        'VALOR_OPERACAO': df_eligible['Saldo Disponível'].values,
        'TIPO_OPERACAO': 'A',
        'CONTA_DESTINO': '',
        'ENVIO_NOTIFICACAO': 'N',
    })

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Zeragem')
    buffer.seek(0)

    st.download_button(
        label='Exportar Excel para Zeragem',
        data=buffer,
        file_name=f'zeragem_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        icon=':material/download:',
    )
