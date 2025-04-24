"""
Chart configurations for global economic data
"""

GLOBAL_CHARTS = {
    # PMI Charts
    "global_pmi_manufacturing": {
        "chart_config": {
            "columns": ["global_pmi_manufacturing"],
            "names": ["Global Manufacturing PMI"],
            "chart_type": "line",
            "title": "Global Manufacturing PMI",
            "y_axis_title": "Index",
        },
        "width": 6,
        "group": "global_pmi"
    },
    "global_pmi_services": {
        "chart_config": {
            "columns": ["global_pmi_services"],
            "names": ["Global Services PMI"],
            "chart_type": "line",
            "title": "Global Services PMI",
            "y_axis_title": "Index",
        },
        "width": 6,
        "group": "global_pmi"
    },
    
    # Commodities Charts
    "commodity_oil": {
        "chart_config": {
            "columns": ["commodity_oil_wti", "commodity_oil_brent"],
            "names": ["WTI Crude Oil", "Brent Crude Oil"],
            "chart_type": "line",
            "title": "Oil Prices",
            "y_axis_title": "USD per barrel",
        },
        "width": 6,
        "group": "global_commodities"
    },
    "commodity_metals": {
        "chart_config": {
            "columns": ["commodity_gold", "commodity_silver", "commodity_copper"],
            "names": ["Gold", "Silver", "Copper"],
            "chart_type": "line",
            "title": "Metals Prices",
            "y_axis_title": "USD",
        },
        "width": 6,
        "group": "global_commodities"
    },
    
    # Currencies Charts
    "currency_dxy": {
        "chart_config": {
            "columns": ["dxy_index"],
            "names": ["DXY Index"],
            "chart_type": "line",
            "title": "US Dollar Index",
            "y_axis_title": "Index",
        },
        "width": 6,
        "group": "global_currencies"
    },
    "currency_major_pairs": {
        "chart_config": {
            "columns": ["eur_usd", "gbp_usd", "usd_jpy"],
            "names": ["EUR/USD", "GBP/USD", "USD/JPY"],
            "chart_type": "line",
            "title": "Major Currency Pairs",
            "y_axis_title": "Exchange Rate",
        },
        "width": 6,
        "group": "global_currencies"
    }
} 