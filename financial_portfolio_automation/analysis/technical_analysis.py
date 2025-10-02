"""
Technical Analysis module for calculating various technical indicators.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TechnicalAnalysis:
    """
    Technical analysis class for calculating various technical indicators
    including moving averages, momentum indicators, and volatility indicators.
    """
    
    def __init__(self):
        """Initialize the TechnicalAnalysis class."""
        self.logger = logger
    
    # Moving Averages
    def simple_moving_average(self, prices: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Simple Moving Average (SMA).
        
        Args:
            prices: List of price values
            period: Number of periods for the moving average
            
        Returns:
            List of SMA values (None for insufficient data points)
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        sma_values = []
        for i in range(len(prices)):
            if i < period - 1:
                sma_values.append(None)
            else:
                sma = sum(prices[i - period + 1:i + 1]) / period
                sma_values.append(sma)
        
        return sma_values
    
    def exponential_moving_average(self, prices: List[float], period: int) -> List[Optional[float]]:
        """
        Calculate Exponential Moving Average (EMA).
        
        Args:
            prices: List of price values
            period: Number of periods for the moving average
            
        Returns:
            List of EMA values (None for insufficient data points)
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        multiplier = 2 / (period + 1)
        ema_values = []
        
        # First EMA is SMA
        first_sma = sum(prices[:period]) / period
        ema_values.extend([None] * (period - 1))
        ema_values.append(first_sma)
        
        # Calculate subsequent EMAs
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[i - 1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    # Momentum Indicators
    def relative_strength_index(self, prices: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: List of price values
            period: Number of periods for RSI calculation (default: 14)
            
        Returns:
            List of RSI values (0-100 scale)
        """
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(prices)):
            price_changes.append(prices[i] - prices[i - 1])
        
        rsi_values = [None]  # First value is always None
        
        for i in range(len(price_changes)):
            if i < period - 1:
                rsi_values.append(None)
            else:
                # Get gains and losses for the period
                period_changes = price_changes[i - period + 1:i + 1]
                gains = [change if change > 0 else 0 for change in period_changes]
                losses = [-change if change < 0 else 0 for change in period_changes]
                
                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(rsi)
        
        return rsi_values
    
    def macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, List[Optional[float]]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: List of price values
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' lists
        """
        fast_ema = self.exponential_moving_average(prices, fast_period)
        slow_ema = self.exponential_moving_average(prices, slow_period)
        
        # Calculate MACD line
        macd_line = []
        for i in range(len(prices)):
            if fast_ema[i] is None or slow_ema[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(fast_ema[i] - slow_ema[i])
        
        # Calculate signal line (EMA of MACD line)
        # Filter out None values for signal calculation
        macd_values_for_signal = [val for val in macd_line if val is not None]
        if len(macd_values_for_signal) >= signal_period:
            signal_ema = self.exponential_moving_average(macd_values_for_signal, signal_period)
            
            # Align signal line with original data
            signal_line = [None] * len(prices)
            signal_start_idx = len(prices) - len(signal_ema)
            for i, val in enumerate(signal_ema):
                if signal_start_idx + i < len(prices):
                    signal_line[signal_start_idx + i] = val
        else:
            signal_line = [None] * len(prices)
        
        # Calculate histogram
        histogram = []
        for i in range(len(prices)):
            if macd_line[i] is None or signal_line[i] is None:
                histogram.append(None)
            else:
                histogram.append(macd_line[i] - signal_line[i])
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def stochastic_oscillator(self, highs: List[float], lows: List[float], closes: List[float], 
                            k_period: int = 14, d_period: int = 3) -> Dict[str, List[Optional[float]]]:
        """
        Calculate Stochastic Oscillator (%K and %D).
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            k_period: Period for %K calculation (default: 14)
            d_period: Period for %D smoothing (default: 3)
            
        Returns:
            Dictionary with '%K' and '%D' lists
        """
        if len(highs) != len(lows) or len(highs) != len(closes):
            raise ValueError("High, low, and close price lists must have the same length")
        
        if len(highs) < k_period:
            return {'%K': [None] * len(highs), '%D': [None] * len(highs)}
        
        k_values = []
        
        for i in range(len(closes)):
            if i < k_period - 1:
                k_values.append(None)
            else:
                period_highs = highs[i - k_period + 1:i + 1]
                period_lows = lows[i - k_period + 1:i + 1]
                
                highest_high = max(period_highs)
                lowest_low = min(period_lows)
                
                if highest_high == lowest_low:
                    k_percent = 50  # Avoid division by zero
                else:
                    k_percent = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100
                
                k_values.append(k_percent)
        
        # Calculate %D (SMA of %K)
        k_values_for_d = [val for val in k_values if val is not None]
        if len(k_values_for_d) >= d_period:
            d_values = self.simple_moving_average(k_values_for_d, d_period)
            
            # Align %D with original data
            d_aligned = [None] * len(closes)
            d_start_idx = len(closes) - len(d_values)
            for i, val in enumerate(d_values):
                if d_start_idx + i < len(closes) and val is not None:
                    d_aligned[d_start_idx + i] = val
        else:
            d_aligned = [None] * len(closes)
        
        return {'%K': k_values, '%D': d_aligned}
    
    # Volatility Indicators
    def bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, List[Optional[float]]]:
        """
        Calculate Bollinger Bands.
        
        Args:
            prices: List of price values
            period: Period for moving average and standard deviation (default: 20)
            std_dev: Number of standard deviations for bands (default: 2.0)
            
        Returns:
            Dictionary with 'upper', 'middle', and 'lower' band lists
        """
        if len(prices) < period:
            return {
                'upper': [None] * len(prices),
                'middle': [None] * len(prices),
                'lower': [None] * len(prices)
            }
        
        middle_band = self.simple_moving_average(prices, period)
        upper_band = []
        lower_band = []
        
        for i in range(len(prices)):
            if middle_band[i] is None:
                upper_band.append(None)
                lower_band.append(None)
            else:
                # Calculate standard deviation for the period
                period_prices = prices[i - period + 1:i + 1]
                mean_price = sum(period_prices) / len(period_prices)
                variance = sum((price - mean_price) ** 2 for price in period_prices) / len(period_prices)
                std_deviation = variance ** 0.5
                
                upper_band.append(middle_band[i] + (std_dev * std_deviation))
                lower_band.append(middle_band[i] - (std_dev * std_deviation))
        
        return {
            'upper': upper_band,
            'middle': middle_band,
            'lower': lower_band
        }
    
    def average_true_range(self, highs: List[float], lows: List[float], closes: List[float], 
                          period: int = 14) -> List[Optional[float]]:
        """
        Calculate Average True Range (ATR).
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            period: Period for ATR calculation (default: 14)
            
        Returns:
            List of ATR values
        """
        if len(highs) != len(lows) or len(highs) != len(closes):
            raise ValueError("High, low, and close price lists must have the same length")
        
        if len(highs) < period + 1:
            return [None] * len(highs)
        
        true_ranges = [None]  # First value is None (no previous close)
        
        # Calculate True Range for each period
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]  # High - Low
            tr2 = abs(highs[i] - closes[i - 1])  # High - Previous Close
            tr3 = abs(lows[i] - closes[i - 1])  # Low - Previous Close
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # Calculate ATR using SMA of True Ranges
        atr_values = []
        for i in range(len(true_ranges)):
            if i < period:
                atr_values.append(None)
            else:
                period_trs = [tr for tr in true_ranges[i - period + 1:i + 1] if tr is not None]
                if len(period_trs) == period:
                    atr = sum(period_trs) / period
                    atr_values.append(atr)
                else:
                    atr_values.append(None)
        
        return atr_values
    
    def calculate_all_indicators(self, highs: List[float], lows: List[float], closes: List[float]) -> Dict[str, any]:
        """
        Calculate all technical indicators for the given price data.
        
        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of closing prices
            
        Returns:
            Dictionary containing all calculated indicators
        """
        try:
            indicators = {}
            
            # Moving Averages
            indicators['sma_20'] = self.simple_moving_average(closes, 20)
            indicators['sma_50'] = self.simple_moving_average(closes, 50)
            indicators['ema_12'] = self.exponential_moving_average(closes, 12)
            indicators['ema_26'] = self.exponential_moving_average(closes, 26)
            
            # Momentum Indicators
            indicators['rsi'] = self.relative_strength_index(closes)
            indicators['macd'] = self.macd(closes)
            indicators['stochastic'] = self.stochastic_oscillator(highs, lows, closes)
            
            # Volatility Indicators
            indicators['bollinger_bands'] = self.bollinger_bands(closes)
            indicators['atr'] = self.average_true_range(highs, lows, closes)
            
            self.logger.info("Successfully calculated all technical indicators")
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {e}")
            raise
    
    # Alias methods for backward compatibility with strategy classes
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[Optional[float]]:
        """Alias for relative_strength_index method."""
        return self.relative_strength_index(prices, period)
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        """Alias for bollinger_bands method that returns tuple format."""
        result = self.bollinger_bands(prices, period, std_dev)
        return result['upper'], result['middle'], result['lower']
    
    def calculate_sma(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Alias for simple_moving_average method."""
        return self.simple_moving_average(prices, period)
    
    def calculate_macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple:
        """Alias for macd method that returns tuple format."""
        result = self.macd(prices, fast_period, slow_period, signal_period)
        # Return as tuple: (macd_line, signal_line, histogram)
        return result['macd'], result['signal'], result['histogram']