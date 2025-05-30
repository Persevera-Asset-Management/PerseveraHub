import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import datetime
import os
from utils.chart_helpers import create_chart

st.set_page_config(
    page_title="Planejamento Financeiro | Persevera",
    page_icon="💹",
    layout="wide"
)

# Inclusão do CSS
assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
css_path = os.path.join(assets_dir, 'style.css')
with open(css_path) as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.title("Planejamento Financeiro")

# Definição dos parâmetros
st.sidebar.header("Parâmetros")

st.sidebar.subheader("Características Pessoais")
data_nascimento = st.sidebar.date_input("Data de Nascimento:", value=datetime.date(1980, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today(), format="DD/MM/YYYY")
# idade_atual = st.sidebar.number_input("Idade Atual:", min_value=18, max_value=100, value=35, step=1, format="%d")
idade_atual = st.sidebar.number_input("Idade Atual:", min_value=18, max_value=100, value=datetime.date.today().year - data_nascimento.year, step=1, format="%d", disabled=True)

# Escolha do método de definição
metodo_calculo = st.sidebar.radio(
    "Método de Planejamento:",
    options=["Expectativa de Vida", "Período de Distribuição"],
    help="Escolha se quer definir sua expectativa de vida ou o período de distribuição dos recursos"
)

st.sidebar.subheader("Patrimônio")
patrimonio_inicial = st.sidebar.number_input("Patrimônio Inicial (R$):", min_value=0.0, value=100000.0, step=10000.0, format="%.0f")

st.sidebar.subheader("Fase de Acumulação")
periodo_acumulacao = st.sidebar.number_input("Período de Acumulação (anos):", min_value=0.0, value=20.0, step=1.0, format="%.0f")

if periodo_acumulacao == 0:
    aporte_mensal = st.sidebar.number_input("Aporte Mensal (R$):", min_value=0.0, value=0.0, step=1000.0, format="%.0f", disabled=True)
else:
    aporte_mensal = st.sidebar.number_input("Aporte Mensal (R$):", min_value=0.0, value=5000.0, step=1000.0, format="%.0f")

st.sidebar.subheader("Fase de Distribuição")

# Lógica condicional baseada na escolha do usuário
if metodo_calculo == "Expectativa de Vida":
    expectativa_vida = st.sidebar.number_input("Expectativa de Vida:", min_value=int(idade_atual + periodo_acumulacao), max_value=120, value=85, step=1, format="%d")
    
    # Calcular período de distribuição automaticamente
    periodo_distribuicao_calculado = expectativa_vida - idade_atual - periodo_acumulacao
    
    if periodo_distribuicao_calculado <= 0:
        st.sidebar.error("⚠️ Período de distribuição resultaria em valor negativo ou zero. Ajuste a expectativa de vida ou período de acumulação.")
        periodo_distribuicao = 1.0  # Valor mínimo para evitar erros
    else:
        periodo_distribuicao = periodo_distribuicao_calculado
    
    # Campo desabilitado mostrando o valor calculado
    st.sidebar.number_input(
        "Período de Distribuição (anos) - Calculado:",
        value=float(periodo_distribuicao),
        disabled=True,
        format="%.0f",
        help=f"Calculado como: {expectativa_vida} - {idade_atual} - {periodo_acumulacao:.0f} = {periodo_distribuicao:.0f} anos"
    )
    
else:  # "Definir Período de Distribuição"
    periodo_distribuicao = st.sidebar.number_input("Período de Distribuição (anos):", min_value=1.0, value=10.0, step=1.0, format="%.0f")
    
    # Calcular expectativa de vida automaticamente
    expectativa_vida = idade_atual + periodo_acumulacao + periodo_distribuicao
    
    # Campo desabilitado mostrando o valor calculado
    st.sidebar.number_input("Expectativa de Vida - Calculada:", value=int(expectativa_vida), disabled=True, format="%d", help=f"Calculada como: {idade_atual} + {periodo_acumulacao:.0f} + {periodo_distribuicao:.0f} = {expectativa_vida:.0f} anos")

resgate_mensal = st.sidebar.number_input("Resgate Mensal (R$):", min_value=0.0, value=10000.0, step=1000.0, format="%.0f")

# Validação da expectativa de vida (agora que a variável está definida)
if metodo_calculo == "Definir Expectativa de Vida" and expectativa_vida <= idade_atual:
    st.sidebar.error("A expectativa de vida deve ser maior que a idade atual!")

st.sidebar.subheader("Hipóteses de Mercado")
rentabilidade_nominal_esperada = st.sidebar.number_input("Rentabilidade Nominal Esperada (% a.a):", min_value=0.0, value=10.0, step=0.1, format="%.1f")
inflacao_esperada = st.sidebar.number_input("Inflação Esperada (% a.a):", min_value=0.0, value=4.0, step=0.1, format="%.1f")
aliquota_irrf = st.sidebar.number_input("Alíquota de Impostos (%):", min_value=0.0, value=15.0, step=0.1, format="%.1f")

# Definindo as taxas anuais a partir dos inputs da sidebar (necessário para cálculos posteriores)
rentabilidade_anual = rentabilidade_nominal_esperada / 100.0
inflacao_anual = inflacao_esperada / 100.0

# Informações contextuais baseadas na idade
anos_restantes = expectativa_vida - idade_atual
idade_fim_acumulacao = idade_atual + periodo_acumulacao
idade_inicio_distribuicao = idade_fim_acumulacao
idade_fim_distribuicao = idade_inicio_distribuicao + periodo_distribuicao

# Mostrar método de cálculo escolhido
st.info(f"**Método Ativo:** {metodo_calculo} \n\n **Expectativa de Vida:** {expectativa_vida:.0f} anos \n\n **Período de Distribuição:** {periodo_distribuicao:.0f} anos")

info_cols = st.columns(3)

with info_cols[0]:
    st.info(f"**Idade Atual:** {idade_atual} anos\n\n**Anos Restantes:** {anos_restantes} anos")

with info_cols[1]:
    if periodo_acumulacao > 0:
        st.info(f"**Fase de Acumulação:**\n\n{idade_atual} → {idade_fim_acumulacao:.0f} anos")
    else:
        st.info(f"**Sem Fase de Acumulação**\n\nIniciando distribuição aos {idade_atual} anos")

with info_cols[2]:
    st.info(f"**Fase de Distribuição:**\n\n{idade_inicio_distribuicao:.0f} → {idade_fim_distribuicao:.0f} anos")

# Alertas se necessário
if idade_fim_distribuicao > expectativa_vida:
    st.warning(f"⚠️ **Atenção:** O período de distribuição se estende até os {idade_fim_distribuicao:.0f} anos, ultrapassando a expectativa de vida de {expectativa_vida} anos.")

if anos_restantes < (periodo_acumulacao + periodo_distribuicao):
    st.warning(f"⚠️ **Atenção:** O período total do planejamento ({periodo_acumulacao + periodo_distribuicao:.0f} anos) é maior que os anos restantes de vida ({anos_restantes} anos).")

# Alertas específicos por método
if metodo_calculo == "Definir Expectativa de Vida" and periodo_distribuicao <= 5:
    st.warning(f"⚠️ **Período curto:** Com sua expectativa de vida de {expectativa_vida} anos, você terá apenas {periodo_distribuicao:.0f} anos para distribuição. Considere reduzir o período de acumulação ou aumentar a expectativa de vida.")

if metodo_calculo == "Definir Período de Distribuição" and expectativa_vida > 100:
    st.info(f"📊 **Expectativa alta:** Sua expectativa de vida calculada é de {expectativa_vida:.0f} anos. Se desejar um planejamento mais conservador, considere usar o método 'Definir Expectativa de Vida'.")

# Função para simular a evolução patrimonial
def simular_patrimonio(patrimonio_inicial, periodo_acumulacao, periodo_distribuicao, resgate_mensal, aporte_mensal, inflacao_esperada, rentabilidade_nominal_esperada, aliquota_irrf):
    
    # Convertendo taxas anuais para mensais
    rentabilidade_mensal_bruta_taxa = (1 + rentabilidade_nominal_esperada / 100.0) ** (1/12) - 1
    inflacao_mensal_calc = (1 + inflacao_esperada / 100.0) ** (1/12) - 1
    
    # Inicializando variáveis para armazenar resultados
    patrimonio_atual_para_prox_mes = patrimonio_inicial # This will carry over the EOM patrimony to next SOM
    resgate_total = 0.0
    aporte_total = 0.0
    rendimento_total = 0.0
    
    # Adicionar o estado inicial (Mês 0)
    resultados = [{
        "Mês": 0,
        "Ano": 0,
        "Patrimônio Inicial Mês": patrimonio_inicial,
        "Rendimento Mensal": 0.0,
        "Aporte Mensal Ajustado": 0.0,
        "Resgate Mensal Ajustado": 0.0,
        "Patrimônio Final Mês": patrimonio_inicial,
        "Rendimento Acumulado": rendimento_total,
        "Resgate Acumulado": resgate_total,
        "Aporte Acumulado": aporte_total,
        "Fator Inflação": 1.0,
        "Inflação Acumulada": 0.0
    }]

    meses_acumulacao = int(periodo_acumulacao * 12)
    meses_distribuicao = int(periodo_distribuicao * 12)
    meses_totais_simulacao = meses_acumulacao + meses_distribuicao
    
    # Simulação mês a mês
    for mes in range(1, meses_totais_simulacao + 1):
        patrimonio_inicial_mes_corrente = patrimonio_atual_para_prox_mes

        # Aplicar rendimento
        rendimento_bruto_mes = patrimonio_inicial_mes_corrente * rentabilidade_mensal_bruta_taxa
        rendimento_liquido_mes_corrente = rendimento_bruto_mes * (1 - aliquota_irrf / 100.0)
        rendimento_total += rendimento_liquido_mes_corrente
        
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
        resgate_ajustado_mes_corrente = resgate_do_mes_base * fator_inflacao
        resgate_total += resgate_ajustado_mes_corrente
        
        # Adicionar aportes (também ajustados pela inflação)
        aporte_ajustado_mes_corrente = aporte_do_mes_base * fator_inflacao
        aporte_total += aporte_ajustado_mes_corrente
        
        # Calcular novo patrimônio (final do mês)
        patrimonio_final_mes_corrente = patrimonio_inicial_mes_corrente + rendimento_liquido_mes_corrente - resgate_ajustado_mes_corrente + aporte_ajustado_mes_corrente
        
        patrimonio_atual_para_prox_mes = patrimonio_final_mes_corrente # Atualizar para o início do próximo mês

        # Armazenar resultado para cada mês (depois agruparemos por ano)
        resultados.append({
            "Mês": mes,
            "Ano": (mes - 1) // 12 + 1,
            "Patrimônio Inicial Mês": patrimonio_inicial_mes_corrente,
            "Rendimento Mensal": rendimento_liquido_mes_corrente,
            "Aporte Mensal Ajustado": aporte_ajustado_mes_corrente,
            "Resgate Mensal Ajustado": resgate_ajustado_mes_corrente,
            "Patrimônio Final Mês": patrimonio_final_mes_corrente,
            "Rendimento Acumulado": rendimento_total,
            "Resgate Acumulado": resgate_total,
            "Aporte Acumulado": aporte_total,
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

st.subheader("Resultados da Simulação")

ultima_linha = df_simulacao.iloc[-1]
patrimonio_final = ultima_linha["Patrimônio Final Mês"] # Atualizado
periodo_total_anos = periodo_acumulacao + periodo_distribuicao

if patrimonio_inicial > 0:
    crescimento_nominal = (patrimonio_final / patrimonio_inicial - 1) * 100
    inflacao_total_fator = (1 + inflacao_anual) ** periodo_total_anos
    if inflacao_total_fator > 0:
        crescimento_real = ((patrimonio_final / patrimonio_inicial) / inflacao_total_fator - 1) * 100
    else:
        crescimento_real = float('inf') if (patrimonio_final / patrimonio_inicial) >= 0 else float('-inf')
elif patrimonio_inicial == 0:
    if patrimonio_final > 0:
        crescimento_nominal = float('inf')
        crescimento_real = float('inf')
    elif patrimonio_final == 0:
        crescimento_nominal = 0.0
        crescimento_real = 0.0
    else:
        crescimento_nominal = float('-inf')
        crescimento_real = float('-inf')
else:
    crescimento_nominal = 0.0
    crescimento_real = 0.0

metricas_col1, metricas_col2 = st.columns(2)

with metricas_col1:
    st.metric("Patrimônio Final", f"R$ {patrimonio_final:,.2f}", border=True)
    st.metric("Total Resgatado", f"R$ {ultima_linha['Resgate Acumulado']:,.2f}", border=True)
    st.metric("Crescimento Nominal", f"{crescimento_nominal:.2f}%", border=True)

with metricas_col2:
    st.metric("Rendimentos Acumulados", f"R$ {ultima_linha['Rendimento Acumulado']:,.2f}", border=True)
    st.metric("Total Aportado", f"R$ {ultima_linha['Aporte Acumulado']:,.2f}", border=True)
    st.metric("Crescimento Real", f"{crescimento_real:.2f}%", border=True)

# Evolução do Patrimônio
st.subheader("Evolução do Patrimônio")

evolucao_options = create_chart(
    data=df_simulacao,
    columns=["Patrimônio Final Mês", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"], # Adicionado Patrimônio Inicial Mês, Renomeado Patrimônio
    names=["Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"], # Adicionado Patrimônio Inicial Mês, Renomeado Patrimônio
    chart_type='line',
    title="",
    y_axis_title="Valor (R$)",
    x_axis_title="Período (meses)",
    x_column="Período Completo",
)

hct.streamlit_highcharts(evolucao_options)

# Análise adicional
st.subheader("Contribuições para o Patrimônio")

categories_bar = ["Patrimônio Inicial", "Rendimentos", "Aportes", "Resgates", "Patrimônio Final"]
values_bar = [
    patrimonio_inicial, 
    ultima_linha["Rendimento Acumulado"], 
    ultima_linha["Aporte Acumulado"], 
    -ultima_linha["Resgate Acumulado"],
    patrimonio_final
]

df_bar_data = pd.DataFrame({
    'Categoria': categories_bar,
    'Valor': values_bar
})

barras_options = create_chart(
    data=df_bar_data,
    columns='Valor',
    names='Valores',
    chart_type='column',
    title="",
    y_axis_title="Valor (R$)",
    x_axis_title="",
    x_column='Categoria'
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
    # Construir df_memoria_anual com Patrimônio Inicial e Final do Ano
    anos = sorted(df_simulacao["Ano"].unique())
    memoria_anual_list = []
    for ano_val in anos:
        ano_data_first_month = df_simulacao[df_simulacao["Ano"] == ano_val].iloc[0]
        ano_data_last_month = df_simulacao[df_simulacao["Ano"] == ano_val].iloc[-1]
        
        memoria_anual_list.append({
            "Período": ano_data_last_month["Período"], # "Inicial" or "Ano X"
            "Patrimônio Inicial Ano": ano_data_first_month["Patrimônio Inicial Mês"],
            "Patrimônio Final Ano": ano_data_last_month["Patrimônio Final Mês"],
            "Rendimento Acumulado": ano_data_last_month["Rendimento Acumulado"],
            "Resgate Acumulado": ano_data_last_month["Resgate Acumulado"],
            "Aporte Acumulado": ano_data_last_month["Aporte Acumulado"],
            "Inflação Acumulada": ano_data_last_month["Inflação Acumulada"]
        })
    df_memoria_anual = pd.DataFrame(memoria_anual_list)

    df_memoria_anual["Patrimônio Inicial Ano"] = df_memoria_anual["Patrimônio Inicial Ano"].map("R$ {:,.2f}".format)
    df_memoria_anual["Patrimônio Final Ano"] = df_memoria_anual["Patrimônio Final Ano"].map("R$ {:,.2f}".format)
    df_memoria_anual["Rendimento Acumulado"] = df_memoria_anual["Rendimento Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Resgate Acumulado"] = df_memoria_anual["Resgate Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Aporte Acumulado"] = df_memoria_anual["Aporte Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_anual["Inflação Acumulada"] = df_memoria_anual["Inflação Acumulada"].map("{:.2%}".format)

    df_memoria_anual = df_memoria_anual[[
        "Período", 
        "Patrimônio Inicial Ano", 
        "Patrimônio Final Ano", 
        "Rendimento Acumulado", 
        "Resgate Acumulado", 
        "Aporte Acumulado", 
        "Inflação Acumulada"
    ]]
    df_memoria_anual.set_index("Período", inplace=True)

    st.dataframe(df_memoria_anual, use_container_width=True)

with tab_mensal:
    df_memoria_mensal = df_simulacao.copy()
    df_memoria_mensal["Patrimônio Inicial Mês"] = df_memoria_mensal["Patrimônio Inicial Mês"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Rendimento Mensal"] = df_memoria_mensal["Rendimento Mensal"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Patrimônio Final Mês"] = df_memoria_mensal["Patrimônio Final Mês"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Rendimento Acumulado"] = df_memoria_mensal["Rendimento Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Resgate Acumulado"] = df_memoria_mensal["Resgate Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Resgate Mensal Ajustado"] = df_memoria_mensal["Resgate Mensal Ajustado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Aporte Acumulado"] = df_memoria_mensal["Aporte Acumulado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Aporte Mensal Ajustado"] = df_memoria_mensal["Aporte Mensal Ajustado"].map("R$ {:,.2f}".format)
    df_memoria_mensal["Inflação Acumulada"] = df_memoria_mensal["Inflação Acumulada"].map("{:.2%}".format)

    df_memoria_mensal = df_memoria_mensal[[
        "Período Completo", 
        "Patrimônio Inicial Mês",
        "Rendimento Mensal",
        "Aporte Mensal Ajustado",
        "Resgate Mensal Ajustado",
        "Patrimônio Final Mês",
        "Rendimento Acumulado", 
        "Resgate Acumulado", 
        "Aporte Acumulado", 
        "Inflação Acumulada"
    ]]
    df_memoria_mensal.set_index("Período Completo", inplace=True)

    st.dataframe(df_memoria_mensal, use_container_width=True)
