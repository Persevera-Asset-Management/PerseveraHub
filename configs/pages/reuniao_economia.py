CHARTS_ECONOMIA = {
    # === Estados Unidos ===
    # PIB
    "us_gdp_qoq": {
        "chart_config": {
            "columns": "us_gdp_qoq",
            "names": "PIB QoQ SA",
            "chart_type": "column",
            "title": "PIB QoQ SA",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "PIB",
        "block_title": "PIB"
    },
    "us_gdp_yoy": {
        "chart_config": {
            "columns": "us_gdp_yoy",
            "names": "PIB YoY SA",
            "chart_type": "column",
            "title": "PIB YoY",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "PIB",
        "block_title": "PIB"
    },
    
    # Indústria
    "us_bloomberg_industry_surprise_index": {
        "chart_config": {
            "columns": "us_bloomberg_industry_surprise_index",
            "names": "Bloomberg US Industrial Sector Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Indústria",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_industrial_production": {
        "chart_config": {
            "columns": ["us_industrial_production_index", "us_capacity_utilization_index"],
            "names": ["Produção Industrial", "Utilização de Capacidade"],
            "chart_type": "dual_axis_line",
            "title": "Industrial Production & Capacity Utilization",
            "y_axis_title": ["Valor", "Taxa (%)"],
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Indústria",
        "block_title": "Industrial Production & Capacity Utilization"
    },
    
    # Varejo
    "us_bloomberg_retail_surprise_index": {
        "chart_config": {
            "columns": "us_bloomberg_retail_surprise_index",
            "names": "Bloomberg Retail & Wholesale Sector Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Varejo",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_advance_retail_sales_total": {
        "chart_config": {
            "columns": ["us_advance_retail_sales_total", "us_advance_retail_sales_ex_auto_total"],
            "names": ["Total", "Total (Ex Autos)"],
            "chart_type": "dual_axis_line",
            "title": "Retail Sales",
            "y_axis_title": ["US$ Mil", "US$ Mil"],
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Varejo",
        "block_title": "Advance Retail Sales"
    },
    "us_advance_retail_sales_yoy": {
        "chart_config": {
            "columns": ["us_advance_retail_sales_total", "us_advance_retail_sales_ex_auto_total"],
            "names": ["Total", "Total (Ex Autos)"],
            "chart_type": "line",
            "title": "Retail Sales (% YoY)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_advance_retail_sales_total", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_advance_retail_sales_ex_auto_total", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Varejo",
        "block_title": "Advance Retail Sales"
    },
    "us_advance_retail_sales_mom": {
        "chart_config": {
            "columns": ["us_advance_retail_sales_total", "us_advance_retail_sales_ex_auto_total"],
            "names": ["Total", "Total (Ex Autos)"],
            "chart_type": "column",
            "title": "Retail Sales (% MoM)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "monthly_variation", "column": "us_advance_retail_sales_total", "frequency": "MS"}, {"type": "monthly_variation", "column": "us_advance_retail_sales_ex_auto_total", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Varejo",
        "block_title": "Advance Retail Sales"
    },
    
    # Construção e Vendas
    "us_bloomberg_housing_surprise_index": {
         "chart_config": {
            "columns": "us_bloomberg_housing_surprise_index",
            "names": "Bloomberg US Housing and Real Estate Market Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Housing",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_new_home_sales_total": {
        "chart_config": {
            "columns": ["us_new_home_sales_total", "us_housing_starts_total", "us_building_permits_total"],
            "names": "Novas Unidades Habitacionais Privadas",
            "chart_type": "line",
            "title": "Vendas e Contruções",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Housing",
        "block_title": "Construção e Vendas"
    },
    "us_case_shiller_home_prices_national_index": {
        "chart_config": {
            "columns": ["us_case_shiller_home_prices_national_index", "us_case_shiller_home_prices_20_city_index"],
            "names": "S&P CoreLogic Case-Shiller Price Indices",
            "chart_type": "line",
            "title": "Preços de Imóveis",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Housing",
        "block_title": "Preços"
    },
    
    # Crédito
    "us_delinquency_rates": {
        "chart_config": {
            "columns": ["us_delinquency_rates_consumer_loans", "us_delinquency_rates_credit_cards", "us_delinquency_rates_business_loans"],
            "names": ["Consumidor", "Cartão de Crédito", "Empresas"],
            "chart_type": "line",
            "title": "Inadimplência",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "Inadimplência e Juros"
    },
    "us_commercial_bank_interest_rates": {
        "chart_config": {
            "columns": ["us_commercial_bank_interest_rates_credit_card_plans"],
            "names": ["Juros"],
            "chart_type": "line",
            "title": "Juros de Bancos Comerciais em Cartão de Crédito",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "Inadimplência e Juros"
    },
    "us_sloos_cni": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_tightening_cni_loans_large", "us_sloos_net_pct_banks_tightening_cni_loans_small"],
            "names": "Net Percent of Domestic Respondents Tightening Standards for Commercial and Industrial Loans",
            "chart_type": "line",
            "title": "SLOOS: Measures of Supply and Demand for Commercial and Industrial Loans",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": ""
    },
    "us_sloos_consumer": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_tightening_consumer_loans_credit_card", "us_sloos_net_pct_banks_tightening_consumer_loans_auto", "us_sloos_net_pct_banks_tightening_consumer_loans_others"],
            "names": "Net Percent of Domestic Respondents Tightening Standards for Consumer Loans",
            "chart_type": "line",
            "title": "SLOOS: Measures of Supply and Demand for Consumer Loans",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": ""
    },
    # Sentimento
    "us_bloomberg_business_cycle_surprise_index": {
         "chart_config": {
            "columns": "us_bloomberg_business_cycle_surprise_index",
            "names": "Bloomberg Surveys & Business Cycle Indicators Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_pmi": {
         "chart_config": {
            "columns": "us_pmi_composite",
            "names": "Composto",
            "chart_type": "line",
            "title": "PMI",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "PMI (S&P Global)"
    },
    "us_ism_composites": {
        "chart_config": {
            "columns": ["us_ism_manufacting", "us_ism_services"],
            "names": ["Manufacturing", "Services"],
            "chart_type": "line",
            "title": "ISM Composites",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Institute for Supply Management (ISM)"
    },
    "us_ism_manufacting": {
        "chart_config": {
            "columns": ["us_ism_manufacturing_new_orders", "us_ism_manufacturing_inventories", "us_ism_manufacturing_prices_paid", "us_ism_manufacturing_employment"],
            "names": ["New Orders", "Inventories", "Prices Paid", "Employment"],
            "chart_type": "line",
            "title": "ISM Manufacturing",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Institute for Supply Management (ISM)"
    },
    "us_ism_services": {
        "chart_config": {
            "columns": ["us_ism_services_new_orders", "us_ism_services_prices_paid", "us_ism_services_employment"],
            "names": ["New Orders", "Prices Paid", "Employment"],
            "chart_type": "line",
            "title": "ISM Services",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Institute for Supply Management (ISM)"
    },
    "us_cb_business_conditions": {
        "chart_config": {
            "columns": ["us_cb_consumer_confidence_business_worse_6m", "us_cb_consumer_confidence_business_better_6m"],
            "names": ["Pior", "Melhor"],
            "chart_type": "line",
            "title": "Condições de Negócios (Próximos 6 Meses)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Conference Board"
    },
    "us_cb_jobs_conditions": {
        "chart_config": {
            "columns": ["us_cb_consumer_confidence_more_jobs_6m", "us_cb_consumer_confidence_fewer_jobs_6m"],
            "names": ["Mais Empregos", "Menos Empregos"],
            "chart_type": "line",
            "title": "Condições de Emprego (Próximos 6 Meses)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Conference Board"
    },
    "us_nfib_sentiment": {
        "chart_config": {
            "columns": ["us_nfib_small_business_optimism_index", "us_nfib_small_business_uncertainty_index"],
            "names": ["Índice de Otimismo", "Índice de Incerteza"],
            "chart_type": "line",
            "title": "Sentimento de Pequenas Empresas (NFIB)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Sentimento de Pequenas Empresas (NFIB)"
    },
    "us_nfib_expansion": {
        "chart_config": {
            "columns": ["us_nfib_small_business_good_time_to_expand", "us_nfib_small_business_plans_increase_capex", "us_nfib_small_business_hiring_plans"],
            "names": ["Boa Hora para Expandir", "Aumentar Capex", "Contratar"],
            "chart_type": "line",
            "title": "Condições de Negócios",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Sentimento de Pequenas Empresas (NFIB)"
    },
    "us_nfib_prices": {
        "chart_config": {
            "columns": ["us_nfib_small_business_higher_prices"],
            "names": ["Maior Preço"],
            "chart_type": "line",
            "title": "Condições de Preços",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Sentimento de Pequenas Empresas (NFIB)"
    },
    "us_nfib_credit_conditions": {
        "chart_config": {
            "columns": ["us_nfib_small_business_credit_conditions_availability_of_loans"],
            "names": ["Disponibilidade de Crédito"],
            "chart_type": "line",
            "title": "Condições de Crédito",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Sentimento",
        "block_title": "Sentimento de Pequenas Empresas (NFIB)"
    },
    
    # Emprego
    "us_bloomberg_labor_surprise_index": {
         "chart_config": {
            "columns": "us_bloomberg_labor_surprise_index",
            "names": "Bloomberg Labor Indicators Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_initial_jobless_claims": {
        "chart_config": {
            "columns": ["us_initial_jobless_claims", "us_initial_jobless_claims_4wma"],
            "names": ["Total", "Total (4-Semanas Móvel)"],
            "chart_type": "line",
            "title": "Initial Jobless Claims",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Unemployment Insurance Weekly Claims Report"
    },
    "us_continuing_jobless_claims": {
        "chart_config": {
            "columns": ["us_continuing_jobless_claims"],
            "names": ["Total"],
            "chart_type": "line",
            "title": "Continuing Jobless Claims",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Unemployment Insurance Weekly Claims Report"
    },
    "us_jolts_job_openings": {
         "chart_config": {
            "columns": "us_jolts_job_openings_total_nonfarm",
            "names": "Total",
            "chart_type": "line",
            "title": "Abertura de Vagas",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Job Openings and Labor Turnover Survey"
    },
    "us_adp_nonfarm_private_payrolls_mom": {
         "chart_config": {
            "columns": "us_adp_nonfarm_private_payrolls",
            "names": "Var. Mensal",
            "chart_type": "column",
            "title": "Non-Farm Private Payroll (MoM)",
            "y_axis_title": "Valor",
        },
        "transformations": [{"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "ADP National Employment Report"
    },
    "us_adp_nonfarm_private_payrolls_yoy": {
         "chart_config": {
            "columns": "us_adp_nonfarm_private_payrolls",
            "names": "Var. Anual (%)",
            "chart_type": "line",
            "title": "Non-Farm Private Payroll (% YoY)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "ADP National Employment Report"
    },
    "us_adp_nonfarm_private_payrolls_by_establishment_size_mom": {
         "chart_config": {
            "columns": ["us_adp_nonfarm_private_payrolls_establishments_1_to_19", "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "us_adp_nonfarm_private_payrolls_establishments_500_over"],
            "names": ["1-19", "20-49", "50-249", "250-499", "500+"],
            "chart_type": "column",
            "title": "Non-Farm Private Payroll (MoM)",
            "y_axis_title": "Valor",
        },
        "transformations": [{"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_1_to_19", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_500_over", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "ADP National Employment Report"
    },
    "us_adp_nonfarm_private_payrolls_by_establishment_size_mom": {
         "chart_config": {
            "columns": ["us_adp_nonfarm_private_payrolls_establishments_1_to_19", "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "us_adp_nonfarm_private_payrolls_establishments_500_over"],
            "names": ["1-19", "20-49", "50-249", "250-499", "500+"],
            "chart_type": "column",
            "title": "Non-Farm Private Payroll (MoM)",
            "y_axis_title": "Valor",
        },
        "transformations": [{"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_1_to_19", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_adp_nonfarm_private_payrolls_establishments_500_over", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "ADP National Employment Report"
    },
    "us_adp_nonfarm_private_payrolls_by_establishment_size_yoy": {
        "chart_config": {
            "columns": ["us_adp_nonfarm_private_payrolls_establishments_1_to_19", "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "us_adp_nonfarm_private_payrolls_establishments_500_over"],
            "names": ["1-19", "20-49", "50-249", "250-499", "500+"],
            "chart_type": "line",
            "title": "Non-Farm Private Payroll (% YoY)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls_establishments_1_to_19", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls_establishments_20_to_49", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls_establishments_50_to_249", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls_establishments_250_to_499", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_adp_nonfarm_private_payrolls_establishments_500_over", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "ADP National Employment Report"
    },
    "us_ces_nonfarm_payrolls_mom": {
        "chart_config": {
            "columns": ["us_ces_nonfarm_payrolls_total", "us_ces_nonfarm_payrolls_private", "us_ces_nonfarm_payrolls_government"],
            "names": ["Total", "Privado", "Público"],
            "chart_type": "column",
            "title": "Non-Farm Payroll (MoM)",
            "y_axis_title": "Valor",
        },
        "transformations": [{"type": "monthly_difference", "column": "us_ces_nonfarm_payrolls_total", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_ces_nonfarm_payrolls_private", "frequency": "MS"}, {"type": "monthly_difference", "column": "us_ces_nonfarm_payrolls_government", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Current Employment Statistics (Establishment Data)"
    },
    "us_ces_nonfarm_payrolls_yoy": {
        "chart_config": {
            "columns": ["us_ces_nonfarm_payrolls_total", "us_ces_nonfarm_payrolls_private", "us_ces_nonfarm_payrolls_government"],
            "names": ["Total", "Privado", "Público"],
            "chart_type": "line",
            "title": "Non-Farm Payroll (% YoY)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_ces_nonfarm_payrolls_total", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_ces_nonfarm_payrolls_private", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_ces_nonfarm_payrolls_government", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Current Employment Statistics (Establishment Data)"
    },
    "us_ces_average_hourly_earnings": {
        "chart_config": {
            "columns": ["us_ces_average_hourly_earnings"],
            "names": ["Var. Anual (%)"],
            "chart_type": "line",
            "title": "Average Hourly Earnings",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_ces_average_hourly_earnings", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Current Employment Statistics (Establishment Data)"
    },
    "us_unemployment_rate": {
        "chart_config": {
            "columns": ["us_unemployment_rate", "us_unemployment_rate_nsa"],
            "names": ["Taxa de Desemprego", "Taxa de Desemprego (NSA)"],
            "chart_type": "line",
            "title": "Taxa de Desemprego",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Current Population Survey (Household Data)"
    },
    "us_unemployment_duration_median": {
        "chart_config": {
            "columns": "us_unemployment_duration_median",
            "names": "Mediana de Tempo de Desemprego",
            "chart_type": "line",
            "title": "Mediana de Tempo de Desemprego",
            "y_axis_title": "Meses",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Current Population Survey (Household Data)"
    },
     "us_indeed_job_postings": {
        "chart_config": {
            "columns": ["us_indeed_job_postings", "us_indeed_new_job_postings"],
            "names": ["Total", "Novas Vagas"],
            "chart_type": "line",
            "title": "Abertura de Vagas (Indeed)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Indeed Job Postings"
    },
    
    # Inflação
    "us_bloomberg_inflation_surprise_index": {
        "chart_config": {
            "columns": "us_bloomberg_inflation_surprise_index",
            "names": "Bloomberg Inflation Data Surprise Index",
            "chart_type": "area",
            "title": "Bloomberg Data Surprise",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_cpi_yoy": {
        "chart_config": {
            "columns": ["us_cpi_index", "us_cpi_core_index"],
            "names": ["CPI", "Core CPI"],
            "chart_type": "line",
            "title": "CPI",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_cpi_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_cpi_core_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Inflação ao Consumidor"
    },
    "us_pce_yoy": {
        "chart_config": {
            "columns": ["us_pce_index", "us_pce_core_index"],
            "names": ["PCE", "Core PCE"],
            "chart_type": "line",
            "title": "PCE",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_pce_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_pce_core_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Inflação ao Consumidor"
    },
    "us_ppi_yoy": {
        "chart_config": {
            "columns": "us_ppi_index",
            "names": "PPI",
            "chart_type": "line",
            "title": "PPI",
            "y_axis_title": "Taxa (%)", 
        },
        "transformations": [{"type": "yearly_variation", "column": "us_ppi_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Inflação ao Produtor"
    },
    "us_mfg_surveys_inflation_dual_axis": {
        "chart_config": {
            "columns": [["us_cpi_index"], ["us_philly_fed_prices_paid", "us_ny_fed_prices_paid"]],
            "names": [["CPI"], ["Philadelphia Fed", "New York Fed"]],
            "chart_type": "dual_axis_line",
            "title": "CPI vs Price Paid Surveys",
            "y_axis_title": ("Taxa (%)", "Índice"),
        },
        "transformations": [{"type": "yearly_variation", "column": "us_cpi_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Soft Data"
    },

    # === Brasil ===
    # IBC-Br
    "br_ibcbr": {
        "chart_config": {
            "columns": "br_ibcbr_index",
            "names": "Índice",
            "chart_type": "line",
            "title": "IBC-Br",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "IBC-Br",
        "block_title": "IBC-Br"
    },
    
    # PIB
    "br_gdp_qoq": {
         "chart_config": {
            "columns": "br_gdp_index",
            "names": "PIB (% QoQ)",
            "chart_type": "column",
            "title": "PIB (% QoQ)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "quarterly_variation", "column": "br_gdp_index", "frequency": "QS"}],
        "width": 6,
        "context": "Brasil",
        "group": "PIB",
        "block_title": "PIB"
    },
    "br_gdp_yoy": {
         "chart_config": {
            "columns": "br_gdp_index_nsa",
            "names": "PIB (% YoY)",
            "chart_type": "column",
            "title": "PIB (% YoY)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_gdp_index_nsa", "frequency": "QS", "periods": 4}],
        "width": 6,
        "context": "Brasil",
        "group": "PIB",
        "block_title": "PIB"
    },
    
    # Serviços
    "br_pms_services_volume": {
        "chart_config": {
            "columns": "br_pms_services_volume_total_index",
            "names": "Volume de Serviços",
            "chart_type": "line",
            "title": "Pesquisa Mensal de Serviços (PMS)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Serviços",
        "block_title": ""
    },
    "br_industrial_production": {
        "chart_config": {
            "columns": "br_industrial_production",
            "names": "Indústria",
            "chart_type": "line",
            "title": "Pesquisa Industrial Mensal (PIM)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Indústria",
        "block_title": ""
    },
    "br_pmc_retail_sales_volume": {
        "chart_config": {
            "columns": ["br_pmc_retail_sales_volume_total_index", "br_pmc_retail_sales_volume_total_amplified_index"],
            "names": "Volume de Vendas",
            "chart_type": "line",
            "title": "Pesquisa Mensal do Comércio (PMC)",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Varejo",
        "block_title": ""
    },
    
    # Sentimento
    "br_pmi": {
        "chart_config": {
            "columns": ["br_pmi_composite", "br_pmi_services"],
            "names": ["Composto", "Serviços"],
            "chart_type": "line",
            "title": "PMI",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Sentimento",
        "block_title": "PMI (S&P Global)"
    },
    "br_fgv_consumer_confidence": {
        "chart_config": {
            "columns": ["br_fgv_consumer_confidence_current_situation_index", "br_fgv_consumer_confidence_expectations_index", "br_fgv_consumer_confidence_index"],
            "names": ["Atual", "Expectativas", "Índice"],
            "chart_type": "line",
            "title": "Índice de Confiança do Consumidor",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Sentimento",
        "block_title": "Índices de Sentimento"
    },
    "br_fgv_business_confidence": {
        "chart_config": {
            "columns": ["br_fgv_business_confidence_current_situation_index", "br_fgv_business_confidence_expectations_index", "br_fgv_business_confidence_index"],
            "names": ["Atual", "Expectativas", "Índice"],
            "chart_type": "line",
            "title": "Índice de Confiança Empresarial",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Sentimento",
        "block_title": "Índices de Sentimento"
    },
    "br_fgv_industrial_confidence": {
        "chart_config": {
            "columns": ["br_fgv_industrial_confidence_current_situation_index", "br_fgv_industrial_confidence_expectations_index", "br_fgv_industrial_confidence_index"],
            "names": ["Atual", "Expectativas", "Índice"],
            "chart_type": "line",
            "title": "Índice de Confiança Industrial",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Sentimento",
        "block_title": "Índices de Sentimento"
    },
    "br_fgv_economic_uncertainty": {
        "chart_config": {
            "columns": ["br_fgv_economic_uncertainty_index"],
            "names": ["Índice"],
            "chart_type": "line",
            "title": "Índice de Incerteza Econômica",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Sentimento",
        "block_title": "Índices de Sentimento"
    },
    "br_caged_mom": {
        "chart_config": {
            "columns": "br_caged_registered_employess_total",
            "names": "Criação de Empregos Formais (MoM)",
            "chart_type": "column",
            "title": "Criação de Empregos Formais (MoM)",
            "y_axis_title": "Valor",
        },
        "transformations": [{"type": "monthly_difference", "column": "br_caged_registered_employess_total", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Emprego",
        "block_title": "CAGED"
    },
    "br_pnad_unemployment_rate": {
        "chart_config": {
            "columns": "br_pnad_unemployment_rate",
            "names": "Taxa de Desemprego",
            "chart_type": "line",
            "title": "Taxa de Desemprego",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Emprego",
        "block_title": "PNAD"
    },
    "br_bcb_credit_outstanding_total": {
        "chart_config": {
            "columns": ["br_bcb_credit_outstanding_total", "br_bcb_credit_outstanding_pf", "br_bcb_credit_outstanding_pj"],
            "names": "Saldo da Carteira de Crédito (Total)",
            "chart_type": "line",
            "title": "Saldo e Concessão de Crédito",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": ""
    },
    "br_bcb_average_interest_rate_total": {
         "chart_config": {
            "columns": ["br_bcb_average_interest_rate_total", "br_bcb_average_interest_rate_pf", "br_bcb_average_interest_rate_pj", "br_selic_target"],
            "names": "Taxa Média de Juros das Operações",
            "chart_type": "line",
            "title": "Taxa de Juros",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": ""
    },
    "br_bcb_past_due_loans": {
        "chart_config": {
            "columns": ["br_bcb_past_due_loans_pf", "br_bcb_past_due_loans_pj"],
            "names": "Inadimplência da Carteira de Crédito",
            "chart_type": "line",
            "title": "Inadimplência",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": ""
    },
     "br_bcb_household_debt_to_income": {
        "chart_config": {
            "columns": ["br_bcb_household_debt_to_income", "br_bcb_household_debt_ex_mortgage_to_income"],
            "names": "Endividamento das Famílias em Relação à Renda",
            "chart_type": "line",
            "title": "Outros Indicadores",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": ""
    },
    "br_terms_of_trade": {
        "chart_config": {
            "columns": ["br_citi_terms_of_trade_index", "br_mdic_terms_of_trade_index"],
            "names": "Termos de Troca",
            "chart_type": "line_two_yaxis",
            "title": "Balança Comercial",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": ""
    },
    "br_current_account_t12": {
        "chart_config": {
            "columns": ["br_current_account_t12", "br_current_account_to_gdp"],
            "names": "Transações Correntes",
            "chart_type": "area_line_two_yaxis",
            "title": "Balanço de Pagamentos",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": ""
    },
     "br_international_reserves_total": {
        "chart_config": {
            "columns": "br_international_reserves_total",
            "names": "Reservas Internacionais",
            "chart_type": "line",
            "title": "Reservas Internacionais",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": ""
    },
    "br_ipca_yoy": {
        "chart_config": {
            "columns": "br_ipca_yoy",
            "names": "IPCA",
            "chart_type": "line",
            "title": "Headline",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": ""
    },
    "br_focus_ipca_median": {
        "chart_config": {
            "columns": ["2025", "2026", "2027"], # Special case: columns derived from pivoted focus data
            "names": "IPCA (Mediana)",
            "chart_type": "line",
            "title": "Expectativas (Focus)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": ""
    },
     "br_ipca_grupos_yoy": {
        "chart_config": {
            "columns": ["br_ipca_yoy", "br_ipca_non_regulated_yoy", "br_ipca_regulated_yoy"],
            "names": "IPCA Grupos (% YoY)",
            "chart_type": "line",
            "title": "Grupos e Núcleos",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": ""
    },
    "crb_index_scaled": {
        "chart_config": {
            "columns": ["crb_index", "crb_fats_oils_index", "crb_food_index", "crb_livestock_index", "crb_metals_index", "crb_raw_industrials_index", "crb_textiles_index"], # Base columns before scaling
            "names": "Índice CRB (2024 = 100)",
            "chart_type": "line",
            "title": "Índices de Commodities",
            "y_axis_title": "Valor", # Scaled index
        },
        "width": 6,
        "context": "Brasil",
        "group": "Commodities",
        "block_title": ""
    },
     "br_debt_to_gdp": {
        "chart_config": {
            "columns": ["br_bcb_gross_gov_debt_to_gdp", "br_bcb_net_gov_debt_to_gdp", "br_bcb_net_public_sector_debt_to_gdp"],
            "names": ["Dívida Bruta", "Dívida Líquida", "Dívida Líquida do Setor Público"],
            "chart_type": "line",
            "title": "Dívida (% do PIB)",
            "y_axis_title": "% do PIB",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Fiscal",
        "block_title": "Fiscal"
    },
     "br_resultado_do_setor_publico": {
        "chart_config": {
            "columns": ["br_bcb_primary_result_12m_to_gdp", "br_bcb_nominal_result_12m_to_gdp", "br_bcb_interest_paid_12m_to_gdp"],
            "names": ["Resultado Primário", "Resultado Nominal", "Pagamento de Juros"],
            "chart_type": "line",
            "title": "Resultado do Setor Publico (% PIB)",
            "y_axis_title": "% do PIB",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Fiscal",
        "block_title": "Fiscal"
    },

    # === Global ===
    "global_pmi": {
        "chart_config": {
            "columns": ["global_pmi_composite", "global_pmi_manufacturing", "global_pmi_services"],
            "names": "PMI Global",
            "chart_type": "line",
            "title": "PMI Global",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Global",
        "group": "PMI",
        "block_title": ""
    },
}
