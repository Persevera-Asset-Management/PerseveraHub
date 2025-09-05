FACTOR_OPTIONS_SCREENER = {
    # Liquidez e Volume
    'ADTV (7d)': 'median_dollar_volume_traded_7d',
    'ADTV (14d)': 'median_dollar_volume_traded_14d',
    'ADTV (21d)': 'median_dollar_volume_traded_21d',
    'ADTV (63d)': 'median_dollar_volume_traded_63d',
    'ADTV (252d)': 'median_dollar_volume_traded_252d',
    'Volume (7d)': 'median_volume_traded_7d',
    'Volume (14d)': 'median_volume_traded_14d',
    'Volume (21d)': 'median_volume_traded_21d',
    'Volume (63d)': 'median_volume_traded_63d',
    'Volume (252d)': 'median_volume_traded_252d',
    'Volume (7d/63d)': 'delta_volume_7d_63d',
    'Volume (14d/63d)': 'delta_volume_14d_63d',
    'Volume (21d/63d)': 'delta_volume_21d_63d',
    'Dollar Volume (7d/63d)': 'delta_dollar_volume_7d_63d',
    'Dollar Volume (14d/63d)': 'delta_dollar_volume_14d_63d',
    'Dollar Volume (21d/63d)': 'delta_dollar_volume_21d_63d',

    # Momentum e Técnico
    'Momentum (7d)': 'momentum_7d',
    'Momentum (14d)': 'momentum_14d',
    'Momentum (1m)': 'momentum_1m',
    'Momentum (3m)': 'momentum_3m',
    'Momentum (3m1)': 'momentum_3m1',
    'Momentum (6m)': 'momentum_6m',
    'Momentum (6m1)': 'momentum_6m1',
    'Momentum (9m)': 'momentum_9m',
    'Momentum (9m1)': 'momentum_9m1',
    'Momentum (12m)': 'momentum_12m',
    'Momentum (12m1)': 'momentum_12m1',
    'Price Range': 'price_range',
    'RSI (3d)': 'rsi_3d',
    'RSI (9d)': 'rsi_9d',
    'RSI (14d)': 'rsi_14d',
    'RSI (30d)': 'rsi_30d',

    # Volatilidade e Risco
    'Beta': 'beta',
    'Beta Downside': 'beta_downside',
    'Beta Upside': 'beta_upside',
    'Volatility (1m)': 'volatility_1m',
    'Volatility (3m)': 'volatility_3m',
    'Volatility (6m)': 'volatility_6m',
    'Volatility (12m)': 'volatility_12m',
    'Implied Volatility (1m)': 'implied_volatility_1m',
    'Implied Volatility (3m)': 'implied_volatility_3m',
    'Implied Volatility (6m)': 'implied_volatility_6m',
    'Short Interest': 'short_interest',
    'Short Interest (%)': 'short_interest_pct',
    'Days to Cover': 'days_to_cover',
    'Lending Rate (%)': 'lending_rate',

    # Múltiplos e Valuation
    'P/E Fwd': 'price_to_earnings_fwd',
    'EV/EBITDA Fwd': 'ev_to_ebitda_fwd',
    'Price Target': 'price_target',
    'Market Cap': 'market_cap',
    'Book Value per Share': 'book_value_per_share',
    'Book Value per Share Fwd': 'book_value_per_share_fwd',
    'Book Yield Fwd': 'book_yield_fwd',
    'Book Yield LTM': 'book_yield_ltm',
    'Book Yield Percentile 10Y': 'book_yield_percentile_10y',
    'Earnings Yield Fwd': 'earnings_yield_fwd',
    'Earnings Yield LTM': 'earnings_yield_ltm',
    'Earnings Yield Percentile 10Y': 'earnings_yield_percentile_10y',
    'EBITDA Yield Fwd': 'ebitda_yield_fwd',
    'EBITDA Yield LTM': 'ebitda_yield_ltm',
    'EBITDA Yield Percentile 10Y': 'ebitda_yield_percentile_10y',
    'EBIT Yield Fwd': 'ebit_yield_fwd',
    'EBIT Yield LTM': 'ebit_yield_ltm',
    'FCF Yield Fwd': 'fcf_yield_fwd',
    'FCF Yield LTM': 'fcf_yield_ltm',

    # Métricas Financeiras
    'EBITDA Fwd': 'ebitda_fwd',
    'EBITDA LTM': 'ebitda_ltm',
    'EBITDA Q': 'ebitda_q',
    'EBIT Fwd': 'ebit_fwd',
    'EBIT LTM': 'ebit_ltm',
    'EBIT Q': 'ebit_q',
    'Free Cash Flow Fwd': 'free_cash_flow_fwd',
    'Free Cash Flow LTM': 'free_cash_flow_ltm',
    'Free Cash Flow Q': 'free_cash_flow_q',
    'Net Income Fwd': 'net_income_fwd',
    'Net Income LTM': 'net_income_ltm',
    'Net Income Q': 'net_income_q',
    'Net Revenues Fwd': 'net_revenues_fwd',
    'Net Revenues LTM': 'net_revenues_ltm',
    'Net Revenues Q': 'net_revenues_q',
    'Gross Profit LTM': 'gross_profit_ltm',
    'Gross Profit Q': 'gross_profit_q',
    'Cash Flow from Operations Q': 'cash_flow_from_operations_q',
    'Cash and Cash Equivalents': 'cash_and_cash_equivalents',
    'Long Term Debt': 'long_term_debt',
    'Short Term Debt': 'short_term_debt',
    'Net Debt': 'net_debt',
    'Total Assets': 'total_assets',
    'Total Equity': 'total_equity',
    'Capital Employed': 'capital_employed',
    'Invested Capital': 'invested_capital',

    # Margens e Rentabilidade
    'EBIT Margin (%)': 'ebit_margin',
    'EBIT Margin Growth 1Y': 'ebit_margin_growth_1y',
    'EBITDA Margin (%)': 'ebitda_margin',
    'EBITDA Margin Growth 1Y': 'ebitda_margin_growth_1y',
    'FCF Margin (%)': 'fcf_margin',
    'FCF Margin Growth 1Y': 'fcf_margin_growth_1y',
    'Gross Margin (%)': 'gross_margin',
    'Gross Margin Growth 1Y': 'gross_margin_growth_1y',
    'Net Margin (%)': 'net_margin',
    'Net Margin Growth 1Y': 'net_margin_growth_1y',
    'ROE (%)': 'roe',
    'ROE Fwd': 'roe_fwd',
    'ROE Growth 1Y': 'roe_growth_1y',
    'ROA (%)': 'roa',
    'ROA Fwd': 'roa_fwd',
    'ROCE (%)': 'roce',
    'ROIC (%)': 'roic',
    'ROIC Growth 1Y': 'roic_growth_1y',
    'Asset Turnover': 'asset_turnover',

    # Endividamento
    'Net Debt to EBITDA': 'net_debt_to_ebitda',
    'Net Debt to Equity': 'net_debt_to_equity',

    # Dividendos
    'Dividend per Share Fwd': 'dividend_per_share_fwd',
    'Dividend per Share LTM': 'dividend_per_share_ltm',
    'Dividend Yield Fwd (%)': 'dividend_yield_fwd',
    'Dividend Yield LTM (%)': 'dividend_yield_ltm',
    'Dividend Payout (%)': 'dividend_payout',

    # Outros
    'Analyst Rating': 'analyst_rating',
    'EPS Fwd': 'earnings_per_share_fwd',
    'EPS LTM': 'earnings_per_share_ltm',
    'Long Term Growth (%)': 'long_term_growth'
}

FACTOR_MOMENTUM_COMPONENTS = {
    'Momentum (6m)': 'momentum_6m',
    'Momentum (12m)': 'momentum_12m',
}

FACTOR_VALUE_COMPONENTS = {
    'Earnings Yield Fwd': 'earnings_yield_fwd',
    'EBITDA Yield Fwd': 'ebitda_yield_fwd',
    'FCF Yield Fwd': 'fcf_yield_fwd',
}

FACTOR_LIQUIDITY_COMPONENTS = {
    'Dollar Volume (7d/63d)': 'delta_dollar_volume_7d_63d',
    'Dollar Volume (14d/63d)': 'delta_dollar_volume_14d_63d',
    'Dollar Volume (21d/63d)': 'delta_dollar_volume_21d_63d',
}

FACTOR_RISK_COMPONENTS = {
    'Beta': 'beta',
    'Volatility (1m)': 'volatility_1m',
    'Volatility (12m)': 'volatility_12m',
}

FACTOR_QUALITY_COMPONENTS = {
    'EBITDA Margin (%)': 'ebitda_margin',
    'FCF Margin (%)': 'fcf_margin',
    'Gross Margin (%)': 'gross_margin',
    'Net Margin (%)': 'net_margin',
    'ROE (%)': 'roe',
    'ROIC (%)': 'roic'
}