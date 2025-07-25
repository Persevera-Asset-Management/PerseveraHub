import pandas as pd
from typing import List, Dict, Any, Optional, Union, Tuple
from utils.charts import create_highcharts_options
from utils.data_transformers import apply_transformations

def create_chart(data, chart_type, title, y_axis_title=None, x_axis_title=None, columns=None, names=None, color=None, instruments=None, **kwargs):
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
    color : str or List[str], optional
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
        instruments=instruments,
        chart_type=chart_type,
        title=title,
        y_axis_title=y_axis_title or "Value",
        x_axis_title=x_axis_title,
        series_name=names,
        color=color,
        **kwargs
    )

def _get_transformed_column_name(original_col_name: str, transformations_list: List[Dict[str, Any]]) -> Union[str, List[str]]:
    """
    Determines the new column name(s) after transformations.
    If multiple transformations apply to the same original_col_name as a direct 'column' input,
    a list of new names is returned.
    Otherwise, a single new name or the original name is returned.
    """
    if not transformations_list:
        return original_col_name

    collected_direct_input_names = []
    # First pass: Collect all names from transformations where original_col_name is a direct 'column' input.
    for t_conf in transformations_list:
        if t_conf.get("column") == original_col_name:
            transform_type = t_conf.get("type")
            generated_name_this_iteration = ""
            
            if transform_type == "yearly_variation":
                generated_name_this_iteration = f"{original_col_name}_yoy"
            elif transform_type == "monthly_variation":
                generated_name_this_iteration = f"{original_col_name}_mom"
            elif transform_type == "quarterly_variation":
                generated_name_this_iteration = f"{original_col_name}_qoq"
            elif transform_type == "monthly_difference":
                generated_name_this_iteration = f"{original_col_name}_mom_diff"
            elif transform_type == "moving_average":
                window = t_conf.get("window", 21) 
                generated_name_this_iteration = f"{original_col_name}_ma{window}"
            elif transform_type == "rolling_max":
                window = t_conf.get("window", 252)
                generated_name_this_iteration = f"{original_col_name}_max{window}"
            elif transform_type == "rolling_min":
                window = t_conf.get("window", 252)
                generated_name_this_iteration = f"{original_col_name}_min{window}"
            elif transform_type == "rolling_sum":
                window = t_conf.get("window", 12)
                generated_name_this_iteration = f"{original_col_name}_rolling_sum_{window}"
            elif transform_type == "rolling_sum_plus_yearly_variation":
                window = t_conf.get("window", 12)
                generated_name_this_iteration = f"{original_col_name}_rolling_sum_yoy"
            elif transform_type == "multiply":
                scalar = t_conf.get("scalar", 1)
                generated_name_this_iteration = f"{original_col_name}_multiplied_by_{scalar}"
            elif transform_type == "divide":
                scalar = t_conf.get("scalar", 1)
                generated_name_this_iteration = f"{original_col_name}_divided_by_{scalar}"
            elif transform_type == "saar":
                period_months = t_conf.get("period_months", 12)
                generated_name_this_iteration = f"{original_col_name}_saar_{period_months}m"
            elif transform_type == "saar_ma":
                period_months = t_conf.get("period_months", 12)
                generated_name_this_iteration = f"{original_col_name}_saar_ma_{period_months}m"
            elif transform_type == "rolling_volatility":
                window = t_conf.get("window", 252)
                annualized = t_conf.get("annualized", False)
                calculate_on_returns = t_conf.get("calculate_on_returns", True)
                name_prefix = original_col_name
                if calculate_on_returns:
                    name_prefix = f"{original_col_name}_returns"
                generated_name_this_iteration = f"{name_prefix}_vol{window}_annualized" if annualized else f"{name_prefix}_vol{window}"
            elif transform_type == "rolling_beta":
                dependent_col = t_conf.get("dependent_column")
                independent_col = t_conf.get("independent_column")
                window = t_conf.get("window", 252)
                generated_name_this_iteration = f"beta_{dependent_col}_vs_{independent_col}_w{window}"

            if generated_name_this_iteration:
                 collected_direct_input_names.append(generated_name_this_iteration)
    
    # If direct input transformations were found, these take precedence.
    if collected_direct_input_names:
        if len(collected_direct_input_names) == 1:
            return collected_direct_input_names[0]
        else:
            return collected_direct_input_names

    # Second pass (only if NO direct input transformations were found): 
    # Check for other types of relations (e.g., original_col_name as a 'target_column').
    # This part mimics the original "find first special match and return" behavior.
    for t_conf in transformations_list:
        transform_type = t_conf.get("type")
        
        if t_conf.get("column") != original_col_name: # Avoid re-processing direct input columns handled above
            if transform_type == "relative_performance":
                if t_conf.get("target_column") == original_col_name:
                    base_column = t_conf.get("base_column")
                    if base_column: 
                        return f"{original_col_name}_vs_{base_column}"
            elif transform_type == "rolling_beta":
                # If original_col_name is an expected output of a rolling_beta transform
                dependent_col = t_conf.get("dependent_column")
                independent_col = t_conf.get("independent_column")
                window = t_conf.get("window", 252)
                if dependent_col and independent_col:
                    expected_beta_col_name = f"beta_{dependent_col}_vs_{independent_col}_w{window}"
                    if original_col_name == expected_beta_col_name:
                        return original_col_name # The name is already the transformed name
            # Add other similar 'elif' blocks here

    return original_col_name # Fallback if no transformation applied

def _update_column_names_recursively(columns_structure: Union[str, List[Any]], transformations_list: List[Dict[str, Any]]) -> Union[str, List[Any]]:
    """Recursively updates column names in simple or nested list structures."""
    if isinstance(columns_structure, str):
        # _get_transformed_column_name now returns Union[str, List[str]]
        return _get_transformed_column_name(columns_structure, transformations_list)
    elif isinstance(columns_structure, list):
        updated_list = []
        for item in columns_structure:
            # result_from_transform can be str or List[str]
            result_from_transform = _update_column_names_recursively(item, transformations_list)
            if isinstance(result_from_transform, list):
                # Check if we're dealing with a nested structure (dual-axis format)
                # If the original item was a list, preserve the structure by appending the result as a list
                # If the original item was a string, then extend to flatten single-level transformations
                if isinstance(item, list):
                    updated_list.append(result_from_transform)  # Preserve nested structure for dual-axis
                else:
                    updated_list.extend(result_from_transform)  # Flatten for single-level transformations
            else:
                updated_list.append(result_from_transform) # Append if str (or other non-list item)
        return updated_list
    else:
        # For any other type, return as is
        return columns_structure

def extract_codes_from_config(chart_configs):
    """
    Extracts all unique column codes from chart configurations.
    Also considers columns used in transformations if they are not primary plot columns.
    """
    all_codes = set()

    for config_id, config_entry in chart_configs.items():
        actual_chart_conf = config_entry.get("chart_config", config_entry)

        if "instruments" in actual_chart_conf:
            instruments = actual_chart_conf.get("instruments", [])
            for instrument in instruments:
                all_codes.add(instrument['id'])
        
        columns_for_plotting = actual_chart_conf.get("columns", [])
        if isinstance(columns_for_plotting, str):
            all_codes.add(columns_for_plotting)
        elif isinstance(columns_for_plotting, list):
            def _flatten_plot_cols(cols_struct):
                if isinstance(cols_struct, str):
                    all_codes.add(cols_struct)
                elif isinstance(cols_struct, list):
                    for item in cols_struct:
                        _flatten_plot_cols(item)
            _flatten_plot_cols(columns_for_plotting)

        transformations = config_entry.get("transformations", [])
        if transformations:
            for t_conf in transformations:
                if "column" in t_conf and isinstance(t_conf["column"], str):
                    all_codes.add(t_conf["column"])
                elif "base_column" in t_conf and "target_column" in t_conf:
                    if isinstance(t_conf["base_column"], str):
                        all_codes.add(t_conf["base_column"])
                    if isinstance(t_conf["target_column"], str):
                        all_codes.add(t_conf["target_column"])
                
    return list(all_codes)

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
