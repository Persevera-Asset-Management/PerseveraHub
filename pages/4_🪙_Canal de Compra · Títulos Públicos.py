import numpy as np
import pandas as pd
import streamlit as st
import streamlit_highcharts as hct
from utils.chart_helpers import create_chart, render_chart
from utils.ui import display_logo, load_css
from utils.auth import check_authentication

st.set_page_config(
    page_title="Tesouro Direto vs Mesa | Persevera",
    page_icon="🪙",
    layout="wide",
)

display_logo()
load_css()
check_authentication()

st.title("NTN-F · Mesa vs. Tesouro Direto")
st.caption("Tesouro Prefixado com Juros Semestrais · Venc. 01/01/2032")

# =============================================================================
# FUNÇÕES DE CÁLCULO
# =============================================================================

COLORS = {
    "mesa":   "#1D9E75",
    "td":     "#378ADD",
    "cust":   "#E24B4A",
    "neutro": "#888780",
    "amber":  "#BA7517",
    "zero":   "rgba(120,120,120,0.4)",
}


def calc_net_annual_bps(yield_mesa: float, yield_td: float, custodia: float) -> float:
    """Vantagem anual da Mesa sobre o TD em bps. Positivo → Mesa melhor."""
    dy = yield_td - yield_mesa
    return (custodia - dy) * 100


def calc_breakeven_prazo(net_annual_bps: float, spread_saida_bps: float) -> float:
    """Tempo mínimo de hold (anos) para a Mesa superar o TD em venda antecipada."""
    if net_annual_bps <= 0:
        return np.inf
    return spread_saida_bps / net_annual_bps


def build_timeseries(
    yield_mesa: float,
    yield_td: float,
    custodia: float,
    spread_saida_bps: float,
    prazo_titulo: float,
    steps: int = 200,
) -> pd.DataFrame:
    t = np.linspace(0, prazo_titulo, steps + 1)
    dy_bps = (yield_td - yield_mesa) * 100
    cust_bps = custodia * 100
    net_annual = cust_bps - dy_bps

    return pd.DataFrame({
        "t":            t,
        "td_custodia":  t * cust_bps,
        "td_dy_bruto":  t * dy_bps,
        "td_net":       t * (cust_bps - dy_bps),
        "mesa_hold":    np.zeros(len(t)),
        "mesa_saida":   np.full(len(t), spread_saida_bps),
        "vant_mesa_htm": t * net_annual,
        "vant_mesa_ant": t * net_annual - spread_saida_bps,
    })


def build_cenarios(
    yield_mesa: float,
    yield_td: float,
    custodia: float,
    prazo_titulo: float,
) -> pd.DataFrame:
    spreads = [5, 10, 15, 20, 25, 30, 40, 50]
    net = calc_net_annual_bps(yield_mesa, yield_td, custodia)
    rows = []
    for sp in spreads:
        bk = calc_breakeven_prazo(net, sp)
        rows.append({
            "Spread saída (bps)": sp,
            "Breakeven (anos)": round(bk, 2) if bk < 99 else "> prazo",
            "Mesa vence no venc.?": "Sim" if net > 0 else "Não",
            "Vantagem Mesa no venc. (bps)": round(net * prazo_titulo, 1),
        })
    return pd.DataFrame(rows)


# =============================================================================
# FUNÇÕES DE VISUALIZAÇÃO
# =============================================================================

def _breakeven_vline(bk_prazo: float, t_max: float) -> dict | None:
    if np.isfinite(bk_prazo) and bk_prazo <= t_max:
        return {
            "value": bk_prazo,
            "color": COLORS["amber"],
            "width": 2,
            "dashStyle": "Dot",
            "label": {"text": f"T* = {bk_prazo:.2f}a", "align": "right", "rotation": 0},
        }
    return None


def chart_custos_acumulados(df: pd.DataFrame, bk_prazo: float) -> dict:
    return create_chart(
        data=df,
        columns=["mesa_hold", "mesa_saida", "td_custodia", "td_net"],
        names=[
            "Mesa — hold (custo adicional = 0)",
            "Mesa — spread de saída antecipada",
            "TD — custódia acumulada",
            "TD — custo líq. (custódia − Δy bruto)",
        ],
        color=[COLORS["mesa"], COLORS["td"], COLORS["cust"], COLORS["neutro"]],
        chart_type="spline",
        title="Custo acumulado por canal (bps)",
        y_axis_title="Bps acumulados",
        x_axis_title="Tempo (anos)",
        x_column="t",
        height=320,
        decimal_precision=1,
        vertical_line=_breakeven_vline(bk_prazo, df["t"].max()),
    )


def chart_vantagem_liquida(df: pd.DataFrame, bk_prazo: float) -> dict:
    return create_chart(
        data=df,
        columns=["vant_mesa_htm", "vant_mesa_ant"],
        names=["Hold to maturity", "Venda antecipada"],
        color=[COLORS["mesa"], COLORS["neutro"]],
        chart_type="areaspline",
        title="Vantagem líquida da Mesa (bps) — positivo = Mesa melhor",
        y_axis_title="Bps",
        x_axis_title="Tempo (anos)",
        x_column="t",
        height=280,
        decimal_precision=1,
        horizontal_line={"value": 0, "color": COLORS["zero"], "width": 1},
        vertical_line=_breakeven_vline(bk_prazo, df["t"].max()),
    )


def chart_sensibilidade_spread(
    yield_mesa: float,
    yield_td: float,
    custodia: float,
    prazo_titulo: float,
) -> dict:
    net = calc_net_annual_bps(yield_mesa, yield_td, custodia)
    spreads = np.linspace(0, 60, 300)
    bks = (
        np.full(len(spreads), np.nan)
        if net <= 0
        else np.minimum(spreads / net, prazo_titulo * 1.5)
    )
    df_sens = pd.DataFrame({"spread": spreads, "breakeven": bks})

    return create_chart(
        data=df_sens,
        columns=["breakeven"],
        names=["Breakeven T*"],
        color=[COLORS["amber"]],
        chart_type="spline",
        title="Sensibilidade do breakeven ao spread de saída",
        y_axis_title="Prazo mínimo de hold (anos)",
        x_axis_title="Spread de saída na Mesa (bps)",
        x_column="spread",
        height=280,
        decimal_precision=2,
        horizontal_line={
            "value": prazo_titulo,
            "color": COLORS["neutro"],
            "width": 1,
            "dashStyle": "Dot",
            "label": {"text": f"Vencimento ({prazo_titulo:.1f}a)", "align": "right"},
        },
    )


# =============================================================================
# SIDEBAR — Parâmetros
# =============================================================================

with st.sidebar:
    st.header("Parâmetros")
    yield_mesa = st.number_input(
        "Yield Mesa — ao comprador (% a.a.)",
        min_value=5.0, max_value=25.0, value=13.81, step=0.01, format="%.2f",
    )
    yield_td = st.number_input(
        "Yield TD — bruto (% a.a.)",
        min_value=5.0, max_value=25.0, value=13.89, step=0.01, format="%.2f",
    )
    custodia = st.number_input(
        "Custódia TD (% a.a.)",
        min_value=0.0, max_value=1.0, value=0.20, step=0.01, format="%.2f",
    )
    st.markdown("---")
    spread_saida = st.slider(
        "Spread de saída antecipada — Mesa (bps)",
        min_value=0, max_value=80, value=15, step=1,
    )
    prazo_titulo = st.slider(
        "Prazo total do título (anos)",
        min_value=0.5, max_value=15.0, value=5.8, step=0.25,
    )

# =============================================================================
# CÁLCULOS
# =============================================================================

net_annual = calc_net_annual_bps(yield_mesa, yield_td, custodia)
bk_prazo   = calc_breakeven_prazo(net_annual, spread_saida)
td_liq     = yield_td - custodia
dy_bps     = (yield_td - yield_mesa) * 100
cust_bps   = custodia * 100
htm_acum   = net_annual * prazo_titulo
df         = build_timeseries(yield_mesa, yield_td, custodia, spread_saida, prazo_titulo)

# =============================================================================
# SEÇÃO 1 — Premissa
# =============================================================================

with st.expander("Premissa do modelo", expanded=False):
    st.markdown(
        """
        O **yield cotado na mesa** (ex: 13,81%) já é o yield ao comprador —
        o spread bid-ask do dealer está embutido na taxa. Não há custo
        adicional de entrada explícito.

        O **Tesouro Direto** oferece yield bruto ligeiramente superior, mas
        cobra **custódia de 0,20% a.a.** (B3) sobre o valor de mercado do
        título, cobrada semestralmente.

        Para **venda antecipada**, o TD tem recompra garantida pelo Tesouro
        Nacional sem spread. A mesa exige negociação no mercado secundário,
        onde um bid-ask é pago pontualmente no momento da saída.

        O breakeven de prazo é:
        ```
        T* = spread_saida_bps / (custódia_bps − Δy_bruto_bps)
        ```
        """
    )

# =============================================================================
# SEÇÃO 2 — Resumo (métricas)
# =============================================================================

st.subheader("Resumo")

rows_1 = st.columns(4)
rows_1[0].metric(
    "Δy bruto (TD − Mesa)",
    f"{dy_bps:+.0f} bps",
    help="Vantagem de yield bruto do TD antes da custódia",
)
rows_1[1].metric(
    "Drag custódia TD",
    f"−{cust_bps:.0f} bps/ano",
    help="Arrasto anual da taxa de custódia B3",
)
rows_1[2].metric(
    "Net Mesa (hold)",
    f"{net_annual:+.1f} bps/ano",
    delta=f"{htm_acum:+.0f} bps em {prazo_titulo:.1f}a",
    delta_color="normal" if net_annual > 0 else "inverse",
)
rows_1[3].metric(
    "Yield líq. TD",
    f"{td_liq:.2f}%",
    delta=f"{(td_liq - yield_mesa)*100:+.0f} bps vs Mesa",
    delta_color="normal" if td_liq > yield_mesa else "inverse",
)

# =============================================================================
# SEÇÃO 3 — Veredito por cenário
# =============================================================================

st.subheader("Veredito")

rows_2 = st.columns(2)

with rows_2[0]:
    st.markdown("**Cenário 1 — Hold to maturity**")
    if net_annual > 0:
        st.success(f"✓ Mesa vence em **+{htm_acum:.0f} bps** acumulados nos {prazo_titulo:.1f} anos.")
    elif net_annual < 0:
        st.info(f"TD vence — Δy bruto supera a custódia em {-net_annual:.1f} bps/ano.")
    else:
        st.warning("Empate exato — Δy = custódia.")

with rows_2[1]:
    st.markdown("**Cenário 2 — Venda antecipada**")
    if not np.isfinite(bk_prazo):
        st.info("TD vence em qualquer prazo — arrasto nunca supera o spread de saída.")
    elif bk_prazo > prazo_titulo:
        st.info(
            f"TD vence em venda antecipada — breakeven ({bk_prazo:.2f}a) "
            f"além do vencimento ({prazo_titulo:.1f}a)."
        )
    else:
        st.success(
            f"Mesa vence após **{bk_prazo:.2f} anos** de hold. "
            f"Antes disso, TD é melhor (sem spread de saída)."
        )

# =============================================================================
# SEÇÃO 4 — Dinâmica de custos
# =============================================================================

st.subheader("Dinâmica dos custos ao longo do tempo")

hct.streamlit_highcharts(chart_custos_acumulados(df, bk_prazo))
hct.streamlit_highcharts(chart_vantagem_liquida(df, bk_prazo))

# =============================================================================
# SEÇÃO 5 — Sensibilidade
# =============================================================================

st.subheader("Sensibilidade — Breakeven vs. Spread de saída")
st.caption(
    "Quanto maior o spread cobrado na venda antecipada da mesa, "
    "mais tempo o investidor precisa segurar o papel para a mesa compensar."
)

hct.streamlit_highcharts(chart_sensibilidade_spread(yield_mesa, yield_td, custodia, prazo_titulo))

# =============================================================================
# SEÇÃO 6 — Tabela de breakeven por spread de saída
# =============================================================================

st.subheader("Tabela de breakeven por spread de saída")

df_cen = build_cenarios(yield_mesa, yield_td, custodia, prazo_titulo)


def color_bk(val):
    if val == "> prazo":
        return "color: #888780"
    try:
        v = float(str(val).replace(",", "."))
        if v < 1:
            return "color: #E24B4A"
        if v < 2.5:
            return "color: #BA7517"
        return "color: #1D9E75"
    except Exception:
        return ""


styled = (
    df_cen.style
    .applymap(color_bk, subset=["Breakeven (anos)"])
    .format({"Vantagem Mesa no venc. (bps)": "{:+.1f}"})
)
st.dataframe(styled, use_container_width=True, hide_index=True)

# =============================================================================
# SEÇÃO 7 — Decomposição no vencimento
# =============================================================================

st.subheader("Decomposição no vencimento")

st.table(pd.DataFrame({
    "Item": [
        "Yield bruto Mesa (spread embutido na taxa)",
        "Yield bruto TD",
        "Δy bruto (TD − Mesa)",
        "Custódia TD acumulada no prazo",
        "Resultado líquido hold-to-maturity (Mesa − TD)",
    ],
    "Valor": [
        f"{yield_mesa:.2f}% a.a.",
        f"{yield_td:.2f}% a.a.",
        f"{dy_bps:+.1f} bps",
        f"−{cust_bps * prazo_titulo:.1f} bps",
        f"{htm_acum:+.1f} bps acum.",
    ],
}))

st.caption(
    "Nota: a análise acima é linear (bps como aproximação de primeira ordem). "
    "Para um cálculo preciso de PU, considere a estrutura de cupons semestrais "
    "e o efeito da marcação a mercado sobre a base de cálculo da custódia."
)
