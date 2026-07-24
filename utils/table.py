import json
from collections import defaultdict

import pandas as pd
import numpy as np
from pandas.io.formats.style import Styler
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional, Union, Tuple, Literal


def style_table(
    df: pd.DataFrame,
    percent_cols: Optional[List[str]] = None,
    date_cols: Optional[List[str]] = None,
    date_format: str = '%Y-%m-%d',
    rank_cols_identifier: Optional[str] = None, # e.g., 'rank' to identify columns like 'rank_A', 'rank_B'
    numeric_cols_format_as_int: Optional[List[str]] = None, # Columns to be formatted as integers with thousands separator
    numeric_cols_format_as_float: Optional[List[str]] = None, # Columns to be formatted as floats with 2 decimal places
    currency_cols: Optional[List[str]] = None, # Columns to be formatted as currency (integers with thousands separator)
    highlight_row_by_column: Optional[str] = None,
    highlight_row_if_value_equals: Optional[Any] = None,
    highlight_color: str = 'lightblue',
    highlight_quartile: Optional[List[str]] = None,
    highlight_min_max_cols: Optional[List[str]] = None,
    highlight_row_if_value_lower: Optional[Dict[str, float]] = None,
    highlight_row_if_value_greater: Optional[Dict[str, float]] = None,
    color_negative_positive_cols: Optional[List[str]] = None,
    quartile_exclude_row_by_column: Optional[str] = None,
    quartile_exclude_row_if_value_is: Optional[List[Any]] = None,
    left_align_cols: Optional[List[str]] = None,
    center_align_cols: Optional[List[str]] = None,
    right_align_cols: Optional[List[str]] = None,
    column_names: Optional[List[str]] = None,
) -> Styler:
    """Applies generic styling to a DataFrame.
    Allows specifying columns for percentage formatting,
    integer formatting (with thousands separators), 
    float formatting (to 2 decimal places), 
    and currency-style formatting (integers with thousands separators).
    Allows conditional row highlighting, color-coding of columns by quartile, and custom alignment for specified columns. Quartile calculations can exclude specified rows.
    Optionally highlights lowest and highest values in specified columns.
    Supports threshold-based row highlighting (lower/greater) and coloring negative/positive values.
    """
    df_styled = df.copy()

    if column_names:
        if len(column_names) == len(df_styled.columns):
            df_styled.columns = column_names
            
    formatters = {}

    # Percentage formatting
    if percent_cols:
        for col in percent_cols:
            if col in df_styled.columns:
                formatters[col] = "{:.2f}%"

    # Date formatting
    if date_cols:
        for col in date_cols:
            if col in df_styled.columns:
                df_styled[col] = pd.to_datetime(df_styled[col], errors='coerce')
                formatters[col] = lambda x: x.strftime(date_format) if pd.notna(x) else ''

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

    # Force white cell backgrounds (Glide grid); highlights below override this
    styled_obj = styled_obj.set_properties(**{"background-color": "#ffffff"})

    # Conditional row highlighting
    if highlight_row_by_column and highlight_row_if_value_equals is not None and highlight_row_by_column in df_styled.columns:
        def highlight_matching_rows(row):
            color_to_apply = f'background-color: {highlight_color}' if row[highlight_row_by_column] == highlight_row_if_value_equals else ''
            return [color_to_apply] * len(row)
        styled_obj = styled_obj.apply(highlight_matching_rows, axis=1)

    # Quartile-based column coloring
    if highlight_quartile:
        def color_by_quartile(column):
            try:
                column_for_calc = column
                # Exclude specified rows from quartile calculation
                if quartile_exclude_row_by_column and \
                   quartile_exclude_row_if_value_is and \
                   quartile_exclude_row_by_column in df_styled.columns:
                    
                    exclusion_mask = df_styled[quartile_exclude_row_by_column].isin(quartile_exclude_row_if_value_is)
                    column_for_calc = column[~exclusion_mask]

                # Convert to numeric, coercing errors, and drop NaNs for quartile calculation
                numeric_col = pd.to_numeric(column_for_calc, errors='coerce').dropna()
                if numeric_col.empty:
                    return [''] * len(column)
                
                quartiles = pd.qcut(numeric_col, 4, labels=False, duplicates='drop')
                
                # Colors from a sequential palette (e.g., Yellow-Green-Blue from ColorBrewer)
                # Higher values get darker colors. For the darkest color, we switch text to white for readability.
                colors = {
                    0: 'background-color: #faf099',  # 1st quartile (lowest)
                    1: 'background-color: #cbe08c',  # 2nd quartile
                    2: 'background-color: #96ce7e',  # 3rd quartile
                    3: 'background-color: #66ba7b'   # 4th quartile (highest)
                }

                # Create a styled series with the same index as the original column
                # Map quartile labels to colors
                styled_column = quartiles.map(colors)
                
                # Reindex to match the original column's index (to handle NaNs) and fill missing with empty string
                return styled_column.reindex(column.index).fillna('')

            except ValueError:
                # This can happen if a column does not have enough unique values to create 4 quartiles.
                # In this case, we don't apply any color.
                return [''] * len(column)

        for col in highlight_quartile:
            if col in df_styled.columns:
                # The 'axis=0' is crucial for applying the function column-wise
                styled_obj = styled_obj.apply(color_by_quartile, subset=[col], axis=0)

    # Highlight min and max values in specified columns
    if highlight_min_max_cols:
        def highlight_extrema(column: pd.Series):
            numeric_column = pd.to_numeric(column, errors='coerce')
            if numeric_column.notna().sum() == 0:
                return [''] * len(column)
            min_value = numeric_column.min()
            max_value = numeric_column.max()
            styles: List[str] = []
            for value in numeric_column:
                if pd.isna(value):
                    styles.append('')
                elif value == min_value:
                    styles.append('background-color: #ffc7ce')  # light red
                elif value == max_value:
                    styles.append('background-color: #c6efce')  # light green
                else:
                    styles.append('')
            return styles

        for col in highlight_min_max_cols:
            if col in df_styled.columns:
                styled_obj = styled_obj.apply(highlight_extrema, subset=[col], axis=0)

    # Highlight rows where a column value is below a threshold
    if highlight_row_if_value_lower:
        for col, threshold in highlight_row_if_value_lower.items():
            if col in df_styled.columns:
                def _highlight_lower(row, _col=col, _threshold=threshold):
                    val = pd.to_numeric(row[_col], errors='coerce')
                    if pd.notna(val) and val < _threshold:
                        return ['background-color: #ffc7ce'] * len(row)
                    return [''] * len(row)
                styled_obj = styled_obj.apply(_highlight_lower, axis=1)

    # Highlight rows where a column value is above a threshold
    if highlight_row_if_value_greater:
        for col, threshold in highlight_row_if_value_greater.items():
            if col in df_styled.columns:
                def _highlight_greater(row, _col=col, _threshold=threshold):
                    val = pd.to_numeric(row[_col], errors='coerce')
                    if pd.notna(val) and val > _threshold:
                        return ['background-color: #c6efce'] * len(row)
                    return [''] * len(row)
                styled_obj = styled_obj.apply(_highlight_greater, axis=1)

    # Color negative values red and positive values green in specified columns
    if color_negative_positive_cols:
        def _color_neg_pos(column: pd.Series):
            numeric_col = pd.to_numeric(column, errors='coerce')
            return [
                'color: #d32f2f' if pd.notna(v) and v < 0
                else 'color: #2e7d32' if pd.notna(v) and v > 0
                else ''
                for v in numeric_col
            ]

        for col in color_negative_positive_cols:
            if col in df_styled.columns:
                styled_obj = styled_obj.apply(_color_neg_pos, subset=[col], axis=0)

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
    if date_cols:
        cols_to_center.update(date_cols)
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


# =============================================================================
# AgGrid variant of style_table
# =============================================================================
# Rendering a pandas.Styler via st.dataframe is slow for large tables because
# Streamlit must walk every single cell in Python to extract the display
# value/style (see streamlit#6340 / streamlit#10952). streamlit-aggrid avoids
# that: formatting and conditional coloring are compiled to small JS
# functions (`JsCode`) that AG Grid runs in the browser, only for the rows
# that are actually rendered (virtualized), so cost no longer scales with the
# full row/column count on the Python side.
#
# `style_table_aggrid` mirrors `style_table`'s parameter surface as closely as
# possible so call sites can be swapped fairly mechanically, but instead of
# returning a Styler it returns a dict of kwargs meant to be unpacked into
# `AgGrid(**style_table_aggrid(df, ...))`.
#
# Notes / known deviations from `style_table`:
# - `date_cols` are formatted with `strftime` in pandas (vectorized) before
#   being sent to the grid, since date formatting is cheap here but doing it
#   with a JS date-parsing routine adds a lot of edge-case complexity for
#   little benefit. This means the column becomes a plain string column, so
#   sorting is lexicographic (fine for the default ISO-like `%Y-%m-%d`), and
#   its filter falls back to the generic text filter (`agTextColumnFilter`)
#   instead of AG Grid's date filter/date-picker (`agDateColumnFilter`).
# - Row-level highlights (`highlight_row_by_column`, `highlight_row_if_value_lower/greater`)
#   are implemented via a single `getRowStyle` grid option. Column-level
#   highlights (`highlight_quartile`, `highlight_min_max_cols`,
#   `color_negative_positive_cols`) are implemented via per-column
#   `cellStyle` functions, which paint over the row background for that
#   specific cell. This is a simplification of the CSS-cascade precedence
#   pandas.Styler ends up with when chaining many `.apply()` calls, so exact
#   pixel-for-pixel precedence between row- and column-level highlights on
#   the same cell may differ slightly. Test manually and adjust if needed.
def style_table_aggrid(
    df: pd.DataFrame,
    percent_cols: Optional[List[str]] = None,
    date_cols: Optional[List[str]] = None,
    date_format: str = '%Y-%m-%d',
    rank_cols_identifier: Optional[str] = None,
    numeric_cols_format_as_int: Optional[List[str]] = None,
    numeric_cols_format_as_float: Optional[List[str]] = None,
    currency_cols: Optional[List[str]] = None,
    highlight_row_by_column: Optional[str] = None,
    highlight_row_if_value_equals: Optional[Any] = None,
    highlight_color: str = 'lightblue',
    highlight_quartile: Optional[List[str]] = None,
    highlight_min_max_cols: Optional[List[str]] = None,
    highlight_row_if_value_lower: Optional[Dict[str, float]] = None,
    highlight_row_if_value_greater: Optional[Dict[str, float]] = None,
    color_negative_positive_cols: Optional[List[str]] = None,
    quartile_exclude_row_by_column: Optional[str] = None,
    quartile_exclude_row_if_value_is: Optional[List[Any]] = None,
    left_align_cols: Optional[List[str]] = None,
    center_align_cols: Optional[List[str]] = None,
    right_align_cols: Optional[List[str]] = None,
    column_names: Optional[List[str]] = None,
    height: int = 400,
    resizable_height: bool = True,
    min_height: int = 150,
    max_height: Optional[int] = None,
    show_toolbar: bool = True,
    show_search: bool = True,
    show_download_button: bool = True,
    auto_size_columns: Optional[Literal["fit_grid_width", "fit_cell_contents"]] = "fit_grid_width",
    floating_filters: bool = False,
    pinned_left_cols: Optional[List[str]] = None,
    pinned_right_cols: Optional[List[str]] = None,
    enable_cell_text_selection: bool = True,
) -> Dict[str, Any]:
    """AgGrid-based counterpart to `style_table`.

    Same styling/formatting options as `style_table`, but returns a dict of
    kwargs to be unpacked into `AgGrid(**...)` (from `st_aggrid`) instead of a
    pandas Styler to be passed to `st.dataframe`. Intended as a drop-in for
    large tables where `st.dataframe(style_table(...))` is too slow.

    Usage:
        from st_aggrid import AgGrid
        AgGrid(**style_table_aggrid(df, percent_cols=[...], ...))

    Extra (AgGrid-only) knobs, addressing two common asks that `style_table`
    doesn't need (a Styler is always fully rendered by the caller's
    `st.dataframe`, so it has no notion of its own height/toolbar):

    - `resizable_height`: adds a native browser drag handle (bottom-right
      corner, like a `<textarea>`) so the user can grow/shrink the grid's
      visible height. This works because AG Grid listens to its own
      container resizing (`gridSizeChanged`) and re-reports the new height to
      Streamlit's iframe automatically - no custom JS needed on our side.
    - `show_toolbar` (+ `show_search`/`show_download_button`): enables the
      built-in AG Grid toolbar, which includes a real "Toggle Fullscreen"
      button (browser Fullscreen API) alongside a client-side search box and
      a CSV download button. The fullscreen button itself isn't
      independently toggleable in the currently installed streamlit-aggrid
      version - it's always shown whenever the toolbar is enabled.
    - `auto_size_columns`: auto-adjusts every column's width in one shot on
      load, via AG Grid's declarative `autoSizeStrategy` (no JS/event
      wiring needed on our side). Two modes:
        - "fit_grid_width" (default): stretches/shrinks all columns
          proportionally so they exactly fill the grid's width (same as
          double-clicking nothing; just distributes available space).
        - "fit_cell_contents": sizes each column to its own widest rendered
          cell content (header + formatted values), like Excel's
          "auto-fit column width" or double-clicking every column border at
          once. Prefer this when column widths look arbitrarily too
          narrow/too wide for the actual data.
      Pass `None` to leave AG Grid's own default sizing untouched.
    - `floating_filters`: per-column filters are always enabled
      (`filterable=True`), with the filter type (text/number/date) inferred
      from each column's dtype - but by default they're tucked behind the
      little menu icon on each header, which isn't very discoverable. This
      surfaces a filter input row right under the headers instead, so users
      can filter without hunting for the icon. This is on top of the toolbar's
      quick search (`show_search`), which does a looser all-columns text match.
    - `pinned_left_cols` / `pinned_right_cols`: unlike a Styler (which always
      shows the pandas index and Streamlit auto-pins it to the left in
      `st.dataframe`), AgGrid only ever sees `df`'s columns - the index is
      silently dropped otherwise, and nothing is pinned by default. Pass the
      column names you want fixed while scrolling horizontally (e.g. the
      columns you'd normally use as an index, such as
      `pinned_left_cols=["Portfolio", "Nome Ativo"]`) - if you need the
      pandas index itself pinned, `reset_index()` the DataFrame before
      calling this function and list the resulting column(s) here.
    - `enable_cell_text_selection`: when True (default), users can drag to
      select text inside cells and copy with Ctrl+C, closer to `st.dataframe`
      behavior. For exporting the full table, use the toolbar CSV download.

    As with any AgGrid usage, pass a stable `key=` to `AgGrid(...)` at the
    call site if you want a manual height resize (or filter/sort state) to
    state) to survive unrelated Streamlit reruns - without it the component
    is torn down and recreated with the original `height` on every rerun.
    """
    from st_aggrid import GridOptionsBuilder, JsCode

    def _safe_num_js(value_expr: str) -> str:
        # Guards against `Number(null) === 0` / `Number(undefined) === NaN`
        # ambiguity by always routing null/undefined to NaN explicitly.
        return f"(({value_expr}) === null || ({value_expr}) === undefined ? NaN : Number({value_expr}))"

    def _num_formatter_js(decimals: int, thousands: bool) -> "JsCode":
        grouping = "true" if thousands else "false"
        return JsCode(
            "function(params) {"
            "  if (params.value === null || params.value === undefined) { return ''; }"
            f"  var v = {_safe_num_js('params.value')};"
            "  if (isNaN(v)) { return ''; }"
            f"  return v.toLocaleString('en-US', {{minimumFractionDigits: {decimals}, maximumFractionDigits: {decimals}, useGrouping: {grouping}}});"
            "}"
        )

    def _quartile_edges_and_colors(series: pd.Series) -> Optional[Tuple[List[float], List[str]]]:
        calc_series = series
        if (
            quartile_exclude_row_by_column
            and quartile_exclude_row_if_value_is
            and quartile_exclude_row_by_column in df_grid.columns
        ):
            exclusion_mask = df_grid[quartile_exclude_row_by_column].isin(quartile_exclude_row_if_value_is)
            calc_series = series[~exclusion_mask]

        numeric = pd.to_numeric(calc_series, errors='coerce').dropna()
        if numeric.empty:
            return None
        try:
            _, edges = pd.qcut(numeric, 4, labels=False, duplicates='drop', retbins=True)
        except ValueError:
            return None

        colors = ['#faf099', '#cbe08c', '#96ce7e', '#66ba7b']
        n_bins = len(edges) - 1
        if n_bins <= 0:
            return None
        return [float(e) for e in edges], colors[:n_bins]

    df_grid = df.copy()

    if column_names and len(column_names) == len(df_grid.columns):
        df_grid.columns = column_names

    # Date formatting (vectorized, becomes a display string column).
    if date_cols:
        for col in date_cols:
            if col in df_grid.columns:
                parsed = pd.to_datetime(df_grid[col], errors='coerce')
                df_grid[col] = parsed.dt.strftime(date_format).where(parsed.notna(), '')

    actual_rank_cols = (
        [col for col in df_grid.columns if rank_cols_identifier in col]
        if rank_cols_identifier else []
    )

    gb = GridOptionsBuilder.from_dataframe(df_grid)
    gb.configure_default_column(
        resizable=True,
        # NOTE: the AG Grid colDef property is `filter`, not `filterable`.
        # `filter=True` enables the default filter for every column; numeric
        # / date columns still get their more specific agNumberColumnFilter /
        # agDateColumnFilter (wired via the `numberColumnFilter` /
        # `dateColumnFilter` `type` tags set in from_dataframe's type
        # mapping), this default just makes sure text columns get a working
        # (agTextColumnFilter) filter too instead of none at all.
        filter=True,
        sortable=True,
        floatingFilter=floating_filters,
    )

    if pinned_left_cols:
        for col in pinned_left_cols:
            if col in df_grid.columns:
                gb.configure_column(col, pinned="left")

    if pinned_right_cols:
        for col in pinned_right_cols:
            if col in df_grid.columns:
                gb.configure_column(col, pinned="right")

    if enable_cell_text_selection:
        gb.configure_grid_options(
            enableCellTextSelection=True,
            ensureDomOrder=True,
        )

    # `from_dataframe` already sets autoSizeStrategy={"type": "fitGridWidth"};
    # override here so callers can opt into content-based auto-sizing (or
    # opt out entirely) instead.
    if auto_size_columns == "fit_grid_width":
        gb.configure_grid_options(autoSizeStrategy={"type": "fitGridWidth"})
    elif auto_size_columns == "fit_cell_contents":
        gb.configure_grid_options(autoSizeStrategy={"type": "fitCellContents"})

    percent_formatter = JsCode(
        "function(params) {"
        "  if (params.value === null || params.value === undefined) { return ''; }"
        f"  var v = {_safe_num_js('params.value')};"
        "  if (isNaN(v)) { return ''; }"
        "  return v.toFixed(2) + '%';"
        "}"
    )

    # --- Value formatting (mirrors style_table's precedence/overwrite rules) ---
    formatted_cols: set = set()

    if percent_cols:
        for col in percent_cols:
            if col in df_grid.columns:
                gb.configure_column(col, valueFormatter=percent_formatter, type=["numericColumn", "numberColumnFilter"])
                formatted_cols.add(col)

    if rank_cols_identifier:
        for col in actual_rank_cols:
            gb.configure_column(col, valueFormatter=_num_formatter_js(0, False), type=["numericColumn", "numberColumnFilter"])
            formatted_cols.add(col)

    if numeric_cols_format_as_int:
        for col in numeric_cols_format_as_int:
            if col in df_grid.columns and col not in formatted_cols:
                gb.configure_column(col, valueFormatter=_num_formatter_js(0, True), type=["numericColumn", "numberColumnFilter"])
                formatted_cols.add(col)

    if numeric_cols_format_as_float:
        for col in numeric_cols_format_as_float:
            if col in df_grid.columns and col not in formatted_cols:
                gb.configure_column(col, valueFormatter=_num_formatter_js(2, True), type=["numericColumn", "numberColumnFilter"])
                formatted_cols.add(col)

    if currency_cols:
        for col in currency_cols:
            if col in df_grid.columns:
                gb.configure_column(col, valueFormatter=_num_formatter_js(0, True), type=["numericColumn", "numberColumnFilter"])
                formatted_cols.add(col)

    # --- Alignment (same precedence as style_table: left > center > right, first match wins) ---
    alignment_map: Dict[str, str] = {}
    processed_for_alignment: set = set()

    if left_align_cols:
        for col in left_align_cols:
            if col in df_grid.columns and col not in processed_for_alignment:
                alignment_map[col] = 'left'
                processed_for_alignment.add(col)

    cols_to_center = set(center_align_cols or [])
    if date_cols:
        cols_to_center.update(date_cols)
    if rank_cols_identifier:
        cols_to_center.update(actual_rank_cols)
    if highlight_row_by_column and highlight_row_if_value_equals is not None:
        cols_to_center.add(highlight_row_by_column)
    for col in cols_to_center:
        if col in df_grid.columns and col not in processed_for_alignment:
            alignment_map[col] = 'center'
            processed_for_alignment.add(col)

    cols_to_right_align = set(right_align_cols or [])
    if percent_cols:
        cols_to_right_align.update(percent_cols)
    if currency_cols:
        cols_to_right_align.update(currency_cols)
    for col in cols_to_right_align:
        if col in df_grid.columns and col not in processed_for_alignment:
            alignment_map[col] = 'right'
            processed_for_alignment.add(col)

    # --- Column-level (cell) conditional coloring ---
    column_style_blocks: Dict[str, List[str]] = defaultdict(list)

    if highlight_quartile:
        for col in highlight_quartile:
            if col not in df_grid.columns:
                continue
            edges_colors = _quartile_edges_and_colors(df_grid[col])
            if edges_colors is None:
                continue
            edges, colors = edges_colors

            exclude_check = "var excluded = false;"
            if (
                quartile_exclude_row_by_column
                and quartile_exclude_row_if_value_is
                and quartile_exclude_row_by_column in df_grid.columns
            ):
                exclude_check = (
                    "var excluded = false;"
                    f"var excludedValues = {json.dumps(list(quartile_exclude_row_if_value_is))};"
                    f"if (excludedValues.indexOf(params.data[{json.dumps(quartile_exclude_row_by_column)}]) !== -1) {{ excluded = true; }}"
                )

            column_style_blocks[col].append(
                "{"
                f"  var v = {_safe_num_js('params.value')};"
                "  if (!isNaN(v)) {"
                f"    {exclude_check}"
                "    if (!excluded) {"
                f"      var edges = {json.dumps(edges)};"
                f"      var colors = {json.dumps(colors)};"
                "      for (var i = 0; i < edges.length - 1; i++) {"
                "        if ((i === 0 && v >= edges[i] && v <= edges[i + 1]) || (i > 0 && v > edges[i] && v <= edges[i + 1])) {"
                "          style.backgroundColor = colors[i];"
                "          break;"
                "        }"
                "      }"
                "    }"
                "  }"
                "}"
            )

    if highlight_min_max_cols:
        for col in highlight_min_max_cols:
            if col not in df_grid.columns:
                continue
            numeric = pd.to_numeric(df_grid[col], errors='coerce')
            if numeric.notna().sum() == 0:
                continue
            min_v, max_v = float(numeric.min()), float(numeric.max())
            column_style_blocks[col].append(
                "{"
                f"  var v = {_safe_num_js('params.value')};"
                "  if (!isNaN(v)) {"
                f"    if (v === {json.dumps(min_v)}) {{ style.backgroundColor = '#ffc7ce'; }}"
                f"    else if (v === {json.dumps(max_v)}) {{ style.backgroundColor = '#c6efce'; }}"
                "  }"
                "}"
            )

    if color_negative_positive_cols:
        for col in color_negative_positive_cols:
            if col not in df_grid.columns:
                continue
            column_style_blocks[col].append(
                "{"
                f"  var v = {_safe_num_js('params.value')};"
                "  if (!isNaN(v)) {"
                "    if (v < 0) { style.color = '#d32f2f'; }"
                "    else if (v > 0) { style.color = '#2e7d32'; }"
                "  }"
                "}"
            )

    all_styled_cols = set(alignment_map) | set(column_style_blocks)
    for col in all_styled_cols:
        if col not in df_grid.columns:
            continue
        align = alignment_map.get(col)
        align_js = f"style.textAlign = '{align}';" if align else ""
        blocks_js = "".join(column_style_blocks.get(col, []))
        cell_style_js = JsCode(
            "function(params) {"
            "  var style = {};"
            f"  {align_js}"
            f"  {blocks_js}"
            "  return style;"
            "}"
        )
        gb.configure_column(col, cellStyle=cell_style_js)

    # --- Row-level conditional coloring ---
    row_style_conditions: List[str] = []

    if (
        highlight_row_by_column
        and highlight_row_if_value_equals is not None
        and highlight_row_by_column in df_grid.columns
    ):
        row_style_conditions.append(
            f"if (d[{json.dumps(highlight_row_by_column)}] === {json.dumps(highlight_row_if_value_equals)}) "
            f"{{ style.backgroundColor = {json.dumps(highlight_color)}; }}"
        )

    if highlight_row_if_value_lower:
        for col, threshold in highlight_row_if_value_lower.items():
            if col in df_grid.columns:
                row_style_conditions.append(
                    "{"
                    f"  var v = {_safe_num_js(f'd[{json.dumps(col)}]')};"
                    f"  if (!isNaN(v) && v < {json.dumps(float(threshold))}) {{ style.backgroundColor = '#ffc7ce'; }}"
                    "}"
                )

    if highlight_row_if_value_greater:
        for col, threshold in highlight_row_if_value_greater.items():
            if col in df_grid.columns:
                row_style_conditions.append(
                    "{"
                    f"  var v = {_safe_num_js(f'd[{json.dumps(col)}]')};"
                    f"  if (!isNaN(v) && v > {json.dumps(float(threshold))}) {{ style.backgroundColor = '#c6efce'; }}"
                    "}"
                )

    if row_style_conditions:
        get_row_style_js = JsCode(
            "function(params) {"
            "  var d = params.data;"
            "  if (!d) { return undefined; }"
            "  var style = {};"
            f"  {''.join(row_style_conditions)}"
            "  return Object.keys(style).length ? style : undefined;"
            "}"
        )
        gb.configure_grid_options(getRowStyle=get_row_style_js)

    grid_options = gb.build()

    custom_css: Dict[str, Dict[str, str]] = {}
    if resizable_height:
        container_style = {
            "resize": "vertical",
            "overflow": "auto",
            "min-height": f"{min_height}px",
        }
        if max_height:
            container_style["max-height"] = f"{max_height}px"
        custom_css["#gridContainer"] = container_style

    return {
        "data": df_grid,
        "gridOptions": grid_options,
        "height": height,
        "allow_unsafe_jscode": True,
        "theme": "material",
        "show_toolbar": show_toolbar,
        "show_search": show_search,
        "show_download_button": show_download_button,
        "custom_css": custom_css or None,
        "update_on": ["filterChanged", "sortChanged"],
    }


def get_performance_table(series):
    df = series.ffill()
    if df.empty:
        return pd.DataFrame()

    gp_daily = df.groupby(pd.Grouper(level='date', freq="1D")).last()
    gp_monthly = df.groupby(pd.Grouper(level='date', freq="ME")).last()
    gp_yearly = df.groupby(pd.Grouper(level='date', freq="YE")).last()

    day_ret = gp_daily.pct_change(fill_method=None).iloc[-1]
    mtd_ret = gp_monthly.pct_change(fill_method=None).iloc[-1]
    ytd_ret = gp_yearly.pct_change(fill_method=None).iloc[-1]

    def get_relative_return(months):
        start_date_calc = df.index[-1] - relativedelta(months=months)
        period_df = df.loc[start_date_calc:]
        if len(period_df) > 1:
            return df.iloc[-1] / period_df.iloc[0] - 1
        return pd.Series(np.nan, index=df.columns)

    ret_1m = get_relative_return(1)
    ret_3m = get_relative_return(3)
    ret_6m = get_relative_return(6)
    ret_12m = get_relative_return(12)
    ret_24m = get_relative_return(24)
    ret_36m = get_relative_return(36)

    returns = {
        'mtd': mtd_ret,
        'ytd': ytd_ret,
        '1m': ret_1m,
        '3m': ret_3m,
        '6m': ret_6m,
        '12m': ret_12m,
        '24m': ret_24m,
        '36m': ret_36m,
    }

    time_frames = {**returns}

    df_result = pd.DataFrame(time_frames)
    df_result = df_result.apply(lambda x: x * 100)    
    df_result = df_result.reset_index()
    
    return df_result


def get_monthly_returns_table(returns_series: pd.Series) -> pd.DataFrame:
    MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    monthly = returns_series.resample('ME').apply(lambda x: (1 + x).prod() - 1) * 100
    df = monthly.to_frame(name='ret')
    df['year'] = df.index.year
    df['month'] = df.index.month
    pivot = df.pivot(index='year', columns='month', values='ret')
    pivot.columns = [MONTH_NAMES[m - 1] for m in pivot.columns]

    annual = returns_series.resample('YE').apply(lambda x: (1 + x).prod() - 1) * 100
    annual.index = annual.index.year
    pivot['Ano'] = annual
    pivot.index.name = None
    return pivot