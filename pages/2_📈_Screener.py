import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from persevera_tools.data import get_descriptors, get_securities_by_exchange, get_equities_info

st.set_page_config(
    page_title="Screener | Persevera",
    page_icon="🗓️",
    layout="wide"
)

@st.cache_data(ttl=3600)
def load_data(start_date, descriptors_list):
    try:
        codes = get_securities_by_exchange(exchange='BZ').values()
        return get_descriptors(list(codes), start_date=start_date, descriptors=descriptors_list)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_sectors(codes):
    try:
        return get_equities_info(codes)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


st.title('Screener')

selected_cols_options = {
    'ADTV (21d)': 'median_dollar_volume_traded_21d',
    'Momentum (1m)': 'momentum_1m',
    'Momentum (6m)': 'momentum_6m',
    'Momentum (12m)': 'momentum_12m',
    'P/L': 'price_to_earnings_fwd',
    'EV/EBITDA': 'ev_to_ebitda_fwd',
    'Volume (7d/63d)': 'delta_volume_7d_63d',
    'Volume (21d/63d)': 'delta_volume_21d_63d',
    'EBIT Margin (%)': 'ebit_margin',
    'FCF Margin (%)': 'fcf_margin',
    'ROE': 'roe'
}

default_selected_display_names = ['ADTV (21d)', 'P/L', 'EV/EBITDA', 'EBIT Margin (%)', 'FCF Margin (%)', 'ROE']

st.sidebar.header("Filters")
selected_display_names = st.sidebar.multiselect(
    "Select metrics to display:",
    options=list(selected_cols_options.keys()),
    default=default_selected_display_names
)

# Filter selected_cols based on user selection
selected_cols = {name: selected_cols_options[name] for name in selected_display_names}
selected_descriptors_list = list(selected_cols.values())

data_load_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
data = load_data(start_date=data_load_date, descriptors_list=selected_descriptors_list)

if not data.empty:
    data = data.ffill()
    data = data.iloc[-1].reset_index()
    data.columns = ['ticker', 'descriptor', 'value']
    data = data.pivot(index='ticker', columns='descriptor', values='value')
    data = data[selected_descriptors_list]
    
    # Rename columns to display names
    inverted_selected_cols = {v: k for k, v in selected_cols.items()}
    data = data.rename(columns=inverted_selected_cols)
    
    # Load and merge sector data
    all_codes = list(get_securities_by_exchange(exchange='BZ').values())
    sector_data = load_sectors(all_codes)
    if not sector_data.empty and 'sector_name_pt' in sector_data.columns:
        sector_data = sector_data[['sector_name_pt']] # Select only the sector column
        data = pd.merge(data, sector_data, left_index=True, right_index=True, how='left')

        # Bring sector to the front
        if 'sector_name_pt' in data.columns:
            cols = ['sector_name_pt'] + [col for col in data.columns if col != 'sector_name_pt']
            data = data[cols]
            data = data.rename(columns={'sector_name_pt': 'Setor'})

    st.dataframe(data)
else:
    st.warning("No data available for the selected metrics and date.")
