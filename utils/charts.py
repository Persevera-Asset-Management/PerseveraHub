import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Literal

def create_highcharts_options(
    data: pd.DataFrame,
    y_column: Union[str, List[str]],
    x_column: Optional[str] = None,
    chart_type: Literal['line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', 'areaspline', 'column', 'area'] = 'line',
    stacking: Optional[Literal['normal', 'percent']] = None,
    title: str = "",
    y_axis_title: str = "",
    series_name: Optional[Union[str, List[str]]] = None,
    color: Optional[Union[str, List[str]]] = None,
    point_markers: Optional[List[Dict[str, Any]]] = None,
    height: int = 400,
    line_width: int = 3,
    zoom_type: str = "x",
    animation: bool = False,
    decimal_precision: int = 2
) -> Dict[str, Any]:
    """
    Generate Highcharts options for various chart types.
    
    Parameters:
    -----------
    data : pd.DataFrame
        DataFrame containing the data to be plotted
    y_column : str or List[str]
        Name(s) of the column(s) containing y-axis data. If a list is provided, multiple series will be created.
    x_column : str, optional
        Name of the column containing x-axis data (usually dates). If None, the DataFrame index is used.
    chart_type : str, optional
        Type of chart ('line', 'bar', 'column', 'area', 'scatter', 'pie', 'spline', etc.)
    stacking : str, optional
        Type of stacking ('normal', 'percent', or None for no stacking)
    title : str, optional
        Chart title
    y_axis_title : str, optional
        Y-axis title (defaults to concatenated y-column names if multiple)
    series_name : str or List[str], optional
        Name(s) of the data series (defaults to y_column if not provided)
    color : str or List[str], optional
        Color(s) of the series (if None, Highcharts default colors are used)
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
        
    Returns:
    --------
    Dict[str, Any]
        Highcharts configuration options
    """
    # Convert y_column to list if it's a string
    y_columns = [y_column] if isinstance(y_column, str) else y_column
    
    # Handle series_name, ensuring it's a list of the same length as y_columns
    if series_name is None:
        series_names = y_columns
    elif isinstance(series_name, str) and len(y_columns) == 1:
        series_names = [series_name]
    elif isinstance(series_name, list) and len(series_name) == len(y_columns):
        series_names = series_name
    else:
        # Default to y_column names if series_name doesn't match
        series_names = y_columns
    
    # Handle colors, ensuring it's a list of the same length as y_columns
    if color is None:
        colors = [None] * len(y_columns)  # Use Highcharts defaults
    elif isinstance(color, str) and len(y_columns) == 1:
        colors = [color]
    elif isinstance(color, list) and len(color) >= len(y_columns):
        colors = color[:len(y_columns)]  # Use the first n colors
    else:
        colors = [None] * len(y_columns)  # Use Highcharts defaults
    
    # Set default y-axis title if not provided
    if not y_axis_title and len(y_columns) > 1:
        y_axis_title = ", ".join(y_columns)
    elif not y_axis_title and len(y_columns) == 1:
        y_axis_title = y_columns[0]
    
    # Use the DataFrame index if x_column is not specified
    is_using_index = False
    if x_column is None:
        is_using_index = True
        # Create a temporary column from the index
        temp_data = data.copy()
        temp_data['_index'] = temp_data.index
        x_column = '_index'
    else:
        temp_data = data
    
    # Determine if we're working with datetime data
    is_datetime = False
    if is_using_index and isinstance(temp_data.index, pd.DatetimeIndex):
        is_datetime = True
        x_label = None
    elif not is_using_index and pd.api.types.is_datetime64_any_dtype(temp_data[x_column]):
        is_datetime = True
        x_label = x_column
    else:
        if chart_type == 'pie':
            x_axis_type = None
            x_label = None
        elif chart_type in ['bar', 'column'] and not is_datetime:
            x_axis_type = 'category'
            x_label = x_column
        else:
            x_axis_type = 'linear'
            x_label = x_column
    
    # Set x-axis type based on data type
    if is_datetime:
        x_axis_type = 'datetime'
    elif chart_type == 'pie':
        x_axis_type = None
    elif chart_type in ['bar', 'column']:
        x_axis_type = 'category'
    else:
        x_axis_type = 'linear'
    
    # Create base chart options
    chart_options = {
        "chart": {
            "type": chart_type,
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
                "text": x_label
            }
        }
        
        chart_options["yAxis"] = {
            "title": {
                "text": y_axis_title
            }
        }
        
        chart_options["tooltip"] = {
            "shared": True,
            "crosshairs": True
        }
        
        # Add date formats for datetime x-axis
        if x_axis_type == 'datetime':
            chart_options["tooltip"]["dateTimeLabelFormats"] = {
                "day": "%Y-%m-%d",
                "month": "%B %Y"
            }
        
        # Set up series for non-pie charts
        chart_options["series"] = []
        
        for i, (y_col, series_name, color_val) in enumerate(zip(y_columns, series_names, colors)):
            # Prepare data for this series
            series_data = []
            for idx, row in temp_data.iterrows():
                # Handle x value based on data type
                if is_using_index and isinstance(temp_data.index, pd.DatetimeIndex):
                    x_value = int(pd.Timestamp(idx).timestamp() * 1000)
                elif pd.api.types.is_datetime64_any_dtype(temp_data[x_column]):
                    x_value = int(row[x_column].timestamp() * 1000)
                else:
                    x_value = row[x_column]
                
                # Only add points where y_value is not null
                if pd.notna(row[y_col]):
                    series_data.append([x_value, float(row[y_col])])
            
            # Create series options
            series_options = {
                "name": series_name,
                "data": series_data,
                "tooltip": {
                    "valueDecimals": decimal_precision
                }
            }
            
            # Add color if specified
            if color_val:
                series_options["color"] = color_val
            
            # Add line width for line-type charts
            if chart_type in ['line', 'spline']:
                series_options["lineWidth"] = line_width
                series_options["marker"] = {
                    "enabled": False
                }
            
            chart_options["series"].append(series_options)
        
        # Add stacking if specified
        if stacking and chart_type in ['column', 'bar', 'area', 'areaspline']:
            chart_options["plotOptions"][chart_type] = {
                "stacking": stacking
            }
    else:
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
        # Use only the first y_column for pie charts
        y_col = y_columns[0]
        
        for idx, row in temp_data.iterrows():
            name = str(row[x_column]) if x_column in row else str(idx)
            if pd.notna(row[y_col]):
                pie_data.append({
                    "name": name,
                    "y": float(row[y_col])
                })
        
        chart_options["series"] = [{
            "name": series_names[0],
            "colorByPoint": True,
            "data": pie_data
        }]
        
        # Add color if specified (for pie charts, this is handled differently)
        if color and isinstance(color, list) and len(color) > 0:
            chart_options["colors"] = color
        elif color and isinstance(color, str):
            chart_options["colors"] = [color]  # This will be the first color in the palette
    
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
    marker_symbol: str = "circle"
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
    
    return marker_series


# Maintain backward compatibility
prepare_meeting_markers = prepare_point_markers 