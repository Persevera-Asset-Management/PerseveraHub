import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from persevera_tools.data import get_series
from utils.chart_helpers import create_chart
import streamlit_highcharts as hct
import requests
import json
import io

# Initialize session state variables
if 'chart_options_for_download' not in st.session_state:
    st.session_state.chart_options_for_download = None
if 'png_payload' not in st.session_state:
    st.session_state.png_payload = None

st.set_page_config(
    page_title="Gerador de Gráficos | Persevera",
    page_icon="📊",
    layout="wide"
)

# Inclusão do CSS
try:
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
    css_path = os.path.join(assets_dir, 'style.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Arquivo CSS não encontrado. Verifique o caminho para 'assets/style.css'.")

st.title('Gerador de Gráficos')

@st.cache_data(ttl=3600)
def load_series_data(codes, start_date, end_date):
    try:
        df = get_series(codes, start_date=start_date, end_date=end_date, field='close')
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                st.warning(f"Não foi possível converter o índice para Datetime: {e}")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados das séries: {str(e)}")
        return pd.DataFrame()

def parse_pasted_data(pasted_text: str, has_header: bool, x_col_name_input: str):
    if not pasted_text.strip():
        return None, [], [] # DataFrame, y_columns, legend_names
    try:
        delimiter = '\t' # Default para tab (Excel)
        if ',' in pasted_text and ';' not in pasted_text and '\t' not in pasted_text:
            # Heurística simples: se tem vírgula e não outros delimitadores comuns, usa vírgula
            # Pode ser melhorado com detecção mais robusta ou selectbox para o usuário
            delimiter = ','
        elif ';' in pasted_text and ',' not in pasted_text and '\t' not in pasted_text:
            delimiter = ';'
        
        df = pd.read_csv(io.StringIO(pasted_text), sep=delimiter, header=0 if has_header else None, skip_blank_lines=True)
        df.dropna(how='all', inplace=True) # Remover linhas totalmente vazias
        df.dropna(how='all', axis=1, inplace=True) # Remover colunas totalmente vazias

        if df.empty:
            st.error("Os dados colados estão vazios ou não puderam ser processados.")
            return None, [], []

        x_column_selected = None
        if has_header:
            if x_col_name_input and x_col_name_input in df.columns:
                x_column_selected = x_col_name_input
            else:
                x_column_selected = df.columns[0] # Default para primeira coluna se nome X não válido
        else: # Sem header, colunas são índices numéricos
            if x_col_name_input: # Usuário pode tentar especificar por índice como string "0", "1" etc.
                try:
                    x_col_idx = int(x_col_name_input)
                    if 0 <= x_col_idx < len(df.columns):
                        x_column_selected = df.columns[x_col_idx]
                    else:
                        x_column_selected = df.columns[0]
                except ValueError:
                    x_column_selected = df.columns[0] # Default para primeira se input não for numérico
            else:
                x_column_selected = df.columns[0] # Default para primeira coluna (índice 0)
        
        df.set_index(x_column_selected, inplace=True)
        try:
            df.index = pd.to_datetime(df.index)
            df.index.name = "Data" # Ou usar o nome da coluna X original
        except Exception:
            st.info("Índice do eixo X não pôde ser convertido para datas. Será tratado como categórico.")
            if df.index.name is None and x_column_selected is not None:
                 df.index.name = str(x_column_selected) if has_header else "Eixo X"
            elif df.index.name is None:
                 df.index.name = "Eixo X"

        y_columns = df.columns.tolist()
        legend_names = [str(col) for col in y_columns] # Por padrão, nomes da legenda são nomes das colunas Y
        
        return df, y_columns, legend_names
    except Exception as e:
        st.error(f"Erro ao processar dados colados: {e}")
        return None, [], []

# --- Inputs do Usuário --- 
st.sidebar.header("Configurações do Gráfico")
data_source = st.sidebar.radio("Fonte dos Dados", ("Buscar por Códigos", "Colar Dados Personalizados"), key="data_source")

# Inputs Comuns
title_name_input = st.sidebar.text_input("Título do Gráfico")
series_names_override_input = st.sidebar.text_input("Nomes das Séries (sobrescrever, separados por ;)", placeholder="EXEMPLO: Série A;Série B")
y_axis_title_input = st.sidebar.text_input("Título do Eixo Y", placeholder="EXEMPLO: Valor (R$)")
chart_type_options = ['line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', 'areaspline', 'dual_axis_line', 'dual_axis_line_area']
selected_chart_type = st.sidebar.selectbox("Tipo de Gráfico", chart_type_options)
stacking_options = [None, 'normal', 'percent']
selected_stacking = st.sidebar.selectbox("Tipo de Empilhamento", stacking_options)

# Pré-seleção de altura e largura do gráfico
chart_size_selection = st.sidebar.radio("Disposição do Gráfico", ["Linha Completa", "Lado a Lado"], horizontal=True, index=0, key="chart_size_radio")

# Definir valores padrão de altura e largura com base na seleção
if chart_size_selection == "Linha Completa":
    default_width = 1200
    default_height = 500
elif chart_size_selection == "Lado a Lado":
    default_width = 600
    default_height = 500
else: # Fallback, embora não deva acontecer com st.radio
    default_width = 600
    default_height = 400

height_input = st.sidebar.number_input("Altura do Gráfico", min_value=200, max_value=1200, value=default_height, step=50, key="height_num_input")
width_input = st.sidebar.number_input("Largura do Gráfico", min_value=200, max_value=1200, value=default_width, step=50, key="width_num_input")

# Inputs Condicionais
if data_source == "Buscar por Códigos":
    codes_input_series = st.sidebar.text_input("Códigos das Séries (separados por ;)", placeholder="EXEMPLO: CODE1;CODE2", key="codes_series")
    start_date_input = st.sidebar.date_input("Data de Início", value=datetime.now() - timedelta(days=365*5), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY", key="start_date_series")
    end_date_input = st.sidebar.date_input("Data de Fim", value=datetime.now(), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY", key="end_date_series")
else: # Colar Dados Personalizados
    pasted_data_area = st.sidebar.text_area("Cole seus dados aqui (Ex: do Excel, CSV)", height=200, key="pasted_data")
    has_header_check = st.sidebar.checkbox("Primeira linha é cabeçalho?", value=True, key="has_header")
    x_column_name_config = st.sidebar.text_input("Nome/Índice da Coluna do Eixo X (opcional)", placeholder="Ex: Data, ou 0 para primeira coluna", key="x_col_name")

# --- Lógica Principal da Página --- 
if st.sidebar.button("Gerar Gráfico", key="generate_chart_button"):
    chart_data = pd.DataFrame()
    y_columns_for_chart = []
    legend_names_for_chart = []
    final_title = title_name_input if title_name_input else "Gráfico"
    color_palette = ["#19202a", "#b99b7b", "#b3bebd", "#cdb89b", "#cad7d8"]

    if data_source == "Buscar por Códigos":
        if codes_input_series:
            codes_list = [code.strip() for code in codes_input_series.split(';') if code.strip()]
            if not codes_list:
                st.sidebar.error("Por favor, insira códigos de séries válidos.")
                st.stop()

            start_date_str = start_date_input.strftime('%Y-%m-%d')
            end_date_str = end_date_input.strftime('%Y-%m-%d')

            chart_data = load_series_data(codes_list, start_date_str, end_date_str)
            y_columns_for_chart = codes_list
            legend_names_for_chart = codes_list
        else:
            st.sidebar.error("Por favor, insira códigos de séries.")
            st.stop()
    
    elif data_source == "Colar Dados Personalizados":
        if pasted_data_area:
            chart_data, y_columns_for_chart, legend_names_for_chart = parse_pasted_data(pasted_data_area, has_header_check, x_column_name_config)
            if chart_data is None or chart_data.empty:
                st.sidebar.error("Não foi possível processar os dados colados.")
                st.stop()
        else:
            st.sidebar.error("Por favor, cole os dados na área indicada.")
            st.stop()

    # Processar sobrescrita de nomes das séries (comum a ambas as fontes)
    if series_names_override_input:
        override_names = [name.strip() for name in series_names_override_input.split(';') if name.strip()]
        if len(override_names) == len(y_columns_for_chart):
            legend_names_for_chart = override_names
        elif override_names:
            st.warning("Número de nomes de séries para sobrescrita não corresponde ao número de séries. Usando nomes padrão/derivados.")
    
    if selected_chart_type in ['dual_axis_line', 'dual_axis_line_area']:
        y_axis_title_list = [name.strip() for name in y_axis_title_input.split(';') if name.strip()]
        if len(y_axis_title_list) == 1:
            y_axis_title_list = y_axis_title_list[0]
    else:
        y_axis_title_list = y_axis_title_input

    if not chart_data.empty and y_columns_for_chart:
        # Criar configuração do gráfico
        chart_options = create_chart(
            data=chart_data,
            columns=y_columns_for_chart,
            names=legend_names_for_chart,
            chart_type=selected_chart_type,
            title=final_title,
            y_axis_title=y_axis_title_list,
            x_axis_title="",
            stacking=selected_stacking,
            height=height_input,
            colors=color_palette[:len(y_columns_for_chart)],
            exporting={"enabled": True}
        )
        st.session_state.chart_options_for_download = chart_options
        st.session_state.png_payload = None
    elif data_source: # Se uma fonte de dados foi selecionada mas resultou em erro/vazio
        st.warning("Não há dados válidos para gerar o gráfico. Verifique os inputs.")
        st.session_state.chart_options_for_download = None

# --- Seção de Exibição do Gráfico e Download (PNG) --- 
if st.session_state.get('chart_options_for_download'):
    current_chart_options_for_display_and_dl = st.session_state.chart_options_for_download
    
    export_scripts = """
    <script src="https://code.highcharts.com/modules/exporting.js"></script>
    <script src="https://code.highcharts.com/modules/export-data.js"></script>
    <script src="https://code.highcharts.com/modules/offline-exporting.js"></script>
    """
    st.markdown(export_scripts, unsafe_allow_html=True)
    
    hct.streamlit_highcharts(current_chart_options_for_display_and_dl, key="user_generated_chart_display", height=current_chart_options_for_display_and_dl.get("chart",{}).get("height", 500))
    
    st.markdown("### Exportar Gráfico para PNG")
    if st.button("Gerar PNG para Download", key="gen_png_button"):
        st.session_state.png_payload = None
        try:
            export_url = "https://export.highcharts.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://your-streamlit-app-domain.com' 
            }
            export_data_payload = {
                "infile": json.dumps(current_chart_options_for_display_and_dl),
                "type": "image/png",
                "width": width_input,
                "scale": 2
            }
            with st.spinner("Gerando PNG..."):
                response = requests.post(export_url, data=export_data_payload, headers=headers, timeout=30)
            if response.status_code == 200:
                st.session_state.png_payload = {
                    "data": response.content,
                    "file_name": f"{current_chart_options_for_display_and_dl.get('title',{}).get('text','grafico').replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    "mime": "image/png"
                }
            else:
                st.error(f"Erro ao gerar PNG: {response.status_code} - {response.text}")
        except requests.exceptions.Timeout:
             st.error("Timeout ao tentar gerar PNG. O servidor de exportação pode estar demorando muito.")
        except Exception as e:
            st.error(f"Exceção ao gerar PNG: {str(e)}")

    if st.session_state.get('png_payload'):
        st.download_button(
            label="⬇️ Baixar PNG Gerado",
            data=st.session_state.png_payload["data"],
            file_name=st.session_state.png_payload["file_name"],
            mime=st.session_state.png_payload["mime"],
            key="dl_png_button"
        )
