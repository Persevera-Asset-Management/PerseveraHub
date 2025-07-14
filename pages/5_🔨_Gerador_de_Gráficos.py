import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import streamlit_highcharts as hct
import requests
import json
import io
from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from utils.chart_helpers import create_chart
from utils.data_transformers import apply_transformations, TRANSFORMERS
from persevera_tools.data import get_series, get_codes
from persevera_tools.db import read_sql

# Initialize session state variables
if 'chart_options_for_download' not in st.session_state:
    st.session_state.chart_options_for_download = None
if 'png_payload' not in st.session_state:
    st.session_state.png_payload = None
if 'transformations' not in st.session_state:
    st.session_state.transformations = []
if 'y_columns_options' not in st.session_state:
    st.session_state.y_columns_options = []

st.set_page_config(
    page_title="Gerador de Gráficos | Persevera",
    page_icon=":hammer:",
    layout="wide"
)

display_logo()
load_css()
check_authentication()

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
        
        if isinstance(df, pd.Series):
            df = df.to_frame(name=codes[0])

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados das séries: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_indicator_codes():
    try:
        # codes = get_codes()
        # return list(set(codes.values()))
        query = """
        SELECT DISTINCT code
        FROM indicadores
        ORDER BY code
        """
        return read_sql(query)
    except Exception as e:
        st.error(f"Erro ao carregar códigos das séries: {str(e)}")
        return []

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

indicators_codes = load_indicator_codes()

# --- Inputs do Usuário --- 
st.sidebar.header("Configurações do Gráfico")
data_source = st.sidebar.radio("Fonte dos Dados", ("Buscar por Códigos", "Colar Dados Personalizados"), key="data_source")

# Inputs Comuns
title_name_input = st.sidebar.text_input("Título do Gráfico")
series_names_override_input = st.sidebar.text_input("Nomes das Séries (sobrescrever, separados por ;)", placeholder="EXEMPLO: Série A;Série B")
y_axis_title_input = st.sidebar.text_input("Título do Eixo Y", placeholder="EXEMPLO: Valor (R$)")
chart_type_options = ['line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', 'areaspline', 'dual_axis_line', 'dual_axis_line_area', 'dual_axis_line_column']
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
    codes_input_series = st.sidebar.multiselect("Códigos das Séries", options=indicators_codes, key="codes_series")
    start_date_input = st.sidebar.date_input("Data de Início", value=datetime.now() - timedelta(days=365*5), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY", key="start_date_series")
    end_date_input = st.sidebar.date_input("Data de Fim", value=datetime.now(), min_value=datetime(1900, 1, 1), max_value=datetime.now(), format="DD/MM/YYYY", key="end_date_series")
else: # Colar Dados Personalizados
    pasted_data_area = st.sidebar.text_area("Cole seus dados aqui (Ex: do Excel, CSV)", height=200, key="pasted_data")
    has_header_check = st.sidebar.checkbox("Primeira linha é cabeçalho?", value=True, key="has_header")
    x_column_name_config = st.sidebar.text_input("Nome/Índice da Coluna do Eixo X (opcional)", placeholder="Ex: Data, ou 0 para primeira coluna", key="x_col_name")

st.sidebar.markdown("---")

# --- Transformation Inputs ---
st.sidebar.header("Transformações de Dados")

if st.sidebar.button("Adicionar Transformação", key="add_transform"):
    st.session_state.transformations.append({
        "column": None, "type": "default", "params": {}
    })

indices_to_remove = []
for i, trans in enumerate(st.session_state.transformations):
    st.sidebar.markdown("---")
    cols = st.sidebar.columns([4, 1])
    cols[0].markdown(f"**Transformação #{i+1}**")
    if cols[1].button("✖️", key=f"remove_transform_{i}", help="Remover esta transformação"):
        indices_to_remove.append(i)
        continue

    # Use a unique key for each widget based on its index
    trans['column'] = st.sidebar.selectbox(
        "Aplicar na coluna:",
        options=st.session_state.get('y_columns_options', []),
        key=f"transform_column_{i}",
        index=st.session_state.y_columns_options.index(trans['column']) if trans['column'] and trans['column'] in st.session_state.y_columns_options else 0
    )
    
    transformation_types = list(TRANSFORMERS.keys())
    trans['type'] = st.sidebar.selectbox(
        "Tipo de Transformação:",
        options=transformation_types,
        key=f"transform_type_{i}",
        index=transformation_types.index(trans['type']) if trans['type'] in transformation_types else 0
    )

    # Dynamic parameter inputs based on selected transformation type
    params = {}
    if trans['type'] == "moving_average":
        params['window'] = st.sidebar.number_input("Janela (períodos)", min_value=1, value=trans.get('params',{}).get('window', 21), key=f"param_ma_window_{i}")
    elif trans['type'] in ["rolling_max", "rolling_min"]:
        params['window'] = st.sidebar.number_input("Janela (períodos)", min_value=1, value=trans.get('params',{}).get('window', 252), key=f"param_rmaxmin_window_{i}")
    elif trans['type'] == "rolling_volatility":
        params['window'] = st.sidebar.number_input("Janela (períodos)", min_value=1, value=trans.get('params',{}).get('window', 252), key=f"param_vol_window_{i}")
        params['annualized'] = st.sidebar.checkbox("Anualizar?", value=trans.get('params',{}).get('annualized', False), key=f"param_vol_annualized_{i}")
        if params['annualized']:
            params['periods_in_year'] = st.sidebar.number_input("Períodos no ano", min_value=1, value=trans.get('params',{}).get('periods_in_year', 252), key=f"param_vol_periods_{i}")
        params['calculate_on_returns'] = st.sidebar.checkbox("Calcular sobre retornos?", value=trans.get('params',{}).get('calculate_on_returns', True), key=f"param_vol_returns_{i}")
    elif trans['type'] == "rolling_sum":
        params['window'] = st.sidebar.number_input("Janela (períodos)", min_value=1, value=trans.get('params',{}).get('window', 12), key=f"param_rs_window_{i}")
    elif trans['type'] == "rolling_sum_plus_yearly_variation":
        params['window'] = st.sidebar.number_input("Janela da soma (períodos)", min_value=1, value=trans.get('params',{}).get('window', 12), key=f"param_rsyv_window_{i}")
        params['frequency'] = st.sidebar.text_input("Frequência (ex: 'MS', 'QS')", value=trans.get('params',{}).get('frequency', 'MS'), key=f"param_rsyv_freq_{i}")
    elif trans['type'] in ["yearly_variation", "monthly_variation", "quarterly_variation", "monthly_difference"]:
        params['frequency'] = st.sidebar.text_input("Frequência (ex: 'MS', 'QS', 'D')", value=trans.get('params',{}).get('frequency', 'MS'), key=f"param_var_freq_{i}")
    elif trans['type'] == "multiply":
        params['scalar'] = st.sidebar.number_input("Multiplicar por", value=trans.get('params',{}).get('scalar', 1.0), format="%.4f", key=f"param_mul_scalar_{i}")
    elif trans['type'] == "divide":
        params['scalar'] = st.sidebar.number_input("Dividir por", value=trans.get('params',{}).get('scalar', 1.0), format="%.4f", key=f"param_div_scalar_{i}")
    elif trans['type'] == "saar":
        params['period_months'] = st.sidebar.number_input("Meses no período", min_value=1, value=trans.get('params',{}).get('period_months', 1), key=f"param_saar_months_{i}")

    params['keep_original_data'] = st.sidebar.checkbox("Manter dados originais?", value=trans.get('params',{}).get('keep_original_data', False), key=f"param_keep_original_data_{i}")

    trans['params'] = params

# Remove transformations marked for deletion
if indices_to_remove:
    st.session_state.transformations = [trans for i, trans in enumerate(st.session_state.transformations) if i not in indices_to_remove]
    st.rerun()

st.sidebar.markdown("---")

# --- Lógica Principal da Página --- 
if st.sidebar.button("Gerar Gráfico", key="generate_chart_button"):
    chart_data = pd.DataFrame()
    y_columns_for_chart = []
    legend_names_for_chart = []
    final_title = title_name_input if title_name_input else "Gráfico"

    if data_source == "Buscar por Códigos":
        if codes_input_series:
            codes_list = codes_input_series # Directly use the list from multiselect
            if not codes_list:
                st.sidebar.error("Por favor, insira códigos de séries válidos.")
                st.stop()

            start_date_str = start_date_input.strftime('%Y-%m-%d')
            end_date_str = end_date_input.strftime('%Y-%m-%d')

            chart_data = load_series_data(codes_list, start_date_str, end_date_str)
            y_columns_for_chart = list(chart_data.columns) # Use actual columns from DataFrame
            legend_names_for_chart = y_columns_for_chart.copy() # Use a copy for legends
            st.session_state.y_columns_options = list(chart_data.columns) # Update options for UI
        else:
            st.sidebar.error("Por favor, insira códigos de séries.")
            st.stop()
    
    elif data_source == "Colar Dados Personalizados":
        if pasted_data_area:
            chart_data, y_columns_for_chart, legend_names_for_chart = parse_pasted_data(pasted_data_area, has_header_check, x_column_name_config)
            st.session_state.y_columns_options = y_columns_for_chart
            if chart_data is None or chart_data.empty:
                st.sidebar.error("Não foi possível processar os dados colados.")
                st.stop()
        else:
            st.sidebar.error("Por favor, cole os dados na área indicada.")
            st.stop()

    # --- Transformation Logic ---
    if st.session_state.transformations and not chart_data.empty:
        transformations_config = []
        columns_to_remove = set()

        for trans_config in st.session_state.transformations:
            if trans_config.get('column') and trans_config.get('type') != 'default':
                config = {'type': trans_config['type'], 'column': trans_config['column'], **trans_config['params']}
                transformations_config.append(config)

                if not trans_config.get('params', {}).get('keep_original_data', False):
                    columns_to_remove.add(trans_config['column'])
        
        if transformations_config:
            original_cols = set(chart_data.columns)
            chart_data = apply_transformations(chart_data, transformations_config)
            new_cols = list(set(chart_data.columns) - original_cols)
            
            y_columns_for_chart.extend(new_cols)
            legend_names_for_chart.extend(new_cols)

            if columns_to_remove:
                y_columns_for_chart = [col for col in y_columns_for_chart if col not in columns_to_remove]
                legend_names_for_chart = [col for col in legend_names_for_chart if col not in columns_to_remove]

    # Processar sobrescrita de nomes das séries (comum a ambas as fontes)
    if series_names_override_input:
        override_names = [name.strip() for name in series_names_override_input.split(';') if name.strip()]
        if len(override_names) == len(y_columns_for_chart):
            legend_names_for_chart = override_names
        elif override_names:
            st.warning("Número de nomes de séries para sobrescrita não corresponde ao número de séries. Usando nomes padrão/derivados.")
    
    if selected_chart_type in ['dual_axis_line', 'dual_axis_line_area', 'dual_axis_line_column']:
        y_axis_title_list = [name.strip() for name in y_axis_title_input.split(';') if name.strip()]
        if len(y_axis_title_list) == 1:
            y_axis_title_list = y_axis_title_list[0]
    else:
        y_axis_title_list = y_axis_title_input

    if not chart_data.empty and y_columns_for_chart:
        # Criar configuração do gráfico
        data_to_plot = chart_data[y_columns_for_chart]

        chart_options = create_chart(
            data=data_to_plot,
            columns=y_columns_for_chart,
            names=legend_names_for_chart,
            chart_type=selected_chart_type,
            title=final_title,
            y_axis_title=y_axis_title_list,
            x_axis_title="",
            stacking=selected_stacking,
            height=height_input,
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
