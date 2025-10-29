import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import os
import io
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.font_manager as fm
from typing import Dict
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from persevera_tools.data import get_series
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from configs.pages.hda import INDICADORES_GRUPOS

st.set_page_config(
    page_title="HDA | Persevera",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="expanded",
)
display_logo()
load_css()
check_authentication()

st.title("HDA")

def create_hda_image(df: pd.DataFrame, groups: Dict[str, Dict[str, str]], report_date: str) -> Figure:
    """
    Creates a styled table image from a DataFrame, similar to the provided image.
    """
    # Load custom font
    font_path = 'assets/fonts/RobotoCondensed-Regular.ttf'
    try:
        font_prop = fm.FontProperties(fname=font_path, size=13)
    except RuntimeError:
        st.error("Arquivo de fonte não encontrado. Verifique o caminho para 'RobotoCondensed-Regular.ttf'.")
        font_prop = fm.FontProperties(family='sans-serif') # Fallback font

    # Flatten groups for easier lookup
    indicators_map = {code: name for group in groups.values() for code, name in group.items()}
    
    # Prepare data for the table
    all_rows = []
    
    # Header
    header = [report_date] + list(df.columns)
    all_rows.append(header)

    for group_name, indicators in groups.items():
        all_rows.append([group_name] + [''] * (len(header) - 1))
        for code, name in indicators.items():
            if name in df.index:
                row_data = [name] + list(df.loc[name].values)
                all_rows.append(row_data)

    num_rows = len(all_rows)
    num_cols = len(header)

    fig, ax = plt.subplots(figsize=(8, num_rows * 0.4))
    ax.axis('off')

    # Definir a largura das colunas: a primeira é mais larga para os nomes dos indicadores.
    col_widths = [0.4] + [0.15] * (num_cols - 1)

    table = ax.table(cellText=all_rows, loc='center', cellLoc='left', colWidths=col_widths)
    # table.auto_set_font_size(True)
    table.set_fontsize(14)
    table.scale(1.2, 1.2)

    # Styling the table
    for i in range(num_rows):
        for j in range(num_cols):
            cell = table[i, j]
            cell.set_edgecolor('none')
            cell.set_text_props(ha='center', va='center', fontproperties=font_prop)

            # Header row
            if i == 0:
                cell.set_facecolor((26/255, 40/255, 49/255))
                cell.set_text_props(color='white', weight='bold', fontproperties=font_prop)
                if j > 0:
                    cell.set_text_props(ha='center', fontproperties=font_prop)
                cell.set_height(0.075)

            # Group header rows
            elif len(all_rows[i]) > 1 and all_rows[i][1] == '':
                cell.set_facecolor((192/255, 176/255, 150/255))
                cell.set_text_props(weight='bold', ha='left', fontproperties=font_prop)

            # Data rows
            else:
                cell.set_facecolor((242/255, 242/255, 242/255) if i % 2 == 0 else 'white')
                if j == 0:
                    cell.set_text_props(ha='left', fontproperties=font_prop)
                else:
                    cell.set_text_props(ha='center', fontproperties=font_prop)
                    try:
                        val = float(all_rows[i][j])
                        cell.set_text_props(color='red' if val < 0 else 'black', fontproperties=font_prop)
                        cell.get_text().set_text(f'{val:.2f}%')
                    except (ValueError, TypeError):
                        pass

    return fig

with st.sidebar:
    st.header("Parâmetros")
    today = datetime.today().date() - relativedelta(days=1)

    # Considera o início da semana como a sexta-feira anterior
    days_since_previous_friday = (today.weekday() - 4 + 7) % 7
    if days_since_previous_friday == 0:  # Se hoje for sexta, pega a anterior
        days_since_previous_friday = 7
    start_of_week = today - timedelta(days=days_since_previous_friday)
    start_of_month = today.replace(day=1) - relativedelta(days=1)
    start_of_year = date(today.year - 1, 12, 31)

    last_date = st.date_input("Data Final", min_value=datetime(1990, 1, 1), max_value=today, value=today, format="DD/MM/YYYY")
    wtd_date = st.date_input("Início da Semana (WTD)", min_value=datetime(1990, 1, 1), max_value=today, value=start_of_week, format="DD/MM/YYYY")
    mtd_date = st.date_input("Início do Mês (MTD)", min_value=datetime(1990, 1, 1), max_value=today, value=start_of_month, format="DD/MM/YYYY")
    ytd_date = st.date_input("Início do Ano (YTD)", min_value=datetime(1990, 1, 1), max_value=today, value=start_of_year, format="DD/MM/YYYY")

    last_date_str = last_date.strftime('%Y-%m-%d')
    wtd_date_str = wtd_date.strftime('%Y-%m-%d')
    mtd_date_str = mtd_date.strftime('%Y-%m-%d')
    ytd_date_str = ytd_date.strftime('%Y-%m-%d')

def load_data(codes, start_date, field='close'):
    try:
        return get_series(codes, start_date=start_date, field=field)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

with st.spinner("Carregando dados...", show_time=True):
    complete_list = [item for sublist in INDICADORES_GRUPOS.values() for item in sublist.keys()]
    data = load_data(complete_list, start_date=(min(last_date, wtd_date, mtd_date, ytd_date) - relativedelta(days=5)).strftime('%Y-%m-%d'))
    data = data.ffill()

with st.spinner("Calculando variações...", show_time=True):
    df = pd.DataFrame()
    df['Variação\nna semana'] = data.loc[last_date_str] / data.loc[wtd_date_str] - 1
    df[f'Variação\nem {(mtd_date + relativedelta(days=1)).strftime("%b/%Y")}'] = data.loc[last_date_str] / data.loc[mtd_date_str] - 1
    df[f'Variação\nem {(ytd_date + relativedelta(years=1)).strftime("%Y")}'] = data.loc[last_date_str] / data.loc[ytd_date_str] - 1
    df = df.mul(100)
    
    # Unir os dicionários de indicadores para renomear o índice de uma só vez
    all_indicators = {**INDICADORES_GRUPOS['Mercados Globais'], **INDICADORES_GRUPOS['Mercado Local']}
    df.rename(index=all_indicators, inplace=True)


if df.empty:
    st.warning("Não foi possível carregar os dados. Verifique sua conexão ou tente novamente mais tarde.")
else:

    with st.expander("Visualizar dados"):
        st.dataframe(data.sort_index(ascending=False))

    report_date = last_date.strftime('%d-%b-%y')
    fig = create_hda_image(df, INDICADORES_GRUPOS, report_date)
    
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
    buf.seek(0)

    st.image(buf, use_container_width=True)

    st.download_button(
        label="Download da Imagem",
        data=buf,
        file_name=f"hda_resumo_mercado_{last_date.strftime('%Y%m%d')}.png",
        mime="image/png"
    )
