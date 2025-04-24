"""
Chart configurations for Brazilian economic data
"""

BR_CHARTS = {
    # Economic Activity Charts
    "br_ibcbr_index": {
        "title": "#### IBC-Br",
        "chart_config": {
            "columns": ["br_ibcbr_index"],
            "names": ["IBC-Br"],
            "chart_type": "line",
            "title": "IBC-Br",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_ibcbr"
    },
    
    # GDP Charts
    "br_gdp_qoq": {
        "title": "#### PIB QoQ",
        "chart_config": {
            "columns": ["br_gdp_index"],
            "names": ["GDP QoQ (%)"],
            "chart_type": "column",
            "title": "PIB QoQ",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_gdp"   
    },
    "br_gdp_yoy": {
        "title": "#### PIB YoY",
        "chart_config": {
            "columns": ["br_gdp_12m"],
            "names": ["GDP YoY (%)"],
            "chart_type": "column",
            "title": "PIB YoY",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_gdp"
    },
    
    # Inflation Charts
    "br_ipca": {
        "chart_config": {
            "columns": ["br_ipca"],
            "names": ["IPCA YoY (%)"],
            "chart_type": "line",
            "title": "Inflação IPCA",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_inflation"
    },
    "br_igpm": {
        "chart_config": {
            "columns": ["br_igpm"],
            "names": ["IGP-M YoY (%)"],
            "chart_type": "line",
            "title": "Inflação IGP-M",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "br_inflation"
    },
    
    # Industry Charts
    "br_industry_production": {
        "chart_config": {
            "columns": ["br_industrial_production_index"],
            "names": ["Produção Industrial"],
            "chart_type": "line",
            "title": "Produção Industrial",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "br_industry"
    }
} 