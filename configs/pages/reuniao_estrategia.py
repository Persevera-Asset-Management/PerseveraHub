CHARTS_ESTRATEGIA = {
    # === Juros ===
    # Taxas de Juros (US)
    "us_treasuries": {
        "chart_config": {
            "columns": ["us_generic_2y", "us_generic_5y", "us_generic_10y", "us_generic_30y"],
            "names": ["2y", "5y", "10y", "30y"],
            "chart_type": "line",
            "title": "Curva Pré (Treasuries)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (US)",
        "block_title": "Taxas de Juros (US)"
    },
    "us_inflation": {
        "chart_config": {
            "columns": ["us_generic_inflation_5y", "us_generic_inflation_10y", "us_generic_inflation_30y"],
            "names": ["5y", "10y", "30y"],
            "chart_type": "line",
            "title": "Curva Inflação (TIPS)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (US)",
        "block_title": "Taxas de Juros (US)"
    },
    "us_breakeven": {
        "chart_config": {
            "columns": ["us_breakeven_2y", "us_breakeven_5y", "us_breakeven_10y", "usd_inflation_swap_fwd_5y5y"],
            "names": ["2y", "5y", "10y", "5y5y"],
            "chart_type": "line",
            "title": "Curva Implícita (Breakeven) e Inflação Futura (Swap)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (US)",
        "block_title": "Taxas de Juros (US)"
    },
    "us_steepness": {
        "chart_config": {
            "columns": ["us_2y10y_steepness", "us_5y10y_steepness", "us_5y30y_steepness"],
            "names": ["2y10y", "5y10y", "5y30y"],
            "chart_type": "line",
            "title": "Inclinações (Steepness)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (US)",
        "block_title": "Taxas de Juros (US)"
    },

    # Taxas Corporativas (US)
    "us_corporate_ig_spread": {
        "chart_config": {
            "columns": ["us_corporate_ig_5y_spread", "us_corporate_ig_10y_spread"],
            "names": ["5y", "10y"],
            "chart_type": "line",
            "title": "IG Spreads",
            "y_axis_title": "bps",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas Corporativas (US)",
        "block_title": "Taxas Corporativas (US)"
    },
    "us_corporate_ig_yield": {
        "chart_config": {
            "columns": ["us_corporate_ig_5y_yield", "us_corporate_ig_10y_yield"],
            "names": ["5y", "10y"],
            "chart_type": "line",
            "title": "IG Taxas",
            "y_axis_title": "bps",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas Corporativas (US)",
        "block_title": "Taxas Corporativas (US)"
    },
    "us_corporate_hy_spread": {
        "chart_config": {
            "columns": ["us_corporate_hy_5y_spread", "us_corporate_hy_10y_spread"],
            "names": ["5y", "10y"],
            "chart_type": "line",
            "title": "HY Spreads",
            "y_axis_title": "bps",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas Corporativas (US)",
        "block_title": "Taxas Corporativas (US)"
    },
    "us_corporate_hy_yield": {
        "chart_config": {
            "columns": ["us_corporate_hy_5y_yield", "us_corporate_hy_10y_yield"],
            "names": ["5y", "10y"],
            "chart_type": "line",
            "title": "HY Taxas",
            "y_axis_title": "bps",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas Corporativas (US)",
        "block_title": "Taxas Corporativas (US)"
    },

    # Taxas de Juros (BR)
    "br_treasuries": {
        "chart_config": {
            "columns": ["br_pre_1y", "br_pre_2y", "br_pre_5y", "br_generic_10y"],
            "names": ["1y", "2y", "5y", "10y"],
            "chart_type": "line",
            "title": "Curva Pré",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (BR)",
        "block_title": "Taxas de Juros (BR)"
    },
    "br_inflation": {
        "chart_config": {
            "columns": ["br_ipca_1y", "br_ipca_2y", "br_ipca_5y", "br_ipca_10y"],
            "names": ["1y", "2y", "5y", "10y"],
            "chart_type": "line",
            "title": "Curva Inflação (IPCA)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (BR)",
        "block_title": "Taxas de Juros (BR)"
    },
    "br_breakeven": {
        "chart_config": {
            "columns": ["br_breakeven_1y", "br_breakeven_2y", "br_breakeven_5y", "br_breakeven_10y"],
            "names": ["1y", "2y", "5y", "10y"],
            "chart_type": "line",
            "title": "Curva Implícita (Breakeven)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (BR)",
        "block_title": "Taxas de Juros (BR)"
    },
    "br_focus_selic": {
        "chart_config": {
            "columns": ["br_focus_selic_median_2025R5", "br_focus_selic_median_2025R6", "br_focus_selic_median_2025R7", "br_focus_selic_median_2025R8", "br_focus_selic_median_2026R1", "br_focus_selic_median_2026R2"],
            "names": ["R5 (jul/25)", "R6 (set/25)", "R7 (nov/25)", "R8 (dez/25)", "R1 (jan/26)", "R2 (fev/26)"],
            "chart_type": "line",
            "title": "SELIC Focus (Próximas Reuniões)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Juros",
        "group": "Taxas de Juros (BR)",
        "block_title": "Taxas de Juros (BR)"
    },

    # === Moedas ===
    # Reservas Internacionais
    "br_international_reserves": {
        "chart_config": {
            "columns": ["br_international_reserves_total"],
            "names": ["Reservas Internacionais"],
            "chart_type": "line",
            "title": "Reservas Internacionais",
            "y_axis_title": "US$",
        },
        "width": 6,
        "context": "Moedas",
        "group": "Reservas Internacionais",
        "block_title": "Reservas Internacionais"
    },

    # === Commodities ===
    "crb_index": {
        "chart_config": {
            "columns": ["crb_index", "crb_fats_oils_index", "crb_food_index", "crb_livestock_index", "crb_metals_index", "crb_raw_industrials_index", "crb_textiles_index"],
            "names": ["Índice CRB", "Fats & Oils", "Food", "Livestock", "Metals", "Raw Industrials", "Textiles"],
            "chart_type": "line",
            "title": "Commodities (CRB)",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "context": "Commodities",
        "group": "Commodities",
        "block_title": "Commodities"
    },
    "cepea_agri": {
        "chart_config": {
            "columns": ["br_cepea_arabica_coffee", "br_cepea_chilled_whole_broiler", "br_cepea_corn_wholesale", "br_cepea_cotton_feather", "br_cepea_ethanol_fuel", "br_cepea_fed_cattle", "br_cepea_paddy_rice", "br_cepea_pork", "br_cepea_soft_wheat", "br_cepea_soybean_wholesale", "br_cepea_sugar"],
            "names": ["Café Arábica", "Frango", "Milho", "Algodão", "Etanol", "Gado", "Arroz", "Peixe", "Trigo", "Soja", "Açúcar"],
            "chart_type": "line",
            "title": "Commodities (Agri - CEPEA)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Commodities",
        "group": "Commodities",
        "block_title": "Commodities"
    },
    "energy_commodities": {
        "chart_config": {
            "columns": ["crude_oil_wti_futures", "crude_oil_brent_futures", "gasoline_rbob_futures", "usda_diesel", "natural_gas_futures", "thermal_coal_futures"],
            "names": ["WTI", "Brent", "Gasolina", "Diesel", "Gás Natural", "Carvão Térmico"],
            "chart_type": "line",
            "title": "Commodities (Energia)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Commodities",
        "group": "Commodities",
        "block_title": "Commodities"
    },
    "metals_commodities": {
        "chart_config": {
            "columns": ["gold_100oz_futures", "silver_futures", "lme_aluminum_futures", "lme_copper_futures", "sgx_iron_ore_62_futures", "platinum_futures", "palladium_futures"],
            "names": ["Ouro", "Prata", "Alumínio", "Cobre", "Minério de Ferro", "Platina", "Paládio"],
            "chart_type": "line",
            "title": "Commodities (Metais)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Commodities",
        "group": "Commodities",
        "block_title": "Commodities"
    },
    
    # Performance
    "currency_performance_dxy": {
        "chart_config": {
            "columns": ["dxy_index", "brl_usd"],
            "names": ["DXY", "BRL/USD"],
            "chart_type": "dual_axis_line",
            "title": "DXY vs BRL",
            "y_axis_title": ["Valor", "Valor"],
        },
        "width": 6,
        "context": "Moedas",
        "group": "Performance",
        "block_title": "Performance"
    },
    "currency_performance_em": {
        "chart_config": {
            "columns": ["dxy_index", "jpm_em_currency_index"],
            "names": ["DXY", "EM"],
            "chart_type": "dual_axis_line",
            "title": "DXY vs EM",
            "y_axis_title": ["Valor", "Valor"],
        },
        "transformations": [
            {"type": "multiply", "column": "jpm_em_currency_index", "scalar": -1},
        ],
        "width": 6,
        "context": "Moedas",
        "group": "Performance",
        "block_title": "Performance"
    },

    # === Equities ===
    # Valuation
    "valuation_dm_equities": {
        "chart_config": {
            "columns": ["us_sp500", "us_magnificent_7", "us_russell2000", "germany_dax40", "japan_nikkei225", "uk_ukx"],
            "names": ["S&P 500", "Mag 7", "Russell 2000", "DAX 40", "Nikkei 225", "UKX"],
            "chart_type": "line",
            "title": "Desenvolvidos",
            "y_axis_title": "P/E",
        },
        "width": 6,
        "context": "Equities",
        "group": "Valuation",
        "block_title": "Valuation"
    },
    "valuation_em_equities": {
        "chart_config": {
            "columns": ["br_ibovespa", "br_smll", "china_csi300", "south_africa_top40", "mexico_bmv", "chile_ipsa", "india_nifty50"],
            "names": ["Ibovespa", "SMLL", "CSI 300", "South Africa Top 40", "BMV", "IPSA", "Nifty 50"],
            "chart_type": "line",
            "title": "Emergentes",
            "y_axis_title": "P/E",
        },
        "width": 6,
        "context": "Equities",
        "group": "Valuation",
        "block_title": "Valuation"
    },
}
