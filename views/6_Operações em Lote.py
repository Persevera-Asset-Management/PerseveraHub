import io

import pandas as pd
import streamlit as st
from datetime import datetime

from utils.ui import show_data_freshness
from utils.table import style_table

from services.position_service import load_accounts
from persevera_tools.data.providers.ws_xp import XPWSProvider
from persevera_tools.data.providers.ws_btg import BTGWSProvider

ZERAGEM_CUSTODIANS = ('XPCV', 'BTG CTVM')

st.title("Operações em Lote")

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

def format_btg_account(nr_conta: str) -> str:
    return str(nr_conta).strip().zfill(9)

def get_balance_xp(accounts: pd.DataFrame, cnpj: str, balance_col: str) -> pd.DataFrame:
    provider = XPWSProvider()
    cnpj_digits = adjust_cnpj(cnpj)
    rows = []

    for _, row in accounts.iterrows():
        df = provider.get_data('consolidated_position_d0', customer_code=row['Nr Conta'])

        fund_balance = 0.0
        for item in df['posicaoDetalhada.fundos.itens'][0]:
            if item['cnpj'] == cnpj_digits:
                fund_balance = float(item['valorAtual'])
                break

        rows.append({
            'Portfolio': row['Portfolio'],
            'Custodiante': row['Custodiante'],
            'Conta': row['Nr Conta'],
            'Saldo Disponível': float(df['posicaoDetalhada.financeiro.valorDisponivel'].values[0]),
            balance_col: fund_balance,
        })

    return pd.DataFrame(rows)

def get_balance_btg(accounts: pd.DataFrame, cnpj: str, balance_col: str) -> pd.DataFrame:
    provider = BTGWSProvider()
    cnpj_digits = adjust_cnpj(cnpj)
    rows = []

    for _, row in accounts.iterrows():
        account_number = format_btg_account(row['Nr Conta'])

        summary_df = provider.get_position_by_asset_class(account_number, 'SummaryAccounts')
        cash_balance = 0.0
        if not summary_df.empty and 'MarketAbbreviation' in summary_df.columns:
            cc_rows = summary_df[summary_df['MarketAbbreviation'] == 'CC']
            if not cc_rows.empty:
                cash_balance = float(cc_rows['EndPositionValue'].astype(float).sum())

        funds_df = provider.get_position_by_asset_class(account_number, 'InvestmentFund')
        fund_balance = 0.0
        fund_cge_code = ''
        if not funds_df.empty and 'FundCNPJCode' in funds_df.columns:
            matching = funds_df[funds_df['FundCNPJCode'].astype(str) == cnpj_digits]
            if not matching.empty:
                if 'Acquisition_GrossAssetValue' in matching.columns:
                    fund_balance = float(matching['Acquisition_GrossAssetValue'].astype(float).sum())
                if 'FundCGECode' in matching.columns:
                    fund_cge_code = str(matching.iloc[0]['FundCGECode']).strip()

        rows.append({
            'Portfolio': row['Portfolio'],
            'Custodiante': row['Custodiante'],
            'Conta': account_number,
            'Código Fundo (CGE)': fund_cge_code,
            'Saldo Disponível': cash_balance,
            balance_col: fund_balance,
        })

    return pd.DataFrame(rows)

def finalize_balance_df(
    df: pd.DataFrame,
    fund_cnpj: str,
    balance_col: str,
    *,
    require_fund_cge: bool = False,
) -> pd.DataFrame:
    df = df.copy()
    eligible = (df['Saldo Disponível'] > 100) & (df[balance_col] > 0)
    if require_fund_cge and 'Código Fundo (CGE)' in df.columns:
        eligible &= df['Código Fundo (CGE)'].astype(str).str.strip().ne('')
    df['Elegivel para Zeragem'] = eligible
    df['CNPJ do Fundo'] = fund_cnpj
    return df.sort_values(
        by=['Elegivel para Zeragem', 'Saldo Disponível'],
        ascending=False,
    )

def balance_cache_key(custodian: str, fund_cnpj: str) -> str:
    slug = custodian.lower().replace(' ', '_')
    version = 'v3' if custodian == 'BTG CTVM' else 'v2'
    return f'zeragem_balance_{slug}_{version}_{fund_cnpj}'

if 'df_accounts' not in st.session_state or st.session_state.df_accounts is None:
    with st.spinner("Carregando contas sob gestão...", show_time=True):
        st.session_state.df_accounts = load_accounts()

show_data_freshness('accounts', label='Contas sob gestão', ttl_minutes=60)

df_accounts = st.session_state.df_accounts
xp_account_count = 0
btg_account_count = 0
if df_accounts is not None:
    xp_account_count = int((df_accounts['Custodiante'] == 'XPCV').sum())
    btg_account_count = int((df_accounts['Custodiante'] == 'BTG CTVM').sum())

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

    cnpj_valid = selected_fund != CUSTOM_FUND_OPTION or is_valid_cnpj(fund_cnpj)

    st.divider()
    st.subheader('Atualização de saldos')
    btn_update_xp = st.button(
        'Atualizar XPCV',
        disabled=not cnpj_valid or xp_account_count == 0,
        width='stretch',
    )
    btn_update_btg = st.button(
        'Atualizar BTG CTVM',
        disabled=not cnpj_valid or btg_account_count == 0,
        width='stretch',
    )

if df_accounts is None:
    st.warning('Não foi possível carregar as contas sob gestão.')
    st.stop()

df_zeragem_accounts = df_accounts[df_accounts['Custodiante'].isin(ZERAGEM_CUSTODIANS)]

if df_zeragem_accounts.empty:
    st.info('Nenhuma conta XPCV ou BTG CTVM encontrada.')
    st.stop()

if not cnpj_valid:
    st.info('Informe um CNPJ válido na barra lateral para consultar os saldos.')
    st.stop()

balance_col = f'Saldo · {fund_label}'
xp_cache_key = balance_cache_key('XPCV', fund_cnpj)
btg_cache_key = balance_cache_key('BTG CTVM', fund_cnpj)

df_xp_accounts = df_zeragem_accounts[df_zeragem_accounts['Custodiante'] == 'XPCV']
df_btg_accounts = df_zeragem_accounts[df_zeragem_accounts['Custodiante'] == 'BTG CTVM']

if btn_update_xp and not df_xp_accounts.empty:
    with st.spinner('Carregando saldos XPCV...', show_time=True):
        st.session_state[xp_cache_key] = finalize_balance_df(
            get_balance_xp(df_xp_accounts, fund_cnpj, balance_col),
            fund_cnpj,
            balance_col,
        )

if btn_update_btg and not df_btg_accounts.empty:
    with st.spinner('Carregando saldos BTG CTVM...', show_time=True):
        st.session_state[btg_cache_key] = finalize_balance_df(
            get_balance_btg(df_btg_accounts, fund_cnpj, balance_col),
            fund_cnpj,
            balance_col,
            require_fund_cge=True,
        )

loaded_parts = []
loaded_labels = []
if xp_cache_key in st.session_state:
    loaded_parts.append(st.session_state[xp_cache_key])
    loaded_labels.append('XPCV')
if btg_cache_key in st.session_state:
    loaded_parts.append(st.session_state[btg_cache_key])
    loaded_labels.append('BTG CTVM')

if not loaded_parts:
    st.info(
        'Clique em **Atualizar XPCV** ou **Atualizar BTG CTVM** na barra lateral '
        'para carregar os saldos do fundo selecionado.'
    )
    st.stop()

df_accounts_data = pd.concat(loaded_parts, ignore_index=True)
df_accounts_data.sort_values(
    by=['Elegivel para Zeragem', 'Saldo Disponível'],
    ascending=False,
    inplace=True,
)

pending_labels = [
    label
    for label, count, cache_key in (
        ('XPCV', xp_account_count, xp_cache_key),
        ('BTG CTVM', btg_account_count, btg_cache_key),
    )
    if count > 0 and cache_key not in st.session_state
]
if pending_labels:
    st.caption(
        f'Saldos carregados: {", ".join(loaded_labels)}. '
        f'Pendentes: {", ".join(pending_labels)}.'
    )
else:
    st.caption(f'Saldos carregados: {", ".join(loaded_labels)}.')

display_cols = ['Portfolio', 'Custodiante', 'Conta', 'CNPJ do Fundo']
if (df_accounts_data['Custodiante'] == 'BTG CTVM').any():
    display_cols.append('Código Fundo (CGE)')
display_cols.extend(['Saldo Disponível', balance_col, 'Elegivel para Zeragem'])

st.dataframe(
    style_table(
        df_accounts_data[display_cols],
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

df_eligible = df_accounts_data[df_accounts_data['Elegivel para Zeragem']].copy()

if df_eligible.empty:
    st.info('Nenhuma conta elegível para zeragem no momento.')
else:
    df_xp_eligible = df_eligible[df_eligible['Custodiante'] == 'XPCV']
    if not df_xp_eligible.empty:
        df_export_xp = pd.DataFrame({
            'COD_CLIENTE': df_xp_eligible['Conta'].values,
            'CNPJ_FUNDO': df_xp_eligible['CNPJ do Fundo'].apply(adjust_cnpj).values,
            'VALOR_OPERACAO': df_xp_eligible['Saldo Disponível'].values,
            'TIPO_OPERACAO': 'A',
            'CONTA_DESTINO': '',
            'ENVIO_NOTIFICACAO': 'N',
        })

        buffer_xp = io.BytesIO()
        with pd.ExcelWriter(buffer_xp, engine='openpyxl') as writer:
            df_export_xp.to_excel(writer, index=False, sheet_name='Zeragem')
        buffer_xp.seek(0)

        st.download_button(
            label='Exportar Excel para Zeragem (XP)',
            data=buffer_xp,
            file_name=f'zeragem_caixa_xp_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            icon=':material/download:',
        )

    df_btg_eligible = df_eligible[df_eligible['Custodiante'] == 'BTG CTVM']
    if not df_btg_eligible.empty:
        operation_date = datetime.now().strftime('%d/%m/%Y')
        df_export_btg = pd.DataFrame({
            'conta': df_btg_eligible['Conta'].values,
            'codigo_fundo': df_btg_eligible['Código Fundo (CGE)'].values,
            'valor_operacao': df_btg_eligible['Saldo Disponível'].values,
            'tipo_operacao': 'A',
            'resgate_total': 'N',
            'data_operacao': operation_date,
            'alavancagem_btg': 'N',
            'pos_horario': 'N',
            'resgate_fmp': 'N',
            'modalidade_resgate_fmp': '',
        })

        buffer_btg = io.BytesIO()
        with pd.ExcelWriter(buffer_btg, engine='openpyxl') as writer:
            df_export_btg.to_excel(writer, index=False, sheet_name='Zeragem')
        buffer_btg.seek(0)

        st.download_button(
            label='Exportar Excel para Zeragem (BTG)',
            data=buffer_btg,
            file_name=f'zeragem_caixa_btg_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            icon=':material/download:',
        )
