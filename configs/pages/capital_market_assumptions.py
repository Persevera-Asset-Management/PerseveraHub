CAPITAL_MARKET_ASSUMPTIONS = {
    "Renda Fixa": {
        "br_cdi_index": "Caixa e Equivalentes (CDI)",

        "anbima_irf_m1": "Títulos Públicos Pré-Fixados Curto (IRF-M 1)",
        "anbima_irf_m1+": "Títulos Públicos Pré-Fixados Longo (IRF-M 1+)",
        
        "anbima_ima_b5": "Títulos Públicos IPCA Curto (IMA-B 5)",
        "anbima_ima_b5+": "Títulos Públicos IPCA Longo (IMA-B 5+)",
        
        "anbima_ida_di": "Debêntures DI (IDA DI)",
        "br_b3_corporate_bond_di_aaa_index": "Debêntures AAA DI (B3)",
        "br_b3_corporate_bond_di_ultra_quality_index": "Debêntures Ultra Quality DI (B3)",
        
        "anbima_ida_ipca": "Debêntures IPCA (IDA IPCA)",
        "br_b3_corporate_bond_incentivized_ipca_aaa_index": "Debêntures Incentivadas AAA IPCA (B3)",
        "br_b3_corporate_bond_incentivized_ipca_ultra_quality_index": "Debêntures Incentivadas Ultra Quality IPCA (B3)",
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
