CHARTS_BRASIL_ASSET = {
    "curva_juros_pre": {
        "chart_config": {
            "columns": ["br_pre_1y", "br_pre_2y", "br_pre_5y", "br_generic_10y"],
            "names": ["1Y", "2Y", "5Y", "10Y"],
            "chart_type": "line",
            "title": "Curva de Juros Pré",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "Curvas de Juros",
        "context": "Títulos Públicos"
    },
    "curva_juros_ipca": {
        "chart_config": {
            "columns": ["br_ipca_1y", "br_ipca_2y", "br_ipca_5y", "br_ipca_10y"],
            "names": ["1Y", "2Y", "5Y", "10Y"],
            "chart_type": "line",
            "title": "Curva de Juros IPCA",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "Curvas de Juros",
        "context": "Títulos Públicos"
    },
    "bolsas_ibov": {
        "chart_config": {
            "columns": "br_ibovespa",
            "names": "Ibovespa",
            "chart_type": "line",
            "title": "Ibovespa",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "Índices",
        "context": "Renda Variável"
    },
    "bolsas_sp500": {
        "chart_config": {
            "columns": "us_sp500",
            "names": "S&P 500",
            "chart_type": "line",
            "title": "S&P 500",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "Índices",
        "context": "Renda Variável"
    },
    "bolsas_euro_stoxx": {
        "chart_config": {
            "columns": "euro_stoxx50",
            "names": "Euro Stoxx 50",
            "chart_type": "line",
            "title": "Euro Stoxx 50",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "Índices",
        "context": "Renda Variável"
    },
    "bolsas_china_csi1000": {
        "chart_config": {
            "columns": "china_csi1000",
            "names": "CSI 1000",
            "chart_type": "line",
            "title": "CSI 1000",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "Índices",
        "context": "Renda Variável"
    },
    "moedas_dxy": {
        "chart_config": {
            "columns": "dxy_index",
            "names": "DXY",
            "chart_type": "line",
            "title": "DXY",
            "y_axis_title": "Pontos",
        },
        "width": 6,
        "group": "Índices e Taxas de Câmbio",
        "context": "Moedas"
    },
    "moedas_eurusd": {
        "chart_config": {
            "columns": "eur_usd",
            "names": "EUR/USD",
            "chart_type": "line",
            "title": "EUR/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "Índices e Taxas de Câmbio",
        "context": "Moedas"
    },
    "moedas_usdbrl": {
        "chart_config": {
            "columns": "brl_usd",
            "names": "BRL/USD",
            "chart_type": "line",
            "title": "BRL/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "Índices e Taxas de Câmbio",
        "context": "Moedas"
    },
    "moedas_mxnusd": {
        "chart_config": {
            "columns": "mxn_usd",
            "names": "MXN/USD",
            "chart_type": "line",
            "title": "MXN/USD",
            "y_axis_title": "Taxa",
        },
        "width": 6,
        "group": "Índices e Taxas de Câmbio",
        "context": "Moedas"
    },
    "br_exports_imports_t12": {
        "chart_config": {
            "columns": (["br_trade_balance_fob_exports_usd", "br_trade_balance_fob_imports_usd"], ["br_trade_balance_fob_net_usd"]),
            "names": (["Exportações", "Importações"], ["Saldo"]),
            "chart_type": "dual_axis_line_area",
            "title": "Exportações e Importações (Acumulado 12 meses)",
            "y_axis_title": ("US$", "US$"),
        },
        "transformations": [{"type": "rolling_sum", "column": "br_trade_balance_fob_exports_usd", "frequency": "MS", "window": 12}, {"type": "rolling_sum", "column": "br_trade_balance_fob_imports_usd", "frequency": "MS", "window": 12}],
        "width": 6,
        "group": "Curvas de Juros",
        "context": "Títulos Públicos"
    },
}