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
            "y_axis_title": "%",
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
            "y_axis_title": "%",
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
            "y_axis_title": "%",
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
            "y_axis_title": "%",
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
            "columns": ["br_focus_selic_median_2025R5", "br_focus_selic_median_2025R6", "br_focus_selic_median_2025R7", "br_focus_selic_median_2025R8"],
            "names": ["R5 (jul)", "R6 (set)", "R7 (nov)", "R8 (dez)"],
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
    # Modelo Cambial
    "br_international_reserves": {
        "chart_config": {
            "columns": ["br_international_reserves_total"],
            "names": ["Reservas Internacionais"],
            "chart_type": "line",
            "title": "Reservas Internacionais",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Moedas",
        "group": "Modelo Cambial",
        "block_title": "Modelo Cambial"
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
            "y_axis_title": "Valor (P/E)",
        },
        "width": 6,
        "context": "Equities",
        "group": "Valuation",
        "block_title": "Valuation"
    },
    "valuation_em_equities": {
        "chart_config": {
            "columns": ["br_ibovespa", "china_csi300", "south_africa_top40", "mexico_bmv", "chile_ipsa", "india_nifty50"],
            "names": ["Ibovespa", "CSI 300", "South Africa Top 40", "BMV", "IPSA", "Nifty 50"],
            "chart_type": "line",
            "title": "Emergentes",
            "y_axis_title": "Valor (P/E)",
        },
        "width": 6,
        "context": "Equities",
        "group": "Valuation",
        "block_title": "Valuation"
    },
}
