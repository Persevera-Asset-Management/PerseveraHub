"""
Meeting configuration for "Reunião de Timing"
"""

# Tab structure configuration defining how charts are organized in this specific meeting
MEETING_TAB_STRUCTURE = {
    "Market Timing": {
        "Calendar": ["timing_calendar"],
        "Equities": ["equity_timing", "market_breadth", "momentum"],
        "Fixed Income": ["bond_timing", "yield_curve"],
        "Currencies": ["currency_timing", "global_currencies"]
    },
    "Market Cycles": {
        "Economic Indicators": ["business_cycle", "leading_indicators"],
        "Market Regime": ["market_regime", "volatility_regime"],
        "Sentiment": ["investor_sentiment", "positioning"]
    },
    "Tactical": {
        "Technical": ["technical_analysis", "trend_following"],
        "Seasonal": ["seasonal_factors", "event_patterns"],
        "Flows": ["fund_flows", "liquidity_indicators"]
    }
}

# Meeting-specific settings
MEETING_SETTINGS = {
    "title": "Reunião de Timing",
    "icon": "⏱️",
    "default_start_date": "2018-01-01",
    "refresh_interval_minutes": 30,  # How often to refresh data (in minutes)
    "chart_groups_to_load": [
        # Market Timing chart groups
        "timing_calendar", "equity_timing", "market_breadth", "momentum",
        "bond_timing", "yield_curve", "currency_timing",
        
        # Market Cycles chart groups
        "business_cycle", "leading_indicators", "market_regime", 
        "volatility_regime", "investor_sentiment", "positioning",
        
        # Tactical chart groups
        "technical_analysis", "trend_following", "seasonal_factors",
        "event_patterns", "fund_flows", "liquidity_indicators",
        
        # Shared chart groups from other configurations
        "global_currencies"  # Reusing this group from Global charts
    ]
}

def get_tab_structure():
    """
    Returns the tab structure configuration for this meeting.
    
    Returns:
    --------
    Dict[str, Dict[str, List[str]]]
        Dictionary of tab structure
    """
    return MEETING_TAB_STRUCTURE

def get_meeting_settings():
    """
    Returns the meeting-specific settings.
    
    Returns:
    --------
    Dict[str, Any]
        Dictionary of meeting settings
    """
    return MEETING_SETTINGS 