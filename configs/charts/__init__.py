"""
Chart configuration package
"""

from configs.charts.us_charts import US_CHARTS
from configs.charts.br_charts import BR_CHARTS
from configs.charts.global_charts import GLOBAL_CHARTS

# Tab structure configuration defining how charts are organized in the UI
TAB_STRUCTURE = {
    "Estados Unidos": {
        "PIB": ["us_gdp"],
        "Inflação": ["us_inflation"],
        "Emprego": ["us_employment"],
        "Indústria": ["Industrial Bloomberg Data Surprise", "Produção Industrial & Utilização de Capacidade"],
        "Varejo": ["Retail & Wholesale Bloomberg Data Surprise", "Vendas no Varejo"],
        "Imobiliário": ["us_real_estate"],
        "Crédito": ["us_credit"],
        "Sentimento": ["us_sentiment"]
    },
    "Brasil": {
        "IBC-Br": ["br_ibcbr"],
        "PIB": ["br_gdp"],
        "Inflação": ["br_inflation"],
        "Indústria": ["br_industry"],
        "Serviços": ["br_services"],
        "Varejo": ["br_retail"],
        "Sentimento": ["br_sentiment"],
        "Emprego": ["br_employment"],
        "Crédito": ["br_credit"],
        "Setor Externo": ["br_external"],
        "Commodities": ["br_commodities"],
        "Fiscal": ["br_fiscal"]
    },
    "Global": {
        "PMI": ["global_pmi"],
        "Commodities": ["global_commodities"],
        "Moedas": ["global_currencies"],
        "Inflação": ["global_inflation"]
    }
}

# Combine all chart configurations into a single dictionary
ALL_CHARTS = {
    **US_CHARTS,
    **BR_CHARTS,
    **GLOBAL_CHARTS
}

def get_all_charts():
    """
    Returns the combined dictionary of all chart configurations.
    
    Returns:
    --------
    Dict[str, Dict]
        Dictionary of all chart configurations
    """
    return ALL_CHARTS

def get_filtered_charts(chart_groups=None):
    """
    Returns a filtered dictionary of chart configurations based on specified groups.
    
    Parameters:
    -----------
    chart_groups : List[str], optional
        List of chart group names to include. If None, returns all charts.
        
    Returns:
    --------
    Dict[str, Dict]
        Filtered dictionary of chart configurations
    """
    if chart_groups is None:
        return ALL_CHARTS
    
    filtered_charts = {}
    for chart_id, config in ALL_CHARTS.items():
        group = config.get("group", "outros")
        if group in chart_groups:
            filtered_charts[chart_id] = config
    
    return filtered_charts

def get_tab_structure():
    """
    Returns the tab structure configuration.
    
    Returns:
    --------
    Dict[str, Dict[str, List[str]]]
        Dictionary of tab structure
    """
    return TAB_STRUCTURE 