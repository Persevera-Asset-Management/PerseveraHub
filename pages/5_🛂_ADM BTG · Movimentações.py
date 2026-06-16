import streamlit as st

from configs.pages.movimentacao_fundos import (
    DISTRIBUIDOR_NOMES,
    DISTRIBUIDORES,
    OPERACAO_APLICACAO,
)
from services.movimentacao_fundos_service import (
    ResultadoMovimentacao,
    TotaisDistribuidor,
    processar,
)
from utils.auth import check_authentication
from utils.ui import display_logo, load_css

SESSION_KEY_RESULTADO = "resultado_movimentacao_fundos"

st.set_page_config(
    page_title="ADM BTG · Movimentações | Persevera",
    page_icon="🛂",
    layout="wide",
    initial_sidebar_state="expanded",
)

display_logo()
load_css()
check_authentication()

st.title("ADM BTG · Movimentações")

COR_APLICACAO = "#10b981"
COR_RESGATE = "#ef4444"
COR_POSITIVO = "#0f6e56"
COR_NEGATIVO = "#a32d2d"
COR_NEUTRO = "#949694"

BADGE_STYLES = {
    "XP": "background:#0c2a47;color:#7ab8f5;",
    "BTG": "background:#162b0f;color:#8ecb6a;",
    "Outros": "background:#2a2a28;color:#9b9994;",
}


def formatar_moeda(valor: float) -> str:
    if valor == 0:
        return "R$ —"
    return f"R$ {abs(valor):,.0f}".replace(",", ".")


def formatar_moeda_compacta(valor: float) -> str:
    absoluto = abs(valor)
    if absoluto >= 1_000_000:
        return f"R$ {absoluto / 1_000_000:.1f}M".replace(".", ",")
    if absoluto >= 1_000:
        return f"R$ {absoluto / 1_000:.0f}K"
    return formatar_moeda(valor)


def formatar_liquido(valor: float) -> str:
    if valor == 0:
        return "R$ —"
    sinal = "+ " if valor > 0 else "− "
    return sinal + formatar_moeda(abs(valor))


def cor_liquido(valor: float) -> str:
    if valor > 0:
        return COR_POSITIVO
    if valor < 0:
        return COR_NEGATIVO
    return COR_NEUTRO


def badge_distribuidor(distribuidor: str) -> str:
    estilo = BADGE_STYLES.get(distribuidor, BADGE_STYLES["Outros"])
    return (
        f'<span style="{estilo}font-size:11px;font-weight:600;padding:2px 9px;'
        f'border-radius:6px;">{distribuidor}</span>'
    )


def render_distribuidor_card(nome: str, totais: TotaisDistribuidor) -> None:
    zerado = totais["aplicacoes"] == 0 and totais["resgates"] == 0
    with st.container(border=True, height="stretch"):
        st.markdown(
            f'{badge_distribuidor(nome)} &nbsp; **{DISTRIBUIDOR_NOMES[nome]}**',
            unsafe_allow_html=True,
        )
        if zerado:
            st.caption("Aplicações · R$ —")
            st.caption("Resgates · R$ —")
            st.caption("Líquido · R$ —")
            return

        col_aplicacoes, col_resgates = st.columns(2)
        with col_aplicacoes:
            st.markdown(
                f'<p style="margin:0;font-size:12px;color:{COR_NEUTRO}">Aplicações</p>'
                f'<p style="margin:0;font-size:16px;font-weight:600;color:{COR_APLICACAO}">'
                f'{formatar_moeda(totais["aplicacoes"])}</p>',
                unsafe_allow_html=True,
            )
        with col_resgates:
            st.markdown(
                f'<p style="margin:0;font-size:12px;color:{COR_NEUTRO}">Resgates</p>'
                f'<p style="margin:0;font-size:16px;font-weight:600;color:{COR_RESGATE}">'
                f'{formatar_moeda(totais["resgates"])}</p>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<p style="margin:8px 0 0;font-size:12px;color:{COR_NEUTRO}">Líquido</p>'
            f'<p style="margin:0;font-size:16px;font-weight:600;color:{cor_liquido(totais["liquido"])}">'
            f'{formatar_liquido(totais["liquido"])}</p>',
            unsafe_allow_html=True,
        )


def render_fundo_card(fundo: dict) -> None:
    with st.container(border=True, height="stretch"):
        st.markdown(f"**{fundo['nome']}**")
        for movimentacao in fundo["movimentacoes"]:
            operacao = movimentacao["operacao"]
            rotulo_operacao = "Aplicação" if operacao == OPERACAO_APLICACAO else "Resgate"
            cor_operacao = COR_APLICACAO if operacao == OPERACAO_APLICACAO else COR_RESGATE
            st.markdown(
                f'<div style="display:grid;grid-template-columns:auto 1fr auto auto;'
                f'gap:8px;align-items:center;margin-bottom:4px;font-size:13px;">'
                f'{badge_distribuidor(movimentacao["distribuidor"])}'
                f'<span style="color:{COR_NEUTRO}">{rotulo_operacao}</span>'
                f'<span style="font-weight:600;color:{cor_operacao};text-align:right;">'
                f'{formatar_moeda(movimentacao["valor"])}</span>'
                f'<span style="color:{COR_NEUTRO};text-align:right;white-space:nowrap;">'
                f'{movimentacao["boletas"]} bol.</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<p style="margin:8px 0 0;font-size:12px;color:{COR_NEUTRO}">Líquido total</p>'
            f'<p style="margin:0;font-size:15px;font-weight:600;color:{cor_liquido(fundo["liquido"])}">'
            f'{formatar_liquido(fundo["liquido"])}</p>',
            unsafe_allow_html=True,
        )


def render_painel(resultado: ResultadoMovimentacao) -> None:
    come_cotas = resultado["come_cotas"]
    total_come_cotas_qtd = sum(item["quantidade"] for item in come_cotas.values())
    total_come_cotas_valor = sum(item["valor"] for item in come_cotas.values())

    st.caption(
        f"Gerado em {resultado['timestamp_geracao']} · "
        f"Arquivo: {resultado['timestamp_arquivo']}"
    )
    if come_cotas:
        st.warning(
            f"Come cotas excluídos da análise ({total_come_cotas_qtd:,} boletas)".replace(",", ".")
        )

    st.markdown("#### Totais gerais")
    col_aplicacoes, col_resgates, col_liquido, col_boletas = st.columns(4)
    with col_aplicacoes:
        st.metric("Aplicações", formatar_moeda_compacta(resultado["total_aplicacoes"]))
    with col_resgates:
        st.metric("Resgates", formatar_moeda_compacta(resultado["total_resgates"]))
    with col_liquido:
        st.metric("Líquido", formatar_liquido(resultado["total_liquido"]))
    with col_boletas:
        st.metric("Boletas", f"{resultado['total_boletas']:,}".replace(",", "."))

    st.markdown("#### Por distribuidor")
    cols = st.columns(3)
    for col, distribuidor in zip(cols, DISTRIBUIDORES):
        with col:
            render_distribuidor_card(distribuidor, resultado["por_distribuidor"][distribuidor])

    st.markdown("#### Por fundo e distribuidor")
    fundos = resultado["fundos"]
    for indice in range(0, len(fundos), 3):
        row_cols = st.columns(3)
        for col, fundo in zip(row_cols, fundos[indice : indice + 3]):
            with col:
                render_fundo_card(fundo)

    if come_cotas:
        st.markdown("#### Resgate Come Cotas")
        linhas_come_cotas = [
            {
                "Fundo": nome,
                "Registros": item["quantidade"],
                "Valor (R$)": item["valor"],
            }
            for nome, item in sorted(come_cotas.items())
        ]
        st.dataframe(linhas_come_cotas, hide_index=True, width="stretch")
        st.caption(f"Total come cotas: **{formatar_moeda(total_come_cotas_valor)}**")

    if resultado["excluidas"]:
        with st.expander(
            f"Boletas excluídas — não contabilizadas ({len(resultado['excluidas'])})",
            expanded=False,
        ):
            for boleta in resultado["excluidas"]:
                st.markdown(
                    f"- {boleta['cliente']} — {boleta['fundo']} · {boleta['operacao']} · "
                    f"{formatar_moeda(boleta['valor'])} · Boleta {boleta['boleta_id']}"
                )


with st.sidebar:
    st.header("Parâmetros")
    uploaded_file = st.file_uploader(
        "Planilha BTG (.xlsx)",
        type=["xlsx", "xls"],
        help="Arquivo de movimentações exportado do ADM BTG.",
    )
    btn_processar = st.button(
        "Processar arquivo",
        width="stretch",
        disabled=uploaded_file is None,
    )
    if st.button("Limpar resultado", width="stretch"):
        st.session_state.pop(SESSION_KEY_RESULTADO, None)
        st.rerun()

st.markdown("Fundos Condominiais (ADM BTG) — Consolidado por Distribuidor")

if btn_processar and uploaded_file is not None:
    with st.spinner("Processando boletas..."):
        try:
            st.session_state[SESSION_KEY_RESULTADO] = processar(
                uploaded_file.getvalue(),
                uploaded_file.name,
            )
        except Exception as exc:
            st.error(f"Não foi possível processar o arquivo: {exc}")

if SESSION_KEY_RESULTADO not in st.session_state:
    if uploaded_file is None:
        st.info("Envie um arquivo .xlsx na barra lateral para iniciar a análise.")
    else:
        st.info("Clique em **Processar arquivo** para gerar o consolidado.")
    st.stop()

render_painel(st.session_state[SESSION_KEY_RESULTADO])
