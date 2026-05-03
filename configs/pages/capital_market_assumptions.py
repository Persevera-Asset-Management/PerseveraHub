CAPITAL_MARKET_ASSUMPTIONS = {
    "Renda Fixa": {
        "br_cdi_index": "Caixa e Equivalentes (CDI)",
        "br_b3_corporate_bond_di_aaa_index": "Renda Fixa Pós-Fixado (Debêntures AAA DI)",
        "br_b3_corporate_bond_di_ultra_quality_index": "Renda Fixa Pós-Fixado (Debêntures Ultra Quality DI)",
        "br_b3_corporate_bond_incentivized_ipca_ultra_quality_index": "Renda Fixa IPCA (Debêntures Incentivadas IPCA Ultra Quality)",
        "br_b3_corporate_bond_incentivized_ipca_aaa_index": "Renda Fixa IPCA (Debêntures Incentivadas IPCA AAA)",
        "anbima_ima_b5": "Títulos Públicos IPCA Curto (IMA-B 5)",
        "anbima_ima_b5+": "Títulos Públicos IPCA Longo (IMA-B 5+)",
        "anbima_irf_m1": "Títulos Públicos Pré-Fixados Curto (IRF-M 1)",
        "anbima_irf_m1+": "Títulos Públicos Pré-Fixados Longo (IRF-M 1+)",
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
        "br_ifix": "Fundos Imobiliários (IFIX)",
        "gold_100oz_futures": "Ouro (sem variação cambial)",
        # "bitcoin_usd": "Bitcoin",
    },
}

BUCKET_ORDER = list(CAPITAL_MARKET_ASSUMPTIONS.keys())

BUCKET_COLORS = {
    "Renda Fixa":     "#4682B4",
    "Renda Variável": "#B99B7B",
    "Alternativos":   "#B3BEBD",
}
