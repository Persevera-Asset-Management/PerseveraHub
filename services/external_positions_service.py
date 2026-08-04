"""Ingestão de carteiras externas para o Controle de Posições.

Parseia CSV/XLSX, faz match com Inv-Taxonomia/Ativos e devolve um DataFrame
no schema canônico usado pela view (mesmo shape de posições Fibery normalizadas).
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import BinaryIO

import pandas as pd

REQUIRED_UPLOAD_COLUMNS = ("Ativo", "Saldo")

OPTIONAL_UPLOAD_COLUMNS = (
    "Quantidade",
    "Valor Unitário",
    "Data Posição",
    "Custodiante",
    "Portfolio",
)

# Aliases aceitos no arquivo do usuário → nome canônico do template.
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "Ativo": ("Ativo", "Ticker", "Nome Ativo", "Código", "Codigo", "Code", "Asset"),
    "Saldo": ("Saldo", "Saldo Bruto", "Valor", "Market Value", "Valor de Mercado"),
    "Quantidade": ("Quantidade", "Qtd", "Qty", "Quantity"),
    "Valor Unitário": ("Valor Unitário", "Valor Unitario", "Preço", "Preco", "PU", "Price"),
    "Data Posição": ("Data Posição", "Data Posicao", "Data", "Date", "Data Ref"),
    "Custodiante": ("Custodiante", "Custodiante Acronimo", "Custodian"),
    "Portfolio": ("Portfolio", "Carteira", "Cliente", "Nome"),
}

# Colunas da taxonomia usadas no enrich (nome Fibery flattened → canônico).
_ASSET_FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Nome Ativo": ("Name",),
    "Nome Ativo Completo": ("Nome Completo", "Name"),
    "Alias": ("Alias", "Alias Warren", "Name"),
    "Classificação do Conjunto": (
        "Classificação do Conjunto",
        "Classificação Conjunto",
    ),
    "Classificação do Sub-Conjunto": (
        "Classificação do Sub-Conjunto",
        "Classificação Sub-Conjunto",
    ),
    "Classificação Instrumento": (
        "Classificação Instrumento",
        "Classificação Instrumento-Relation",
    ),
    "Nome Emissor": ("Nome Emissor",),
    "Nome Devedor": ("Nome Devedor",),
    "Indexador": ("Indexador",),
    "Data Vencimento": ("Data Vencimento",),
}

MATCH_MATCHED = "matched"
MATCH_AMBIGUOUS = "ambiguous"
MATCH_UNMATCHED = "unmatched"

_TEMPLATE_COLUMNS = list(REQUIRED_UPLOAD_COLUMNS) + list(OPTIONAL_UPLOAD_COLUMNS)


def normalize_asset_key(value) -> str:
    """Normaliza chave de match (trim + casefold)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().casefold()


def build_external_positions_template() -> pd.DataFrame:
    """DataFrame vazio com o cabeçalho do template de upload."""
    return pd.DataFrame(columns=_TEMPLATE_COLUMNS)


def template_csv_bytes() -> bytes:
    """CSV do template para download na UI."""
    return build_external_positions_template().to_csv(index=False).encode("utf-8-sig")


def _normalize_column_name(name) -> str:
    """Remove BOM, aspas e espaços de nomes de coluna (comum em CSV do Excel)."""
    text = str(name)
    text = text.replace("\ufeff", "").replace("\u200b", "")
    return text.strip().strip('"').strip("'").strip()


def _rename_upload_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Mapeia aliases de coluna para os nomes canônicos do template."""
    df = df.rename(columns={orig: _normalize_column_name(orig) for orig in df.columns})

    rename_map: dict[str, str] = {}
    used_targets: set[str] = set()
    lower_to_actual = {str(c).casefold(): c for c in df.columns}

    for canonical, aliases in _COLUMN_ALIASES.items():
        if canonical in used_targets:
            continue
        for alias in aliases:
            actual = lower_to_actual.get(alias.casefold())
            if actual is not None and actual not in rename_map:
                rename_map[actual] = canonical
                used_targets.add(canonical)
                break

    return df.rename(columns=rename_map)


def _coerce_saldo_series(series: pd.Series) -> pd.Series:
    """Converte Saldo aceitando vírgula decimal brasileira."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    text = series.astype(str).str.strip()
    text = text.str.replace(r"\s+", "", regex=True)
    # 1.234,56 → 1234.56 ; 1234,56 → 1234.56 ; 1234.56 permanece
    has_comma = text.str.contains(",", na=False)
    text = text.where(
        ~has_comma,
        text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    return pd.to_numeric(text, errors="coerce")


def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Lê CSV tolerando BOM, UTF-8/Latin-1 e separador vírgula ou ponto-e-vírgula."""
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    last_error: Exception | None = None

    for encoding in encodings:
        for sep in (None, ",", ";"):
            try:
                buffer = BytesIO(raw)
                kwargs = {"encoding": encoding, "engine": "python"}
                if sep is None:
                    kwargs["sep"] = None  # sniffer
                else:
                    kwargs["sep"] = sep
                df = pd.read_csv(buffer, **kwargs)
                if df.shape[1] >= 2:
                    return df
            except Exception as exc:  # noqa: BLE001 — tenta próximo encoding/sep
                last_error = exc
                continue

    if last_error:
        raise ValueError(f"Não foi possível ler o CSV: {last_error}") from last_error
    raise ValueError("Não foi possível ler o CSV.")


def parse_external_positions_file(uploaded_file: BinaryIO | BytesIO) -> pd.DataFrame:
    """
    Lê CSV ou Excel e normaliza colunas do template.

    Raises:
        ValueError: arquivo inválido ou colunas obrigatórias ausentes.
    """
    name = getattr(uploaded_file, "name", "") or ""
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if suffix in ("xlsx", "xls"):
        df = pd.read_excel(uploaded_file)
    else:
        raw = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        df = _read_csv_bytes(raw)

    if df.empty:
        raise ValueError("Arquivo sem linhas de dados.")

    df = _rename_upload_columns(df)
    missing = [c for c in REQUIRED_UPLOAD_COLUMNS if c not in df.columns]
    if missing:
        found = ", ".join(map(str, df.columns.tolist())) or "(nenhuma)"
        raise ValueError(
            "Colunas obrigatórias ausentes: "
            + ", ".join(missing)
            + f". Encontradas: {found}. Use o template (Ativo, Saldo)."
        )

    out = df.copy()
    out["Ativo"] = out["Ativo"].astype(str).str.strip()
    out = out[out["Ativo"].ne("") & out["Ativo"].str.casefold().ne("nan")]
    out["Saldo"] = _coerce_saldo_series(out["Saldo"])
    out = out[out["Saldo"].notna()]

    if out.empty:
        raise ValueError("Nenhuma linha válida com Ativo e Saldo.")

    if "Quantidade" in out.columns:
        out["Quantidade"] = pd.to_numeric(out["Quantidade"], errors="coerce")
    if "Valor Unitário" in out.columns:
        out["Valor Unitário"] = _coerce_saldo_series(out["Valor Unitário"])
    if "Data Posição" in out.columns:
        out["Data Posição"] = pd.to_datetime(out["Data Posição"], errors="coerce", dayfirst=True)

    return out.reset_index(drop=True)


def _pick_asset_column(df_assets: pd.DataFrame, canonical: str) -> str | None:
    for candidate in _ASSET_FIELD_CANDIDATES[canonical]:
        if candidate in df_assets.columns:
            return candidate
    return None


def _build_asset_key_index(df_assets: pd.DataFrame) -> dict[str, list[int]]:
    """Mapa chave normalizada → lista de índices em df_assets (Name e Alias)."""
    index: dict[str, list[int]] = {}
    name_col = "Name" if "Name" in df_assets.columns else None
    alias_col = "Alias" if "Alias" in df_assets.columns else None

    for i, row in df_assets.iterrows():
        keys: set[str] = set()
        if name_col:
            keys.add(normalize_asset_key(row.get(name_col)))
        if alias_col:
            keys.add(normalize_asset_key(row.get(alias_col)))
        for key in keys:
            if not key:
                continue
            index.setdefault(key, [])
            if i not in index[key]:
                index[key].append(i)
    return index


def match_external_positions(
    df_upload: pd.DataFrame,
    df_assets: pd.DataFrame,
) -> pd.DataFrame:
    """
    Cruza Ativo do arquivo com Name/Alias da taxonomia.

    Returns:
        DataFrame de relatório com Status Match e campos do ativo quando matched.
    """
    key_index = _build_asset_key_index(df_assets)
    rows = []

    name_col = _pick_asset_column(df_assets, "Nome Ativo")
    alias_col = _pick_asset_column(df_assets, "Alias")
    conjunto_col = _pick_asset_column(df_assets, "Classificação do Conjunto")
    instrumento_col = _pick_asset_column(df_assets, "Classificação Instrumento")

    for _, up in df_upload.iterrows():
        key = normalize_asset_key(up["Ativo"])
        hits = key_index.get(key, [])
        base = {
            "Ativo": up["Ativo"],
            "Saldo": up["Saldo"],
            "Status Match": MATCH_UNMATCHED,
            "Nome Ativo": pd.NA,
            "Alias": pd.NA,
            "Classificação do Conjunto": pd.NA,
            "Classificação Instrumento": pd.NA,
            "Candidatos": "",
            "_asset_idx": pd.NA,
        }

        if len(hits) == 1:
            asset = df_assets.loc[hits[0]]
            base["Status Match"] = MATCH_MATCHED
            base["_asset_idx"] = hits[0]
            if name_col:
                base["Nome Ativo"] = asset.get(name_col)
            if alias_col:
                base["Alias"] = asset.get(alias_col)
            if conjunto_col:
                base["Classificação do Conjunto"] = asset.get(conjunto_col)
            if instrumento_col:
                base["Classificação Instrumento"] = asset.get(instrumento_col)
        elif len(hits) > 1:
            base["Status Match"] = MATCH_AMBIGUOUS
            labels = []
            for idx in hits:
                asset = df_assets.loc[idx]
                name = asset.get(name_col) if name_col else idx
                alias = asset.get(alias_col) if alias_col else ""
                labels.append(f"{name}" + (f" ({alias})" if pd.notna(alias) and alias else ""))
            base["Candidatos"] = "; ".join(labels)

        rows.append(base)

    return pd.DataFrame(rows)


def match_summary(df_match: pd.DataFrame) -> dict[str, int]:
    """Contagens por status de match."""
    counts = df_match["Status Match"].value_counts()
    return {
        MATCH_MATCHED: int(counts.get(MATCH_MATCHED, 0)),
        MATCH_AMBIGUOUS: int(counts.get(MATCH_AMBIGUOUS, 0)),
        MATCH_UNMATCHED: int(counts.get(MATCH_UNMATCHED, 0)),
        "total": int(len(df_match)),
    }


def enrich_external_positions(
    df_upload: pd.DataFrame,
    df_assets: pd.DataFrame,
    *,
    portfolio_label: str = "EXTERNA",
    position_date: datetime | None = None,
    allow_partial: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Gera posições no schema canônico + relatório de match.

    Args:
        allow_partial: se True, inclui só linhas matched mesmo com falhas;
            se False, exige 100% matched (ainda assim devolve report).

    Returns:
        (df_positions_canonical, df_match_report)

    Raises:
        ValueError: se allow_partial=False e houver ambiguous/unmatched.
    """
    df_match = match_external_positions(df_upload, df_assets)
    summary = match_summary(df_match)
    if not allow_partial and (summary[MATCH_AMBIGUOUS] or summary[MATCH_UNMATCHED]):
        raise ValueError(
            "Há ativos sem match único. Corrija o arquivo ou cadastre os ativos no Fibery."
        )

    matched_mask = df_match["Status Match"].eq(MATCH_MATCHED)
    if not matched_mask.any():
        raise ValueError("Nenhum ativo foi encontrado na taxonomia do Fibery.")

    default_date = position_date or datetime.now()
    field_cols = {
        canonical: _pick_asset_column(df_assets, canonical)
        for canonical in _ASSET_FIELD_CANDIDATES
    }

    canonical_rows = []
    upload_matched = df_upload.loc[matched_mask.to_numpy()].reset_index(drop=True)
    match_matched = df_match.loc[matched_mask].reset_index(drop=True)

    for i, up in upload_matched.iterrows():
        asset_idx = match_matched.loc[i, "_asset_idx"]
        asset = df_assets.loc[asset_idx]

        def _asset_val(canonical: str):
            col = field_cols[canonical]
            if col is None:
                return pd.NA
            return asset.get(col)

        saldo = float(up["Saldo"])
        quantidade = up["Quantidade"] if "Quantidade" in up.index and pd.notna(up.get("Quantidade")) else pd.NA
        valor_unitario = (
            up["Valor Unitário"]
            if "Valor Unitário" in up.index and pd.notna(up.get("Valor Unitário"))
            else (saldo / quantidade if pd.notna(quantidade) and quantidade else pd.NA)
        )

        if "Data Posição" in up.index and pd.notna(up.get("Data Posição")):
            data_pos = pd.Timestamp(up["Data Posição"])
        else:
            data_pos = pd.Timestamp(default_date)

        if "Custodiante" in up.index and pd.notna(up.get("Custodiante")) and str(up.get("Custodiante")).strip():
            custodiante = str(up["Custodiante"]).strip()
        else:
            custodiante = "N/D"

        if "Portfolio" in up.index and pd.notna(up.get("Portfolio")) and str(up.get("Portfolio")).strip():
            portfolio = str(up["Portfolio"]).strip()
        else:
            portfolio = portfolio_label

        conjunto = _asset_val("Classificação do Conjunto")
        subconjunto = _asset_val("Classificação do Sub-Conjunto")
        if pd.isna(subconjunto) or not str(subconjunto).strip():
            subconjunto = "Sem Classificação"

        nome_ativo = _asset_val("Nome Ativo")
        alias = _asset_val("Alias")
        if pd.isna(alias) or not str(alias).strip():
            alias = nome_ativo

        canonical_rows.append(
            {
                "Data Posição": data_pos,
                "Portfolio": portfolio,
                "Custodiante Acronimo": custodiante,
                "Nome Ativo": nome_ativo,
                "Nome Ativo Completo": _asset_val("Nome Ativo Completo"),
                "Alias": alias,
                "Classificação do Conjunto": conjunto,
                "Classificação do Sub-Conjunto": subconjunto,
                "Classificação Instrumento": _asset_val("Classificação Instrumento"),
                "Nome Emissor": _asset_val("Nome Emissor"),
                "Nome Devedor": _asset_val("Nome Devedor"),
                "Quantidade": quantidade if pd.notna(quantidade) else pd.NA,
                "Valor Unitário": valor_unitario,
                "Saldo": saldo,
                "Indexador": _asset_val("Indexador"),
                "Data Vencimento": _asset_val("Data Vencimento"),
            }
        )

    df_positions = pd.DataFrame(canonical_rows)
    df_positions["Data Posição"] = pd.to_datetime(df_positions["Data Posição"])
    df_positions["Data Vencimento"] = pd.to_datetime(
        df_positions["Data Vencimento"], errors="coerce"
    )
    # Análise atual exige Classificação do Conjunto
    df_positions = df_positions.dropna(subset=["Classificação do Conjunto"])

    report_cols = [
        "Ativo",
        "Saldo",
        "Status Match",
        "Nome Ativo",
        "Alias",
        "Classificação do Conjunto",
        "Classificação Instrumento",
        "Candidatos",
    ]
    return df_positions, df_match[report_cols]
