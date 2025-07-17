import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table
from utils.auth import check_authentication
from persevera_tools.quant_research.metrics import calculate_tracking_error
from persevera_tools.data.sma import get_building_blocks
from persevera_tools.data import get_series

st.set_page_config(
    page_title="Building Blocks | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

st.title("Building Blocks")

@st.cache_data(ttl=3600)
def load_data(codes, start_date):
    try:
        return get_series(codes, start_date=start_date, field='close')
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()
    
building_blocks_dict = {
    # Renda Fixa
    'IMA-B': 'anbima_ima_b',
    'IMA-B 5': 'anbima_ima_b5',
    'IMA-B 5+': 'anbima_ima_b5+',
    'IRF-M': 'anbima_irf_m',
    'IRF-M 1+': 'anbima_irf_m1+',

    # Renda Variável BR
    'Ibovespa': 'br_ibovespa',
    'SMLL': 'br_smll',
    'IBr-X 100': 'br_ibx100',
    'IBr-X 50': 'br_ibx50',

    # Renda Variável US
    'Nasdaq-100': 'us_nasdaq100',
    'S&P 500': 'us_sp500',
    
    # Commodities
    'Ouro': 'gold_100oz_futures',

    # Alternativos
    'Bitcoin': 'br_bmf_bitcoin_futures',
    'IFIX': 'br_ifix',
}

start_date = datetime.now() - timedelta(days=5*365)
start_date_str = start_date.strftime('%Y-%m-%d')

building_blocks_df = get_building_blocks()

indicadores_list = list(building_blocks_dict.values()) + building_blocks_df['code'].tolist()
data = load_data(indicadores_list, start_date_str)

for block in building_blocks_dict:
    with st.expander(block):
        temp = building_blocks_df[building_blocks_df['reference'] == block].drop(columns=['reference'])
        temp.set_index('code', inplace=True)
        temp['tracking_error'] = np.nan
        reference_series = data[building_blocks_dict[block]]
        for code in temp.index:
            instrument_series = data[code]
            temp.loc[code, 'tracking_error'] = calculate_tracking_error(instrument_series, reference_series)

        st.dataframe(
            style_table(
                temp.sort_values(by='tracking_error', ascending=True),
                column_names=['Instrumento', 'Nome', 'Hedge Cambial?', 'Tracking Error'],
            ),
        )
