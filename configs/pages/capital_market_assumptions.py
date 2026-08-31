CMA_ASSET_PRICES = {
    "Renda Fixa": {
        "br_cdi_index": "Caixa e Equivalentes (CDI)",

        "anbima_irf_m1": "Títulos Públicos Pré-Fixados Curto (IRF-M 1)",
        "anbima_irf_m1+": "Títulos Públicos Pré-Fixados Longo (IRF-M 1+)",
        "br_teva_pre_fixado_5y_index": "Títulos Públicos Pré-Fixados 5 Anos (ITBR Pré 5 Anos)",
        
        "anbima_ima_b5": "Títulos Públicos IPCA Curto (IMA-B 5)",
        "anbima_ima_b5+": "Títulos Públicos IPCA Longo (IMA-B 5+)",
        
        "anbima_ida_di": "Debêntures DI (IDA DI)",
        "anbima_ida_liq_di": "Debêntures DI Liquidez (IDA LIQ DI)",
        
        "anbima_ida_ipca": "Debêntures IPCA (IDA IPCA)",

        "br_teva_fii_papel_index": "FII Papel (Teva)",
    },
    "Renda Variável": {
        "br_ibovespa": "Bolsa Brasileira (Ibovespa)",
        "br_mlcx": "Large Caps Brasileiros (MLCX)",
        "br_smll": "Small Caps Brasileiros (SMLL)",
        "IVVB11": "Bolsa Americana (com variação cambial - IVVB11)",
        "us_sp500": "Bolsa Americana (sem variação cambial)",
    },
    "Alternativos": {
        "anbima_ihfa": "Fundos Multimercado (IHFA)",
        "persevera_anbima_ihfa_long_short": "Fundos Multimercado L&S (Sub-Índice IHFA)",
        "gold_100oz_futures": "Ouro (sem variação cambial)",
        "bitcoin_usd": "Bitcoin",
        "usd_brl": "Real (USD/BRL)",
        "br_teva_fii_tijolo_index": "FII Tijolo (Teva)",
    },
}

CMA_ASSET_YIELDS = {
    "Juros Nominais": {
        "br_pre_1y": "Pré 1 Ano",
        "br_pre_5y": "Pré 5 Anos",
        "br_pre_10y": "Pré 10 Anos",
    },
    "Juros Reais": {
        "br_ipca_1y": "IPCA 1 Ano",
        "br_ipca_5y": "IPCA 5 Anos",
        "br_ipca_10y": "IPCA 10 Anos",
        "br_ipca_20y": "IPCA 20 Anos",
        "br_ipca_30y": "IPCA 30 Anos",
    },
}

BUCKET_ORDER = list(CMA_ASSET_PRICES.keys())
YIELD_BUCKET_ORDER = list(CMA_ASSET_YIELDS.keys())

BUCKET_COLORS = {
    "Renda Fixa":     "#4682B4",
    "Renda Variável": "#B99B7B",
    "Alternativos":   "#B3BEBD",
}
