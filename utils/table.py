import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union, Tuple, Literal

def style_performance_table(df):
    """Applies styling to the performance DataFrame."""
    df_styled = df.copy()

    # Identify columns
    percent_cols = ['day', 'mtd', 'ytd', '3m', '6m', '12m', '24m', '36m', 'custom']
    rank_cols = [col for col in df_styled.columns if 'rank' in col]
    pl_col = 'PL'

    formatters = {}
    for col in percent_cols:
        if col in df_styled.columns:
            formatters[col] = "{:.2f}%"
    for col in rank_cols:
        if col in df_styled.columns:
            formatters[col] = "{:.0f}"
    if pl_col in df_styled.columns:
        formatters[pl_col] = "{:,.0f}"

    styled_obj = df_styled.style.format(formatters)

    # Highlight Persevera rows
    def highlight_persevera(row):
        color = 'background-color: lightblue' if row.type == 'Persevera' else ''
        return [color] * len(row)

    if 'type' in df_styled.columns:
        styled_obj = styled_obj.apply(highlight_persevera, axis=1)

    alignment_styles = []
    if 'fund_name' in df_styled.columns:
        alignment_styles.append({'selector': 'td.col-fund_name', 'props': [('text-align', 'left')]})
    else:
        alignment_styles.append({'selector': 'th.row_heading', 'props': [('text-align', 'left')]})
        
    for col_name in df_styled.columns:
        if col_name == 'type' or col_name in rank_cols:
            alignment_styles.append({'selector': f'td.col{df_styled.columns.get_loc(col_name)}', 'props': [('text-align', 'center')]})
        elif col_name in percent_cols or col_name == pl_col:
            alignment_styles.append({'selector': f'td.col{df_styled.columns.get_loc(col_name)}', 'props': [('text-align', 'right')]})
    
    styled_obj = styled_obj.set_table_styles(alignment_styles, overwrite=False)

    return styled_obj
