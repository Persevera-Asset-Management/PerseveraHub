import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from configs.pages.screener import FACTOR_OPTIONS_SCREENER
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

def style_screener_table(df_to_style):
    """Applies styling to the screener DataFrame using Pandas Styler."""
    if df_to_style.empty:
        # For an empty DataFrame, return its default style to avoid errors
        return pd.DataFrame().style

    df_styled = df_to_style.copy()
    formatters = {}

    # Identify columns for formatting based on their names
    for col_name in df_styled.columns:
        if 'ADTV' in col_name:
            formatters[col_name] = "{:,.0f}"  # Comma for thousands, no decimal places
        else:
            formatters[col_name] = "{:.2f}"  # Two decimal places for general numbers
        # 'Setor' column and 'ticker' (index) will not be in formatters by default.

    styled_obj = df_styled.style.format(formatters)

    # Define alignment styles
    alignment_styles = [
        # Left-align index header and values
        {'selector': 'th.row_heading', 'props': [('text-align', 'left'), ('min-width', '80px')]},
        {'selector': 'td.data.row_heading', 'props': [('text-align', 'left')]}
    ]

    for i, col_name in enumerate(df_styled.columns):
        col_selector_th = f'th.col_heading.col{i}'
        col_selector_td = f'td.col{i}'
        
        if col_name == 'Setor':
            alignment_styles.append({'selector': col_selector_th, 'props': [('text-align', 'left')]})
            alignment_styles.append({'selector': col_selector_td, 'props': [('text-align', 'left'), ('min-width', '150px')]})
        elif col_name in formatters:  # Numeric columns that were formatted
            alignment_styles.append({'selector': col_selector_th, 'props': [('text-align', 'right')]})
            alignment_styles.append({'selector': col_selector_td, 'props': [('text-align', 'right')]})
        # Else, default alignment for other columns

    styled_obj = styled_obj.set_table_styles(alignment_styles, overwrite=False)

    return styled_obj

st.title('Screener')

selected_cols_options = FACTOR_OPTIONS_SCREENER

default_selected_display_names = ['ADTV (21d)', 'P/E Fwd', 'EV/EBITDA Fwd', 'EBIT Margin (%)', 'FCF Margin (%)', 'ROE (%)']

st.sidebar.header("Filtros")

# ADTV Filter
adtv_filter = st.sidebar.number_input(
    "ADTV Mínimo (21d):",
    min_value=0.0,
    value=8000000.0,
    step=500000.0,
    format="%.0f"
)

selected_display_names = st.sidebar.multiselect(
    "Selecione as métricas para exibir:",
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
    
    # Ensure only selected descriptors are present before renaming
    data = data[selected_descriptors_list] 

    # Rename columns to display names
    inverted_selected_cols = {v: k for k, v in selected_cols.items()}
    data = data.rename(columns=inverted_selected_cols)

    # Apply ADTV filter if 'ADTV (21d)' is in the columns
    if 'ADTV (21d)' in data.columns and adtv_filter > 0:
        data = data[data['ADTV (21d)'] >= adtv_filter]

    # Load and merge sector data
    all_codes = list(get_securities_by_exchange(exchange='BZ').values())
    sector_data = load_sectors(all_codes)
    if not sector_data.empty and 'sector_name_pt' in sector_data.columns:
        sector_data_to_merge = sector_data[['sector_name_pt']].copy() # Select only the sector column
        data = pd.merge(data, sector_data_to_merge, left_index=True, right_index=True, how='left')
        data = data.rename(columns={'sector_name_pt': 'Setor'})
        
        # Bring 'Setor' to the front if it exists
        if 'Setor' in data.columns:
            cols = ['Setor'] + [col for col in data.columns if col != 'Setor']
            data = data[cols]
            
    # Apply styling
    styled_data = style_screener_table(data)
    st.write(styled_data)

else:
    st.warning("No data available for the selected metrics and date.")
