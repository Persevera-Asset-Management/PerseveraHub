"""
Chart configurations for US economic data
"""

US_CHARTS = {
    # GDP Charts
    "us_gdp_qoq": {
        "title": "#### US GDP Growth QoQ",
        "chart_config": {
            "columns": ["us_gdp_qoq"],
            "names": ["GDP QoQ (%)"],
            "chart_type": "column",
            "title": "PIB QoQ",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "us_gdp"
    },
    "us_gdp_yoy": {
        "title": "#### US GDP Growth YoY",
        "chart_config": {
            "columns": ["us_gdp_yoy"],
            "names": ["GDP YoY (%)"],
            "chart_type": "column",
            "title": "PIB YoY",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "group": "us_gdp"
    },
    
    # Industry Charts
    "us_industry_surprise": {
        "chart_config": {
            "columns": ["us_bloomberg_industry_surprise_index"],
            "names": ["Industry"],
            "chart_type": "area",
            "title": "Bloomberg US Industrial Sector Surprise Index",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Industrial Bloomberg Data Surprise"
    },
    "us_industry_production": {
        "chart_config": {
            "columns": ["us_industrial_production_index", "us_capacity_utilization_index"],
            "names": ["Industrial Production", "Capacity Utilization"],
            "chart_type": "line",
            "title": "Produção Industrial e Utilização de Capacidade",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Produção Industrial & Utilização de Capacidade"
    },
    
    # Retail Charts
    "us_retail_surprise": {
        "chart_config": {
            "columns": ["us_bloomberg_retail_surprise_index"],
            "names": ["Retail Sales"],
            "chart_type": "area",
            "title": "Bloomberg Retail & Wholesale Sector Surprise Index",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Retail & Wholesale Bloomberg Data Surprise"
    },
    "us_retail_sales": {
        "chart_config": {
            "columns": ["us_advance_retail_sales_total", "us_advance_retail_sales_ex_auto_total"],
            "names": ["Retail Sales"],
            "chart_type": "line",
            "title": "Vendas no Varejo",
            "y_axis_title": "Índice",
        },
        "width": 6,
        "group": "Vendas no Varejo"
    },
    
    # Example Inflation Charts (placeholders)
    "us_cpi": {
        "chart_config": {
            "columns": ["us_cpi", "us_cpi_core"],
            "names": ["CPI YoY (%)", "Core CPI YoY (%)"],
            "chart_type": "line",
            "title": "US Consumer Price Index",
            "y_axis_title": "Rate (%)",
        },
        "width": 6,
        "group": "us_inflation"
    },
    "us_pce": {
        "chart_config": {
            "columns": ["us_pce", "us_pce_core"],
            "names": ["PCE YoY (%)", "Core PCE YoY (%)"],
            "chart_type": "line",
            "title": "US Personal Consumption Expenditures",
            "y_axis_title": "Rate (%)",
        },
        "width": 6,
        "group": "us_inflation"
    }
} 