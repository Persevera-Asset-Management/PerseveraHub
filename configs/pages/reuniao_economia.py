CHARTS_ECONOMIA = {
    # === Estados Unidos ===
    # PIB
    "us_gdp_qoq": {
        "chart_config": {
            "columns": "us_gdp_qoq",
            "names": "PIB",
            "chart_type": "column",
            "title": "PIB (var. Trimestral %)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "PIB",
        "block_title": "PIB"
    },
    "us_gdp_yoy": {
        "chart_config": {
            "columns": "us_gdp_yoy",
            "names": "PIB",
            "chart_type": "column",
            "title": "PIB (var. Anual %)",
            "y_axis_title": "%",
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
            "title": "Produção Industrial e Utilização de Capacidade",
            "y_axis_title": ["Valor", "Taxa (%)"],
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Indústria",
        "block_title": "Industrial Production & Capacity Utilization"
    },
    "us_industrial_production_yoy": {
        "chart_config": {
            "columns": ["us_industrial_production_index"],
            "names": ["Produção Industrial"],
            "chart_type": "line",
            "title": "Produção Industrial (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_industrial_production_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Indústria",
        "block_title": "Industrial Production & Capacity Utilization"
    },
    "us_industrial_production_mom": {
        "chart_config": {
            "columns": ["us_industrial_production_index"],
            "names": ["Produção Industrial"],
            "chart_type": "column",
            "title": "Produção Industrial (var. Mensal %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "monthly_variation", "column": "us_industrial_production_index", "frequency": "MS"}],
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
            "title": "Retail Sales (var. Anual %)",
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
            "title": "Retail Sales (var. Mensal %)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "monthly_variation", "column": "us_advance_retail_sales_total", "frequency": "MS"}, {"type": "monthly_variation", "column": "us_advance_retail_sales_ex_auto_total", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Varejo",
        "block_title": "Advance Retail Sales"
    },
    
    # Imobiliário
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
        "group": "Imobiliário",
        "block_title": "Bloomberg Data Surprise"
    },
    "us_new_home_sales_starts_permits": {
        "chart_config": {
            "columns": ["us_new_home_sales_total", "us_housing_starts_total", "us_building_permits_total"],
            "names": ["Vendas", "Contruções", "Permissões"],
            "chart_type": "line",
            "title": "Novas Unidades Habitacionais Privadas",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Imobiliário",
        "block_title": "Vendas e Contruções"
    },
    "us_new_home_sales_starts_permits_yoy": {
        "chart_config": {
            "columns": ["us_new_home_sales_total", "us_housing_starts_total", "us_building_permits_total"],
            "names": ["Vendas", "Contruções", "Permissões"],
            "chart_type": "line",
            "title": "Novas Unidades Habitacionais Privadas (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_new_home_sales_total", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_housing_starts_total", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_building_permits_total", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Imobiliário",
        "block_title": "Vendas e Contruções"
    },
    "us_case_shiller_home_prices_index_yoy": {
        "chart_config": {
            "columns": ["us_case_shiller_home_prices_national_index", "us_case_shiller_home_prices_20_city_index", "us_zillow_home_prices_national_index"],
            "names": ["Nacional (S&P CS)", "Maiores 20 Cidades (S&P CS)", "Nacional (Zillow)"],
            "chart_type": "line",
            "title": "S&P CoreLogic Case-Shiller Price Indices (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_case_shiller_home_prices_national_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_case_shiller_home_prices_20_city_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_zillow_home_prices_national_index", "frequency": "MS"}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Imobiliário",
        "block_title": "Índices de Preços de Imóveis"
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
    "us_sloos_net_pct_banks_tightening_cni": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_tightening_cni_loans_large", "us_sloos_net_pct_banks_tightening_cni_loans_small"],
            "names": ["Grandes e médias empresas", "Pequenas empresas"],
            "chart_type": "area",
            "title": "% líquido de bancos que estão tornando os critérios de aprovação mais rigorosos",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "SLOOS: Measures of Supply and Demand for Commercial and Industrial Loans"
    },
    "us_sloos_net_pct_banks_loan_spreads": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_loan_spreads_large", "us_sloos_net_pct_banks_loan_spreads_small"],
            "names": ["Grandes e médias empresas", "Pequenas empresas"],
            "chart_type": "area",
            "title": "% líquido de bancos que estão aumentando as margens sobre seus custos de financiamento",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "SLOOS: Measures of Supply and Demand for Commercial and Industrial Loans"
    },
    "us_sloos_net_pct_banks_demand_cni": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_demand_cni_loans_large", "us_sloos_net_pct_banks_demand_cni_loans_small"],
            "names": ["Grandes e médias empresas", "Pequenas empresas"],
            "chart_type": "area",
            "title": "% líquido de bancos que estão relatando uma demanda mais forte para empréstimos comerciais e industriais",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "SLOOS: Measures of Supply and Demand for Commercial and Industrial Loans"
    },
    "us_sloos_net_pct_banks_tightening_consumer_loans": {
        "chart_config": {
            "columns": ["us_sloos_net_pct_banks_tightening_consumer_loans_credit_card", "us_sloos_net_pct_banks_tightening_consumer_loans_auto", "us_sloos_net_pct_banks_tightening_consumer_loans_others"],
            "names": ["Cartão de Crédito", "Auto", "Outros"],
            "chart_type": "area",
            "title": "% líquido de bancos que estão tornando os critérios de aprovação mais rigorosos",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Crédito",
        "block_title": "SLOOS: Measures of Supply and Demand for Consumer Loans"
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
            "columns": ["us_pmi_composite", "us_pmi_manufacturing", "us_pmi_services"],
            "names": ["Composto", "Indústria", "Serviços"],
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
            "names": ["Indústria", "Serviços"],
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
            "title": "Índices de Sentimento",
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
    "us_jolts_job_openings_detailed": {
         "chart_config": {
            "columns": ["us_jolts_job_openings_total_private", "us_jolts_job_openings_government"],
            "names": ["Privado", "Público"],
            "chart_type": "dual_axis_line",
            "title": "Abertura de Vagas (Privado e Público)",
            "y_axis_title": ["Valor", "Valor"],
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Job Openings and Labor Turnover Survey"
    },
    "us_jolts_hires_quits": {
         "chart_config": {
            "columns": ["us_jolts_hires_total_nonfarm", "us_jolts_quits_total_nonfarm"],
            "names": ["Contratações", "Saídas Voluntárias"],
            "chart_type": "dual_axis_line",
            "title": "Contratações e Saídas Voluntárias",
            "y_axis_title": ["Valor", "Valor"],
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Job Openings and Labor Turnover Survey"
    },
    "us_jolts_turnover_rates": {
         "chart_config": {
            "columns": ["us_jolts_job_openings_rate_total_nonfarm", "us_jolts_hiring_rate_total_nonfarm", "us_jolts_quits_rate_total_nonfarm", "us_jolts_layoffs_rate_total_nonfarm"],
            "names": ["Abertura de Vagas", "Contratações", "Saídas Voluntárias", "Demissões"],
            "chart_type": "line",
            "title": "Rotatividade de Emprego",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Job Openings and Labor Turnover Survey"
    },
    "us_jolts_hiring_rate": {
         "chart_config": {
            "columns": ["us_jolts_hiring_rate_total_nonfarm", "us_jolts_hiring_rate_total_private"],
            "names": ["Total", "Privado"],
            "chart_type": "line",
            "title": "Taxa de Contratação",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Emprego",
        "block_title": "Job Openings and Labor Turnover Survey"
    },
    # "us_jolts_layoffs_composition": {
    #      "chart_config": {
    #         "columns": ["us_jolts_quits_total_nonfarm", "us_jolts_layoffs_total_nonfarm", "us_jolts_separations_other_total_nonfarm"],
    #         "names": ["Saídas Voluntárias", "Demissões", "Outras"],
    #         "chart_type": "area",
    #         "stacked": True,
    #         "title": "Composição das Demissões",
    #         "y_axis_title": "%",
    #     },
    #     "width": 6,
    #     "context": "Estados Unidos",
    #     "group": "Emprego",
    #     "block_title": "Job Openings and Labor Turnover Survey"
    # },
    "us_adp_nonfarm_private_payrolls_mom": {
         "chart_config": {
            "columns": "us_adp_nonfarm_private_payrolls",
            "names": "Var. Mensal",
            "chart_type": "column",
            "title": "Non-Farm Private Payroll (var. Mensal)",
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
            "title": "Non-Farm Private Payroll (var. Anual %)",
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
            "title": "Non-Farm Private Payroll (var. Mensal)",
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
            "title": "Non-Farm Private Payroll (var. Mensal)",
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
            "title": "Non-Farm Private Payroll (var. Anual %)",
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
            "title": "Non-Farm Payroll (var. Mensal)",
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
            "title": "Non-Farm Payroll (var. Anual %)",
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
            "names": "Mediana",
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
    "us_cpi_saar": {
        "chart_config": {
            "columns": ["us_cpi_index", "us_cpi_core_index"],
            "names": ["CPI", "CPI (3-month SAAR)", "Core CPI", "Core CPI (3-month SAAR)"],
            "chart_type": "line",
            "title": "CPI (3-month SAAR)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_cpi_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_cpi_core_index", "frequency": "MS"}, {"type": "saar", "column": "us_cpi_index", "period_months": 3, "calculate_pct_change": True}, {"type": "saar", "column": "us_cpi_core_index", "period_months": 3, "calculate_pct_change": True}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Inflação",
        "block_title": "Inflação ao Consumidor"
    },
    "us_pce_saar": {
        "chart_config": {
            "columns": ["us_pce_index", "us_pce_core_index"],
            "names": ["PCE", "PCE (3-month SAAR)", "Core PCE", "Core PCE (3-month SAAR)"],
            "chart_type": "line",
            "title": "PCE (3-month SAAR)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "yearly_variation", "column": "us_pce_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "us_pce_core_index", "frequency": "MS"}, {"type": "saar", "column": "us_pce_index", "period_months": 3, "calculate_pct_change": True}, {"type": "saar", "column": "us_pce_core_index", "period_months": 3, "calculate_pct_change": True}],
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

    # Fiscal
    "us_total_public_debt_to_gdp": {
        "chart_config": {
            "columns": "us_total_public_debt_to_gdp",
            "names": "Dívida Pública / PIB",
            "chart_type": "line",
            "title": "Dívida Pública / PIB",
            "y_axis_title": "% do PIB",
        },
        "width": 6,
        "context": "Estados Unidos",
        "group": "Fiscal",
        "block_title": "Dívida Pública"
    },
    "us_total_public_debt_to_gdp_participants": {
        "chart_config": {
            "columns": ["us_federal_debt_held_by_fed_banks_to_gdp", "us_federal_debt_held_by_foreign_investors_to_gdp", "us_federal_debt_held_by_private_investors_to_gdp", "us_federal_debt_held_by_trusts_to_gdp"],
            "names": ["Fed Banks", "Foreign Investors", "Private Investors", "Trusts"],
            "chart_type": "line",
            "title": "Dívida Pública / PIB (por Participantes)",
            "y_axis_title": "% do PIB",
        },

        "width": 6,
        "context": "Estados Unidos",
        "group": "Fiscal",
        "block_title": "Dívida Pública"
    },
    "us_total_public_debt_participants": {
        "chart_config": {
            "columns": ["us_federal_debt_held_by_fed_banks", "us_federal_debt_held_by_foreign_investors", "us_federal_debt_held_by_private_investors", "us_federal_debt_held_by_trusts"],
            "names": ["Fed Banks", "Foreign Investors", "Private Investors", "Trusts"],
            "chart_type": "area",
            "stacking": "percent",
            "title": "Dívida Pública (por Participantes)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "divide", "column": "us_federal_debt_held_by_trusts", "scalar": 1e3}],
        "width": 6,
        "context": "Estados Unidos",
        "group": "Fiscal",
        "block_title": "Dívida Pública"
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
    "br_ibcbr_yoy": {
        "chart_config": {
            "columns": "br_ibcbr_index",
            "names": "Índice",
            "chart_type": "line",
            "title": "IBC-Br (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_ibcbr_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "IBC-Br",
        "block_title": "IBC-Br"
    },
    "br_ibcbr_mom": {
        "chart_config": {
            "columns": "br_ibcbr_index",
            "names": "Índice",
            "chart_type": "column",
            "title": "IBC-Br (var. Mensal %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "monthly_variation", "column": "br_ibcbr_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "IBC-Br",
        "block_title": "IBC-Br"
    },
    
    # PIB
    "br_gdp_qoq": {
         "chart_config": {
            "columns": "br_gdp_index",
            "names": "PIB",
            "chart_type": "column",
            "title": "PIB (var. Trimestral %)",
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
            "names": "PIB (var. Anual %)",
            "chart_type": "column",
            "title": "PIB (var. Anual %)",
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
            "names": "Índice",
            "chart_type": "line",
            "title": "Volume de Serviços",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Serviços",
        "block_title": "Pesquisa Mensal de Serviços (PMS)"
    },
    "br_pms_services_volume_yoy": {
        "chart_config": {
            "columns": "br_pms_services_volume_total_index",
            "names": "Índice",
            "chart_type": "line",
            "title": "Volume de Serviços (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_pms_services_volume_total_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Serviços",
        "block_title": "Pesquisa Mensal de Serviços (PMS)"
    },
    "br_pms_services_volume_mom": {
        "chart_config": {
            "columns": "br_pms_services_volume_total_index",
            "names": "Índice",
            "chart_type": "column",
            "title": "Volume de Serviços (var. Mensal %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "monthly_variation", "column": "br_pms_services_volume_total_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Serviços",
        "block_title": "Pesquisa Mensal de Serviços (PMS)"
    },

    # Indústria
    "br_industrial_production": {
        "chart_config": {
            "columns": "br_industrial_production",
            "names": "Índice",
            "chart_type": "line",
            "title": "Produção Industrial",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Indústria",
        "block_title": "Pesquisa Industrial Mensal (PIM)"
    },
    "br_industrial_production_yoy": {
        "chart_config": {
            "columns": "br_industrial_production",
            "names": "Índice",
            "chart_type": "line",
            "title": "Produção Industrial (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_industrial_production", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Indústria",
        "block_title": "Pesquisa Industrial Mensal (PIM)"
    },
    "br_industrial_production_mom": {
        "chart_config": {
            "columns": "br_industrial_production",
            "names": "Índice",
            "chart_type": "column",
            "title": "Produção Industrial (var. Mensal %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "monthly_variation", "column": "br_industrial_production", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Indústria",
        "block_title": "Pesquisa Industrial Mensal (PIM)"
    },

    # Varejo
    "br_pmc_retail_sales_volume": {
        "chart_config": {
            "columns": ["br_pmc_retail_sales_volume_total_index", "br_pmc_retail_sales_volume_total_amplified_index"],
            "names": ["Índice", "Índice Ampliado"],
            "chart_type": "line",
            "title": "Volume de Vendas",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Varejo",
        "block_title": "Pesquisa Mensal do Comércio (PMC)"
    },
    "br_pmc_retail_sales_volume_yoy": {
        "chart_config": {
            "columns": ["br_pmc_retail_sales_volume_total_index", "br_pmc_retail_sales_volume_total_amplified_index"],
            "names": ["Índice", "Índice Ampliado"],
            "chart_type": "line",
            "title": "Volume de Vendas (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_pmc_retail_sales_volume_total_index", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_pmc_retail_sales_volume_total_amplified_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Varejo",
        "block_title": "Pesquisa Mensal do Comércio (PMC)"
    },
    "br_pmc_retail_sales_volume_mom": {
        "chart_config": {
            "columns": ["br_pmc_retail_sales_volume_total_index", "br_pmc_retail_sales_volume_total_amplified_index"],
            "names": ["Índice", "Índice Ampliado"],
            "chart_type": "column",
            "title": "Volume de Vendas (var. Mensal %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "monthly_variation", "column": "br_pmc_retail_sales_volume_total_index", "frequency": "MS"}, {"type": "monthly_variation", "column": "br_pmc_retail_sales_volume_total_amplified_index", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Varejo",
        "block_title": "Pesquisa Mensal do Comércio (PMC)"
    },

    # Sentimento
    "br_pmi": {
        "chart_config": {
            "columns": ["br_pmi_composite", "br_pmi_manufacturing", "br_pmi_services"],
            "names": ["Composto", "Indústria", "Serviços"],
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
    
    # Emprego
    "br_caged_mom": {
        "chart_config": {
            "columns": "br_caged_registered_employess_total",
            "names": "Criação de Empregos Formais (var. Mensal)",
            "chart_type": "column",
            "title": "Criação de Empregos Formais (var. Mensal)",
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
    "br_pnad_personal_real_income": {
        "chart_config": {
            "columns": ["br_pnad_personal_real_income_formal_work_contract", "br_pnad_personal_real_income_non_formal_work_contract", "br_pnad_personal_real_income_private_sector", "br_pnad_personal_real_income_total"],
            "names": ["Formal", "Não Formal", "Setor Privado", "Total"],
            "chart_type": "line",
            "title": "Renda Real Mensal",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_pnad_personal_real_income_formal_work_contract", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_pnad_personal_real_income_non_formal_work_contract", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_pnad_personal_real_income_private_sector", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_pnad_personal_real_income_total", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Emprego",
        "block_title": "PNAD"
    },

    # Crédito
    "br_bcb_credit_outstanding": {
        "chart_config": {
            "columns": ["br_bcb_credit_outstanding_total", "br_bcb_credit_outstanding_pf", "br_bcb_credit_outstanding_pj"],
            "names": ["Total", "PF", "PJ"],
            "chart_type": "line",
            "title": "Saldo da Carteira de Crédito (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_bcb_credit_outstanding_total", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_credit_outstanding_pf", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_credit_outstanding_pj", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Saldo da Carteira de Crédito"
    },
    "br_bcb_credit_outstanding_details": {
        "chart_config": {
            "columns": ["br_bcb_nonearmarked_credit_outstanding_pj", "br_bcb_earmarked_credit_outstanding_pj", "br_bcb_nonearmarked_credit_outstanding_pf", "br_bcb_earmarked_credit_outstanding_pf"],
            "names": ["PJ (Recursos Livres)", "PJ (Direcionados)", "PF (Recursos Livres)", "PF (Direcionados)"],
            "chart_type": "line",
            "title": "Saldo da Carteira de Crédito (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_bcb_nonearmarked_credit_outstanding_pj", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_earmarked_credit_outstanding_pj", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_nonearmarked_credit_outstanding_pf", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_earmarked_credit_outstanding_pf", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Saldo da Carteira de Crédito"
    },
    "br_bcb_new_operations": {
        "chart_config": {
            "columns": ["br_bcb_new_operations_pj", "br_bcb_new_operations_pf"],
            "names": ["PJ", "PF"],
            "chart_type": "line",
            "title": "Concessão de Crédito (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_bcb_new_operations_pj", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_new_operations_pf", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Concessão de Crédito"
    },
    "br_bcb_new_operations_details": {
        "chart_config": {
            "columns": ["br_bcb_nonearmarked_new_operations_pj", "br_bcb_earmarked_new_operations_pj", "br_bcb_nonearmarked_new_operations_pf", "br_bcb_earmarked_new_operations_pf"],
            "names": ["PJ (Recursos Livres)", "PJ (Direcionados)", "PF (Recursos Livres)", "PF (Direcionados)"],
            "chart_type": "line",
            "title": "Concessão de Crédito (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_bcb_nonearmarked_new_operations_pj", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_earmarked_new_operations_pj", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_nonearmarked_new_operations_pf", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_earmarked_new_operations_pf", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Concessão de Crédito"
    },
    "br_bcb_sfn_loans": {
        "chart_config": {
            "columns": ["br_bcb_sfn_loans_to_government", "br_bcb_sfn_loans_to_companies", "br_bcb_sfn_loans_to_individuals"],
            "names": ["Governo", "Empresas", "Indivíduos"],
            "chart_type": "line",
            "title": "Saldo de Empréstimos e Financiamentos do SFN (var. Anual %)",
            "y_axis_title": "%",
        },
        "transformations": [{"type": "yearly_variation", "column": "br_bcb_sfn_loans_to_government", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_sfn_loans_to_companies", "frequency": "MS"}, {"type": "yearly_variation", "column": "br_bcb_sfn_loans_to_individuals", "frequency": "MS"}],
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Saldo e Concessão de Crédito"
    },

    "br_bcb_average_interest_rate": {
        "chart_config": {
            "columns": ["br_bcb_average_interest_rate_total", "br_bcb_average_interest_rate_pf", "br_bcb_average_interest_rate_pj"],
            "names": ["Total", "PF", "PJ"],
            "chart_type": "line",
            "title": "Taxa Média de Juros das Operações",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Taxa de Juros"
    },
    "br_bcb_average_interest_rate_details": {
        "chart_config": {
            "columns": ["br_bcb_average_interest_rate_nonearmarked_pf", "br_bcb_average_interest_rate_nonearmarked_pj", "br_bcb_average_interest_rate_earmarked_pf", "br_bcb_average_interest_rate_earmarked_pj"],
            "names": ["PF (Recursos Livres)", "PJ (Recursos Livres)", "PF (Direcionados)", "PJ (Direcionados)"],
            "chart_type": "line",
            "title": "Taxa Média de Juros das Operações (Abertura)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Taxa de Juros"
    },
    "br_bcb_average_interest_rate_details_pj": {
        "chart_config": {
            "columns": ["br_bcb_average_interest_rate_nonearmarked_discount_pj", "br_bcb_average_interest_rate_nonearmarked_working_capital_pj"],
            "names": ["Desconto de Dupl. e Receb.", "Capital de Giro"],
            "chart_type": "line",
            "title": "Taxa Média de Juros das Operações (Abertura - PJ)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Taxa de Juros"
    },
    "br_bcb_average_interest_rate_details_pf": {
        "chart_config": {
            "columns": ["br_bcb_average_interest_rate_nonearmarked_overdraft_pf", "br_bcb_average_interest_rate_nonearmarked_personal_credit_pf", "br_bcb_average_interest_rate_nonearmarked_payroll_deducted_personal_loans_pf", "br_bcb_average_interest_rate_nonearmarked_credit_card_revolving_credit_pf", "br_bcb_average_interest_rate_nonearmarked_credit_card_financing_pf"],
            "names": ["Cheque Especial", "Crédito Pessoal Não Consignado", "Crédito Pessoal Consignado", "Cartão de Crédito Rotativo", "Cartão de Crédito Parcelado"],
            "chart_type": "line",
            "title": "Taxa Média de Juros das Operações (Abertura - PF)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Taxa de Juros"
    },
    
    "br_bcb_past_due_loans": {
        "chart_config": {
            "columns": ["br_bcb_past_due_loans_pf", "br_bcb_past_due_loans_pj"],
            "names": ["PF", "PJ"],
            "chart_type": "line",
            "title": "Carteira de Crédito",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Inadimplência"
    },
    "br_bcb_past_due_loans_details": {
        "chart_config": {
            "columns": ["br_bcb_past_due_loans_nonearmarked_pj", "br_bcb_past_due_loans_earmarked_pj", "br_bcb_past_due_loans_nonearmarked_pf", "br_bcb_past_due_loans_earmarked_pf"],
            "names": ["PJ (Recursos Livres)", "PJ (Direcionados)", "PF (Recursos Livres)", "PF (Direcionados)"],
            "chart_type": "line",
            "title": "Carteira de Crédito (Abertura)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Inadimplência"
    },
    "br_bcb_icc": {
        "chart_config": {
            "columns": ["br_bcb_icc_total", "br_bcb_icc_pf", "br_bcb_icc_pj"],
            "names": ["Total", "PF", "PJ"],
            "chart_type": "line",
            "title": "Indicador de Custo de Crédito (ICC)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Custo de Crédito (ICC)"
    },
    "br_bcb_icc_spread": {
        "chart_config": {
            "columns": ["br_bcb_icc_spread_total", "br_bcb_icc_spread_pf", "br_bcb_icc_spread_pj"],
            "names": ["Total", "PF", "PJ"],
            "chart_type": "line",
            "title": "Spread do Custo de Crédito (ICC)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Custo de Crédito (ICC)"
    },
    "br_bcb_household_debt": {
        "chart_config": {
            "columns": ["br_bcb_household_debt_to_income", "br_bcb_household_debt_ex_mortgage_to_income"],
            "names": ["Total", "Total (ex Crédito Habitacional)"],
            "chart_type": "line",
            "title": "Endividamento das Famílias em Relação à Renda",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Endividamento e Compromentimento de Renda"
    },
    "br_bcb_household_debt_service": {
        "chart_config": {
            "columns": ["br_bcb_household_debt_service_ratio", "br_bcb_household_debt_service_ratio_interest", "br_bcb_household_debt_service_ratio_ex_mortgage", "br_bcb_household_debt_service_ratio_principal"],
            "names": ["Serviço da Dívida", "Juros da Dívida", "Serviço da Dívida (ex Crédito Habitacional)", "Amortização da Dívida"],
            "chart_type": "line",
            "title": "Comprometimento de Renda das Famílias",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Crédito",
        "block_title": "Endividamento e Compromentimento de Renda"
    },

    # Setor Externo
    "br_terms_of_trade": {
        "chart_config": {
            "columns": ["br_citi_terms_of_trade_index", "br_mdic_terms_of_trade_index"],
            "names": ["Índice de Termos de Troca (Citi)", "Índice de Termos de Troca (MDIC)"],
            "chart_type": "dual_axis_line",
            "title": "Termos de Troca",
            "y_axis_title": ("Valor", "Valor"),
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": "Balança Comercial"
    },
    "br_exports_imports": {
        "chart_config": {
            "columns": ["br_trade_balance_fob_exports", "br_trade_balance_fob_imports"],
            "names": ["Exportações", "Importações"],
            "chart_type": "line",
            "title": "Exportações e Importações",
            "y_axis_title": "Valor",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": "Balança Comercial"
    },
    "br_current_account": {
        "chart_config": {
            "columns": ["br_current_account_to_gdp", "br_current_account_t12"],
            "names": ["% do PIB", "Acumulado 12 meses"],
            "chart_type": "dual_axis_line_area",
            "title": "Transações Correntes",
            "y_axis_title": ("% do PIB", "Valor"),
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": "Balanço de Pagamentos"
    },
    "br_direct_investment_liabilities": {
        "chart_config": {
            "columns": ["br_direct_investment_liabilities_to_gdp", "br_direct_investment_liabilities_t12"],
            "names": ["% do PIB", "Acumulado 12 meses"],
            "chart_type": "dual_axis_line_area",
            "title": "Investimentos Diretos no País (IDP) - Ingresso Líquido",
            "y_axis_title": ("% do PIB", "Valor"),
        },
        "width": 6,
        "context": "Brasil",
        "group": "Setor Externo",
        "block_title": "Balanço de Pagamentos"
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
        "block_title": "Reservas Internacionais"
    },

    # Inflação
    "br_ipca_yoy": {
        "chart_config": {
            "columns": ["br_ipca_yoy", "br_ipca_sa_mom"],
            "names": ["IPCA", "3-month SAAR"],
            "chart_type": "line",
            "title": "IPCA (var. Anual %)",
            "y_axis_title": "Taxa (%)",
        },
        "transformations": [{"type": "saar", "column": "br_ipca_sa_mom", "period_months": 3, "calculate_pct_change": False}],
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": "Headline"
    },
    "br_ipca_mom": {
        "chart_config": {
            "columns": ["br_ipca_sa_mom", "br_ipca15_mom"],
            "names": ["IPCA", "IPCA-15"],
            "chart_type": "column",
            "title": "IPCA (var. Mensal %)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": "Headline"
    },
    "br_focus_ipca_median": {
        "chart_config": {
            "columns": ["br_focus_ipca_median_2025", "br_focus_ipca_median_2026", "br_focus_ipca_median_2027"],
            "names": ["2025", "2026", "2027"],
            "chart_type": "line",
            "title": "IPCA (Mediana)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": "Expectativas (Focus)"
    },
    "br_ipca_grupos_yoy": {
        "chart_config": {
            "columns": ["br_ipca_yoy", "br_ipca_non_regulated_yoy", "br_ipca_regulated_yoy"],
            "names": ["IPCA", "Livres", "Administrados"],
            "chart_type": "line",
            "title": "IPCA Grupos (var. Anual %)",
            "y_axis_title": "Taxa (%)",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": "Grupos e Núcleos"
    },
    "br_ipca_grupos_outros_yoy": {
        "chart_config": {
            "columns": ["br_ipca_yoy", "br_ipca_services_yoy", "br_ipca_durable_yoy", "br_ipca_semi_durable_yoy", "br_ipca_non_durable_yoy"],
            "names": ["IPCA", "Serviços", "Duráveis", "Semi-Duráveis", "Não-Duráveis"],
            "chart_type": "line",
            "title": "IPCA Grupos (var. Anual %)",
            "y_axis_title": "%",
        },
        "width": 6,
        "context": "Brasil",
        "group": "Inflação",
        "block_title": "Grupos e Núcleos"
    },

    # Commodities
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

    # Fiscal
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
        "transformations": [{"type": "multiply", "column": "br_bcb_primary_result_12m_to_gdp", "scalar": -1}, {"type": "multiply", "column": "br_bcb_nominal_result_12m_to_gdp", "scalar": -1}, {"type": "multiply", "column": "br_bcb_interest_paid_12m_to_gdp", "scalar": -1}],
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
