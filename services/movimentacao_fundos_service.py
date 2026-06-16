import io
import re
from datetime import datetime
from typing import TypedDict

import pandas as pd

from configs.pages.movimentacao_fundos import (
    COLUNA_BOLETA_ID,
    COLUNA_CLIENTE,
    COLUNA_FINANCEIRO,
    COLUNA_FUNDO,
    COLUNA_OPERACAO,
    COLUNA_STATUS,
    COLUNA_TIPO_MOVIMENTO,
    DISTRIBUIDORES,
    EXCLUIR_FUNDOS,
    OPERACAO_APLICACAO,
    OPERACAO_RESGATE,
    OPERACOES,
    REQUIRED_COLUMNS,
    TIPO_MOVIMENTO_COME_COTAS,
)


class TotaisDistribuidor(TypedDict):
    aplicacoes: float
    resgates: float
    liquido: float


class MovimentacaoFundo(TypedDict):
    distribuidor: str
    operacao: str
    valor: float
    boletas: int


class ResumoFundo(TypedDict):
    nome: str
    movimentacoes: list[MovimentacaoFundo]
    liquido: float


class ComeCotaFundo(TypedDict):
    valor: float
    quantidade: int


class BoletaExcluida(TypedDict):
    cliente: str
    fundo: str
    operacao: str
    valor: float
    boleta_id: str


class ResultadoMovimentacao(TypedDict):
    timestamp_arquivo: str
    timestamp_geracao: str
    total_aplicacoes: float
    total_resgates: float
    total_liquido: float
    total_boletas: int
    por_distribuidor: dict[str, TotaisDistribuidor]
    fundos: list[ResumoFundo]
    come_cotas: dict[str, ComeCotaFundo]
    excluidas: list[BoletaExcluida]


def extrair_distribuidor(cliente: str) -> str:
    cliente_upper = str(cliente).upper()
    if "XP INVESTIMENTOS" in cliente_upper:
        return "XP"
    if "BTG" in cliente_upper:
        return "BTG"
    return "Outros"


def extrair_timestamp_arquivo(nome_arquivo: str) -> str:
    match = re.search(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", nome_arquivo)
    if match:
        ano, mes, dia, hora, minuto, segundo = match.groups()
        return f"{dia}/{mes}/{ano} {hora}:{minuto}:{segundo}"
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def validar_colunas(df: pd.DataFrame) -> list[str]:
    return [coluna for coluna in REQUIRED_COLUMNS if coluna not in df.columns]


def _somar_por_operacao(df: pd.DataFrame, operacao: str) -> float:
    return float(df[df[COLUNA_OPERACAO] == operacao][COLUNA_FINANCEIRO].sum())


def _calcular_totais_distribuidor(df: pd.DataFrame, distribuidor: str) -> TotaisDistribuidor:
    subset = df[df["Distribuidor"] == distribuidor]
    aplicacoes = _somar_por_operacao(subset, OPERACAO_APLICACAO)
    resgates = _somar_por_operacao(subset, OPERACAO_RESGATE)
    return {
        "aplicacoes": aplicacoes,
        "resgates": resgates,
        "liquido": aplicacoes - resgates,
    }


def _montar_boletas_excluidas(excluidas: pd.DataFrame) -> list[BoletaExcluida]:
    if excluidas.empty:
        return []

    resultado: list[BoletaExcluida] = []
    for registro in excluidas.to_dict("records"):
        valor = registro.get(COLUNA_FINANCEIRO, 0)
        resultado.append(
            {
                "cliente": str(registro.get(COLUNA_CLIENTE, "—")),
                "fundo": str(registro.get(COLUNA_FUNDO, "—")),
                "operacao": str(registro.get(COLUNA_OPERACAO, "—")),
                "valor": float(valor) if pd.notna(valor) else 0.0,
                "boleta_id": str(registro.get(COLUNA_BOLETA_ID, "—")),
            }
        )
    return resultado


def _montar_resumo_fundos(pivot: pd.DataFrame, fundos: list[str]) -> list[ResumoFundo]:
    resumo: list[ResumoFundo] = []
    for fundo in fundos:
        pivot_fundo = pivot[pivot[COLUNA_FUNDO] == fundo]
        liquido_total = 0.0
        movimentacoes: list[MovimentacaoFundo] = []

        for distribuidor in DISTRIBUIDORES:
            for operacao in OPERACOES:
                linha = pivot_fundo[
                    (pivot_fundo["Distribuidor"] == distribuidor)
                    & (pivot_fundo[COLUNA_OPERACAO] == operacao)
                ]
                if linha.empty:
                    continue

                valor = float(linha["valor"].values[0])
                boletas = int(linha["boletas"].values[0])
                liquido_total += valor if operacao == OPERACAO_APLICACAO else -valor
                movimentacoes.append(
                    {
                        "distribuidor": distribuidor,
                        "operacao": operacao,
                        "valor": valor,
                        "boletas": boletas,
                    }
                )

        resumo.append({"nome": fundo, "movimentacoes": movimentacoes, "liquido": liquido_total})

    return resumo


def processar(file_bytes: bytes, nome_arquivo: str) -> ResultadoMovimentacao:
    df = pd.read_excel(io.BytesIO(file_bytes), header=1)

    colunas_faltantes = validar_colunas(df)
    if colunas_faltantes:
        raise ValueError(f"Colunas ausentes na planilha: {', '.join(colunas_faltantes)}")

    df[COLUNA_FINANCEIRO] = pd.to_numeric(df[COLUNA_FINANCEIRO], errors="coerce")

    status_upper = df[COLUNA_STATUS].astype(str).str.upper()
    excluidas = df[status_upper.str.contains("EXCLU", na=False)].copy()
    df = df[~status_upper.str.contains("EXCLU", na=False)].copy()

    tipo_upper = df[COLUNA_TIPO_MOVIMENTO].astype(str).str.upper()
    df_come_cotas = df[tipo_upper == TIPO_MOVIMENTO_COME_COTAS].copy()
    df = df[tipo_upper != TIPO_MOVIMENTO_COME_COTAS].copy()
    df = df[~df[COLUNA_FUNDO].isin(EXCLUIR_FUNDOS)].copy()

    df["Distribuidor"] = df[COLUNA_CLIENTE].apply(extrair_distribuidor)

    total_aplicacoes = _somar_por_operacao(df, OPERACAO_APLICACAO)
    total_resgates = _somar_por_operacao(df, OPERACAO_RESGATE)

    por_distribuidor = {
        distribuidor: _calcular_totais_distribuidor(df, distribuidor)
        for distribuidor in DISTRIBUIDORES
    }

    pivot = (
        df.groupby([COLUNA_FUNDO, "Distribuidor", COLUNA_OPERACAO])
        .agg(valor=(COLUNA_FINANCEIRO, "sum"), boletas=(COLUNA_FINANCEIRO, "count"))
        .reset_index()
    )

    fundos = sorted(df[COLUNA_FUNDO].dropna().unique().tolist())

    come_cotas: dict[str, ComeCotaFundo] = {}
    if not df_come_cotas.empty:
        for fundo in df_come_cotas[COLUNA_FUNDO].dropna().unique():
            subset = df_come_cotas[df_come_cotas[COLUNA_FUNDO] == fundo]
            come_cotas[fundo] = {
                "valor": float(subset[COLUNA_FINANCEIRO].sum()),
                "quantidade": int(len(subset)),
            }

    return {
        "timestamp_arquivo": extrair_timestamp_arquivo(nome_arquivo),
        "timestamp_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "total_aplicacoes": total_aplicacoes,
        "total_resgates": total_resgates,
        "total_liquido": total_aplicacoes - total_resgates,
        "total_boletas": int(len(df)),
        "por_distribuidor": por_distribuidor,
        "fundos": _montar_resumo_fundos(pivot, fundos),
        "come_cotas": come_cotas,
        "excluidas": _montar_boletas_excluidas(excluidas),
    }
