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
            return data
            
        result = data.copy()
        
        # Calculate moving average
        result[f"{column}_ma{window}"] = result[column].rolling(window=window).mean()
        
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

class RelativePerformanceTransformer(DataTransformer):
    """Calculates relative performance between two columns"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        base_column = config.get('base_column')
        target_column = config.get('target_column')
        
        if (not base_column or base_column not in data.columns or
            not target_column or target_column not in data.columns):
            return data
            
        result = data.copy()
        
        # Normalize both series to start at 100
        base_normalized = 100 * data[base_column] / data[base_column].iloc[0]
        target_normalized = 100 * data[target_column] / data[target_column].iloc[0]
        
        # Calculate relative performance
        result[f"{target_column}_vs_{base_column}"] = target_normalized / base_normalized * 100
        
        return result

class YTDChangeTransformer(DataTransformer):
    """Calculates year-to-date change for a given column"""
    @staticmethod
    def transform(data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        column = config.get('column')
        if not column or column not in data.columns:
            return data
            
        result = data.copy()
        
        # Get the year for each date
        years = pd.DatetimeIndex(data.index).year
        
        # For each year, calculate the first value and then the percentage change
        ytd_changes = []
        
        for idx, value in data[column].items():
            year = pd.DatetimeIndex([idx]).year[0]
            # Get first value of the year
            year_start = data[column][years == year].iloc[0]
            # Calculate YTD change
            ytd_change = (value / year_start - 1) * 100
            ytd_changes.append(ytd_change)
            
        result[f"{column}_ytd"] = ytd_changes
        
        return result

# Register all transformers in a dictionary for easy lookup
TRANSFORMERS = {
    "yearly_variation": YearlyVariationTransformer,
    "monthly_variation": MonthlyVariationTransformer,
    "monthly_difference": MonthlyDifferenceTransformer,
    "moving_average": MovingAverageTransformer,
    "rolling_max": RollingMaxTransformer,
    "rolling_min": RollingMinTransformer,
    "relative_performance": RelativePerformanceTransformer,
    "ytd_change": YTDChangeTransformer,
    "default": DataTransformer,
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