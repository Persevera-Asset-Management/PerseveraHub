import streamlit as st
import pandas as pd
import numpy as np
import streamlit_highcharts as hct
from dateutil.relativedelta import relativedelta
from persevera_tools.data import get_funds_data, get_persevera_peers, get_series
from utils.table import style_table
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Análise de Fundos | Persevera",
    page_icon="📈",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Análise de Fundos")

peers = get_persevera_peers()

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_fund_data(fund_name):
    """
    Loads NAV and Total Equity data for a given fund and its peers.
    """
    if peers.empty:
        st.warning("Peers data is not loaded. Cannot load fund data.")
        return pd.DataFrame(), pd.DataFrame()

    fund_peers = peers[peers['persevera_group'] == fund_name].copy()

    # Adjustment for Compass fund
    if 'fund_cnpj' in fund_peers.columns:
        fund_peers['fund_cnpj'] = fund_peers['fund_cnpj'].str.replace('32.041.825/0001-40', '44.417.598/0001-94', regex=False)
    if 'short_name' in fund_peers.columns:
        fund_peers['short_name'] = fund_peers['short_name'].str.replace('Persevera Compass Advisory FIC FIMs', 'Persevera Nemesis Total Return FIM', regex=False)
    
    if fund_peers.empty:
        st.warning(f"No peers found for fund group: {fund_name}")
        return pd.DataFrame(), pd.DataFrame()

    fund_cnpjs = list(fund_peers['fund_cnpj'].unique())

    try:
        df = get_funds_data(cnpjs=fund_cnpjs, fields=['fund_nav', 'fund_total_equity'])

    except Exception as e:
        st.error(f"Error calling get_funds_data: {e}")
        return pd.DataFrame(), pd.DataFrame()

    if df.empty:
        st.warning(f"No data returned by get_funds_data for CNPJs: {fund_cnpjs}")
        return pd.DataFrame(), pd.DataFrame()

    # Map fund_name using peers DataFrame
    df = df.swaplevel(axis=1).stack()
    df.columns = df.columns.map(peers.set_index('fund_cnpj')['short_name'].to_dict())
    df = df.unstack().swaplevel(axis=1)

    # Select NAV data
    if 'fund_nav' not in df.columns:
        st.error("fund_nav column missing for NAV pivot.")
        nav = pd.DataFrame()
    else:
        nav = df['fund_nav']
        if not nav.empty:
            persevera_cols_nav = nav.filter(like='Persevera').columns
            if not persevera_cols_nav.empty:
                nav = nav.dropna(subset=[persevera_cols_nav[0]])
            nav = nav.sort_index(axis=1)

    # Select Total Equity data
    if 'fund_total_equity' not in df.columns:
        st.error("fund_total_equity column missing for Total Equity pivot.")
        total_equity = pd.DataFrame()
    else:
        total_equity = df['fund_total_equity']
        if not total_equity.empty:
            persevera_cols_equity = total_equity.filter(like='Persevera').columns
            if not persevera_cols_equity.empty:
                total_equity = total_equity.dropna(subset=[persevera_cols_equity[0]])
            total_equity = total_equity.sort_index(axis=1)
    
    return nav, total_equity

@st.cache_data(ttl=3600)
def get_performance_table(nav, total_equity, start_date, end_date):
    df = nav.ffill()
    if df.empty:
        return pd.DataFrame()

    gp_daily = df.groupby(pd.Grouper(level='date', freq="1D")).last()
    gp_monthly = df.groupby(pd.Grouper(level='date', freq="ME")).last()
    gp_yearly = df.groupby(pd.Grouper(level='date', freq="YE")).last()

    benchmarks = ['CDI', 'Ibovespa', 'SMLL']

    day_ret = gp_daily.pct_change(fill_method=None).iloc[-1]
    mtd_ret = gp_monthly.pct_change(fill_method=None).iloc[-1]
    ytd_ret = gp_yearly.pct_change(fill_method=None).iloc[-1]

    def get_relative_return(months):
        start_date_calc = df.index[-1] - relativedelta(months=months)
        period_df = df.loc[start_date_calc:]
        if len(period_df) > 1:
            return df.iloc[-1] / period_df.iloc[0] - 1
        return pd.Series(np.nan, index=df.columns)

    ret_3m = get_relative_return(3)
    ret_6m = get_relative_return(6)
    ret_12m = get_relative_return(12)
    ret_24m = get_relative_return(24)
    ret_36m = get_relative_return(36)

    custom_period_df = df.loc[start_date:end_date]
    if len(custom_period_df) > 1:
        custom_ret = custom_period_df.iloc[-1] / custom_period_df.iloc[0] - 1
    else:
        custom_ret = pd.Series(np.nan, index=df.columns)

    returns = {
        'day': day_ret,
        'mtd': mtd_ret,
        'ytd': ytd_ret,
        '3m': ret_3m,
        '6m': ret_6m,
        '12m': ret_12m,
        '24m': ret_24m,
        '36m': ret_36m,
        'custom': custom_ret,
    }

    ranks = {
        f'{key}_rank': value.drop(benchmarks, errors='ignore').rank(ascending=False)
        for key, value in returns.items()
    }

    time_frames = {**returns, **ranks}

    df_result = pd.DataFrame(time_frames)
    df_result = df_result.apply(lambda x: x * 100 if 'rank' not in x.name else x)
    
    pl_series = pd.Series(np.nan, index=df_result.index)
    if not total_equity.empty:
        last_pl = total_equity.iloc[-1]
        pl_series = last_pl.reindex(df_result.index)

    df_result = df_result.assign(PL=pl_series)
    df_result['type'] = df_result.index.map(lambda x: 'Persevera' if 'Persevera' in x else ('Benchmark' if x in benchmarks else 'Peer'))
    
    col_order = ['type', 'PL'] + list(time_frames.keys())
    df_result = df_result[col_order]
    
    df_result = df_result.reset_index().rename(columns={'index': 'fund_name'})
    return df_result

@st.cache_data(ttl=3600)
def calculate_performance(df):
    if df.empty or df.shape[0] < 2:
        return df
    df_pct_change = df.ffill().pct_change(fill_method=None)
    cumulative_returns = (1 + df_pct_change).cumprod()
    cumulative_returns.iloc[0] = 1 
    final_returns = cumulative_returns.sub(1)
    final_returns = final_returns.ffill()
    return final_returns

@st.cache_data(ttl=3600)
def load_benchmark_data(fund_name, _nav_index):
    benchmark_map = {'Trinity': ('br_cdi_index',),
                     'Yield': ('br_cdi_index',),
                     'Phoenix': ('br_cdi_index',),
                     'Compass': ('br_cdi_index',),
                     'Nemesis': ('br_cdi_index', 'br_ibovespa', 'br_smll'),
                     'Proteus': ('br_cdi_index', 'br_ibovespa', 'br_smll')}

    codes_to_fetch = benchmark_map.get(fund_name, ('br_cdi_index',)) # Default to CDI
    df_benchmark = get_series(list(codes_to_fetch), start_date=_nav_index.min(), field='close')
    
    # Ensure df_benchmark is a DataFrame before renaming columns
    if isinstance(df_benchmark, pd.Series):
        df_benchmark = df_benchmark.to_frame('br_cdi_index')

    df_benchmark = df_benchmark.rename(columns={'br_cdi_index': 'CDI', 'br_ibovespa': 'Ibovespa', 'br_smll': 'SMLL'})
    return df_benchmark

with st.sidebar:
    fund_names_list = ['Trinity', 'Yield', 'Phoenix', 'Compass', 'Nemesis', 'Proteus']
    selected_fund_name = st.selectbox("Selecione o fundo:", fund_names_list, index=4)

st.header(selected_fund_name)

# Load data for the selected fund
nav_data, total_equity_data = load_fund_data(selected_fund_name)

if nav_data.empty:
    st.warning(f"Não foi possível carregar dados de NAV para o fundo {selected_fund_name}.")
    if not total_equity_data.empty:
        st.subheader(f"Patrimônio Líquido para {selected_fund_name}")
        st.line_chart(total_equity_data.filter(like='Persevera'))

# Determine the Persevera fund's actual name from the loaded data
persevera_fund_col_name = next((col for col in nav_data.columns if 'Persevera' in col), None)
if not persevera_fund_col_name:
    st.error("Não foi possível identificar a coluna do fundo Persevera principal nos dados carregados.")
    
# Load benchmark data
benchmark_df = load_benchmark_data(selected_fund_name, nav_data.index)

# Merge NAV data with benchmark data
if not isinstance(benchmark_df.index, pd.DatetimeIndex):
    benchmark_df.index = pd.to_datetime(benchmark_df.index)

combined_nav_data = pd.merge(nav_data, benchmark_df, left_index=True, right_index=True, how='left')

for col in benchmark_df.columns:
    if col in combined_nav_data:
        combined_nav_data[col] = combined_nav_data[col].ffill()


# Date Range Selection
min_date_val = combined_nav_data.index.min().date()
max_date_val = combined_nav_data.index.max().date()

# Initialize or validate st.session_state.start_date (as Timestamp)
if 'start_date' not in st.session_state:
    st.session_state.start_date = pd.to_datetime(min_date_val)
else:
    # Ensure it's a Timestamp if it exists
    if not isinstance(st.session_state.start_date, pd.Timestamp):
         st.session_state.start_date = pd.to_datetime(st.session_state.start_date)
    # Compare .date() part and clamp
    if st.session_state.start_date.date() < min_date_val:
        st.session_state.start_date = pd.to_datetime(min_date_val)
    elif st.session_state.start_date.date() > max_date_val: 
        st.session_state.start_date = pd.to_datetime(max_date_val)

# Initialize or validate st.session_state.end_date (as Timestamp)
if 'end_date' not in st.session_state:
    st.session_state.end_date = pd.to_datetime(max_date_val)
else:
    # Ensure it's a Timestamp if it exists
    if not isinstance(st.session_state.end_date, pd.Timestamp):
        st.session_state.end_date = pd.to_datetime(st.session_state.end_date)
    # Compare .date() part and clamp
    if st.session_state.end_date.date() > max_date_val:
        st.session_state.end_date = pd.to_datetime(max_date_val)
    elif st.session_state.end_date.date() < min_date_val: 
        st.session_state.end_date = pd.to_datetime(min_date_val)
            
# Ensure start_date <= end_date after clamping
if st.session_state.start_date > st.session_state.end_date:
    st.session_state.start_date = st.session_state.end_date
    
cols_date = st.columns(2)
with cols_date[0]:
    start_date_input = st.date_input(
        "Data Inicial",
        format="DD/MM/YYYY",
        value=st.session_state.start_date.date(), 
        min_value=min_date_val,
        max_value=max_date_val,
        key='start_date_picker'
    )
with cols_date[1]:
    end_date_input = st.date_input(
        "Data Final",
        format="DD/MM/YYYY",
        value=st.session_state.end_date.date(), 
        min_value=min_date_val,
        max_value=max_date_val,
        key='end_date_picker'
    )
    
# Update session state with Timestamps from the input (which are datetime.date objects)
st.session_state.start_date = pd.to_datetime(start_date_input)
st.session_state.end_date = pd.to_datetime(end_date_input)

if st.session_state.start_date > st.session_state.end_date: # Check after user input
    st.warning("Data inicial deve ser anterior à data final.")
    st.stop() 

# Initial selection for the chart and table: Persevera fund + benchmarks
initial_selection_cols = [persevera_fund_col_name]
if 'CDI' in combined_nav_data.columns: initial_selection_cols.append('CDI')
if 'Ibovespa' in combined_nav_data.columns: initial_selection_cols.append('Ibovespa')
if 'SMLL' in combined_nav_data.columns: initial_selection_cols.append('SMLL')

# Ensure only existing columns are selected
initial_selection_cols = [col for col in initial_selection_cols if col in combined_nav_data.columns]

# Allow user to select funds/benchmarks for the chart
all_available_funds_for_chart = list(combined_nav_data.columns)

# Set default selection: Persevera fund and available benchmarks
default_chart_selection = initial_selection_cols

selected_funds_for_chart = st.multiselect(
    "Selecione fundos/benchmarks para o gráfico:",
    options=all_available_funds_for_chart,
    default=default_chart_selection,
    key=f'chart_multiselect_{selected_fund_name}'
)

# Filter data for the selected date range and funds for the chart
chart_data_filtered = combined_nav_data.loc[
    st.session_state.start_date : st.session_state.end_date,
    selected_funds_for_chart
]

# Calculate and display performance chart
st.subheader("Performance Acumulada")
performance_to_plot = calculate_performance(chart_data_filtered) * 100
if not performance_to_plot.empty:
    perf_chart_options = create_chart(
        data=performance_to_plot,
        columns=list(performance_to_plot.columns),
        names=list(performance_to_plot.columns),
        chart_type='line',
        title="",
        y_axis_title="%"
    )
    hct.streamlit_highcharts(perf_chart_options, key=f"perf_acumulada_{selected_fund_name}")
else:
    st.info("Não há dados de performance acumulada para exibir com os filtros selecionados.")

# Performance Table
st.subheader("Tabela de Performance")
performance_table_data = get_performance_table(
    combined_nav_data,
    total_equity_data,
    st.session_state.start_date,
    st.session_state.end_date
)

if not performance_table_data.empty:
    styled_performance_table = style_table(
        performance_table_data.set_index('fund_name'),
        rank_cols_identifier='rank',
        numeric_cols_format_as_int=['PL'],
        numeric_cols_format_as_float=['day', 'mtd', 'ytd', '3m', '6m', '12m', '24m', '36m', 'custom'],
        highlight_quartile=['day', 'mtd', 'ytd', '3m', '6m', '12m', '24m', '36m', 'custom'],
        quartile_exclude_row_by_column='type',
        quartile_exclude_row_if_value_is=['Benchmark'],
        highlight_row_by_column='type',
        highlight_row_if_value_equals='Persevera',
        highlight_color='lightblue'
    )
    st.dataframe(styled_performance_table, use_container_width=True)

else:
    st.info("Não há dados para a tabela de performance com os filtros selecionados.")

# Retorno x Patrimônio Líquido
st.subheader("Retorno x Patrimônio Líquido")
period_options = ['day', 'mtd', 'ytd', '3m', '6m', '12m', '24m', '36m', 'custom']
period_selected = st.radio("Selecione o período:", period_options, index=0, horizontal=True)

short_term_chart_options = create_chart(
    data=performance_table_data.dropna(),
    columns=period_selected,
    names="Fundos",
    chart_type='scatter',
    title="",
    y_axis_title=f"Retorno {period_selected.upper()} (%)",
    x_axis_title="Patrimônio Líquido (R$)",
    x_column="PL",
    zoom_type="xy",
    point_name_column="fund_name",
    tooltip_point_format='<b>{point.name}</b><br/>Patrimônio Líquido: {point.x:,.0f}<br/>Retorno: {point.y:.2f}%'
)
hct.streamlit_highcharts(short_term_chart_options, key=f"scatter_1d_pl_{selected_fund_name}")

# Additional Statistics (Drawdown, Volatility, Net Equity)
st.subheader("Estatísticas Adicionais")

# Filter combined_nav_data for the selected funds for these stats
stats_data_selection = initial_selection_cols

stats_data_options = st.multiselect(
    "Selecione fundos/benchmarks para Estatísticas Adicionais:",
    options=all_available_funds_for_chart,
    default=stats_data_selection,
    key=f'stats_multiselect_{selected_fund_name}'
)

if not stats_data_options:
    st.info("Selecione fundos/benchmarks para as estatísticas adicionais.")
    
stats_data_filtered = combined_nav_data.loc[
    st.session_state.start_date : st.session_state.end_date,
    stats_data_options
].ffill()


if not stats_data_filtered.empty:
    tabs = st.tabs(["Drawdown", "Volatilidade (21d)", "Patrimônio Líquido"])

    with tabs[0]:
        st.subheader("Drawdown")
        drawdown_data = (stats_data_filtered / stats_data_filtered.cummax() - 1) * 100
        if not drawdown_data.empty:
            drawdown_chart_options = create_chart(
                data=drawdown_data,
                columns=list(drawdown_data.columns),
                names=list(drawdown_data.columns),
                chart_type='area',
                title="",
                y_axis_title="%"
            )
            hct.streamlit_highcharts(drawdown_chart_options, key=f"drawdown_{selected_fund_name}")
        else:
            st.info("Não há dados de drawdown para exibir com os filtros selecionados.")

    with tabs[1]:
        st.subheader("Volatilidade Anualizada (Janela de 21 dias úteis)")
        volatility_data = stats_data_filtered.pct_change().rolling(window=21).std() * np.sqrt(252) * 100
        if not volatility_data.empty:
            vol_chart_options = create_chart(
                data=volatility_data,
                columns=list(volatility_data.columns),
                names=list(volatility_data.columns),
                chart_type='line',
                title="",
                y_axis_title="%"
            )
            hct.streamlit_highcharts(vol_chart_options, key=f"volatility_{selected_fund_name}")
        else:
            st.info("Não há dados de volatilidade para exibir com os filtros selecionados.")

    with tabs[2]:
        st.subheader("Patrimônio Líquido")
        # Display PL for the main Persevera fund of the selected group
        persevera_pl_col_names = [col for col in total_equity_data.columns if persevera_fund_col_name in col]
        
        if persevera_pl_col_names:
            # Assuming persevera_fund_col_name is unique enough or we take the first match
            actual_persevera_pl_col = persevera_pl_col_names[0]
            pl_to_display = total_equity_data[[actual_persevera_pl_col]].copy()
            pl_to_display = pl_to_display.loc[st.session_state.start_date : st.session_state.end_date]
            if not pl_to_display.empty:
                pl_chart_options = create_chart(
                    data=pl_to_display,
                    columns=list(pl_to_display.columns),
                    names=list(pl_to_display.columns),
                    chart_type='area',
                    title="",
                    y_axis_title="Valor"
                )
                hct.streamlit_highcharts(pl_chart_options, key=f"pl_{selected_fund_name}")
            else:
                st.info(f"Dados de Patrimônio Líquido não disponíveis para {actual_persevera_pl_col} no período selecionado.")
        else:
            st.info(f"Coluna de Patrimônio Líquido para {persevera_fund_col_name} não encontrada nos dados de PL total.")
else:
    st.warning("Nenhum dado para calcular estatísticas adicionais com os filtros atuais.")