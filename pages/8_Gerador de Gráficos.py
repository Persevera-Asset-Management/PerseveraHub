import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import requests
import json
import io
from utils.chart_helpers import create_chart, render_chart
from utils.data_transformers import apply_transformations, TRANSFORMERS
from persevera_tools.data import get_series
from persevera_tools.db import read_sql

CHART_TYPE_OPTIONS = {
    "Linha": "line",
    "Linha suave (spline)": "spline",
    "Área": "area",
    "Área suave": "areaspline",
    "Colunas": "column",
    "Barras": "bar",
    "Dispersão": "scatter",
    "Pizza": "pie",
    "Dois eixos — linhas": "dual_axis_line",
    "Dois eixos — linha + área": "dual_axis_line_area",
    "Dois eixos — linha + colunas": "dual_axis_line_column",
}

STACKING_OPTIONS = {
    "Nenhum": None,
    "Empilhado": "normal",
    "Empilhado (%)": "percent",
}

TRANSFORMER_LABELS = {
    "default": "Nenhuma",
    "yearly_variation": "Variação anual (YoY)",
    "monthly_variation": "Variação mensal (MoM)",
    "quarterly_variation": "Variação trimestral (QoQ)",
    "monthly_difference": "Diferença mensal",
    "moving_average": "Média móvel",
    "rolling_max": "Máximo móvel",
    "rolling_min": "Mínimo móvel",
    "rolling_volatility": "Volatilidade móvel",
    "rolling_beta": "Beta móvel",
    "rolling_sum": "Soma móvel",
    "cumulative_sum": "Soma acumulada",
    "rolling_sum_plus_yearly_variation": "Soma móvel + variação anual",
    "multiply": "Multiplicar por escalar",
    "divide": "Dividir por escalar",
    "subtract": "Subtrair escalar",
    "base_100": "Índice base 100",
    "saar": "Taxa anualizada sazonalmente (SAAR)",
    "saar_ma": "SAAR com média móvel",
    "year_to_date": "Acumulado no ano (YTD)",
    "accumulated_by_year": "Acumulado por ano",
}

STACKING_CHART_TYPES = {"bar", "column", "area", "areaspline", "line", "spline"}

# Initialize session state variables
if "chart_options_for_download" not in st.session_state:
    st.session_state.chart_options_for_download = None
if "png_payload" not in st.session_state:
    st.session_state.png_payload = None
if "transformations" not in st.session_state:
    st.session_state.transformations = []
if "y_columns_options" not in st.session_state:
    st.session_state.y_columns_options = []

st.title("Gerador de Gráficos")


def _set_date_preset_years(years: int) -> None:
    st.session_state.end_date_series = date.today()
    st.session_state.start_date_series = date.today() - timedelta(days=365 * years)


def _set_date_preset_ytd() -> None:
    st.session_state.end_date_series = date.today()
    st.session_state.start_date_series = date(date.today().year, 1, 1)


@st.cache_data(ttl=3600)
def load_series_data(codes, start_date, end_date):
    try:
        df = get_series(codes, start_date=start_date, end_date=end_date, field="close")
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
        query = """
        SELECT DISTINCT code
        FROM indicadores
        ORDER BY code
        """
        result = read_sql(query)
        if isinstance(result, pd.DataFrame):
            col = "code" if "code" in result.columns else result.columns[0]
            return result[col].dropna().astype(str).tolist()
        return [str(c) for c in result] if result else []
    except Exception as e:
        st.error(f"Erro ao carregar códigos das séries: {str(e)}")
        return []


def parse_pasted_data(pasted_text: str, has_header: bool, x_col_name_input: str):
    if not pasted_text.strip():
        return None, [], []
    try:
        delimiter = "\t"
        if "," in pasted_text and ";" not in pasted_text and "\t" not in pasted_text:
            delimiter = ","
        elif ";" in pasted_text and "," not in pasted_text and "\t" not in pasted_text:
            delimiter = ";"

        df = pd.read_csv(
            io.StringIO(pasted_text),
            sep=delimiter,
            header=0 if has_header else None,
            skip_blank_lines=True,
        )
        df.dropna(how="all", inplace=True)
        df.dropna(how="all", axis=1, inplace=True)

        if df.empty:
            st.error("Os dados colados estão vazios ou não puderam ser processados.")
            return None, [], []

        x_column_selected = None
        if has_header:
            if x_col_name_input and x_col_name_input in df.columns:
                x_column_selected = x_col_name_input
            else:
                x_column_selected = df.columns[0]
        else:
            if x_col_name_input:
                try:
                    x_col_idx = int(x_col_name_input)
                    if 0 <= x_col_idx < len(df.columns):
                        x_column_selected = df.columns[x_col_idx]
                    else:
                        x_column_selected = df.columns[0]
                except ValueError:
                    x_column_selected = df.columns[0]
            else:
                x_column_selected = df.columns[0]

        df.set_index(x_column_selected, inplace=True)
        try:
            df.index = pd.to_datetime(df.index)
            df.index.name = "Data"
        except Exception:
            st.info("Índice do eixo X não pôde ser convertido para datas. Será tratado como categórico.")
            if df.index.name is None and x_column_selected is not None:
                df.index.name = str(x_column_selected) if has_header else "Eixo X"
            elif df.index.name is None:
                df.index.name = "Eixo X"

        y_columns = df.columns.tolist()
        legend_names = [str(col) for col in y_columns]

        return df, y_columns, legend_names
    except Exception as e:
        st.error(f"Erro ao processar dados colados: {e}")
        return None, [], []


with st.spinner("Carregando códigos das séries...", show_time=True):
    indicators_codes = load_indicator_codes()

# --- Sidebar ---
with st.sidebar:
    st.header("Configurações")

    with st.expander("Fonte dos dados", expanded=True):
        data_source = st.radio(
            "Como obter os dados?",
            ("Buscar por Códigos", "Colar Dados Personalizados"),
            key="data_source",
            label_visibility="collapsed",
        )

        if data_source == "Buscar por Códigos":
            codes_input_series = st.multiselect(
                "Códigos das séries",
                options=indicators_codes,
                key="codes_series",
                placeholder="Digite para buscar um código…",
                help="Selecione uma ou mais séries do banco de indicadores.",
            )
            if codes_input_series:
                st.caption(f"{len(codes_input_series)} série(s) selecionada(s)")

            st.caption("Atalhos de período")
            p1, p2, p3 = st.columns(3)
            p1.button("1A", on_click=_set_date_preset_years, args=(1,), use_container_width=True)
            p2.button("3A", on_click=_set_date_preset_years, args=(3,), use_container_width=True)
            p3.button("5A", on_click=_set_date_preset_years, args=(5,), use_container_width=True)
            p4, p5, p6 = st.columns(3)
            p4.button("10A", on_click=_set_date_preset_years, args=(10,), use_container_width=True)
            p5.button("YTD", on_click=_set_date_preset_ytd, use_container_width=True)
            p6.button("Máx", on_click=_set_date_preset_years, args=(30,), use_container_width=True)

            start_date_input = st.date_input(
                "Data de início",
                value=pd.to_datetime(date.today() - timedelta(days=365 * 5)),
                min_value=datetime(1900, 1, 1),
                max_value=pd.to_datetime(date.today()),
                format="DD/MM/YYYY",
                key="start_date_series",
            )
            end_date_input = st.date_input(
                "Data de fim",
                value=pd.to_datetime(date.today()),
                min_value=datetime(1900, 1, 1),
                max_value=pd.to_datetime(date.today()),
                format="DD/MM/YYYY",
                key="end_date_series",
            )
        else:
            pasted_data_area = st.text_area(
                "Cole seus dados (Excel, CSV ou TSV)",
                height=160,
                key="pasted_data",
                placeholder="Cole aqui com Ctrl+V. A primeira coluna será o eixo X.",
            )
            has_header_check = st.checkbox(
                "Primeira linha é cabeçalho?",
                value=True,
                key="has_header",
            )
            x_column_name_config = st.text_input(
                "Coluna do eixo X (opcional)",
                placeholder="Ex.: Data, ou 0 para a primeira coluna",
                key="x_col_name",
            )

    with st.expander("Aparência do gráfico", expanded=True):
        title_name_input = st.text_input(
            "Título",
            placeholder="Ex.: IPCA acumulado 12 meses",
        )
        series_names_override_input = st.text_input(
            "Nomes na legenda (opcional)",
            placeholder="Série A;Série B",
            help="Separe com ponto e vírgula (;). Deve haver um nome para cada série plotada.",
        )
        y_axis_title_input = st.text_input(
            "Título do eixo Y",
            placeholder="Ex.: Valor (%)",
            help="Para gráficos com dois eixos, separe com ponto e vírgula: Eixo esquerdo;Eixo direito",
        )

        chart_type_labels = list(CHART_TYPE_OPTIONS.keys())
        selected_chart_label = st.selectbox("Tipo de gráfico", chart_type_labels)
        selected_chart_type = CHART_TYPE_OPTIONS[selected_chart_label]

        if selected_chart_type in ("dual_axis_line", "dual_axis_line_area", "dual_axis_line_column"):
            st.info(
                "Gráficos com dois eixos: a **primeira série** usa o eixo esquerdo; "
                "as **demais** usam o eixo direito."
            )

        selected_stacking = None
        if selected_chart_type in STACKING_CHART_TYPES:
            stacking_label = st.selectbox("Empilhamento", list(STACKING_OPTIONS.keys()))
            selected_stacking = STACKING_OPTIONS[stacking_label]

        decimal_precision_input = st.number_input(
            "Casas decimais",
            min_value=0,
            max_value=10,
            value=2,
            step=1,
            key="decimal_precision_input",
        )

    with st.expander("Limites do eixo Y", expanded=False):
        use_y_max = st.checkbox("Definir valor máximo", value=False, key="use_y_max")
        y_axis_max_input = (
            st.number_input(
                "Valor máximo",
                min_value=-1_000_000_000.0,
                max_value=1_000_000_000.0,
                value=100.0,
                step=1.0,
                key="y_axis_max_input",
            )
            if use_y_max
            else None
        )
        use_y_min = st.checkbox("Definir valor mínimo", value=False, key="use_y_min")
        y_axis_min_input = (
            st.number_input(
                "Valor mínimo",
                min_value=-1_000_000_000.0,
                max_value=1_000_000_000.0,
                value=0.0,
                step=1.0,
                key="y_axis_min_input",
            )
            if use_y_min
            else None
        )

    with st.expander("Tamanho e disposição", expanded=False):
        def _chart_size_presets_callback() -> None:
            if "chart_size_radio" not in st.session_state:
                return
            sel = st.session_state.chart_size_radio
            if sel == "Linha completa":
                st.session_state.height_num_input = 500
                st.session_state.width_num_input = 1200
            elif sel == "Lado a lado":
                st.session_state.height_num_input = 500
                st.session_state.width_num_input = 600

        chart_size_selection = st.radio(
            "Disposição",
            ["Linha completa", "Lado a lado"],
            horizontal=True,
            index=0,
            key="chart_size_radio",
            on_change=_chart_size_presets_callback,
            help="“Lado a lado” reduz a largura para encaixar dois gráficos na mesma linha em apresentações.",
        )

        if chart_size_selection == "Linha completa":
            default_width, default_height = 1200, 500
        else:
            default_width, default_height = 600, 500

        height_input = st.number_input(
            "Altura (px)",
            min_value=200,
            max_value=1200,
            value=default_height,
            step=50,
            key="height_num_input",
        )
        width_input = st.number_input(
            "Largura (px)",
            min_value=200,
            max_value=1200,
            value=default_width,
            step=50,
            key="width_num_input",
        )

    with st.expander("Linha vertical", expanded=False):
        vline_enable = st.checkbox(
            "Marcar uma data no gráfico",
            value=False,
            key="vline_enable",
            help="Desenha uma linha vertical no eixo de datas. Não se aplica a gráficos de pizza.",
        )
        vline_date = None
        vline_label = ""
        if vline_enable:
            vline_date = st.date_input(
                "Data",
                value=date.today(),
                format="DD/MM/YYYY",
                key="vline_date",
            )
            vline_label = st.text_input(
                "Rótulo (opcional)",
                value="",
                key="vline_label",
                placeholder="Ex.: Marco regulatório",
            )

    with st.expander("Transformações de dados", expanded=False):
        if not st.session_state.y_columns_options:
            st.caption(
                "Gere um gráfico primeiro para ver as colunas disponíveis, "
                "ou cole dados personalizados com séries nomeadas."
            )

        t_col1, t_col2 = st.columns([3, 1])
        if t_col1.button("Adicionar transformação", key="add_transform", use_container_width=True):
            st.session_state.transformations.append({"column": None, "type": "default", "params": {}})
        if t_col2.button("Limpar", key="clear_transforms", use_container_width=True):
            st.session_state.transformations = []
            st.rerun()

        indices_to_remove = []
        transformer_keys = list(TRANSFORMERS.keys())
        transformer_labels = [TRANSFORMER_LABELS.get(k, k) for k in transformer_keys]

        for i, trans in enumerate(st.session_state.transformations):
            st.markdown(f"**Transformação #{i + 1}**")
            if st.button("Remover", key=f"remove_transform_{i}", type="secondary"):
                indices_to_remove.append(i)
                continue

            col_options = st.session_state.get("y_columns_options", [])
            if not col_options:
                col_options = ["— gere o gráfico primeiro —"]

            trans["column"] = st.selectbox(
                "Coluna",
                options=col_options,
                key=f"transform_column_{i}",
                index=(
                    col_options.index(trans["column"])
                    if trans["column"] and trans["column"] in col_options
                    else 0
                ),
                disabled=col_options == ["— gere o gráfico primeiro —"],
            )

            type_label = st.selectbox(
                "Tipo",
                options=transformer_labels,
                key=f"transform_type_{i}",
                index=(
                    transformer_labels.index(TRANSFORMER_LABELS.get(trans["type"], trans["type"]))
                    if trans["type"] in TRANSFORMERS
                    else 0
                ),
            )
            trans["type"] = transformer_keys[transformer_labels.index(type_label)]

            params = {}
            if trans["type"] == "moving_average":
                params["window"] = st.number_input(
                    "Janela (períodos)",
                    min_value=1,
                    value=trans.get("params", {}).get("window", 21),
                    key=f"param_ma_window_{i}",
                )
            elif trans["type"] in ["rolling_max", "rolling_min"]:
                params["window"] = st.number_input(
                    "Janela (períodos)",
                    min_value=1,
                    value=trans.get("params", {}).get("window", 252),
                    key=f"param_rmaxmin_window_{i}",
                )
            elif trans["type"] == "rolling_volatility":
                params["window"] = st.number_input(
                    "Janela (períodos)",
                    min_value=1,
                    value=trans.get("params", {}).get("window", 252),
                    key=f"param_vol_window_{i}",
                )
                params["annualized"] = st.checkbox(
                    "Anualizar?",
                    value=trans.get("params", {}).get("annualized", False),
                    key=f"param_vol_annualized_{i}",
                )
                if params["annualized"]:
                    params["periods_in_year"] = st.number_input(
                        "Períodos no ano",
                        min_value=1,
                        value=trans.get("params", {}).get("periods_in_year", 252),
                        key=f"param_vol_periods_{i}",
                    )
                params["calculate_on_returns"] = st.checkbox(
                    "Calcular sobre retornos?",
                    value=trans.get("params", {}).get("calculate_on_returns", True),
                    key=f"param_vol_returns_{i}",
                )
            elif trans["type"] == "rolling_sum":
                params["window"] = st.number_input(
                    "Janela (períodos)",
                    min_value=1,
                    value=trans.get("params", {}).get("window", 12),
                    key=f"param_rs_window_{i}",
                )
            elif trans["type"] == "cumulative_sum":
                params["frequency"] = st.text_input(
                    "Frequência (opcional, ex: MS)",
                    value=trans.get("params", {}).get("frequency", ""),
                    key=f"param_cumsum_freq_{i}",
                    help="Vazio: cumsum na série original. Com frequência: reamostra e depois soma acumulada.",
                )
            elif trans["type"] == "rolling_sum_plus_yearly_variation":
                params["window"] = st.number_input(
                    "Janela da soma (períodos)",
                    min_value=1,
                    value=trans.get("params", {}).get("window", 12),
                    key=f"param_rsyv_window_{i}",
                )
                params["frequency"] = st.text_input(
                    "Frequência (ex: MS, QS)",
                    value=trans.get("params", {}).get("frequency", "MS"),
                    key=f"param_rsyv_freq_{i}",
                )
            elif trans["type"] in [
                "yearly_variation",
                "monthly_variation",
                "quarterly_variation",
                "monthly_difference",
            ]:
                params["frequency"] = st.text_input(
                    "Frequência (ex: MS, QS, D)",
                    value=trans.get("params", {}).get("frequency", "MS"),
                    key=f"param_var_freq_{i}",
                )
            elif trans["type"] == "multiply":
                params["scalar"] = st.number_input(
                    "Multiplicar por",
                    value=trans.get("params", {}).get("scalar", 1.0),
                    format="%.4f",
                    key=f"param_mul_scalar_{i}",
                )
            elif trans["type"] == "divide":
                params["scalar"] = st.number_input(
                    "Dividir por",
                    value=trans.get("params", {}).get("scalar", 1.0),
                    format="%.4f",
                    key=f"param_div_scalar_{i}",
                )
            elif trans["type"] == "subtract":
                params["scalar"] = st.number_input(
                    "Subtrair",
                    value=trans.get("params", {}).get("scalar", 1.0),
                    format="%.4f",
                    key=f"param_sub_scalar_{i}",
                )
            elif trans["type"] == "base_100":
                _bd = trans.get("params", {}).get("base_date", "") or ""
                params["base_date"] = st.text_input(
                    "Data base (AAAA-MM-DD), vazio = primeira observação",
                    value=_bd,
                    key=f"param_base100_date_{i}",
                )
            elif trans["type"] == "saar":
                params["period_months"] = st.number_input(
                    "Meses no período",
                    min_value=1,
                    value=trans.get("params", {}).get("period_months", 1),
                    key=f"param_saar_months_{i}",
                )
            elif trans["type"] == "saar_ma":
                params["period_months"] = st.number_input(
                    "Meses no período",
                    min_value=1,
                    value=trans.get("params", {}).get("period_months", 1),
                    key=f"param_saar_ma_months_{i}",
                )

            params["keep_original_data"] = st.checkbox(
                "Manter série original",
                value=trans.get("params", {}).get("keep_original_data", False),
                key=f"param_keep_original_data_{i}",
            )
            trans["params"] = params
            st.divider()

        if indices_to_remove:
            st.session_state.transformations = [
                trans for j, trans in enumerate(st.session_state.transformations) if j not in indices_to_remove
            ]
            st.rerun()

    generate_clicked = st.button("Gerar gráfico", key="generate_chart_button", type="primary", use_container_width=True)

# --- Área principal: estado vazio e pré-visualização ---
if data_source == "Colar Dados Personalizados" and st.session_state.get("pasted_data", "").strip():
    preview_df, preview_cols, _ = parse_pasted_data(
        st.session_state.pasted_data,
        st.session_state.get("has_header", True),
        st.session_state.get("x_col_name", ""),
    )
    if preview_df is not None and not preview_df.empty:
        with st.expander("Pré-visualização dos dados colados", expanded=False):
            st.caption(
                f"{len(preview_df)} linhas · {len(preview_cols)} série(s): "
                + ", ".join(str(c) for c in preview_cols[:5])
                + ("…" if len(preview_cols) > 5 else "")
            )
            st.dataframe(preview_df.head(20), use_container_width=True)
            st.session_state.y_columns_options = preview_cols

# --- Lógica principal ---
if generate_clicked:
    chart_data = pd.DataFrame()
    y_columns_for_chart = []
    legend_names_for_chart = []
    final_title = title_name_input if title_name_input else "Gráfico"

    if data_source == "Buscar por Códigos":
        if codes_input_series:
            codes_list = codes_input_series
            start_date_str = start_date_input.strftime("%Y-%m-%d")
            end_date_str = end_date_input.strftime("%Y-%m-%d")

            with st.spinner("Carregando dados das séries...", show_time=True):
                chart_data = load_series_data(codes_list, start_date_str, end_date_str)

            y_columns_for_chart = list(chart_data.columns)
            legend_names_for_chart = y_columns_for_chart.copy()
            st.session_state.y_columns_options = list(chart_data.columns)
        else:
            st.sidebar.error("Selecione ao menos um código de série.")
            st.stop()

    elif data_source == "Colar Dados Personalizados":
        if pasted_data_area:
            chart_data, y_columns_for_chart, legend_names_for_chart = parse_pasted_data(
                pasted_data_area, has_header_check, x_column_name_config
            )
            st.session_state.y_columns_options = y_columns_for_chart
            if chart_data is None or chart_data.empty:
                st.sidebar.error("Não foi possível processar os dados colados.")
                st.stop()
        else:
            st.sidebar.error("Cole os dados na área indicada.")
            st.stop()

    if st.session_state.transformations and not chart_data.empty:
        transformations_config = []
        columns_to_remove = set()

        for trans_config in st.session_state.transformations:
            if trans_config.get("column") and trans_config.get("type") != "default":
                config = {"type": trans_config["type"], "column": trans_config["column"], **trans_config["params"]}
                transformations_config.append(config)

                if not trans_config.get("params", {}).get("keep_original_data", False):
                    columns_to_remove.add(trans_config["column"])

        if transformations_config:
            original_cols = set(chart_data.columns)
            chart_data = apply_transformations(chart_data, transformations_config)
            new_cols = list(set(chart_data.columns) - original_cols)

            y_columns_for_chart.extend(new_cols)
            legend_names_for_chart.extend(new_cols)

            if columns_to_remove:
                y_columns_for_chart = [col for col in y_columns_for_chart if col not in columns_to_remove]
                legend_names_for_chart = [col for col in legend_names_for_chart if col not in columns_to_remove]

    if series_names_override_input:
        override_names = [name.strip() for name in series_names_override_input.split(";") if name.strip()]
        if len(override_names) == len(y_columns_for_chart):
            legend_names_for_chart = override_names
        elif override_names:
            st.warning(
                "Número de nomes na legenda não corresponde ao número de séries. "
                "Usando nomes padrão."
            )

    if selected_chart_type in ["dual_axis_line", "dual_axis_line_area", "dual_axis_line_column"]:
        y_axis_title_list = [name.strip() for name in y_axis_title_input.split(";") if name.strip()]
        if len(y_axis_title_list) == 1:
            y_axis_title_list = y_axis_title_list[0]
    else:
        y_axis_title_list = y_axis_title_input

    if not chart_data.empty and y_columns_for_chart:
        data_to_plot = chart_data[y_columns_for_chart]

        chart_extra = {}
        if vline_enable and vline_date is not None and selected_chart_type not in ("pie", "donut"):
            vline_conf: dict = {
                "value": vline_date,
                "color": "#666666",
                "width": 2,
                "dashStyle": "Dash",
                "zIndex": 5,
            }
            if vline_label and vline_label.strip():
                vline_conf["label"] = {
                    "text": vline_label.strip(),
                    "rotation": 0,
                    "style": {"color": "#666666"},
                }
            chart_extra["vertical_line"] = vline_conf
        elif vline_enable and selected_chart_type in ("pie", "donut"):
            st.warning("Linha vertical não está disponível para gráficos de pizza.")

        chart_options = create_chart(
            data=data_to_plot,
            columns=y_columns_for_chart,
            names=legend_names_for_chart,
            chart_type=selected_chart_type,
            title=final_title,
            y_axis_title=y_axis_title_list,
            x_axis_title="",
            y_axis_max=y_axis_max_input,
            y_axis_min=y_axis_min_input,
            decimal_precision=decimal_precision_input,
            stacking=selected_stacking,
            height=height_input,
            width=int(width_input),
            exporting={"enabled": True},
            enable_fullscreen_on_dblclick=True,
            **chart_extra,
        )
        st.session_state.chart_options_for_download = chart_options
        st.session_state.png_payload = None
        st.session_state.last_chart_meta = {
            "series_count": len(y_columns_for_chart),
            "row_count": len(data_to_plot),
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
    else:
        st.warning("Não há dados válidos para gerar o gráfico. Verifique os inputs.")
        st.session_state.chart_options_for_download = None

# --- Exibição do gráfico ou estado vazio ---
if not st.session_state.get("chart_options_for_download"):
    st.markdown("### Como usar")
    st.markdown(
        """
1. **Escolha a fonte** — busque códigos no banco ou cole uma tabela do Excel.
2. **Ajuste aparência** — título, tipo de gráfico e formatação.
3. **Clique em “Gerar gráfico”** na barra lateral.

**Dicas:** use os atalhos **1A / 3A / 5A / YTD** para períodos rápidos; duplo clique no gráfico abre em tela cheia; o menu ⋮ do gráfico exporta PNG/SVG.
        """
    )
elif st.session_state.get("chart_options_for_download"):
    current_chart_options = st.session_state.chart_options_for_download
    meta = st.session_state.get("last_chart_meta", {})

    if meta:
        st.caption(
            f"Gerado em {meta.get('generated_at', '—')} · "
            f"{meta.get('series_count', '—')} série(s) · "
            f"{meta.get('row_count', '—')} observações · "
            "duplo clique para tela cheia"
        )

    export_scripts = """
    <script src="https://code.highcharts.com/modules/exporting.js"></script>
    <script src="https://code.highcharts.com/modules/export-data.js"></script>
    <script src="https://code.highcharts.com/modules/offline-exporting.js"></script>
    """
    st.markdown(export_scripts, unsafe_allow_html=True)

    render_chart(
        current_chart_options,
        key="user_generated_chart_display",
        use_fullscreen_wrapper=True,
    )
