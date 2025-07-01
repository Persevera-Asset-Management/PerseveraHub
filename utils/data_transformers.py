import pandas as pd
import numpy as np
from typing import Dict, List, Union, Any
import streamlit as st

class DataTransformer:
    """Base class for all data transformations"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Default implementation returns data unchanged"""
        return data

class YearlyVariationTransformer(DataTransformer):
    """Calculates yearly variation for a given column respecting its frequency"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        freq = config.get('frequency') # Get the target frequency ('M', 'Q', 'A', etc.)

        # If frequency is not provided or column doesn't exist, return original data
        # This maintains backward compatibility for daily data or cases where freq isn't set
        if not column or column not in data.columns:
             print(f"Warning: Column '{column}' not found for yearly variation. Skipping.")
             return data

        result = data.copy()
        new_column_name = f"{column}_yoy"

        if not freq:
            # Original behavior: Assume daily data (252 periods) if frequency not specified
            print(f"Warning: Frequency not specified for {column}. Assuming daily data for yearly variation.")
            result[new_column_name] = result[column].pct_change(periods=252) * 100
            return result

        # Proceed with frequency-aware calculation
        col_data = result[[column]].dropna() # Work on non-NaN data

        # Ensure index is DatetimeIndex
        if not isinstance(col_data.index, pd.DatetimeIndex):
            print(f"Error: Index for {column} is not DatetimeIndex. Cannot perform frequency-aware transformation.")
            return data # Return original data to avoid errors

        try:
            # Resample to the target frequency, taking the last available value in the period
            resampled_data = col_data.resample(freq).last()

            # Calculate yearly variation on the resampled data
            # For monthly freq ('M'), periods=12; quarterly ('Q'), periods=4; annual ('A'), periods=1
            periods_map = {'M': 12, 'Q': 4, 'A': 1}
            # Handle variations like 'MS' (Month Start), 'QS', 'AS'
            clean_freq = freq.upper().replace('S', '')
            periods = periods_map.get(clean_freq)

            if periods is None:
                 print(f"Warning: Unsupported frequency '{freq}' for yearly variation on {column}. Skipping transformation.")
                 return result # Return original data

            variation = resampled_data[column].pct_change(periods=periods) * 100

            # Reindex back to the original DataFrame's index, forward filling the calculated values
            # Ensure the index used for reindexing exists entirely in the variation's index
            # This might require aligning indexes first if resampling created new dates not in original
            aligned_variation = variation.reindex(result.index)
            result[new_column_name] = aligned_variation

        except Exception as e:
            print(f"Error during yearly variation transformation for {column} with freq {freq}: {e}")
            # Optionally return original data in case of error, or re-raise
            return data # Safest option for now

        return result

class MonthlyVariationTransformer(DataTransformer):
    """Calculates monthly variation for a given column, respecting its frequency if provided."""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        freq = config.get('frequency') # Get the target frequency, e.g., 'M', 'W', 'D'

        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for monthly variation. Skipping.")
            return data

        result = data.copy()
        new_column_name = f"{column}_mom"

        if not freq:
            # Original behavior: Assume daily-like data (21 periods) if frequency not specified
            print(f"Warning: Frequency not specified for {column}. Assuming daily-like data for monthly variation (21 periods).")
            result[new_column_name] = result[column].pct_change(periods=21) * 100
            return result

        # Proceed with frequency-aware calculation
        col_data = result[[column]].dropna() # Work on non-NaN data

        # Ensure index is DatetimeIndex
        if not isinstance(col_data.index, pd.DatetimeIndex):
            print(f"Error: Index for {column} is not DatetimeIndex. Cannot perform frequency-aware monthly transformation.")
            return data # Return original data to avoid errors

        try:
            # Determine periods for pct_change based on the provided frequency
            # This map defines how many periods of the given frequency constitute "one month"
            _freq_upper = freq.upper()
            cleaned_base_freq = None
            if _freq_upper in ['M', 'MS']: # Monthly frequencies
                cleaned_base_freq = 'M'
            elif _freq_upper.startswith('W'): # Weekly frequencies (W, W-SUN, W-MON, etc.)
                cleaned_base_freq = 'W'
            elif _freq_upper == 'D': # Daily frequency
                cleaned_base_freq = 'D'
            elif _freq_upper == 'B': # Business daily frequency
                cleaned_base_freq = 'B'

            # Periods needed for a month-over-month calculation based on the data's (resampled) frequency
            periods_map_for_mom = {'M': 1, 'W': 4, 'D': 21, 'B': 21} # Approx for W, D, B
            periods = periods_map_for_mom.get(cleaned_base_freq)

            if periods is None:
                print(f"Warning: Unsupported frequency '{freq}' for monthly variation on {column}. Skipping transformation.")
                return data # Return original data, similar to YearlyVariationTransformer

            # Resample to the target frequency, taking the last available value in the period
            resampled_data = col_data.resample(freq).last() # Use the original `freq` from config

            # Calculate monthly variation on the resampled data
            variation = resampled_data[column].pct_change(periods=periods) * 100

            # Reindex back to the original DataFrame's index
            aligned_variation = variation.reindex(result.index)
            result[new_column_name] = aligned_variation

        except Exception as e:
            print(f"Error during monthly variation transformation for {column} with freq {freq}: {e}")
            return data # Safest option, return original data in case of error

        return result

class QuarterlyVariationTransformer(DataTransformer):
    """Calculates quarterly variation for a given column, respecting its frequency if provided."""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        freq = config.get('frequency') # Get the target frequency, e.g., 'Q', 'M', 'D'

        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for quarterly variation. Skipping.")
            return data

        result = data.copy()
        new_column_name = f"{column}_qoq"

        if not freq:
            # Default behavior: Assume daily-like data (63 periods) if frequency not specified
            # (approx. 21 days/month * 3 months/quarter)
            print(f"Warning: Frequency not specified for {column}. Assuming daily-like data for quarterly variation (63 periods).")
            result[new_column_name] = result[column].pct_change(periods=63) * 100
            return result

        # Proceed with frequency-aware calculation
        col_data = result[[column]].dropna() # Work on non-NaN data

        # Ensure index is DatetimeIndex
        if not isinstance(col_data.index, pd.DatetimeIndex):
            print(f"Error: Index for {column} is not DatetimeIndex. Cannot perform frequency-aware quarterly transformation.")
            return data # Return original data to avoid errors

        try:
            # Determine periods for pct_change based on the provided frequency
            # This map defines how many periods of the given frequency constitute "one quarter"
            _freq_upper = freq.upper()
            cleaned_base_freq = None
            if _freq_upper in ['Q', 'QS']: # Quarterly frequencies
                cleaned_base_freq = 'Q'
            elif _freq_upper in ['M', 'MS']: # Monthly frequencies
                cleaned_base_freq = 'M'
            # Add other base frequencies as needed, e.g., 'D', 'B', 'W'
            elif _freq_upper.startswith('W'): # Weekly frequencies
                 cleaned_base_freq = 'W'
            elif _freq_upper == 'D': # Daily frequency
                 cleaned_base_freq = 'D'
            elif _freq_upper == 'B': # Business daily frequency
                 cleaned_base_freq = 'B'


            # Periods needed for a quarter-over-quarter calculation based on the data's (resampled) frequency
            periods_map_for_qoq = {'Q': 1, 'M': 3, 'W': 13, 'D': 63, 'B': 63} # Approx for W, D, B
            periods = periods_map_for_qoq.get(cleaned_base_freq)

            # Resample to the target frequency (from config), taking the last available value
            resampled_data = col_data.resample(freq).last()

            # Calculate quarterly variation on the resampled data
            variation = resampled_data[column].pct_change(periods=periods) * 100

            # Reindex back to the original DataFrame's index
            # Using ffill to propagate last known good variation if original index is more granular
            aligned_variation = variation.reindex(result.index, method='ffill')
            result[new_column_name] = aligned_variation

            if periods is None:
                print(f"Warning: Unsupported frequency '{freq}' for monthly variation on {column}. Skipping transformation.")
                return data # Return original data, similar to YearlyVariationTransformer

            # Resample to the target frequency, taking the last available value in the period
            resampled_data = col_data.resample(freq).last() # Use the original `freq` from config

            # Calculate monthly variation on the resampled data
            variation = resampled_data[column].pct_change(periods=periods) * 100

            # Reindex back to the original DataFrame's index
            aligned_variation = variation.reindex(result.index)
            result[new_column_name] = aligned_variation


        except Exception as e:
            print(f"Error during quarterly variation transformation for {column} with freq {freq}: {e}")
            return data # Safest option, return original data in case of error

        return result

class MonthlyDifferenceTransformer(DataTransformer):
    """Calculates monthly difference for a given column, respecting its frequency if provided."""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        freq = config.get('frequency') # Get the target frequency, e.g., 'M', 'W', 'D'

        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for monthly difference. Skipping.")
            return data

        result = data.copy()
        new_column_name = f"{column}_mom_diff"

        if not freq:
            # Original behavior: Assume daily-like data (21 periods) if frequency not specified
            print(f"Warning: Frequency not specified for {column}. Assuming daily-like data for monthly difference (21 periods).")
            result[new_column_name] = result[column].diff(periods=21)
            return result

        # Proceed with frequency-aware calculation
        col_data = result[[column]].dropna() # Work on non-NaN data

        # Ensure index is DatetimeIndex
        if not isinstance(col_data.index, pd.DatetimeIndex):
            print(f"Error: Index for {column} is not DatetimeIndex. Cannot perform frequency-aware monthly difference transformation.")
            return data # Return original data to avoid errors

        try:
            # Determine periods for difference calculation based on the provided frequency
            # This map defines how many periods of the given frequency constitute "one month"
            _freq_upper = freq.upper()
            cleaned_base_freq = None
            if _freq_upper in ['M', 'MS']: # Monthly frequencies
                cleaned_base_freq = 'M'
            elif _freq_upper.startswith('W'): # Weekly frequencies (W, W-SUN, W-MON, etc.)
                cleaned_base_freq = 'W'
            elif _freq_upper == 'D': # Daily frequency
                cleaned_base_freq = 'D'
            elif _freq_upper == 'B': # Business daily frequency
                cleaned_base_freq = 'B'

            # Periods needed for a month-over-month calculation based on the data's (resampled) frequency
            periods_map_for_monthly_calc = {'M': 1, 'W': 4, 'D': 21, 'B': 21} # Approx for W, D, B
            periods = periods_map_for_monthly_calc.get(cleaned_base_freq)

            if periods is None:
                print(f"Warning: Unsupported frequency '{freq}' for monthly difference on {column}. Skipping transformation.")
                return data # Return original data

            # Resample to the target frequency, taking the last available value in the period
            resampled_data = col_data.resample(freq).last() # Use the original `freq` from config

            # Calculate monthly difference on the resampled data
            calculated_difference = resampled_data[column].diff(periods=periods)

            # Reindex back to the original DataFrame's index, forward filling the values
            aligned_difference = calculated_difference.reindex(result.index)
            result[new_column_name] = aligned_difference

        except Exception as e:
            print(f"Error during monthly difference transformation for {column} with freq {freq}: {e}")
            return data # Safest option, return original data in case of error

        return result

class MovingAverageTransformer(DataTransformer):
    """Calculates moving average for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 21)  # Default to 21 days (approx. 1 month)
        
        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for moving average. Skipping.")
            return data
            
        result = data.copy()
        
        # Calculate moving average
        result[f"{column}_ma{window}"] = result[column].rolling(window=window).mean()
        
        return result

class RollingSumTransformer(DataTransformer):
    """Calculates rolling sum for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 12)
        
        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for rolling sum. Skipping.")
            return data
            
        result = data.copy()
        
        # Calculate rolling sum
        result[f"{column}_rolling_sum{window}"] = result[column].rolling(window=window).sum()
        
        return result

class RollingSumPlusYearlyVariationTransformer(DataTransformer):
    """Calculates rolling sum and yearly variation for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 12)
        freq = config.get('frequency') # Get the target frequency ('M', 'Q', 'A', etc.)

        # If frequency is not provided or column doesn't exist, return original data
        # This maintains backward compatibility for daily data or cases where freq isn't set
        if not column or column not in data.columns:
             print(f"Warning: Column '{column}' not found for yearly variation. Skipping.")
             return data

        result = data.copy()
        new_column_name = f"{column}_rolling_sum_yoy"

        if not freq:
            # Original behavior: Assume daily data (252 periods) if frequency not specified
            print(f"Warning: Frequency not specified for {column}. Assuming daily data for yearly variation.")
            result[new_column_name] = result[column].rolling(window=window).sum().pct_change(periods=252) * 100
            return result

        # Proceed with frequency-aware calculation
        col_data = result[[column]].dropna() # Work on non-NaN data

        # Ensure index is DatetimeIndex
        if not isinstance(col_data.index, pd.DatetimeIndex):
            print(f"Error: Index for {column} is not DatetimeIndex. Cannot perform frequency-aware transformation.")
            return data # Return original data to avoid errors

        try:
            # Resample to the target frequency, taking the last available value in the period
            resampled_data = col_data.resample(freq).last()

            # Calculate yearly variation on the resampled data
            # For monthly freq ('M'), periods=12; quarterly ('Q'), periods=4; annual ('A'), periods=1
            periods_map = {'M': 12, 'Q': 4, 'A': 1}
            # Handle variations like 'MS' (Month Start), 'QS', 'AS'
            clean_freq = freq.upper().replace('S', '')
            periods = periods_map.get(clean_freq)

            if periods is None:
                 print(f"Warning: Unsupported frequency '{freq}' for yearly variation on {column}. Skipping transformation.")
                 return result # Return original data

            variation = resampled_data[column].rolling(window=window).sum().pct_change(periods=periods) * 100

            # Reindex back to the original DataFrame's index, forward filling the calculated values
            # Ensure the index used for reindexing exists entirely in the variation's index
            # This might require aligning indexes first if resampling created new dates not in original
            aligned_variation = variation.reindex(result.index)
            result[new_column_name] = aligned_variation

        except Exception as e:
            print(f"Error during yearly variation transformation for {column} with freq {freq}: {e}")
            # Optionally return original data in case of error, or re-raise
            return data # Safest option for now

        return result

class RollingMaxTransformer(DataTransformer):
    """Calculates rolling maximum for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 252)  # Default to 252 days (approx. 1 year)
        
        if not column or column not in data.columns:
            return data
            
        result = data.copy()
        
        # Calculate rolling maximum
        result[f"{column}_max{window}"] = result[column].rolling(window=window).max()
        
        return result

class RollingMinTransformer(DataTransformer):
    """Calculates rolling minimum for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 252)  # Default to 252 days (approx. 1 year)
        
        if not column or column not in data.columns:
            return data
            
        result = data.copy()
        
        # Calculate rolling minimum
        result[f"{column}_min{window}"] = result[column].rolling(window=window).min()
        
        return result

class RollingVolatilityTransformer(DataTransformer):
    """Calculates rolling volatility (standard deviation) for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        window = config.get('window', 252)  # Default to 252 days (approx. 1 year)
        annualized = config.get('annualized', False)  # Option to annualize volatility
        periods_in_year = config.get('periods_in_year', 252) # Added for flexible annualization
        calculate_on_returns = config.get('calculate_on_returns', True) # New: control return calculation

        if not column: # Check if column name itself is missing or empty
            print(f"Warning: 'column' parameter is missing or invalid in the configuration for RollingVolatilityTransformer. Skipping.")
            return data

        if column not in data.columns: # Check if the specified column exists in the DataFrame
            print(f"Warning: Column '{column}' not found in DataFrame for rolling volatility. Skipping.")
            return data
            
        result = data.copy()
        
        series_to_calculate_on = result[column]
        name_prefix = column

        if calculate_on_returns:
            # Calculate 1-period percentage change (returns)
            returns = result[column].pct_change()
            series_to_calculate_on = returns
            name_prefix = f"{column}_returns"

        # Calculate rolling standard deviation
        rolling_std_dev = series_to_calculate_on.rolling(window=window).std()
        
        # Annualize volatility if requested
        if annualized:
            annualized_vol = rolling_std_dev * np.sqrt(periods_in_year)
            result[f"{name_prefix}_vol{window}_annualized"] = annualized_vol * 100
        else:
            result[f"{name_prefix}_vol{window}"] = rolling_std_dev * 100
        
        return result

class MultiplyTransformer(DataTransformer):
    """Multiplies a given column by a scalar value"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        scalar = config.get('scalar')

        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for multiplication. Skipping.")
            return data

        if scalar is None:
            print(f"Warning: Scalar not provided for multiplication on column '{column}'. Skipping.")
            return data
        
        if not isinstance(scalar, (int, float)):
            print(f"Warning: Scalar '{scalar}' is not a number. Skipping multiplication for column '{column}'.")
            return data

        result = data.copy()
        new_column_name = f"{column}_multiplied_by_{scalar}"
        result[new_column_name] = result[column] * scalar
        
        return result

class DivideTransformer(DataTransformer):
    """Divides a given column by a scalar value"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        scalar = config.get('scalar')

        if not column or column not in data.columns:
            print(f"Warning: Column '{column}' not found for division. Skipping.")
            return data

        if scalar is None:
            print(f"Warning: Scalar not provided for division on column '{column}'. Skipping.")
            return data
        
        if not isinstance(scalar, (int, float)):
            print(f"Warning: Scalar '{scalar}' is not a number. Skipping division for column '{column}'.")
            return data

        if scalar == 0:
            print(f"Warning: Scalar is zero. Division by zero is not allowed for column '{column}'. Skipping.")
            return data

        result = data.copy()
        new_column_name = f"{column}_divided_by_{scalar}"
        result[new_column_name] = result[column] / scalar
        
        return result

class SeasonallyAdjustedAnnualRateTransformer(DataTransformer):
    """
    Calculates the Seasonally Adjusted Annual Rate (SAAR) for a given column.
    The calculation is based on ((current_period_value / past_period_value_N_months_ago) ** (12 / N) - 1) * 100.
    Input data is resampled to month-start frequency before calculation.
    """
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        period_months = config.get('period_months')
        calculate_pct_change = config.get('calculate_pct_change', False)

        # Validate essential config for forming the new column name and core logic
        if not isinstance(column, str) or not column:
            print(f"Warning: SAAR transformer requires a valid 'column' name string in config. Skipping.")
            return data # Cannot form new_column_name or proceed

        if not isinstance(period_months, int) or period_months <= 0:
            print(f"Warning: SAAR transformer 'period_months' ({period_months}) for column '{column}' must be a positive integer. Skipping.")
            return data # Cannot proceed with logic

        result = pd.DataFrame(data.copy())
        new_column_name = f"{column}_saar_{period_months}m"
        
        result[new_column_name] = np.nan # Ensure column exists

        if column not in result.columns:
            print(f"Warning: Column '{column}' not found in DataFrame for SAAR. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result

        if not isinstance(result.index, pd.DatetimeIndex):
            print(f"Error: DataFrame index is not a DatetimeIndex for SAAR on column '{column}'. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result

        col_data_series = result[column].dropna()
        
        if col_data_series.empty:
            print(f"Warning: Column '{column}' has no non-NaN data for SAAR. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result

        try:
            # Resample to month-start frequency, taking the last observation of the month.
            monthly_series = col_data_series.resample('MS').last()
        except Exception as e:
            print(f"Error during resampling for SAAR on column '{column}': {e}. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result
        
        if monthly_series.empty or monthly_series.isnull().all():
            print(f"Warning: Column '{column}' is empty or all NaN after resampling to 'MS' for SAAR. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result

        if len(monthly_series) < period_months + 1:
            print(f"Warning: Not enough data points in monthly series for column '{column}' ({len(monthly_series)} points) to calculate SAAR with period {period_months} months. At least {period_months + 1} points needed. Adding NaN column '{new_column_name}'.")
            result[new_column_name] = np.nan
            return result
            
        try:
            # Reconstruct SA index from monthly series
            if calculate_pct_change:
                periodic_growth_rate = monthly_series.pct_change(period_months)
            else:
                # Assumes monthly_series contains MoM % changes.
                sa_series = np.cumprod(1 + monthly_series/100.0)
                periodic_growth_rate = sa_series.pct_change(period_months)
            
            # Annualize: ( (1 + periodic_growth_rate) ^ (12 / period_months) ) - 1, then * 100
            saar_pct_values = ((1 + periodic_growth_rate).pow(12.0/period_months) - 1) * 100.0
 
            aligned_saar = saar_pct_values.reindex(result.index) # User removed ffill, kept here
            result[new_column_name] = aligned_saar

        except Exception as e:
            print(f"Error during SAAR calculation for column '{column}': {e}. Output column '{new_column_name}' will remain NaN.")
            # new_column_name is already NaN if error occurs here
        
        return result

class RollingBetaTransformer(DataTransformer):
    """Calculates rolling beta of a dependent series returns against an independent series returns."""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        dependent_col_name = config.get('dependent_column')
        independent_col_name = config.get('independent_column')
        window = config.get('window', 252)  # Default to 252 periods

        if not dependent_col_name:
            print(f"Warning: 'dependent_column' parameter is missing in the configuration for RollingBetaTransformer. Skipping.")
            return data
        if not independent_col_name:
            print(f"Warning: 'independent_column' parameter is missing in the configuration for RollingBetaTransformer. Skipping.")
            return data

        if dependent_col_name not in data.columns:
            print(f"Warning: Dependent column '{dependent_col_name}' not found in DataFrame for rolling beta. Skipping.")
            return data
        if independent_col_name not in data.columns:
            print(f"Warning: Independent column '{independent_col_name}' not found in DataFrame for rolling beta. Skipping.")
            return data
            
        result = data.copy()

        # Calculate 1-period percentage change (returns) for both series
        dependent_returns = result[dependent_col_name].pct_change()
        independent_returns = result[independent_col_name].pct_change()

        # Calculate rolling covariance between dependent and independent returns
        rolling_cov = dependent_returns.rolling(window=window).cov(independent_returns)
        
        # Calculate rolling variance of independent returns
        rolling_var_independent = independent_returns.rolling(window=window).var()

        # Calculate rolling beta
        # Beta = Cov(Dep, Ind) / Var(Ind)
        # Handle potential division by zero if variance is zero or NaN, resulting in NaN beta
        rolling_beta = rolling_cov / rolling_var_independent
        
        new_column_name = f"beta_{dependent_col_name}_vs_{independent_col_name}_w{window}"
        result[new_column_name] = rolling_beta
        
        return result

# Register all transformers in a dictionary for easy lookup
TRANSFORMERS = {
    "default": DataTransformer,
    "yearly_variation": YearlyVariationTransformer,
    "monthly_variation": MonthlyVariationTransformer,
    "quarterly_variation": QuarterlyVariationTransformer,
    "monthly_difference": MonthlyDifferenceTransformer,
    "moving_average": MovingAverageTransformer,
    "rolling_max": RollingMaxTransformer,
    "rolling_min": RollingMinTransformer,
    "rolling_volatility": RollingVolatilityTransformer,
    "rolling_beta": RollingBetaTransformer,
    "rolling_sum": RollingSumTransformer,
    "rolling_sum_plus_yearly_variation": RollingSumPlusYearlyVariationTransformer,
    "multiply": MultiplyTransformer,
    "divide": DivideTransformer,
    "saar": SeasonallyAdjustedAnnualRateTransformer,
}

def apply_transformations(data: pd.DataFrame, transformations_config: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Apply a series of transformations to the data
    
    Parameters:
    -----------
    data : pd.DataFrame
        Original data
    transformations_config : List[Dict]
        List of transformation configurations
        Each dict should have:
        - 'type': The transformer type
        - Additional parameters needed by the transformer
        
    Returns:
    --------
    pd.DataFrame
        Transformed data
    """
    result = data.copy()
    
    if not transformations_config:
        return result
        
    for config in transformations_config:
        transformer_type = config.get('type', 'default')
        transformer = TRANSFORMERS.get(transformer_type, DataTransformer)
        result = transformer.transform(result, config)
        
    return result