import numpy as np
import pandas as pd
from datetime import date

import streamlit as st
import streamlit_highcharts as hct

from utils.chart_helpers import create_chart
from utils.table import style_table

from persevera_tools.fixed_income import get_series

st.title("Precificação")

FIELD_LABELS = {
    "price_close": "Preço",
    "price_close_adj": "Preço Adj.",
    "yield_to_maturity": "YTM",
}

SOURCE_LABELS = {
    "anbima": "Anbima",
    "b3": "B3",
    "mais_retorno": "Mais Retorno",
}

PRICE_FIELDS = {"price_close", "price_close_adj"}


def column_display_name(col):
    if isinstance(col, tuple):
        field, source = col[0], col[1] if len(col) > 1 else ""
        source_label = SOURCE_LABELS.get(source, source)
        if field == "price_close":
            return f"Preço {source_label}"
        if field == "price_close_adj":
            return f"Preço Adj. ({source_label})"
        if field == "yield_to_maturity":
            return f"YTM {source_label}"
        field_label = FIELD_LABELS.get(field, field)
        return f"{field_label} ({source_label})" if source_label else field_label
    return SOURCE_LABELS.get(col, str(col))


def rename_columns(df):
    out = df.copy()
    out.columns = [column_display_name(c) for c in out.columns]
    return out


def select_columns(df, fields):
    if df.empty or not isinstance(df.columns, pd.MultiIndex):
        return pd.DataFrame(index=df.index)
    cols = [c for c in df.columns if c[0] in fields]
    return df[cols] if cols else pd.DataFrame(index=df.index)


def value_on_date(series, target_date):
    s = series.dropna()
    if s.empty:
        return np.nan
    subset = s.loc[:pd.Timestamp(target_date)]
    if subset.empty:
        return np.nan
    return subset.iloc[-1]


def last_business_day_of_previous_month(reference_date):
    ref = pd.Timestamp(reference_date)
    prev_month_last_cal = ref.replace(day=1) - pd.Timedelta(days=1)
    return pd.bdate_range(end=prev_month_last_cal, periods=1)[0].date()


def default_variation_dates(max_date, min_date):
    end_default = last_business_day_of_previous_month(max_date)
    end_default = min(max(end_default, min_date), max_date)
    start_default = last_business_day_of_previous_month(end_default)
    start_default = min(max(start_default, min_date), end_default)
    return start_default, end_default


def compute_price_variation(prices, start_date, end_date):
    rows = []
    for col in prices.columns:
        val_start = value_on_date(prices[col], start_date)
        val_end = value_on_date(prices[col], end_date)
        if pd.isna(val_start) or pd.isna(val_end):
            var_pct = np.nan
            var_abs = np.nan
        elif val_start == 0:
            var_pct = np.nan
            var_abs = val_end - val_start
        else:
            var_pct = (val_end / val_start - 1) * 100
            var_abs = val_end - val_start
        rows.append({
            "Série": col,
            "Preço Inicial (R$)": val_start,
            "Preço Final (R$)": val_end,
            "Variação (R$)": var_abs,
            "Variação (%)": var_pct,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def load_data(code):
    try:
        return get_series(
            code,
            field=["price_close", "price_close_adj", "yield_to_maturity"],
        )
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()


if "precificacao_code" not in st.session_state:
    st.session_state.precificacao_code = None

with st.sidebar:
    st.header("Parâmetros")
    code = st.text_input(
        "Código do Ativo",
        value=st.session_state.precificacao_code or "",
    )
    btn_load = st.button("Carregar Dados")

if btn_load and code.strip():
    with st.spinner("Carregando dados...", show_time=True):
        st.session_state.precificacao_code = code.strip().upper()

loaded_code = st.session_state.precificacao_code
if loaded_code:
    raw = load_data(loaded_code)

    if raw.empty:
        st.warning("Não foi possível carregar os dados. Código de ativo não encontrado.")
    else:
        prices = rename_columns(select_columns(raw, PRICE_FIELDS))
        ytm = rename_columns(select_columns(raw, {"yield_to_maturity"}))

        if prices.empty:
            st.warning("Não há séries de preço disponíveis para este ativo.")
        else:
            min_date = prices.dropna(how="all").index.min().date()
            max_date = prices.index.max().date()
            default_start, default_end = default_variation_dates(max_date, min_date)

            if st.session_state.get("precificacao_dates_code") != loaded_code:
                st.session_state.precificacao_dates_code = loaded_code
                for key in ("precificacao_start_picker", "precificacao_end_picker"):
                    st.session_state.pop(key, None)

            if "precificacao_start_picker" not in st.session_state:
                st.session_state.precificacao_start_picker = default_start
            if "precificacao_end_picker" not in st.session_state:
                st.session_state.precificacao_end_picker = default_end

            start_val = max(
                min_date,
                min(st.session_state.precificacao_start_picker, max_date),
            )
            end_val = max(
                min_date,
                min(st.session_state.precificacao_end_picker, max_date),
            )
            if start_val > end_val:
                start_val = end_val
            st.session_state.precificacao_start_picker = start_val
            st.session_state.precificacao_end_picker = end_val

            st.subheader(f"Preço por Fonte · {loaded_code}")

            st.markdown("**Variação de Preço entre Datas**")
            cols_date = st.columns(2)
            with cols_date[0]:
                start_date_input = st.date_input(
                    "Data Inicial",
                    min_value=min_date,
                    max_value=max_date,
                    format="DD/MM/YYYY",
                    key="precificacao_start_picker",
                )
            with cols_date[1]:
                end_date_input = st.date_input(
                    "Data Final",
                    min_value=min_date,
                    max_value=max_date,
                    format="DD/MM/YYYY",
                    key="precificacao_end_picker",
                )

            if start_date_input > end_date_input:
                st.warning("Data inicial deve ser anterior ou igual à data final.")
            else:
                variation = compute_price_variation(prices, start_date_input, end_date_input)
                st.dataframe(
                    style_table(
                        variation,
                        numeric_cols_format_as_float=[
                            "Preço Inicial (R$)",
                            "Preço Final (R$)",
                            "Variação (R$)",
                        ],
                        percent_cols=["Variação (%)"],
                        color_negative_positive_cols=["Variação (R$)", "Variação (%)"],
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

            row_1 = st.columns(2)
            with row_1[0]:
                table_data = prices.sort_index(ascending=False).reset_index()
                st.dataframe(
                    style_table(
                        table_data,
                        numeric_cols_format_as_float=prices.columns.tolist(),
                        date_cols=["date"],
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
            with row_1[1]:
                if not ytm.empty and ytm.dropna(how="all").shape[1] > 0:
                    tabs = st.tabs(["Preço", "YTM"])
                    with tabs[0]:
                        chart_price = create_chart(
                            data=prices,
                            columns=prices.columns.tolist(),
                            names=prices.columns.tolist(),
                            chart_type="line",
                            title="Evolução do Preço do Ativo",
                            y_axis_title="Preço (R$)",
                            decimal_precision=2,
                        )
                        hct.streamlit_highcharts(chart_price)
                    with tabs[1]:
                        chart_ytm = create_chart(
                            data=ytm,
                            columns=ytm.columns.tolist(),
                            names=ytm.columns.tolist(),
                            chart_type="line",
                            title="Evolução do YTM",
                            y_axis_title="YTM (%)",
                            decimal_precision=2,
                        )
                        hct.streamlit_highcharts(chart_ytm)
                else:
                    chart_price = create_chart(
                        data=prices,
                        columns=prices.columns.tolist(),
                        names=prices.columns.tolist(),
                        chart_type="line",
                        title="Evolução do Preço do Ativo",
                        y_axis_title="Preço (R$)",
                        decimal_precision=2,
                    )
                    hct.streamlit_highcharts(chart_price)