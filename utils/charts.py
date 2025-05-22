import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Literal

def create_highcharts_options(
    data: pd.DataFrame,
    y_column: Union[str, List[str], Tuple[str, str], Tuple[List[str], List[str]]],
    x_column: Optional[str] = None,
    chart_type: Literal['line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', 'areaspline', 'dual_axis_line', 'dual_axis_line_area'] = 'line',
    stacking: Optional[Literal['normal', 'percent']] = None,
    title: str = "",
    y_axis_title: Union[str, Tuple[str, str]] = "",
    x_axis_title: Optional[str] = None,
    series_name: Optional[Union[str, List[str], Tuple[Optional[Union[str, List[Optional[str]]]], Optional[Union[str, List[Optional[str]]]]]]] = None,
    color: Optional[Union[str, List[str], Tuple[Optional[Union[str, List[Optional[str]]]], Optional[Union[str, List[Optional[str]]]]]]] = None,
    point_markers: Optional[List[Dict[str, Any]]] = None,
    height: int = 400,
    line_width: int = 3,
    zoom_type: str = "x",
    animation: bool = False,
    decimal_precision: int = 2,
    point_name_column: Optional[str] = None,
    tooltip_point_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate Highcharts options for various chart types.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the data to be plotted
    y_column : str or List[str] or Tuple[str, str] or Tuple[List[str], List[str]]
        Name(s) of the column(s) containing y-axis data. 
        - For single-axis charts: a string or a list of strings.
        - For 'dual_axis_line' or 'dual_axis_line_area': 
            - Tuple[str, str] for one series per axis (e.g., ('col_L', 'col_R')).
            - Tuple[List[str], List[str]] for potentially multiple series per axis (e.g., (['col_L1'], ['col_R1', 'col_R2'])).
    x_column : str, optional
        Name of the column containing x-axis data (usually dates). If None, the DataFrame index is used.
    chart_type : str, optional
        Type of chart ('line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', etc.)
    stacking : str, optional
        Type of stacking ('normal', 'percent', or None for no stacking)
    title : str, optional
        Chart title
    y_axis_title : str or Tuple[str, str], optional
        Y-axis title. For 'dual_axis_line' or 'dual_axis_line_area', this must be a Tuple[str, str] (e.g., ('Title Left', 'Title Right')). 
        For single-axis charts, a string. Defaults to concatenated y-column names if multiple y-columns on a single axis.
    x_axis_title : str, optional
        X-axis title. Defaults to x_column name if not provided, or None if x_column is also None.
    series_name : str or List[str] or Tuple, optional
        Name(s) of the data series.
        - For single-axis charts: a string (if one y_column) or a list of strings (matching y_columns). Defaults to y_column names.
        - For 'dual_axis_line' or 'dual_axis_line_area': A tuple of two elements, e.g., (config_ax1, config_ax2).
          Each config_axN can be None (use column names), a string (if axis N has 1 series), or a List[Optional[str]] (for multiple series on axis N).
          Example: (['Name L1'], ['Name R1', None])
    color : str or List[str] or Tuple, optional
        Color(s) of the series.
        - For single-axis charts: a string or a list of strings.
        - For 'dual_axis_line' or 'dual_axis_line_area': Similar structure to series_name, e.g., (config_ax1_color, config_ax2_color).
          Each config_axN_color can be None (use Highcharts default), a string (if axis N has 1 series), or a List[Optional[str]].
          Example: (['blue'], [None, 'green'])
    point_markers : List[Dict], optional
        Additional point markers to overlay on the chart (e.g., for meetings)
    height : int, optional
        Chart height in pixels
    line_width : int, optional
        Width of the line in the main series (applies to line charts)
    zoom_type : str, optional
        Type of zoom ('x', 'y', or 'xy')
    animation : bool, optional
        Whether to enable animations
    decimal_precision : int, optional
        Number of decimal places in tooltips
    point_name_column : str, optional
        Column to use for individual point names, especially for scatter charts.
    tooltip_point_format : str, optional
        Custom HTML string format for the tooltip's point display.
        
    Returns:
    --------
    Dict[str, Any]
        Highcharts configuration options
    """
    is_dual_axis = chart_type in ['dual_axis_line', 'dual_axis_line_area']

    # Variables for processed parameters - will be populated based on chart type
    y_cols_for_single_axis: List[str]
    s_names_for_single_axis: List[str]
    colors_for_single_axis: List[Optional[str]]
    y_axis_title_processed: Union[str, Tuple[str,str]] # Can be str or Tuple[str,str]

    # Specific parameter handling for dual_axis_line
    if is_dual_axis:
        y_cols_list_ax1: List[str]
        y_cols_list_ax2: List[str]
        series_names_processed_ax1: List[str]
        series_names_processed_ax2: List[str]
        colors_processed_ax1: List[Optional[str]]
        colors_processed_ax2: List[Optional[str]]

        # Pattern 1: New format (recommended) - (['L1', 'L2'], ['R1'])
        if (isinstance(y_column, (list, tuple)) and len(y_column) == 2 and
            isinstance(y_column[0], list) and all(isinstance(s, str) for s in y_column[0]) and len(y_column[0]) > 0 and
            isinstance(y_column[1], list) and all(isinstance(s, str) for s in y_column[1]) and len(y_column[1]) > 0):
            y_cols_list_ax1 = y_column[0]
            y_cols_list_ax2 = y_column[1]
        else:
            # Try to adapt from old formats
            temp_processed_y = y_column
            if (isinstance(y_column, list) and len(y_column) == 1 and # Handles case like y_column=[('colA', 'colB')]
                    isinstance(y_column[0], tuple) and len(y_column[0]) == 2 and
                    all(isinstance(s, str) for s in y_column[0])):
                temp_processed_y = y_column[0]  # Unwrapped from [('L', 'R')] to ('L', 'R')

            # Pattern 2: Old format - ('L', 'R') or ['L', 'R'] for one series per axis
            if (isinstance(temp_processed_y, (list, tuple)) and len(temp_processed_y) == 2 and
                    all(isinstance(s, str) for s in temp_processed_y)):
                y_cols_list_ax1 = [temp_processed_y[0]] # Convert to list of one string
                y_cols_list_ax2 = [temp_processed_y[1]] # Convert to list of one string
            else:
                raise ValueError(
                    f"For dual-axis charts (e.g., 'dual_axis_line', 'dual_axis_line_area'), y_column must be a tuple/list of two non-empty lists of strings (e.g., (['col_L1'], ['col_R1', 'col_R2'])) "
                    "or a tuple/list of two strings for single series per axis (e.g., ('col_L', 'col_R')). "
                    f"Received: {y_column}"
                )
        
        # --- Parse y_axis_title for dual_axis_line ---
        if not (isinstance(y_axis_title, (list, tuple)) and len(y_axis_title) == 2 and all(isinstance(yt, str) for yt in y_axis_title)):
            raise ValueError(f"For dual-axis charts (e.g., 'dual_axis_line', 'dual_axis_line_area'), y_axis_title must be a tuple/list of two strings.")
        y_title_ax1, y_title_ax2 = y_axis_title[0], y_axis_title[1]
        y_axis_title_processed = (y_title_ax1, y_title_ax2) # y_axis_title_processed is Tuple[str,str]

        # --- Parse series_name for dual_axis_line ---
        default_s_names_ax1 = list(y_cols_list_ax1)
        default_s_names_ax2 = list(y_cols_list_ax2)

        if series_name is None:
            series_names_processed_ax1 = default_s_names_ax1
            series_names_processed_ax2 = default_s_names_ax2
        else:
            if not (isinstance(series_name, (list, tuple)) and len(series_name) == 2):
                raise ValueError(
                    f"For dual-axis charts (e.g., 'dual_axis_line', 'dual_axis_line_area') with series_name, it must be a tuple/list of two elements (one for each axis). "
                    f"Received: {series_name}"
                )
            
            s_name_config_ax1, s_name_config_ax2 = series_name[0], series_name[1]

            # Process axis 1 series names
            if s_name_config_ax1 is None:
                series_names_processed_ax1 = default_s_names_ax1
            elif isinstance(s_name_config_ax1, str):
                if len(y_cols_list_ax1) == 1:
                    series_names_processed_ax1 = [s_name_config_ax1]
                else:
                    raise ValueError(
                        f"For dual-axis chart axis 1, series_name was a string ('{s_name_config_ax1}') but there are "
                        f"{len(y_cols_list_ax1)} series. Provide a list of names, or None for defaults."
                    )
            elif isinstance(s_name_config_ax1, list):
                if len(s_name_config_ax1) != len(y_cols_list_ax1):
                    raise ValueError(
                        f"For dual-axis chart axis 1, series_name list length ({len(s_name_config_ax1)}) does not match "
                        f"number of y-columns ({len(y_cols_list_ax1)})."
                    )
                series_names_processed_ax1 = [name if name is not None else default_s_names_ax1[i] for i, name in enumerate(s_name_config_ax1)]
            else:
                raise ValueError(
                    f"For dual-axis chart axis 1, series_name config must be None, a string (for single series), or a list. "
                    f"Got: {s_name_config_ax1}"
                )

            # Process axis 2 series names
            if s_name_config_ax2 is None:
                series_names_processed_ax2 = default_s_names_ax2
            elif isinstance(s_name_config_ax2, str):
                if len(y_cols_list_ax2) == 1:
                    series_names_processed_ax2 = [s_name_config_ax2]
                else:
                    raise ValueError(
                        f"For dual-axis chart axis 2, series_name was a string ('{s_name_config_ax2}') but there are "
                        f"{len(y_cols_list_ax2)} series. Provide a list of names, or None for defaults."
                    )
            elif isinstance(s_name_config_ax2, list):
                if len(s_name_config_ax2) != len(y_cols_list_ax2):
                    raise ValueError(
                        f"For dual-axis chart axis 2, series_name list length ({len(s_name_config_ax2)}) does not match "
                        f"number of y-columns ({len(y_cols_list_ax2)})."
                    )
                series_names_processed_ax2 = [name if name is not None else default_s_names_ax2[i] for i, name in enumerate(s_name_config_ax2)]
            else:
                raise ValueError(
                    f"For dual-axis chart axis 2, series_name config must be None, a string (for single series), or a list. "
                    f"Got: {s_name_config_ax2}"
                )
        
        # --- Parse color for dual_axis_line ---
        colors_processed_ax1 = [None] * len(y_cols_list_ax1)
        colors_processed_ax2 = [None] * len(y_cols_list_ax2)

        if color is not None:
            if not (isinstance(color, (list, tuple)) and len(color) == 2):
                raise ValueError(
                    f"For dual-axis charts (e.g., 'dual_axis_line', 'dual_axis_line_area') with color, it must be a tuple/list of two elements (one for each axis). "
                    f"Received: {color}"
                )
            
            color_config_ax1, color_config_ax2 = color[0], color[1]

            # Process axis 1 colors
            if color_config_ax1 is not None:
                if isinstance(color_config_ax1, str):
                    if len(y_cols_list_ax1) == 1:
                        colors_processed_ax1 = [color_config_ax1]
                    # Removed the strict error for single color string with multiple series on an axis.
                    # Behavior: if one color string for an axis with multiple series, it applies to the first series. Others get None.
                    # For applying to all, user should provide a list: [color_str] * num_series or [color_str, color_str, ...]
                    elif len(y_cols_list_ax1) > 1:
                         colors_processed_ax1[0] = color_config_ax1 # Apply to first, rest remain None
                elif isinstance(color_config_ax1, list):
                    if len(color_config_ax1) != len(y_cols_list_ax1):
                        raise ValueError(
                            f"For dual-axis chart axis 1, color list length ({len(color_config_ax1)}) does not match "
                            f"number of y-columns ({len(y_cols_list_ax1)})."
                        )
                    colors_processed_ax1 = [c_val if isinstance(c_val, str) or c_val is None else str(c_val) for c_val in color_config_ax1]
                else:
                    raise ValueError(
                        f"For dual-axis chart axis 1, color config must be None, a string, or a list. "
                        f"Got: {color_config_ax1}"
                    )

            # Process axis 2 colors
            if color_config_ax2 is not None:
                if isinstance(color_config_ax2, str):
                    if len(y_cols_list_ax2) == 1:
                        colors_processed_ax2 = [color_config_ax2]
                    elif len(y_cols_list_ax2) > 1:
                        colors_processed_ax2[0] = color_config_ax2 # Apply to first, rest remain None
                elif isinstance(color_config_ax2, list):
                    if len(color_config_ax2) != len(y_cols_list_ax2):
                        raise ValueError(
                            f"For dual-axis chart axis 2, color list length ({len(color_config_ax2)}) does not match "
                            f"number of y-columns ({len(y_cols_list_ax2)})."
                        )
                    colors_processed_ax2 = [c_val if isinstance(c_val, str) or c_val is None else str(c_val) for c_val in color_config_ax2]
                else:
                    raise ValueError(
                        f"For dual-axis chart axis 2, color config must be None, a string, or a list. "
                        f"Got: {color_config_ax2}"
                    )

    else: # Existing logic for single axis or pie charts
        # Ensure y_column is List[str] for single axis processing below
        # This part handles 'str' or 'List[str]' for y_column for non-dual-axis charts.
        if isinstance(y_column, str):
            y_cols_for_single_axis = [y_column]
        elif isinstance(y_column, list) and all(isinstance(yc_item, str) for yc_item in y_column):
            y_cols_for_single_axis = y_column
        # If y_column is Tuple[str,str] or Tuple[List[str],List[str]] and not dual_axis_line, it's an error.
        elif isinstance(y_column, (tuple, list)) and not is_dual_axis: 
             raise ValueError(f"Invalid y_column format '{y_column}' for chart_type '{chart_type}'. Expected str or List[str].")
        else: # Fallback, though should be covered by specific checks
            raise ValueError(f"Unsupported y_column format: {y_column} for chart_type '{chart_type}'.")
        
        if series_name is None:
            s_names_for_single_axis = y_cols_for_single_axis
        elif isinstance(series_name, str) and len(y_cols_for_single_axis) == 1:
            s_names_for_single_axis = [series_name]
        elif isinstance(series_name, list) and len(series_name) == len(y_cols_for_single_axis) and all(isinstance(sn, str) for sn in series_name):
            s_names_for_single_axis = series_name
        # If series_name is a tuple (meant for dual_axis) but chart is not dual_axis, it's an error or needs specific handling.
        elif isinstance(series_name, (tuple,list)) and len(y_cols_for_single_axis) > 0: # Check if series_name can be adapted if it's a list of strings
             if all(isinstance(sn_item, str) for sn_item in series_name) and len(series_name) == len(y_cols_for_single_axis):
                 s_names_for_single_axis = series_name
             else:
                s_names_for_single_axis = y_cols_for_single_axis # Default if format is unexpected for single axis
        else:
            s_names_for_single_axis = y_cols_for_single_axis
        
        if color is None:
            colors_for_single_axis = [None] * len(y_cols_for_single_axis)
        elif isinstance(color, str) and len(y_cols_for_single_axis) == 1:
            colors_for_single_axis = [color]
        elif isinstance(color, list) and all(isinstance(c, (str, type(None))) for c in color) and len(color) >= len(y_cols_for_single_axis):
            colors_for_single_axis = color[:len(y_cols_for_single_axis)]
        # If color is a tuple (meant for dual_axis) but chart is not dual_axis, it's an error or needs specific handling.
        elif isinstance(color, (tuple,list)) and len(y_cols_for_single_axis) > 0: # Check if color can be adapted if it's a list
            if all(isinstance(c_item, (str, type(None))) for c_item in color) and len(color) >= len(y_cols_for_single_axis):
                colors_for_single_axis = color[:len(y_cols_for_single_axis)]
            else:
                colors_for_single_axis = [None] * len(y_cols_for_single_axis) # Default
        else:
            colors_for_single_axis = [None] * len(y_cols_for_single_axis)
        
        # y_axis_title for single axis charts
        current_y_axis_title = ""
        if isinstance(y_axis_title, str): # Should always be str if not dual_axis_line
             current_y_axis_title = y_axis_title
        elif isinstance(y_axis_title, tuple) and not is_dual_axis: # y_axis_title was a tuple, but not dual_axis
            raise ValueError(f"y_axis_title must be a string for chart_type '{chart_type}'. Got: {y_axis_title}")
        
        if not current_y_axis_title and len(y_cols_for_single_axis) > 1:
            y_axis_title_processed = ", ".join(y_cols_for_single_axis)
        elif not current_y_axis_title and len(y_cols_for_single_axis) == 1:
            y_axis_title_processed = y_cols_for_single_axis[0]
        else:
            y_axis_title_processed = current_y_axis_title # y_axis_title_processed is str

    # Use the DataFrame index if x_column is not specified
    is_using_index = False
    x_column_effective: str
    if x_column is None:
        is_using_index = True
        # Create a temporary column from the index
        temp_data = data.copy()
        temp_data['_index'] = temp_data.index
        x_column_effective = '_index'
    else:
        temp_data = data
        x_column_effective = x_column
    
    # Determine if we're working with datetime data
    is_datetime = False
    x_label: Optional[str] = None # Initialize x_label

    if is_using_index and isinstance(temp_data.index, pd.DatetimeIndex):
        is_datetime = True
        x_label = None 
    elif not is_using_index and pd.api.types.is_datetime64_any_dtype(temp_data[x_column_effective]):
        is_datetime = True
        x_label = x_column_effective
    else: # Not datetime
        if chart_type == 'pie':
            x_label = None
        elif chart_type in ['bar', 'column']: # Category axis type for non-datetime bar/column
            x_label = x_column_effective
        else: # Linear axis for other types like line, scatter, area, dual_axis_line
            x_label = x_column_effective
            
    # Use provided x_axis_title if available, otherwise use the derived x_label
    final_x_axis_title = x_axis_title if x_axis_title is not None else x_label

    # Set x-axis type based on data type and chart type
    x_axis_type: Optional[str]
    if is_datetime:
        x_axis_type = 'datetime'
    elif chart_type == 'pie':
        x_axis_type = None
    elif chart_type in ['bar', 'column']: # Ensure this only applies if not datetime
        x_axis_type = 'category'
    else: # Covers 'line', 'scatter', 'area', 'spline', 'dual_axis_line', 'dual_axis_line_area', etc.
        x_axis_type = 'linear'
    
    # Create base chart options
    chart_options = {
        "chart": {
            "type": chart_type if not is_dual_axis else 'line', # dual_axis is effectively multiple line/area series on a base 'line' chart
            "zoomType": zoom_type if chart_type != 'pie' else None,
            "resetZoomButton": {
                "position": {
                    "align": "right",
                    "verticalAlign": "top",
                    "x": -10,
                    "y": 10
                }
            } if chart_type != 'pie' else None,
            "height": height
        },
        "title": {
            "text": title
        },
        "legend": {
            "enabled": True
        },
        "credits": {
            "enabled": False
        },
        "plotOptions": {
            "series": {
                "animation": animation
            }
        }
    }
    
    # Add chart-type specific options
    if chart_type != 'pie':
        chart_options["xAxis"] = {
            "type": x_axis_type,
            "title": {
                "text": final_x_axis_title
            }
        }
        
        if is_dual_axis:
            # y_axis_title_processed is Tuple[str, str] here, as set in the dual_axis_line block
            title_ax1, title_ax2 = y_axis_title_processed 
            chart_options["yAxis"] = [
                { # Primary yAxis
                    "title": {"text": title_ax1},
                    "labels": {"format": "{value}"}, 
                },
                { # Secondary yAxis
                    "title": {"text": title_ax2},
                    "labels": {"format": "{value}"}, 
                    "opposite": True
                }
            ]
        else: # Single y-axis configuration
            # y_axis_title_processed is a string here, as set in the single-axis block
            chart_options["yAxis"] = {
                "title": {
                    "text": str(y_axis_title_processed)
                }
            }
        
        chart_options["tooltip"] = {
            "shared": True if chart_type != 'scatter' else False, # Scatter usually has non-shared tooltips
            "crosshairs": True
        }
        
        # Add date formats for datetime x-axis
        if x_axis_type == 'datetime':
            chart_options["tooltip"]["dateTimeLabelFormats"] = {
                "day": "%Y-%m-%d",
                "month": "%B %Y"
            }
        
        # Apply custom tooltip point format if provided
        if tooltip_point_format:
            chart_options["tooltip"]["pointFormat"] = tooltip_point_format
        elif chart_type != 'scatter': # Default pointFormat if not scatter and no custom one
            chart_options["tooltip"]["pointFormat"] = '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b><br/>'
        
        # Set up series
        chart_options["series"] = []

        def _prepare_series_data_points(y_col_for_series: str) -> List[Union[List[Union[int, float, str]], Dict[str, Union[int, float, str]]]]: # Allow dict for scatter points
            _s_data = []
            for _idx, _row in temp_data.iterrows():
                _x_val: Union[int, float, str]
                if is_using_index and isinstance(temp_data.index, pd.DatetimeIndex):
                    _x_val = int(pd.Timestamp(_idx).timestamp() * 1000)
                elif not is_using_index and pd.api.types.is_datetime64_any_dtype(temp_data[x_column_effective]):
                    _x_val = int(_row[x_column_effective].timestamp() * 1000)
                elif x_axis_type == 'category': # For category axis, x_value should be the category name
                    _x_val = str(_row[x_column_effective]) if x_column_effective in _row else str(_idx)
                else: # Linear axis
                    _x_val = _row[x_column_effective]
                
                if pd.notna(_row[y_col_for_series]):
                    if chart_type == 'scatter' and point_name_column and point_name_column in _row:
                        _s_data.append({
                            "x": float(_x_val) if isinstance(_x_val, (int, float, str)) and str(_x_val).replace('.', '', 1).isdigit() else _x_val, # ensure numeric for scatter x
                            "y": float(_row[y_col_for_series]),
                            "name": str(_row[point_name_column])
                        })
                    else:
                        _s_data.append([_x_val, float(_row[y_col_for_series])])
            return _s_data

        if is_dual_axis:
            # Loop for Axis 0 series (Primary Y-Axis)
            for i, y_col_ax1 in enumerate(y_cols_list_ax1):
                data_s = _prepare_series_data_points(y_col_ax1)
                s_opts = {
                    "name": series_names_processed_ax1[i],
                    "data": data_s, 
                    "type": "line", 
                    "yAxis": 0,
                    "tooltip": {"valueDecimals": decimal_precision},
                    "lineWidth": line_width, 
                    "marker": {"enabled": False}
                }
                if colors_processed_ax1[i]: 
                    s_opts["color"] = colors_processed_ax1[i]
                chart_options["series"].append(s_opts)

            # Loop for Axis 1 series (Secondary Y-Axis)
            for i, y_col_ax2 in enumerate(y_cols_list_ax2):
                data_s = _prepare_series_data_points(y_col_ax2)
                s_opts = {
                    "name": series_names_processed_ax2[i],
                    "data": data_s, 
                    "type": "area" if chart_type == 'dual_axis_line_area' else "line", 
                    "yAxis": 1,
                    "tooltip": {"valueDecimals": decimal_precision},
                    "lineWidth": line_width, 
                    "marker": {"enabled": False}
                }
                if colors_processed_ax2[i]: 
                    s_opts["color"] = colors_processed_ax2[i]
                chart_options["series"].append(s_opts)

        else: # Existing loop for single-axis, non-pie charts
            for i, (y_col, series_name_val, color_val) in enumerate(zip(y_cols_for_single_axis, s_names_for_single_axis, colors_for_single_axis)):
                series_data = _prepare_series_data_points(y_col)
            
                # Create series options
                series_options = {
                    "name": series_name_val,
                    "data": series_data,
                    "tooltip": {
                        "valueDecimals": decimal_precision
                    }
                }
            
                # Add color if specified
                if color_val:
                    series_options["color"] = color_val
            
                # Add line width for line-type charts
                # Note: For single axis, chart_type is directly used. For dual_axis_line, type is fixed to 'line'.
                if chart_options["chart"]["type"] in ['line', 'spline']:
                    series_options["lineWidth"] = line_width
                    series_options["marker"] = {
                        "enabled": False
                    }
                # For other chart types like 'bar', 'column', 'area', these are not set here by default
                # but rely on the main chart_type setting.
                
                chart_options["series"].append(series_options)
        
        # Add stacking if specified (not for dual_axis_line or pie)
        # For dual_axis_line, stacking is not applicable as series are on different axes.
        effective_chart_type_for_stacking = chart_options["chart"]["type"]
        if stacking and effective_chart_type_for_stacking in ['column', 'bar', 'area', 'areaspline']:
            # Ensure plotOptions and chart_type key exist before assigning stacking
            if effective_chart_type_for_stacking not in chart_options["plotOptions"]:
                 chart_options["plotOptions"][effective_chart_type_for_stacking] = {}
            elif not isinstance(chart_options["plotOptions"][effective_chart_type_for_stacking], dict) : # Make sure it's a dict
                 chart_options["plotOptions"][effective_chart_type_for_stacking] = {}

            chart_options["plotOptions"][effective_chart_type_for_stacking]["stacking"] = stacking
    else: # Pie chart logic
        # Pie chart specific options
        chart_options["plotOptions"]["pie"] = {
            "allowPointSelect": True,
            "cursor": "pointer",
            "dataLabels": {
                "enabled": True,
                "format": "<b>{point.name}</b>: {point.percentage:.1f} %"
            }
        }
        
        # Prepare pie chart data
        pie_data = []
        # Use only the first y_column for pie charts (from y_cols_for_single_axis)
        y_col_pie = y_cols_for_single_axis[0]
        
        for idx, row in temp_data.iterrows():
            name = str(row[x_column_effective]) if x_column_effective in row and pd.notna(row[x_column_effective]) else str(idx)
            if pd.notna(row[y_col_pie]):
                pie_data.append({
                    "name": name,
                    "y": float(row[y_col_pie])
                })
        
        chart_options["series"] = [{
            "name": s_names_for_single_axis[0], # Use first series name for pie
            "colorByPoint": True,
            "data": pie_data
        }]
        
        # Add color if specified (for pie charts, this is handled differently)
        # colors_for_single_axis would contain the list of colors if provided for single axis pie.
        if colors_for_single_axis and any(c is not None for c in colors_for_single_axis):
            # Use the list of colors if provided. Highcharts pie uses 'colors' array at root.
            chart_options["colors"] = [c for c in colors_for_single_axis if c is not None]
            if not chart_options["colors"]: # If all were None, remove empty list
                del chart_options["colors"]
        elif isinstance(color, str): # A single color string might have been passed
             chart_options["colors"] = [color]

    # Add additional point marker series if provided (not for pie charts)
    if point_markers and chart_type != 'pie':
        for marker in point_markers:
            chart_options["series"].append(marker)
    
    return chart_options


def prepare_point_markers(
    data: pd.DataFrame,
    filter_column: str,
    filter_value: Any,
    date_column: str,
    value_column: str,
    marker_name: str = "Points",
    marker_color: str = "red",
    marker_radius: int = 6,
    marker_symbol: str = "circle",
    y_axis_index: Optional[int] = None
) -> Dict[str, Any]:
    """
    Prepares a marker series for highlighting specific points on a chart.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the full dataset
    filter_column : str
        Column to filter on to find markers
    filter_value : Any
        Value to filter for (e.g., True for rows where some_flag=True)
    date_column : str
        Column containing x-axis values for markers (often dates)
    value_column : str
        Column containing y-values for markers
    marker_name : str, optional
        Name of the marker series
    marker_color : str, optional
        Color of the markers
    marker_radius : int, optional
        Size of the markers
    marker_symbol : str, optional
        Symbol to use for markers (circle, square, diamond, triangle, etc.)
    y_axis_index : int, optional
        For dual-axis charts, specifies which y-axis the markers should be linked to (0 for primary, 1 for secondary). 
        Defaults to None, which typically links to the primary axis.
        
    Returns:
    --------
    Dict[str, Any]
        Highcharts series configuration for markers, or None if no points match the filter
    """
    # Filter data for points
    marker_points = data[data[filter_column] == filter_value]
    
    if marker_points.empty:
        return None
    
    # Format data for Highcharts
    marker_data = []
    for idx, row in marker_points.iterrows():
        # Check if the date_column contains datetime objects
        if pd.api.types.is_datetime64_any_dtype(marker_points[date_column]):
            x_value = int(row[date_column].timestamp() * 1000)
        else:
            x_value = row[date_column]
        marker_data.append([x_value, float(row[value_column])])
    
    # Create marker series configuration
    marker_series = {
        "name": marker_name,
        "data": marker_data,
        "color": marker_color,
        "lineWidth": 0,
        "marker": {
            "enabled": True,
            "radius": marker_radius,
            "symbol": marker_symbol
        }
    }
    
    if y_axis_index is not None:
        marker_series["yAxis"] = y_axis_index
        
    return marker_series


# Maintain backward compatibility
prepare_meeting_markers = prepare_point_markers 