import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from utils.chart_helpers import create_chart

st.set_page_config(
    page_title="Planejamento Financeiro | Persevera",
    page_icon="�",
    layout="wide"
)

st.title("Planejamento Financeiro")

# Definição dos parâmetros
st.sidebar.header("Parâmetros")

st.sidebar.subheader("Patrimônio")
patrimonio_inicial = st.sidebar.number_input("Patrimônio Inicial (R$):", min_value=0.0, value=100000.0, step=10000.0, format="%.0f")

st.sidebar.subheader("Fase de Acumulação")
periodo_acumulacao = st.sidebar.number_input("Período de Acumulação (anos):", min_value=0.0, value=10.0, step=1.0, format="%.0f")

if periodo_acumulacao == 0:
    aporte_mensal = st.sidebar.number_input("Aporte Mensal (R$):", min_value=0.0, value=0.0, step=1000.0, format="%.0f", disabled=True)
else:
    aporte_mensal = st.sidebar.number_input("Aporte Mensal (R$):", min_value=0.0, value=0.0, step=1000.0, format="%.0f")

st.sidebar.subheader("Fase de Distribuição")
periodo_distribuicao = st.sidebar.number_input("Período de Distribuição (anos):", min_value=1.0, value=10.0, step=1.0, format="%.0f")
resgate_mensal = st.sidebar.number_input("Resgate Mensal (R$):", min_value=0.0, value=10000.0, step=1000.0, format="%.0f")

st.sidebar.subheader("Hipóteses de Mercado")
rentabilidade_nominal_esperada = st.sidebar.number_input("Rentabilidade Nominal Esperada (% a.a):", min_value=0.0, value=10.0, step=0.1, format="%.1f")
inflacao_esperada = st.sidebar.number_input("Inflação Esperada (% a.a):", min_value=0.0, value=2.0, step=0.1, format="%.1f")
aliquota_irrf = st.sidebar.number_input("Alíquota de Impostos (%):", min_value=0.0, value=15.0, step=0.1, format="%.1f")

# Definindo as taxas anuais a partir dos inputs da sidebar (necessário para cálculos posteriores)
rentabilidade_anual = rentabilidade_nominal_esperada / 100.0
inflacao_anual = inflacao_esperada / 100.0

# Função para simular a evolução patrimonial
def simular_patrimonio(patrimonio_inicial, periodo_acumulacao, periodo_distribuicao, resgate_mensal, aporte_mensal, inflacao_esperada, rentabilidade_nominal_esperada, aliquota_irrf):
    
    # Convertendo taxas anuais para mensais
    rentabilidade_mensal_liquida_bruta = (1 + rentabilidade_nominal_esperada / 100.0) ** (1/12) - 1
    inflacao_mensal_calc = (1 + inflacao_esperada / 100.0) ** (1/12) - 1
    
    # Inicializando variáveis para armazenar resultados
    patrimonio_atual = patrimonio_inicial
    resgate_total = 0.0
    aporte_total = 0.0
    rendimento_total = 0.0
    
    # Adicionar o estado inicial (Mês 0)
    resultados = [{
        "Mês": 0,
        "Ano": 0,
        "Patrimônio": patrimonio_atual,
        "Rendimento Acumulado": rendimento_total,
        "Resgate Acumulado": resgate_total,
        "Resgate Mensal Ajustado": 0.0,
        "Aporte Acumulado": aporte_total,
        "Aporte Mensal Ajustado": 0.0,
        "Fator Inflação": 1.0,
        "Inflação Acumulada": 0.0
    }]

    meses_acumulacao = int(periodo_acumulacao * 12)
    meses_distribuicao = int(periodo_distribuicao * 12)
    meses_totais_simulacao = meses_acumulacao + meses_distribuicao
    
    # Simulação mês a mês
    for mes in range(1, meses_totais_simulacao + 1):
        # Aplicar rendimento
        rendimento_bruto = patrimonio_atual * rentabilidade_mensal_liquida_bruta
        rendimento_liquido = rendimento_bruto * (1 - aliquota_irrf / 100.0)
        rendimento_total += rendimento_liquido
        
        fator_inflacao = (1 + inflacao_mensal_calc) ** (mes - 1)
        
        aporte_do_mes_base = 0.0
        resgate_do_mes_base = 0.0

        if mes <= meses_acumulacao:
            # Fase de Acumulação
            aporte_do_mes_base = aporte_mensal
        else:
            # Fase de Distribuição (ocorre após os meses de acumulação)
            resgate_do_mes_base = resgate_mensal
        
        # Aplicar resgate ajustado pela inflação
        resgate_ajustado = resgate_do_mes_base * fator_inflacao
        resgate_total += resgate_ajustado
        
        # Adicionar aportes (também ajustados pela inflação)
        aporte_ajustado = aporte_do_mes_base * fator_inflacao
        aporte_total += aporte_ajustado
        
        # Calcular novo patrimônio
        patrimonio_atual = patrimonio_atual + rendimento_liquido - resgate_ajustado + aporte_ajustado
        
        # Armazenar resultado para cada mês (depois agruparemos por ano)
        resultados.append({
            "Mês": mes,
            "Ano": (mes - 1) // 12 + 1,
            "Patrimônio": patrimonio_atual,
            "Rendimento Acumulado": rendimento_total,
            "Resgate Acumulado": resgate_total,
            "Resgate Mensal Ajustado": resgate_ajustado,
            "Aporte Acumulado": aporte_total,
            "Aporte Mensal Ajustado": aporte_ajustado,
            "Fator Inflação": fator_inflacao,
            "Inflação Acumulada": (1 + inflacao_mensal_calc) ** (mes - 1) - 1
        })
    
    # Converter para DataFrame
    df_resultados = pd.DataFrame(resultados)
    
    # Adicionar coluna para período formatado (para visualização)
    df_resultados["Período"] = df_resultados["Ano"].apply(lambda ano: "Inicial" if ano == 0 else f"Ano {ano}")
    df_resultados["Período Completo"] = df_resultados.apply(
        lambda row: "Inicial" if row["Mês"] == 0 else f"Ano {row['Ano']} Mês {((row['Mês'] - 1) % 12) + 1}",
        axis=1
    )
    
    return df_resultados

# Calcular a simulação
df_simulacao = simular_patrimonio(
    patrimonio_inicial=patrimonio_inicial,
    periodo_acumulacao=periodo_acumulacao,
    periodo_distribuicao=periodo_distribuicao,
    resgate_mensal=resgate_mensal,
    aporte_mensal=aporte_mensal,
    inflacao_esperada=inflacao_esperada,
    rentabilidade_nominal_esperada=rentabilidade_nominal_esperada,
    aliquota_irrf=aliquota_irrf
)

# Agrupar resultados por ano (para visualização)
df_anual = df_simulacao.groupby("Ano").last().reset_index()

st.subheader("Resultados da Simulação")

ultima_linha = df_simulacao.iloc[-1]
patrimonio_final = ultima_linha["Patrimônio"]
periodo_total_anos = periodo_acumulacao + periodo_distribuicao

if patrimonio_inicial > 0:
    crescimento_nominal = (patrimonio_final / patrimonio_inicial - 1) * 100
    inflacao_total_fator = (1 + inflacao_anual) ** periodo_total_anos
    if inflacao_total_fator > 0:
        crescimento_real = ((patrimonio_final / patrimonio_inicial) / inflacao_total_fator - 1) * 100
    else: # Edge case for extreme deflation
        crescimento_real = float('inf') if (patrimonio_final / patrimonio_inicial) >= 0 else float('-inf')
elif patrimonio_inicial == 0:
    if patrimonio_final > 0:
        crescimento_nominal = float('inf')
        crescimento_real = float('inf')
    elif patrimonio_final == 0:
        crescimento_nominal = 0.0
        crescimento_real = 0.0
    else: # patrimonio_final < 0
        crescimento_nominal = float('-inf')
        crescimento_real = float('-inf')
else: # patrimonio_inicial < 0 (not allowed by UI but robust)
    crescimento_nominal = 0.0 # Or indicate N/A
    crescimento_real = 0.0   # Or indicate N/A

metricas_col1, metricas_col2 = st.columns(2)

with metricas_col1:
    st.metric("Patrimônio Final", f"R$ {patrimonio_final:,.2f}", border=True)
    st.metric("Total Resgatado", f"R$ {ultima_linha['Resgate Acumulado']:,.2f}", border=True)
    st.metric("Crescimento Nominal", f"{crescimento_nominal:.2f}%", border=True)

with metricas_col2:
    st.metric("Rendimentos Acumulados", f"R$ {ultima_linha['Rendimento Acumulado']:,.2f}", border=True)
    st.metric("Total Aportado", f"R$ {ultima_linha['Aporte Acumulado']:,.2f}", border=True)
    st.metric("Crescimento Real", f"{crescimento_real:.2f}%", border=True)

st.subheader("Evolução do Patrimônio")

evolucao_options = create_chart(
    data=df_simulacao,
    columns=["Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"],
    names=["Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"],
    chart_type='line',
    title="",
    y_axis_title="Valor (R$)",
    x_axis_title="Período (meses)",
    x_column="Período Completo",
)

hct.streamlit_highcharts(evolucao_options)

# Análise adicional - gráfico de barras comparativas
st.subheader("Análise Comparativa Anual")

categories_bar = ["Patrimônio Inicial", "Rendimentos", "Aportes", "Resgates", "Patrimônio Final"]
values_bar = [
    patrimonio_inicial, 
    ultima_linha["Rendimento Acumulado"], 
    ultima_linha["Aporte Acumulado"], 
    -ultima_linha["Resgate Acumulado"],
    patrimonio_final
]

df_bar_data = pd.DataFrame({
    'Category': categories_bar,
    'Value': values_bar
})

barras_options = create_chart(
    data=df_bar_data,
    columns='Value',
    names='Valores',
    chart_type='column',
    title="",
    y_axis_title="Valor (R$)",
    x_axis_title="",
    x_column='Category',
)
hct.streamlit_highcharts(barras_options, height=400)

# if barras_options:
#     # Manually adjust for colorByPoint and specific colors, and disable legend for this specific chart type
#     if 'plotOptions' not in barras_options:
#         barras_options['plotOptions'] = {}
#     if 'column' not in barras_options['plotOptions']:
#         barras_options['plotOptions']['column'] = {}
#     barras_options['plotOptions']['column']['colorByPoint'] = True
#     barras_options['colors'] = colors_bar
#     barras_options['legend'] = {'enabled': False} # Typically legend is not needed when colorByPoint is true for categories
#     barras_options['xAxis'] = {'type': 'category', 'title': {'text': None}}

#     hct.streamlit_highcharts(barras_options, height=400)


# Tabela detalhada
st.subheader("Memória de Cálculo")
tab_anual, tab_mensal = st.tabs(["Anual", "Mensal"])

with tab_anual:
    df_memoria_anual = df_anual.copy()
    df_memoria_anual["Patrimônio"] = df_memoria_anual["Patrimônio"].map("R$ {:,.2f}".format)
    df_memoria_anual["Rendimento Acumulado"] = df_memoria_anual["Rendimento Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Resgate Acumulado"] = df_memoria_anual["Resgate Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Aporte Acumulado"] = df_memoria_anual["Aporte Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Inflação Acumulada"] = df_memoria_anual["Inflação Acumulada"].map("{:.2%}".format)

    df_memoria_anual = df_memoria_anual[["Período", "Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado", "Inflação Acumulada"]]
    df_memoria_anual.set_index("Período", inplace=True)

    st.dataframe(df_memoria_anual, use_container_width=True)

with tab_mensal:
    df_memoria_mensal = df_simulacao.copy()
    df_memoria_mensal["Patrimônio"] = df_memoria_mensal["Patrimônio"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Rendimento Acumulado"] = df_memoria_mensal["Rendimento Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Resgate Acumulado"] = df_memoria_mensal["Resgate Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Resgate Mensal Ajustado"] = df_memoria_mensal["Resgate Mensal Ajustado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Aporte Acumulado"] = df_memoria_mensal["Aporte Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Aporte Mensal Ajustado"] = df_memoria_mensal["Aporte Mensal Ajustado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Inflação Acumulada"] = df_memoria_mensal["Inflação Acumulada"].map("{:.2%}".format)

    df_memoria_mensal = df_memoria_mensal[["Período Completo", "Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Resgate Mensal Ajustado", "Aporte Acumulado", "Aporte Mensal Ajustado", "Inflação Acumulada"]]
    df_memoria_mensal.set_index("Período Completo", inplace=True)

    st.dataframe(df_memoria_mensal, use_container_width=True)
