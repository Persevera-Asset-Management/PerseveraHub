import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
from utils.charts import create_highcharts_options
from utils.data_transformers import apply_transformations

def create_chart(data, columns, names, chart_type, title, y_axis_title=None, x_axis_title=None, colors=None, **kwargs):
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
    x_axis_title : str, optional
        X-axis title (defaults to None)
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
        x_axis_title=x_axis_title,
        series_name=names,
        color=colors,
        **kwargs
    )

def _get_transformed_column_name(original_col_name: str, transformations_list: List[Dict[str, Any]]) -> str:
    """Determines the new column name after transformations."""
    new_col_name = original_col_name
    if not transformations_list: # No transformations, return original name
        return new_col_name

    for t_conf in transformations_list:
        transform_type = t_conf.get("type")
        # Check if this transformation applies to the current original column (most common case)
        if t_conf.get("column") == original_col_name:
            if transform_type == "yearly_variation":
                new_col_name = f"{original_col_name}_yoy"
                break 
            elif transform_type == "monthly_variation":
                new_col_name = f"{original_col_name}_mom"
                break
            elif transform_type == "quarterly_variation":
                new_col_name = f"{original_col_name}_qoq"
                break
            elif transform_type == "monthly_difference":
                new_col_name = f"{original_col_name}_mom_diff"
                break
            elif transform_type == "moving_average":
                window = t_conf.get("window", 21) 
                new_col_name = f"{original_col_name}_ma{window}"
                break
            elif transform_type == "rolling_max":
                window = t_conf.get("window", 252)
                new_col_name = f"{original_col_name}_max{window}"
                break
            elif transform_type == "rolling_min":
                window = t_conf.get("window", 252)
                new_col_name = f"{original_col_name}_min{window}"
                break
            elif transform_type == "multiply":
                scalar = t_conf.get("scalar", 1)
                new_col_name = f"{original_col_name}_multiplied_by_{scalar}"
                break
            elif transform_type == "divide":
                scalar = t_conf.get("scalar", 1)
                new_col_name = f"{original_col_name}_divided_by_{scalar}"
                break
            elif transform_type == "saar":
                period_months = t_conf.get("period_months", 12)
                new_col_name = f"{original_col_name}_saar_{period_months}m"
                break
            # Add other specific single-column input transformers here

        # Handle transformers that don't use 'column' but whose output name might match original_col_name
        # if it was, for instance, the target_column of such a transformation.
        elif transform_type == "relative_performance":
            if t_conf.get("target_column") == original_col_name:
                base_column = t_conf.get("base_column")
                if base_column: 
                    new_col_name = f"{original_col_name}_vs_{base_column}"
                    break 
    return new_col_name

def _update_column_names_recursively(columns_structure: Union[str, List[Any]], transformations_list: List[Dict[str, Any]]) -> Union[str, List[Any]]:
    """Recursively updates column names in simple or nested list structures."""
    if isinstance(columns_structure, str):
        return _get_transformed_column_name(columns_structure, transformations_list)
    elif isinstance(columns_structure, list):
        updated_list = []
        for item in columns_structure:
            updated_list.append(_update_column_names_recursively(item, transformations_list))
        return updated_list
    else:
        # For any other type, return as is (should not happen with expected config)
        return columns_structure

def extract_codes_from_config(chart_configs):
    """
    Extracts all unique column codes from chart configurations.
    Also considers columns used in transformations if they are not primary plot columns.
    """
    all_codes = [] 
    processed_for_chart_columns = set() # To store raw column names for plotting

    for config_id, config_entry in chart_configs.items():
        # Determine the actual chart configuration part
        actual_chart_conf = config_entry.get("chart_config", config_entry) # Handles both nested and flat
        
        # Extract columns intended for plotting
        columns_for_plotting = actual_chart_conf.get("columns", [])
        if isinstance(columns_for_plotting, str):
            processed_for_chart_columns.add(columns_for_plotting)
        elif isinstance(columns_for_plotting, list):
            def _flatten_plot_cols(cols_struct):
                if isinstance(cols_struct, str):
                    processed_for_chart_columns.add(cols_struct)
                elif isinstance(cols_struct, list):
                    for item in cols_struct:
                        _flatten_plot_cols(item)
            _flatten_plot_cols(columns_for_plotting)

        # Extract columns used in transformations
        transformations = config_entry.get("transformations", []) # From the outer config_entry
        if transformations:
            for t_conf in transformations:
                if "column" in t_conf: # e.g., yearly_variation, moving_average
                    if isinstance(t_conf["column"], str):
                         processed_for_chart_columns.add(t_conf["column"])
                elif "base_column" in t_conf and "target_column" in t_conf: # e.g., relative_performance
                    if isinstance(t_conf["base_column"], str):
                        processed_for_chart_columns.add(t_conf["base_column"])
                    if isinstance(t_conf["target_column"], str):
                        processed_for_chart_columns.add(t_conf["target_column"])
                # Add other transformation-specific column extractions if needed
                
    all_codes = list(processed_for_chart_columns)
    return all_codes

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
    st.markdown(f"### {group_name}")
    
    # Calculate number of rows needed (2 charts per row)
    chart_ids = charts_by_group[group_name]
    num_charts = len(chart_ids)
    num_rows = (num_charts + 1) // 2  # Ceiling division
    
    for row in range(num_rows):
        cols = st.columns(2)
        for col_idx_in_row in range(2): # Renamed 'col' to avoid conflict with column names
            idx = row * 2 + col_idx_in_row
            if idx < num_charts:
                chart_id = chart_ids[idx]
                config = chart_configs[chart_id]
                
                # Get chart config (support both nested and flat structures)
                current_chart_config = config.get("chart_config", config).copy()
                
                # Prepare data for this specific chart
                chart_data_for_this_chart = data.copy() 
                transformations_to_apply = config.get("transformations")

                if transformations_to_apply:
                    chart_data_for_this_chart = apply_transformations(chart_data_for_this_chart, transformations_to_apply)
                    
                    original_columns_structure = current_chart_config.get("columns")
                    if original_columns_structure is not None:
                        updated_columns_structure = _update_column_names_recursively(original_columns_structure, transformations_to_apply)
                        current_chart_config["columns"] = updated_columns_structure
                
                with cols[col_idx_in_row]:                    
                    chart_obj = create_chart(chart_data_for_this_chart, **current_chart_config) # Renamed to chart_obj
                    key = f"{group_name}_{chart_id}_{row}_{col_idx_in_row}"
                    hct.streamlit_highcharts(chart_obj, key=key)

def organize_charts_by_context(chart_configs):
    """
    Organizes chart configurations by their context and group attributes.
    
    Parameters:
    -----------
    chart_configs : Dict[str, Dict]
        Dictionary of chart configurations
        
    Returns:
    --------
    Dict[str, Dict[str, List[Tuple[str, Dict]]]]
        Dictionary with contexts as outer keys, groups as inner keys,
        and lists of (chart_id, full_config_entry) tuples as values.
    """
    charts_by_context = {}
    for chart_id, config_entry in chart_configs.items():
        context = config_entry.get("context", "global")
        group = config_entry.get("group", "outros")
        
        if context not in charts_by_context:
            charts_by_context[context] = {}
        if group not in charts_by_context[context]:
            charts_by_context[context][group] = []
            
        charts_by_context[context][group].append((chart_id, config_entry))
    return charts_by_context

def render_chart_group_with_context(data, chart_configs_original, context, group, charts_by_context_organized):
    """
    Renders a group of charts in a responsive grid layout, with context and block awareness.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the chart data (original, pre-transformation for this call)
    chart_configs_original : Dict[str, Dict]
        Not used directly, but kept for signature consistency if needed elsewhere.
        The necessary configs are inside charts_by_context_organized.
    context : str
        Context identifier (region, tab, etc.)
    group : str
        Name of the group to render
    charts_by_context_organized : Dict[str, Dict[str, List[Tuple[str, Dict]]]]
        Dictionary from organize_charts_by_context: {context: {group: [(chart_id, full_config_entry)]}}
    
    Returns:
    --------
    None
        Renders charts directly to Streamlit
    """
    import streamlit as st
    import streamlit_highcharts as hct
    from collections import defaultdict
    
    if (context not in charts_by_context_organized or 
        group not in charts_by_context_organized[context] or 
        not charts_by_context_organized[context][group]):
        return
    
    chart_id_config_list = charts_by_context_organized[context][group]
    
    charts_by_block = defaultdict(list)
    block_order = [] 
    
    for chart_id, full_config_entry in chart_id_config_list:
        block_title = full_config_entry.get("block_title") 
        # Use a consistent key for charts without an explicit block_title
        # This helps in grouping them together if multiple such charts exist.
        block_key_to_use = block_title if block_title is not None else "_no_block_title_"
        is_explicit_block = block_title is not None

        if block_key_to_use not in charts_by_block:
            if is_explicit_block and block_key_to_use not in block_order:
                 block_order.append(block_key_to_use)
            # Store (chart_id, full_config_entry, is_explicit_block) for rendering
            charts_by_block[block_key_to_use].append((chart_id, full_config_entry, is_explicit_block))
        else:
            charts_by_block[block_key_to_use].append((chart_id, full_config_entry, is_explicit_block))
    
    # Ensure blocks without explicit titles are rendered after those with titles
    if "_no_block_title_" in charts_by_block and "_no_block_title_" not in block_order:
        block_order.append("_no_block_title_")

    for block_key in block_order:
        chart_tuples_in_block = charts_by_block.get(block_key, []) # Use .get for safety
        if not chart_tuples_in_block:
            continue

        is_explicit_block_header = chart_tuples_in_block[0][2] # Check first item for block type
        if is_explicit_block_header:
            st.subheader(block_key)

        num_charts_in_block = len(chart_tuples_in_block)
        num_rows = (num_charts_in_block + 1) // 2
        
        for row in range(num_rows):
            cols = st.columns(2)
            for col_idx_in_row in range(2):
                chart_render_idx = row * 2 + col_idx_in_row
                if chart_render_idx < num_charts_in_block:
                    chart_id, full_config_entry_for_chart, _ = chart_tuples_in_block[chart_render_idx]
                    
                    current_chart_config_dict = full_config_entry_for_chart.get("chart_config", full_config_entry_for_chart).copy()
                    
                    chart_data_for_this_specific_chart = data.copy()
                    transformations_to_apply_list = full_config_entry_for_chart.get("transformations")

                    if transformations_to_apply_list:
                        chart_data_for_this_specific_chart = apply_transformations(chart_data_for_this_specific_chart, transformations_to_apply_list)
                        
                        original_cols_structure = current_chart_config_dict.get("columns")
                        if original_cols_structure is not None:
                            updated_cols_structure = _update_column_names_recursively(original_cols_structure, transformations_to_apply_list)
                            current_chart_config_dict["columns"] = updated_cols_structure
                    
                    with cols[col_idx_in_row]:                    
                        chart_object_to_render = create_chart(chart_data_for_this_specific_chart, **current_chart_config_dict)
                        unique_key = f"{context}_{group}_{block_key}_{chart_id}_{row}_{col_idx_in_row}"
                        hct.streamlit_highcharts(chart_object_to_render, key=unique_key)

        if is_explicit_block_header:
            st.markdown("<br>", unsafe_allow_html=True)
