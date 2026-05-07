import io
import numpy as np
import pandas as pd
import streamlit as st
import streamlit_highcharts as hct
from datetime import datetime

from utils.ui import display_logo, load_css
from utils.auth import check_authentication
from utils.table import style_table
from utils.chart_helpers import create_chart

from persevera_tools.quant_research.two_stage_risk_parity import build_spectrum
from persevera_tools.quant_research.two_stage_risk_parity.loaders import load_from_fibery

from configs.pages.capital_market_assumptions import BUCKET_COLORS


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Modelo de Alocação | Persevera",
    page_icon="💹",
    layout="wide",
)

display_logo()
load_css()
check_authentication()

st.title("Modelo de Alocação · Two-Stage Risk Parity")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner="Carregando calibração do Fibery...")
def _load_config(status: str):
    return load_from_fibery(status=status)


@st.cache_data(ttl=3600, show_spinner="Calculando espectro de alocação...")
def _build_spectrum_with_overrides(
    status: str,
    sigma_min_pct: float | None,
    sigma_max_pct: float | None,
    n_profiles: int | None,
    min_weight_threshold: float | None,
):
    config = _load_config(status)
    overrides = {}
    if sigma_min_pct is not None:
        overrides["sigma_min_pct"] = sigma_min_pct
    if sigma_max_pct is not None:
        overrides["sigma_max_pct"] = sigma_max_pct
    if n_profiles is not None:
        overrides["n_profiles"] = n_profiles
    if min_weight_threshold is not None:
        overrides["min_weight_threshold"] = min_weight_threshold
    if overrides:
        config = config.with_overrides(**overrides)
    return config, build_spectrum(config)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _shade(hex_color: str, factor: float) -> str:
    """Lighten (factor>0) or darken (factor<0) a color. factor in [-1, 1]."""
    r, g, b = _hex_to_rgb(hex_color)
    if factor >= 0:
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
    else:
        r = int(r * (1 + factor))
        g = int(g * (1 + factor))
        b = int(b * (1 + factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_asset_palette(classes: list[str], buckets_for_class: list[str]) -> dict[str, str]:
    """Generate one color per asset, derived from its bucket color with shades
    that span from light to dark *within* the bucket."""
    palette: dict[str, str] = {}
    by_bucket: dict[str, list[str]] = {}
    for cls, bk in zip(classes, buckets_for_class):
        by_bucket.setdefault(bk, []).append(cls)

    for bucket, names in by_bucket.items():
        base = BUCKET_COLORS.get(bucket, "#888888")
        n = len(names)
        if n == 1:
            palette[names[0]] = base
            continue
        for i, name in enumerate(names):
            # spread shades from -0.35 (darker) to +0.45 (lighter)
            factor = -0.35 + (0.80 * i / (n - 1))
            palette[name] = _shade(base, factor)
    return palette


# ---------------------------------------------------------------------------
# Sidebar — parâmetros da simulação
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Parâmetros")
    status_filter = st.selectbox(
        "Status da calibração",
        options=["Rascunho", "Em Vigor", "Histórica"],
        index=0,
    )

    st.markdown("---")
    st.caption("Overrides (deixe em branco para usar o valor da calibração)")
    use_overrides = st.toggle("Habilitar overrides", value=False)
    sigma_min_input = sigma_max_input = n_profiles_input = thr_input = None
    if use_overrides:
        sigma_min_input = st.number_input(
            "σ mínimo (%)",
            min_value=0.1,
            max_value=50.0,
            value=1.0,
            step=0.1,
            format="%.2f",
        )
        sigma_max_input = st.number_input(
            "σ máximo (%)",
            min_value=0.1,
            max_value=50.0,
            value=12.0,
            step=0.1,
            format="%.2f",
        )
        n_profiles_input = st.number_input(
            "Nº de perfis",
            min_value=2,
            max_value=20,
            value=10,
            step=1,
        )
        thr_input = st.number_input(
            "Limite mínimo de peso",
            min_value=0.0,
            max_value=0.05,
            value=0.005,
            step=0.001,
            format="%.3f",
        )


# ---------------------------------------------------------------------------
# Carregamento + cálculo
# ---------------------------------------------------------------------------
try:
    config, result = _build_spectrum_with_overrides(
        status=status_filter,
        sigma_min_pct=sigma_min_input,
        sigma_max_pct=sigma_max_input,
        n_profiles=n_profiles_input,
        min_weight_threshold=thr_input,
    )
except Exception as e:
    st.error(f"Erro ao carregar/calcular espectro: {e}")
    st.stop()


classes: list[str] = result["classes"]
vols: np.ndarray = result["vols"]
cov: np.ndarray = result["cov"]
vol_targets: np.ndarray = result["vol_targets"]
weights: dict[int, np.ndarray] = result["weights"]
vol_realized: dict[int, float] = result["vol_realized"]
risk_contrib: dict[int, np.ndarray] = result["risk_contrib"]
rc_target_bucket: dict[int, np.ndarray] = result["rc_target_bucket"]
rc_realized_bucket: dict[int, np.ndarray] = result["rc_realized_bucket"]
rc_target_asset: dict[int, np.ndarray] = result["rc_target_asset"]
converged_per_profile: dict[int, bool] = result["converged_per_profile"]
bucket_indices: dict[str, list[int]] = result["bucket_indices"]
bucket_labels: dict[str, str] = result["bucket_labels"]
w_hrp: np.ndarray = result["w_hrp"]
w_macro: np.ndarray = result["w_macro"]
vol_hrp: float = result["vol_hrp"]

profiles = sorted(weights.keys())
buckets_order = list(bucket_indices.keys())
profile_labels = [f"P{p}" for p in profiles]

# Bucket lookup per asset
bucket_for_asset = {a.name: a.bucket for a in config.assets}
buckets_for_class = [bucket_for_asset[c] for c in classes]
asset_palette = _build_asset_palette(classes, buckets_for_class)
bucket_rank = {b: i for i, b in enumerate(buckets_order)}

# Class order: by bucket then as defined in config
ordered_classes = [
    cls for bk in buckets_order for cls in classes if bucket_for_asset[cls] == bk
]


# ---------------------------------------------------------------------------
# Header — metadados da calibração
# ---------------------------------------------------------------------------
calib_name = config.calibration_name or "—"
calib_status = config.calibration_status or "—"
calib_date = config.calibration_date or "—"

meta_cols = st.columns(4)
meta_cols[0].metric("Calibração", calib_name)
meta_cols[1].metric("Status", calib_status)
meta_cols[2].metric("Data", calib_date)
meta_cols[3].metric(
    "Faixa de σ",
    f"{config.sigma_min_pct:.2f}% – {config.sigma_max_pct:.2f}%",
)

if not all(converged_per_profile.values()):
    bad = [p for p, ok in converged_per_profile.items() if not ok]
    st.warning(f"Solver não convergiu para os perfis: {bad}")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_overview, tab_spectrum, tab_profile, tab_inputs, tab_hrp = st.tabs(
    [
        "Visão Geral",
        "Espectro de Alocação",
        "Detalhe do Perfil",
        "Inputs do Modelo",
        "Diagnóstico HRP",
    ]
)


# ===========================================================================
# Tab 1 — Visão Geral
# ===========================================================================
with tab_overview:
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Classes de ativo", len(classes))
    kpi_cols[1].metric("Buckets", len(buckets_order))
    kpi_cols[2].metric("Perfis", len(profiles))
    kpi_cols[3].metric(
        "Limite mínimo de peso", f"{config.min_weight_threshold * 100:.2f}%"
    )

    st.markdown("#### Configuração das Classes")
    df_assets = pd.DataFrame(
        [
            {
                "Bucket": a.bucket,
                "Classe de Ativo": a.name,
                "Proxy": a.proxy,
                "Vol (a.a.)": a.default_vol * 100,
                "Max Weight": a.max_weight * 100 if a.max_weight is not None else np.nan,
                "Max RC": a.max_rc * 100 if a.max_rc is not None else np.nan,
            }
            for a in config.assets
        ]
    )
    df_assets["__rank"] = df_assets["Bucket"].map(bucket_rank)
    df_assets = (
        df_assets.sort_values(["__rank", "Classe de Ativo"])
        .drop(columns="__rank")
        .set_index(["Bucket", "Classe de Ativo"])
    )

    st.dataframe(
        style_table(
            df_assets,
            percent_cols=["Vol (a.a.)", "Max Weight", "Max RC"],
        ),
        width='stretch',
    )

    st.markdown("#### RC-Targets por Bucket (endpoints)")
    df_rc = pd.DataFrame(
        [
            {
                "Bucket": rc.bucket,
                "RC P1": rc.rc_p1 * 100,
                f"RC P{config.n_profiles}": rc.rc_p10 * 100,
            }
            for rc in config.rc_targets.values()
        ]
    ).set_index("Bucket")
    st.dataframe(
        style_table(df_rc, percent_cols=df_rc.columns.tolist()),
        width='stretch',
    )


# ===========================================================================
# Tab 2 — Espectro de Alocação
# ===========================================================================
with tab_spectrum:
    # Wide DataFrames (rows=profile labels, columns=class/bucket) in % units
    df_w_class = pd.DataFrame(
        {cls: [weights[p][i] * 100 for p in profiles] for i, cls in enumerate(classes)},
        index=profile_labels,
    )[ordered_classes]

    df_rc_class = pd.DataFrame(
        {
            cls: [risk_contrib[p][i] * 100 for p in profiles]
            for i, cls in enumerate(classes)
        },
        index=profile_labels,
    )[ordered_classes]

    df_w_bucket = pd.DataFrame(
        {bk: df_w_class.iloc[:, idxs].sum(axis=1) for bk, idxs in bucket_indices.items()}
    )
    df_rc_bucket = pd.DataFrame(
        {bk: df_rc_class.iloc[:, idxs].sum(axis=1) for bk, idxs in bucket_indices.items()}
    )

    asset_colors = [asset_palette[c] for c in ordered_classes]
    bucket_colors_list = [BUCKET_COLORS.get(b, "#888888") for b in buckets_order]

    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### Pesos por Classe")
        chart = create_chart(
            data=df_w_class,
            columns=ordered_classes,
            names=ordered_classes,
            color=asset_colors,
            chart_type="column",
            stacking="percent",
            title="Espectro de Pesos · Classe",
            y_axis_title="%",
            x_axis_title="Perfil",
            height=420,
        )
        hct.streamlit_highcharts(chart)

    with cols[1]:
        st.markdown("#### Pesos por Bucket")
        chart = create_chart(
            data=df_w_bucket,
            columns=buckets_order,
            names=buckets_order,
            color=bucket_colors_list,
            chart_type="column",
            stacking="percent",
            title="Espectro de Pesos · Bucket",
            y_axis_title="%",
            x_axis_title="Perfil",
            height=420,
        )
        hct.streamlit_highcharts(chart)

    cols = st.columns(2)
    with cols[0]:
        st.markdown("#### Contribuição de Risco por Classe")
        chart = create_chart(
            data=df_rc_class,
            columns=ordered_classes,
            names=ordered_classes,
            color=asset_colors,
            chart_type="column",
            stacking="percent",
            title="Espectro de Contrib. de Risco · Classe",
            y_axis_title="%",
            x_axis_title="Perfil",
            height=420,
        )
        hct.streamlit_highcharts(chart)

    with cols[1]:
        st.markdown("#### Contribuição de Risco por Bucket")
        chart = create_chart(
            data=df_rc_bucket,
            columns=buckets_order,
            names=buckets_order,
            color=bucket_colors_list,
            chart_type="column",
            stacking="percent",
            title="Espectro de Contrib. de Risco · Bucket",
            y_axis_title="%",
            x_axis_title="Perfil",
            height=420,
        )
        hct.streamlit_highcharts(chart)

    # σ alvo vs σ realizado
    st.markdown("#### σ Alvo vs σ Realizado")
    df_vol = pd.DataFrame(
        {
            "σ Alvo (%)": vol_targets * 100,
            "σ Realizado (%)": [vol_realized[p] for p in profiles],
        },
        index=profile_labels,
    )
    chart_vol = create_chart(
        data=df_vol,
        columns=["σ Alvo (%)", "σ Realizado (%)"],
        names=["σ Alvo", "σ Realizado"],
        color=["#9CA3AF", "#4682B4"],
        chart_type="column",
        title="σ por Perfil",
        y_axis_title="%",
        x_axis_title="Perfil",
        height=350,
    )
    hct.streamlit_highcharts(chart_vol)

    # Tabela de pesos
    st.markdown("#### Tabela de Pesos por Perfil (%)")
    df_w_table = df_w_class.T.round(2)
    df_w_table.index.name = "Classe de Ativo"
    df_w_table.insert(0, "Bucket", [bucket_for_asset[c] for c in df_w_table.index])
    df_w_table = df_w_table.reset_index().set_index(["Bucket", "Classe de Ativo"])

    st.dataframe(
        style_table(df_w_table, percent_cols=df_w_table.columns.tolist()),
        width='stretch',
    )


# ===========================================================================
# Tab 3 — Detalhe do Perfil
# ===========================================================================
with tab_profile:
    sel_cols = st.columns([1, 3])
    with sel_cols[0]:
        selected_profile = st.selectbox(
            "Perfil",
            options=profiles,
            format_func=lambda p: f"P{p}  (σ={vol_realized[p]:.2f}%)",
            index=len(profiles) // 2,
        )

    p = selected_profile
    w_p = weights[p]
    rc_p = risk_contrib[p]
    rc_t_a = rc_target_asset[p]
    rc_r_b = rc_realized_bucket[p]
    rc_t_b = rc_target_bucket[p]

    kpi = st.columns(4)
    kpi[0].metric("σ alvo", f"{vol_targets[profiles.index(p)] * 100:.2f}%")
    kpi[1].metric("σ realizado", f"{vol_realized[p]:.2f}%")
    kpi[2].metric("Σ pesos", f"{w_p.sum() * 100:.2f}%")
    kpi[3].metric(
        "Convergiu",
        "Sim" if converged_per_profile[p] else "Não",
        delta=None if converged_per_profile[p] else "atenção",
        delta_color="off" if converged_per_profile[p] else "inverse",
    )

    detail_cols = st.columns([3, 2])

    # Tabela de pesos / RC por classe
    with detail_cols[0]:
        st.markdown("#### Composição por Classe")
        df_p = pd.DataFrame(
            {
                "Bucket": buckets_for_class,
                "Classe de Ativo": classes,
                "Peso": w_p * 100,
                "RC Realizado": rc_p * 100,
                "RC Alvo": rc_t_a * 100,
            }
        )
        df_p["Δ RC"] = df_p["RC Realizado"] - df_p["RC Alvo"]
        df_p["__rank"] = df_p["Bucket"].map(bucket_rank)
        df_p = (
            df_p.sort_values(["__rank", "Peso"], ascending=[True, False])
            .drop(columns="__rank")
            .set_index(["Bucket", "Classe de Ativo"])
        )

        st.dataframe(
            style_table(
                df_p,
                percent_cols=["Peso", "RC Realizado", "RC Alvo"],
                numeric_cols_format_as_float=["Δ RC"],
                color_negative_positive_cols=["Δ RC"],
            ),
            width='stretch',
        )

    # Donut de pesos por classe
    with detail_cols[1]:
        st.markdown("#### Distribuição de Pesos")
        df_donut = pd.DataFrame(
            {"Classe": classes, "Peso": w_p * 100, "Bucket": buckets_for_class}
        )
        df_donut = df_donut[df_donut["Peso"] > 0].copy()
        df_donut["__rank"] = df_donut["Bucket"].map(bucket_rank)
        df_donut = df_donut.sort_values(["__rank", "Peso"], ascending=[True, False])
        df_donut = df_donut.drop(columns="__rank").set_index("Classe")

        chart_donut = create_chart(
            data=df_donut,
            columns="Peso",
            names="Peso",
            chart_type="donut",
            title="Distribuição de Pesos",
            height=420,
        )
        hct.streamlit_highcharts(chart_donut)

    # RC alvo vs realizado por bucket
    st.markdown("#### Contribuição de Risco por Bucket — Alvo vs. Realizado")
    df_b = pd.DataFrame(
        {
            "Alvo": np.array(rc_t_b) * 100,
            "Realizado": np.array(rc_r_b) * 100,
        },
        index=buckets_order,
    )
    chart_rc = create_chart(
        data=df_b,
        columns=["Alvo", "Realizado"],
        names=["Alvo", "Realizado"],
        color=["#9CA3AF", "#4682B4"],
        chart_type="column",
        title="RC · Alvo vs Realizado",
        y_axis_title="%",
        x_axis_title="Bucket",
        height=350,
    )
    hct.streamlit_highcharts(chart_rc)


# ===========================================================================
# Tab 4 — Inputs do Modelo
# ===========================================================================
with tab_inputs:
    st.markdown("#### Volatilidades por Classe")
    df_vols = pd.DataFrame(
        {
            "Bucket": buckets_for_class,
            "Classe de Ativo": classes,
            "Vol (a.a.)": vols * 100,
        }
    )
    df_vols["__rank"] = df_vols["Bucket"].map(bucket_rank)
    df_vols = df_vols.sort_values(
        ["__rank", "Vol (a.a.)"], ascending=[True, False]
    ).drop(columns="__rank")

    cols = st.columns([1, 2])
    with cols[0]:
        df_vols_table = df_vols.set_index(["Bucket", "Classe de Ativo"])
        st.dataframe(
            style_table(df_vols_table, percent_cols=["Vol (a.a.)"]),
            width='stretch',
        )

    with cols[1]:
        df_vols_chart = df_vols.set_index("Classe de Ativo")[["Vol (a.a.)"]]
        # color per asset based on bucket
        vol_colors = [
            BUCKET_COLORS.get(bucket_for_asset[c], "#888888")
            for c in df_vols_chart.index
        ]
        chart_vol = create_chart(
            data=df_vols_chart,
            columns=["Vol (a.a.)"],
            names=["Vol (a.a.)"],
            color=vol_colors,
            chart_type="column",
            title="Volatilidade Anualizada",
            y_axis_title="%",
            height=400,
            show_legend=False,
        )
        hct.streamlit_highcharts(chart_vol)

    def _corr_lower_triangle(matrix: np.ndarray, labels: list[str]) -> pd.DataFrame:
        df = pd.DataFrame(matrix, index=labels, columns=labels)
        return df.where(np.tril(np.ones(df.shape)).astype(np.bool_))

    st.markdown("#### Correlação Implícita (matriz completa)")
    std = np.sqrt(np.diag(cov))
    corr_full = cov / np.outer(std, std)
    np.fill_diagonal(corr_full, 1.0)
    chart_corr = create_chart(
        data=_corr_lower_triangle(corr_full, classes),
        chart_type="heatmap",
        title="Correlação entre Classes",
        height=max(400, 35 * len(classes) + 100),
    )
    hct.streamlit_highcharts(chart_corr)

    st.markdown("#### Correlações Macro e Intra-Bucket")
    chart_macro = create_chart(
        data=_corr_lower_triangle(np.asarray(config.macro_corr), buckets_order),
        chart_type="heatmap",
        title="Correlação Macro (entre Buckets)",
        height=max(280, 50 * len(buckets_order) + 100),
    )
    hct.streamlit_highcharts(chart_macro)

    intra_cols = st.columns(len(config.intra_corrs))
    for i, (bk, mtx) in enumerate(config.intra_corrs.items()):
        names = [classes[j] for j in bucket_indices[bk]]
        with intra_cols[i]:
            chart_intra = create_chart(
                data=_corr_lower_triangle(np.asarray(mtx), names),
                chart_type="heatmap",
                title=f"Intra · {bk}",
                height=max(280, 40 * len(names) + 100),
            )
            hct.streamlit_highcharts(chart_intra)


# ===========================================================================
# Tab 5 — Diagnóstico HRP
# ===========================================================================
with tab_hrp:
    st.markdown(
        "Pesos provenientes da etapa **HRP** (Hierarchical Risk Parity), antes "
        "da imposição dos targets de RC do espectro. Útil para auditoria do "
        "primeiro estágio do modelo."
    )

    cols = st.columns(2)

    with cols[0]:
        st.markdown("#### Pesos HRP por Classe")
        df_hrp = pd.DataFrame(
            {
                "Bucket": buckets_for_class,
                "Classe de Ativo": classes,
                "Peso HRP": w_hrp * 100,
            }
        )
        df_hrp["__rank"] = df_hrp["Bucket"].map(bucket_rank)
        df_hrp = df_hrp.sort_values(
            ["__rank", "Peso HRP"], ascending=[True, False]
        ).drop(columns="__rank")

        st.dataframe(
            style_table(
                df_hrp.set_index(["Bucket", "Classe de Ativo"]),
                percent_cols=["Peso HRP"],
            ),
            width='stretch',
        )

        df_hrp_chart = df_hrp.set_index("Classe de Ativo")[["Peso HRP"]]
        hrp_colors = [
            asset_palette.get(c, "#888888") for c in df_hrp_chart.index
        ]
        chart_hrp = create_chart(
            data=df_hrp_chart,
            columns=["Peso HRP"],
            names=["Peso HRP"],
            color=hrp_colors,
            chart_type="column",
            title="Pesos HRP",
            y_axis_title="%",
            height=400,
            show_legend=False,
        )
        hct.streamlit_highcharts(chart_hrp)

    with cols[1]:
        st.markdown("#### Pesos HRP por Bucket (estágio macro)")
        df_macro = pd.DataFrame(
            {"Peso Macro": np.asarray(w_macro) * 100}, index=buckets_order
        )
        df_macro.index.name = "Bucket"
        st.dataframe(
            style_table(df_macro, percent_cols=["Peso Macro"]),
            width='stretch',
        )

        chart_macro_pie = create_chart(
            data=df_macro,
            columns="Peso Macro",
            names="Peso Macro",
            chart_type="donut",
            title="Distribuição Macro",
            height=400,
        )
        hct.streamlit_highcharts(chart_macro_pie)

        st.metric("Vol HRP", f"{vol_hrp:.2f}%")


# ---------------------------------------------------------------------------
# Export — Excel
# ---------------------------------------------------------------------------
with st.expander("Exportar resultado", expanded=False):
    df_w_export = pd.DataFrame(
        {f"P{p}": weights[p] for p in profiles},
        index=classes,
    )
    df_rc_export = pd.DataFrame(
        {f"P{p}": risk_contrib[p] for p in profiles},
        index=classes,
    )
    df_meta_export = pd.DataFrame(
        {
            "Perfil": [f"P{p}" for p in profiles],
            "σ Alvo (decimal)": [vol_targets[profiles.index(p)] for p in profiles],
            "σ Realizado (%)": [vol_realized[p] for p in profiles],
            "Convergiu": [converged_per_profile[p] for p in profiles],
        }
    )

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_meta_export.to_excel(writer, sheet_name="Metadados", index=False)
        df_w_export.to_excel(writer, sheet_name="Pesos")
        df_rc_export.to_excel(writer, sheet_name="RC Realizado")

    st.download_button(
        label="Baixar Excel",
        data=buffer.getvalue(),
        file_name=f"two_stage_risk_parity_{datetime.now():%Y%m%d_%H%M}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
