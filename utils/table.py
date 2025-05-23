import pandas as pd
from pandas.io.formats.style import Styler
from typing import List, Dict, Any, Optional, Union, Tuple, Literal

def style_table(
    df: pd.DataFrame,
    percent_cols: Optional[List[str]] = None,
    rank_cols_identifier: Optional[str] = None, # e.g., 'rank' to identify columns like 'rank_A', 'rank_B'
    numeric_cols_format_as_int: Optional[List[str]] = None, # Columns to be formatted as integers with thousands separator
    numeric_cols_format_as_float: Optional[List[str]] = None, # Columns to be formatted as floats with 2 decimal places
    currency_cols: Optional[List[str]] = None, # Columns to be formatted as currency (integers with thousands separator)
    highlight_row_by_column: Optional[str] = None,
    highlight_row_if_value_equals: Optional[Any] = None,
    highlight_color: str = 'lightblue',
    left_align_cols: Optional[List[str]] = None,
    center_align_cols: Optional[List[str]] = None,
    right_align_cols: Optional[List[str]] = None
) -> Styler:
    """Applies generic styling to a DataFrame.
    Allows specifying columns for percentage formatting, 
    integer formatting (with thousands separators), 
    float formatting (to 2 decimal places), 
    and currency-style formatting (integers with thousands separators).
    Allows conditional row highlighting and custom alignment for specified columns.
    """
    df_styled = df.copy()
    formatters = {}

    # Percentage formatting
    if percent_cols:
        for col in percent_cols:
            if col in df_styled.columns:
                formatters[col] = "{:.2f}%"

    # Integer formatting for identified rank columns (no comma, typically for ranks)
    actual_rank_cols = []
    if rank_cols_identifier:
        actual_rank_cols = [col for col in df_styled.columns if rank_cols_identifier in col]
        for col in actual_rank_cols:
            if col in df_styled.columns:
                formatters[col] = "{:.0f}" # Simple integer, no comma for ranks
    
    # Integer formatting with thousands separator
    if numeric_cols_format_as_int:
        for col in numeric_cols_format_as_int:
            if col in df_styled.columns and col not in formatters: # Avoid double-formatting
                 formatters[col] = "{:,.0f}"

    # Float formatting (2 decimal places)
    if numeric_cols_format_as_float:
        for col in numeric_cols_format_as_float:
            if col in df_styled.columns and col not in formatters: # Avoid double-formatting if also a rank col
                formatters[col] = "{:,.2f}"

    # Currency formatting (e.g., with thousands separator)
    if currency_cols:
        for col in currency_cols:
            if col in df_styled.columns:
                formatters[col] = "{:,.0f}"

    styled_obj = df_styled.style.format(formatters)

    # Conditional row highlighting
    if highlight_row_by_column and highlight_row_if_value_equals is not None and highlight_row_by_column in df_styled.columns:
        def highlight_matching_rows(row):
            color_to_apply = f'background-color: {highlight_color}' if row[highlight_row_by_column] == highlight_row_if_value_equals else ''
            return [color_to_apply] * len(row)
        styled_obj = styled_obj.apply(highlight_matching_rows, axis=1)

    alignment_styles = []
    
    # Default: Left-align index (row headers)
    alignment_styles.append({'selector': 'th.row_heading', 'props': [('text-align', 'left')]})

    # Apply alignments based on explicit lists or derived column types
    processed_for_alignment = set()

    if left_align_cols:
        for col_name in left_align_cols:
            if col_name in df_styled.columns and col_name not in processed_for_alignment:
                alignment_styles.append({'selector': f'td.col-{df_styled.columns.get_loc(col_name)}', 'props': [('text-align', 'left')]})
                processed_for_alignment.add(col_name)
    
    # Center alignment:
    # - Explicitly centered columns
    # - Rank columns (if identifier provided)
    # - Column used for highlighting (if active)
    cols_to_center = set(center_align_cols or [])
    if rank_cols_identifier:
        cols_to_center.update(actual_rank_cols)
    if highlight_row_by_column and highlight_row_if_value_equals is not None:
        cols_to_center.add(highlight_row_by_column)
        
    for col_name in cols_to_center:
        if col_name in df_styled.columns and col_name not in processed_for_alignment:
            alignment_styles.append({'selector': f'td.col-{df_styled.columns.get_loc(col_name)}', 'props': [('text-align', 'center')]})
            processed_for_alignment.add(col_name)

    # Right alignment:
    # - Explicitly right-aligned columns
    # - Percentage columns
    # - Currency columns
    cols_to_right_align = set(right_align_cols or [])
    if percent_cols:
        cols_to_right_align.update(percent_cols)
    if currency_cols:
        cols_to_right_align.update(currency_cols)

    for col_name in cols_to_right_align:
        if col_name in df_styled.columns and col_name not in processed_for_alignment:
            alignment_styles.append({'selector': f'td.col-{df_styled.columns.get_loc(col_name)}', 'props': [('text-align', 'right')]})
            processed_for_alignment.add(col_name)
            
    styled_obj = styled_obj.set_table_styles(alignment_styles, overwrite=False)

    return styled_obj
