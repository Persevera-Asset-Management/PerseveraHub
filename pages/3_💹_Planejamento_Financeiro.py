import streamlit as st
import streamlit_highcharts as hct
import pandas as pd
import numpy as np
import datetime
import math
import os
from utils.chart_helpers import create_chart
from utils.ui import display_logo, load_css
from utils.table import style_table

st.set_page_config(
    page_title="Planejamento Financeiro | Persevera",
    page_icon="💹",
    layout="wide"
)

display_logo()
load_css()

st.title("Planejamento Financeiro")

def simular_patrimonio(data_nascimento, patrimonio_inicial, periodo_acumulacao, periodo_distribuicao, resgate_mensal, aporte_mensal, inflacao_esperada, rentabilidade_nominal_esperada, aliquota_irrf):
    
    # Convertendo taxas anuais para mensais
    rentabilidade_mensal_bruta_taxa = (1 + rentabilidade_nominal_esperada / 100.0) ** (1/12) - 1
    inflacao_mensal_calc = (1 + inflacao_esperada / 100.0) ** (1/12) - 1
    
    # Inicializando variáveis para armazenar resultados
    patrimonio_atual_para_prox_mes = patrimonio_inicial
    resgate_total = 0.0
    aporte_total = 0.0
    rendimento_total = 0.0
    data_atual = datetime.date.today()
    
    # Adicionar o estado inicial (Mês 0)
    resultados = [{
        "Data": data_atual,
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
        
        # Atualizar data para o próximo mês
        if data_atual.month == 12:
            data_atual = datetime.date(data_atual.year + 1, 1, 1)
        else:
            data_atual = datetime.date(data_atual.year, data_atual.month + 1, 1)

        # Armazenar resultado para cada mês (depois agruparemos por ano)
        resultados.append({
            "Data": data_atual,
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
    
    # CORREÇÃO: Converter a coluna para datetime antes de usar o acessor .dt
    df_resultados['Data'] = pd.to_datetime(df_resultados['Data'])
    
    # Inclui a idade do usuário no DataFrame e as colunas necessárias para as tabelas/gráficos
    df_resultados['Idade Contínua'] = (df_resultados['Data'] - pd.to_datetime(data_nascimento)).dt.days / 365.25
    df_resultados['Idade Anos'] = df_resultados['Idade Contínua'].astype(int)
    df_resultados['Idade Meses'] = ((df_resultados['Idade Contínua'] - df_resultados['Idade Anos']) * 12).apply(np.floor)
    df_resultados['Idade Completa'] = df_resultados.apply(lambda x: f"{int(x['Idade Anos'])} anos e {int(x['Idade Meses'])} meses", axis=1)

    # Reordenar colunas
    df_resultados = df_resultados[['Data', 'Idade Anos', 'Idade Meses', 'Idade Completa', 'Idade Contínua', 'Patrimônio Inicial Mês', 'Rendimento Mensal', 'Aporte Mensal Ajustado', 'Resgate Mensal Ajustado', 'Patrimônio Final Mês', 'Rendimento Acumulado', 'Resgate Acumulado', 'Aporte Acumulado', 'Fator Inflação', 'Inflação Acumulada']]

    # st.write(df_resultados)
    return df_resultados

def goal_seek_solver(
    data_nascimento,
    target_value,
    variable_to_solve,
    guess_params,
    low_bound,
    high_bound,
    tolerance=1.0,  # Tolera uma diferença de R$1.00
    max_iterations=100
):
    """
    Encontra o valor de `variable_to_solve` que faz com que o resultado da simulação
    resulte em um patrimônio final igual a `target_value`.
    Usa o método da bisseção.
    """
    low = low_bound
    high = high_bound

    def get_final_patrimony(value):
        params = guess_params.copy()
        params[variable_to_solve] = value
        df_sim = simular_patrimonio(data_nascimento=data_nascimento, **params)
        return df_sim.iloc[-1]["Patrimônio Final Mês"]

    val_low = get_final_patrimony(low)
    val_high = get_final_patrimony(high)

    # Verifica se o alvo é alcançável dentro dos limites
    # A função deve ser monotônica (ou seja, sempre crescer ou diminuir com a variável)
    if (val_low - target_value) * (val_high - target_value) > 0:
        return None  # Alvo fora do intervalo alcançável com os limites fornecidos

    for _ in range(max_iterations):
        mid = (low + high) / 2
        val_mid = get_final_patrimony(mid)

        if abs(val_mid - target_value) < tolerance:
            return mid

        if (val_mid - target_value) * (val_low - target_value) < 0:
            high = mid
        else:
            low = mid
            val_low = val_mid
    
    return (low + high) / 2


# Definição dos parâmetros
with st.sidebar:
    with st.container(border=True):
        # st.header("Modo de Planejamento")
        st.markdown("#### Modo de Planejamento")
        modo_planejamento = st.radio(
            "Escolha seu objetivo:",
            ("Simulação", "Meta"),
            label_visibility="collapsed",
            key="modo_planejamento",
            horizontal=True,
        )

    st.header("Parâmetros")

    st.markdown("#### Características Pessoais")
    data_nascimento = st.date_input("Data de Nascimento:", value=datetime.date(1980, 1, 2), min_value=datetime.date(1900, 1, 2), max_value=datetime.date.today(), format="DD/MM/YYYY")
    idade_atual = st.number_input("Idade Atual:", min_value=18, max_value=100, value=datetime.date.today().year - data_nascimento.year, step=1, format="%d", disabled=True)

    # Escolha do método de definição
    metodo_calculo = st.radio(
        "Método de Planejamento:",
        options=["Expectativa de Vida", "Período de Distribuição"],
        help="Escolha se quer definir sua expectativa de vida ou o período de distribuição dos recursos"
    )

    st.markdown("#### Patrimônio")
    patrimonio_inicial = st.number_input("Patrimônio Inicial (R$):", min_value=0.0, value=100000.0, step=10000.0, format="%.0f")

    st.markdown("#### Fase de Acumulação")
    periodo_acumulacao = st.number_input("Período de Acumulação (anos):", min_value=0.0, value=20.0, step=1.0, format="%.0f")

    # Inputs são definidos aqui e podem ser desabilitados no modo "Meta"
    aporte_mensal_input = st.number_input("Aporte Mensal (R$):", min_value=0.0, value=5000.0, step=1000.0, format="%.0f", key="aporte_input")
    
    st.markdown("#### Fase de Distribuição")

    # Lógica condicional baseada na escolha do usuário
    if metodo_calculo == "Expectativa de Vida":
        expectativa_vida = st.number_input("Expectativa de Vida:", min_value=int(idade_atual + periodo_acumulacao), max_value=120, value=85, step=1, format="%d")
        
        # Calcular período de distribuição automaticamente
        periodo_distribuicao_calculado = expectativa_vida - idade_atual - periodo_acumulacao
        
        if periodo_distribuicao_calculado <= 0:
            st.error("⚠️ Período de distribuição resultaria em valor negativo ou zero. Ajuste a expectativa de vida ou período de acumulação.")
            periodo_distribuicao = 1.0  # Valor mínimo para evitar erros
        else:
            periodo_distribuicao = periodo_distribuicao_calculado
        
        # Campo desabilitado mostrando o valor calculado
        st.number_input(
            "Período de Distribuição (anos) - Calculado:",
            value=float(periodo_distribuicao),
            disabled=True,
            format="%.0f",
            help=f"Calculado como: {expectativa_vida} - {idade_atual} - {periodo_acumulacao:.0f} = {periodo_distribuicao:.0f} anos"
        )
        
    else:  # "Definir Período de Distribuição"
        periodo_distribuicao = st.number_input("Período de Distribuição (anos):", min_value=1.0, value=10.0, step=1.0, format="%.0f")
        
        # Calcular expectativa de vida automaticamente
        expectativa_vida = idade_atual + periodo_acumulacao + periodo_distribuicao
        
        # Campo desabilitado mostrando o valor calculado
        st.number_input("Expectativa de Vida - Calculada:", value=int(expectativa_vida), disabled=True, format="%d", help=f"Calculada como: {idade_atual} + {periodo_acumulacao:.0f} + {periodo_distribuicao:.0f} = {expectativa_vida:.0f} anos")

    resgate_mensal_input = st.number_input("Resgate Mensal (R$):", min_value=0.0, value=10000.0, step=1000.0, format="%.0f", key="resgate_input")

    # Validação da expectativa de vida (agora que a variável está definida)
    if metodo_calculo == "Definir Expectativa de Vida" and expectativa_vida <= idade_atual:
        st.error("A expectativa de vida deve ser maior que a idade atual!")

    st.markdown("#### Hipóteses de Mercado")
    rentabilidade_nominal_input = st.number_input("Rentabilidade Nominal Esperada (% a.a):", min_value=0.0, value=10.0, step=0.1, format="%.1f", key="rentabilidade_input")
    inflacao_esperada = st.number_input("Inflação Esperada (% a.a):", min_value=0.0, value=4.0, step=0.1, format="%.1f")
    aliquota_irrf = st.number_input("Alíquota de Impostos (%):", min_value=0.0, value=15.0, step=0.1, format="%.1f")

    # Lógica do modo Meta
    if modo_planejamento == "Meta":
        st.markdown("#### Configuração da Meta")
        patrimonio_final_alvo = st.number_input("Patrimônio Final Alvo (R$):", min_value=0.0, value=1000000.0, step=50000.0, format="%.0f")
        variavel_a_calcular = st.selectbox(
            "Calcular qual variável?",
            ("Aporte Mensal", "Resgate Mensal", "Rentabilidade Nominal Esperada")
        )

# --- LÓGICA PRINCIPAL ---
# Define os valores padrão das variáveis
aporte_mensal = aporte_mensal_input
resgate_mensal = resgate_mensal_input
rentabilidade_nominal_esperada = rentabilidade_nominal_input

if modo_planejamento == "Meta":
    st.markdown("#### Resultado do Planejamento por Meta")

    # Parâmetros base para o solver
    params = {
        'patrimonio_inicial': patrimonio_inicial,
        'periodo_acumulacao': periodo_acumulacao,
        'periodo_distribuicao': periodo_distribuicao,
        'aporte_mensal': aporte_mensal,
        'resgate_mensal': resgate_mensal,
        'inflacao_esperada': inflacao_esperada,
        'rentabilidade_nominal_esperada': rentabilidade_nominal_esperada,
        'aliquota_irrf': aliquota_irrf
    }
    
    variavel_map = {
        "Aporte Mensal": {'name': 'aporte_mensal', 'bounds': [0, 100000], 'format': "R$ {:,.2f}"},
        "Resgate Mensal": {'name': 'resgate_mensal', 'bounds': [0, 100000], 'format': "R$ {:,.2f}"},
        "Rentabilidade Nominal Esperada": {'name': 'rentabilidade_nominal_esperada', 'bounds': [0, 50], 'format': "{:.2f}%"}
    }
    
    var_info = variavel_map[variavel_a_calcular]
    var_name = var_info['name']
    
    # Roda o solver
    resultado = goal_seek_solver(
        data_nascimento=data_nascimento,
        target_value=patrimonio_final_alvo,
        variable_to_solve=var_name,
        guess_params=params,
        low_bound=var_info['bounds'][0],
        high_bound=var_info['bounds'][1]
    )
    
    if resultado is not None:
        st.metric(f"Valor Necessário para: {variavel_a_calcular}", var_info['format'].format(resultado))
        # Atualiza a variável com o valor encontrado para rodar a simulação
        if var_name == 'aporte_mensal':
            aporte_mensal = resultado
        elif var_name == 'resgate_mensal':
            resgate_mensal = resultado
        elif var_name == 'rentabilidade_nominal_esperada':
            rentabilidade_nominal_esperada = resultado
    else:
        st.error(f"Não foi possível atingir o patrimônio final de R$ {patrimonio_final_alvo:,.2f} ajustando a variável '{variavel_a_calcular}'. Tente ajustar outros parâmetros ou os limites da busca.")


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

# Calcular a simulação
df_simulacao = simular_patrimonio(
    data_nascimento=data_nascimento,
    patrimonio_inicial=patrimonio_inicial,
    periodo_acumulacao=periodo_acumulacao,
    periodo_distribuicao=periodo_distribuicao,
    resgate_mensal=resgate_mensal,
    aporte_mensal=aporte_mensal,
    inflacao_esperada=inflacao_esperada,
    rentabilidade_nominal_esperada=rentabilidade_nominal_esperada,
    aliquota_irrf=aliquota_irrf
)

st.markdown("#### Resultados da Simulação")

ultima_linha = df_simulacao.iloc[-1]
patrimonio_final = ultima_linha["Patrimônio Final Mês"]
periodo_total_anos = periodo_acumulacao + periodo_distribuicao

metricas_col = st.columns(2)

with metricas_col[0]:
    st.metric("Patrimônio Final", f"R$ {patrimonio_final:,.2f}", border=True)
    st.metric("Total Resgatado", f"R$ {ultima_linha['Resgate Acumulado']:,.2f}", border=True)

with metricas_col[1]:
    st.metric("Rendimentos Acumulados", f"R$ {ultima_linha['Rendimento Acumulado']:,.2f}", border=True)
    st.metric("Total Aportado", f"R$ {ultima_linha['Aporte Acumulado']:,.2f}", border=True)

# Evolução do Patrimônio
st.markdown("#### Evolução do Patrimônio")

evolucao_options = create_chart(
    data=df_simulacao.set_index("Idade Contínua"),
    columns=["Patrimônio Final Mês", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"],
    names=["Patrimônio", "Rendimento Acumulado", "Resgate Acumulado", "Aporte Acumulado"],
    chart_type='line',
    title="",
    y_axis_title="Valor (R$)",
    x_axis_title="Idade",
    # x_column="Idade Contínua",
)

hct.streamlit_highcharts(evolucao_options)

# Análise adicional
st.markdown("#### Contribuições para o Patrimônio")

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

# Tabela detalhada
st.markdown("#### Memória de Cálculo")
tab_anual, tab_mensal = st.tabs(["Anual", "Mensal"])

with tab_anual:
    # Construir df_memoria_anual com base na idade
    df_anual = df_simulacao.groupby('Idade Anos').agg(
        patrimonio_inicial_ano=('Patrimônio Inicial Mês', 'first'),
        patrimonio_final_ano=('Patrimônio Final Mês', 'last'),
        rendimento_acumulado=('Rendimento Acumulado', 'last'),
        resgate_acumulado=('Resgate Acumulado', 'last'),
        aporte_acumulado=('Aporte Acumulado', 'last'),
        inflacao_acumulada=('Inflação Acumulada', 'last')
    ).reset_index()

    # Adicionando a linha inicial (se aplicável)
    linha_inicial = df_simulacao.iloc[0]
    if not linha_inicial.empty:
        inicial_data = {
            'Idade Anos': int(idade_atual),
            'patrimonio_inicial_ano': patrimonio_inicial,
            'patrimonio_final_ano': patrimonio_inicial,
            'rendimento_acumulado': 0,
            'resgate_acumulado': 0,
            'aporte_acumulado': 0,
            'inflacao_acumulada': 0
        }
        df_anual = pd.concat([pd.DataFrame([inicial_data]), df_anual], ignore_index=True)

    df_anual.rename(columns={
        'Idade Anos': 'Idade',
        'patrimonio_inicial_ano': 'Patrimônio Inicial Ano',
        'patrimonio_final_ano': 'Patrimônio Final Ano',
        'rendimento_acumulado': 'Rendimento Acumulado',
        'resgate_acumulado': 'Resgate Acumulado',
        'aporte_acumulado': 'Aporte Acumulado',
        'inflacao_acumulada': 'Inflação Acumulada'
    }, inplace=True)

    # df_anual['Idade'] = df_anual['Idade'].apply(lambda x: f"{int(idade_atual)}" if x == int(idade_atual) else int(idade_atual))
    df_anual.set_index("Idade", inplace=True)
    
    st.dataframe(
        style_table(
            df_anual,
            numeric_cols_format_as_float=['Patrimônio Inicial Ano', 'Patrimônio Final Ano', 'Rendimento Acumulado', 'Resgate Acumulado', 'Aporte Acumulado'], percent_cols=['Inflação Acumulada']))

with tab_mensal:
    df_memoria_mensal = df_simulacao.copy()

    df_memoria_mensal = df_memoria_mensal[[
        "Idade Anos",
        "Idade Meses",
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
    df_memoria_mensal['Idade'] = df_memoria_mensal.apply(lambda x: f"{int(x['Idade Anos'])} anos e {int(x['Idade Meses'])} meses", axis=1)
    df_memoria_mensal.set_index(["Idade"], inplace=True)
    df_memoria_mensal.drop(columns=["Idade Anos", "Idade Meses"], inplace=True)

    st.dataframe(
        style_table(
            df_memoria_mensal,
            numeric_cols_format_as_float=['Patrimônio Inicial Mês', 'Rendimento Mensal', 'Aporte Mensal Ajustado', 'Resgate Mensal Ajustado', 'Patrimônio Final Mês', 'Rendimento Acumulado', 'Resgate Acumulado', 'Aporte Acumulado'],
            percent_cols=['Inflação Acumulada']
        )
    )
