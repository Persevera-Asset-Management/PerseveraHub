import pandas as pd
from typing import List, Dict, Any, Optional, Union
from utils.charts import create_highcharts_options

def create_chart(data, columns, names, chart_type, title, y_axis_title=None, colors=None, **kwargs):
    """
    Creates a Highcharts chart configuration with specified parameters.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the data to plot
    columns : str or List[str]
        Column name(s) to plot from the DataFrame
    names : str or List[str]
        Series name(s) for the legend
    chart_type : str
        Type of chart ('line', 'area', 'column', 'spline', etc.)
    title : str
        Chart title
    y_axis_title : str, optional
        Y-axis title (defaults to "Value" if None)
    colors : str or List[str], optional
        Color(s) for the series
    **kwargs : dict
        Additional parameters to pass to create_highcharts_options
        
    Returns:
    --------
    Dict[str, Any]
        Highcharts configuration object
    """
    return create_highcharts_options(
        data=data,
        y_column=columns,
        chart_type=chart_type,
        title=title,
        y_axis_title=y_axis_title or "Value",
        series_name=names,
        color=colors,
        **kwargs
    )

def extract_codes_from_config(chart_configs):
    """
    Extracts all unique column codes from chart configurations.
    
    Parameters:
    -----------
    chart_configs : Dict[str, Dict]
        Dictionary of chart configurations
        
    Returns:
    --------
    List[str]
        List of unique column codes needed for all charts
    """
    all_codes = []
    for config_id, config in chart_configs.items():
        if "chart_config" in config:
            # Handle nested config structure
            columns = config["chart_config"].get("columns", [])
        else:
            # Handle flat config structure
            columns = config.get("columns", [])
        
        if isinstance(columns, str):
            all_codes.append(columns)
        elif isinstance(columns, list):
            all_codes.extend(columns)
    
    # Return deduplicated list
    return list(set(all_codes))

def organize_charts_by_group(chart_configs):
    """
    Organizes chart configurations by their group attribute.
    
    Parameters:
    -----------
    chart_configs : Dict[str, Dict]
        Dictionary of chart configurations
        
    Returns:
    --------
    Dict[str, List[str]]
        Dictionary with groups as keys and lists of chart IDs as values
    """
    charts_by_group = {}
    for chart_id, config in chart_configs.items():
        group = config.get("group", "outros")
        if group not in charts_by_group:
            charts_by_group[group] = []
        charts_by_group[group].append(chart_id)
    
    return charts_by_group

def render_chart_group(data, chart_configs, group_name, charts_by_group):
    """
    Renders a group of charts in a responsive grid layout.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the chart data
    chart_configs : Dict[str, Dict]
        Dictionary of chart configurations
    group_name : str
        Name of the group to render
    charts_by_group : Dict[str, List[str]]
        Dictionary mapping group names to lists of chart IDs
    
    Returns:
    --------
    None
        Renders charts directly to Streamlit
    """
    import streamlit as st
    import streamlit_highcharts as hct
    
    if group_name not in charts_by_group or not charts_by_group[group_name]:
        return
    
    # Format group name for display
    display_name = " ".join(word.title() for word in group_name.split("_"))
    st.markdown(f"### {display_name}")
    
    # Calculate number of rows needed (2 charts per row)
    chart_ids = charts_by_group[group_name]
    num_charts = len(chart_ids)
    num_rows = (num_charts + 1) // 2  # Ceiling division
    
    for row in range(num_rows):
        cols = st.columns(2)
        for col in range(2):
            idx = row * 2 + col
            if idx < num_charts:
                chart_id = chart_ids[idx]
                config = chart_configs[chart_id]
                
                # Get chart config (support both nested and flat structures)
                chart_config = config.get("chart_config", config)
                
                with cols[col]:
                    chart = create_chart(data, **chart_config)
                    # Add a unique key for each chart to avoid duplicate IDs
                    key = f"{group_name}_{chart_id}_{row}_{col}"
                    hct.streamlit_highcharts(chart, key=key)

def render_category_tabs(data, chart_configs, region_tab_mapping):
    """
    Renders a nested tab structure with charts organized by region and category.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the chart data
    chart_configs : Dict[str, Dict]
        Dictionary of chart configurations
    region_tab_mapping : Dict[str, Dict[str, List[str]]]
        Dictionary mapping regions to tab categories to chart groups
        Example:
        {
            "Estados Unidos": {
                "PIB": ["us_gdp"],
                "Inflação": ["us_inflation"],
                ...
            },
            "Brasil": {...},
            ...
        }
    
    Returns:
    --------
    None
        Renders tabs and charts directly to Streamlit
    """
    import streamlit as st
    
    # Organize charts by group
    charts_by_group = organize_charts_by_group(chart_configs)
    
    # Create main region tabs
    region_tabs = st.tabs(list(region_tab_mapping.keys()))
    
    # For each region tab, create category tabs and render charts
    for i, (region, categories) in enumerate(region_tab_mapping.items()):
        with region_tabs[i]:
            # Create category tabs for this region
            category_names = list(categories.keys())
            category_tabs = st.tabs(category_names)
            
            # For each category, render the associated chart groups
            for j, (category, groups) in enumerate(categories.items()):
                with category_tabs[j]:
                    # Render each chart group in this category
                    for group in groups:
                        if group in charts_by_group:
                            render_chart_group(data, chart_configs, group, charts_by_group) 