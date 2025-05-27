BITCOIN_DASHBOARD = {
    "bitcoin_volatility": {
        "chart_config": {
            "columns": ["bitcoin_volatility_index", "bitcoin_usd"],
            "names": ["CF Bitcoin Volatility Index", "Vol Realizada (21d)", "Vol Realizada (252d)"],
            "chart_type": "line",
            "title": "Volatilidade",
            "y_axis_title": "Volatilidade (%)",
        },
        "transformations": [
            {"type": "rolling_volatility", "column": "bitcoin_usd", "window": 21, "annualized": True, "calculate_on_returns": True},
            {"type": "rolling_volatility", "column": "bitcoin_usd", "window": 252, "annualized": True, "calculate_on_returns": True}
        ],
        "width": 6,
        "group": "Volatilidade",
        "context": "Bitcoin"
    },
    "bitcoin_correlation": {
        "chart_config": {
            "columns": ["bitcoin_usd", "us_nasdaq100"],
            "names": ["Bitcoin", "Nasdaq 100"],
            "chart_type": "dual_axis_line",
            "title": "Bitcoin vs Nasdaq 100",
            "y_axis_title": ("Bitcoin (USD)", "Nasdaq 100 (USD)"),
        },
        "width": 6,
        "group": "Correlação",
        "context": "Bitcoin"
    },
    "bitcoin_beta": {
        "chart_config": {
            "columns": ["beta_bitcoin_usd_vs_us_nasdaq100_w60"],
            "names": ["Beta (60d)"],
            "chart_type": "line",
            "title": "Bitcoin vs Nasdaq 100 (Beta 60d)",
            "y_axis_title": "Beta"
        },
        "transformations": [
            {"type": "rolling_beta", "dependent_column": "bitcoin_usd", "independent_column": "us_nasdaq100", "window": 60}
        ],
        "width": 6,
        "group": "Correlação",
        "context": "Bitcoin"
    },
}