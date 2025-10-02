"""
Unit tests for TechnicalAnalysis class.
"""

import pytest
import numpy as np
from financial_portfolio_automation.analysis.technical_analysis import TechnicalAnalysis


class TestTechnicalAnalysis:
    """Test cases for TechnicalAnalysis class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ta = TechnicalAnalysis()
        
        # Sample price data for testing
        self.sample_prices = [10.0, 11.0, 12.0, 11.5, 13.0, 12.5, 14.0, 13.5, 15.0, 14.5,
                             16.0, 15.5, 17.0, 16.5, 18.0, 17.5, 19.0, 18.5, 20.0, 19.5]
        
        self.sample_highs = [10.5, 11.5, 12.5, 12.0, 13.5, 13.0, 14.5, 14.0, 15.5, 15.0,
                            16.5, 16.0, 17.5, 17.0, 18.5, 18.0, 19.5, 19.0, 20.5, 20.0]
        
        self.sample_lows = [9.5, 10.5, 11.5, 11.0, 12.5, 12.0, 13.5, 13.0, 14.5, 14.0,
                           15.5, 15.0, 16.5, 16.0, 17.5, 17.0, 18.5, 18.0, 19.5, 19.0]
    
    def test_simple_moving_average(self):
        """Test Simple Moving Average calculation."""
        # Test with period 5
        sma_5 = self.ta.simple_moving_average(self.sample_prices, 5)
        
        # First 4 values should be None
        assert sma_5[:4] == [None, None, None, None]
        
        # 5th value should be average of first 5 prices
        expected_5th = sum(self.sample_prices[:5]) / 5
        assert abs(sma_5[4] - expected_5th) < 0.001
        
        # Test with insufficient data
        short_prices = [10.0, 11.0, 12.0]
        sma_short = self.ta.simple_moving_average(short_prices, 5)
        assert sma_short == [None, None, None]
    
    def test_exponential_moving_average(self):
        """Test Exponential Moving Average calculation."""
        # Test with period 5
        ema_5 = self.ta.exponential_moving_average(self.sample_prices, 5)
        
        # First 4 values should be None
        assert ema_5[:4] == [None, None, None, None]
        
        # 5th value should be SMA of first 5 prices
        expected_5th = sum(self.sample_prices[:5]) / 5
        assert abs(ema_5[4] - expected_5th) < 0.001
        
        # 6th value should use EMA formula
        multiplier = 2 / (5 + 1)
        expected_6th = (self.sample_prices[5] * multiplier) + (ema_5[4] * (1 - multiplier))
        assert abs(ema_5[5] - expected_6th) < 0.001
    
    def test_relative_strength_index(self):
        """Test RSI calculation."""
        # Create test data with known RSI behavior
        trending_up = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
        rsi_up = self.ta.relative_strength_index(trending_up, 14)
        
        # RSI should be high for uptrending data
        assert rsi_up[-1] > 70  # Should be in overbought territory
        
        # Test with insufficient data
        short_prices = [10.0, 11.0, 12.0]
        rsi_short = self.ta.relative_strength_index(short_prices, 14)
        assert all(val is None for val in rsi_short)
    
    def test_macd(self):
        """Test MACD calculation."""
        macd_result = self.ta.macd(self.sample_prices)
        
        # Should return dictionary with required keys
        assert 'macd' in macd_result
        assert 'signal' in macd_result
        assert 'histogram' in macd_result
        
        # All lists should have same length as input
        assert len(macd_result['macd']) == len(self.sample_prices)
        assert len(macd_result['signal']) == len(self.sample_prices)
        assert len(macd_result['histogram']) == len(self.sample_prices)
        
        # Early values should be None due to EMA calculation requirements
        assert macd_result['macd'][0] is None
        assert macd_result['signal'][0] is None
        assert macd_result['histogram'][0] is None
    
    def test_stochastic_oscillator(self):
        """Test Stochastic Oscillator calculation."""
        stoch_result = self.ta.stochastic_oscillator(self.sample_highs, self.sample_lows, self.sample_prices)
        
        # Should return dictionary with %K and %D
        assert '%K' in stoch_result
        assert '%D' in stoch_result
        
        # All lists should have same length as input
        assert len(stoch_result['%K']) == len(self.sample_prices)
        assert len(stoch_result['%D']) == len(self.sample_prices)
        
        # %K values should be between 0 and 100 (where not None)
        for k_val in stoch_result['%K']:
            if k_val is not None:
                assert 0 <= k_val <= 100
        
        # Test with mismatched input lengths
        with pytest.raises(ValueError):
            self.ta.stochastic_oscillator([1, 2], [1, 2, 3], [1, 2])
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        bb_result = self.ta.bollinger_bands(self.sample_prices, 10, 2.0)
        
        # Should return dictionary with upper, middle, lower
        assert 'upper' in bb_result
        assert 'middle' in bb_result
        assert 'lower' in bb_result
        
        # All lists should have same length as input
        assert len(bb_result['upper']) == len(self.sample_prices)
        assert len(bb_result['middle']) == len(self.sample_prices)
        assert len(bb_result['lower']) == len(self.sample_prices)
        
        # Where values exist, upper > middle > lower
        for i in range(len(self.sample_prices)):
            if (bb_result['upper'][i] is not None and 
                bb_result['middle'][i] is not None and 
                bb_result['lower'][i] is not None):
                assert bb_result['upper'][i] > bb_result['middle'][i]
                assert bb_result['middle'][i] > bb_result['lower'][i]
    
    def test_average_true_range(self):
        """Test ATR calculation."""
        atr_result = self.ta.average_true_range(self.sample_highs, self.sample_lows, self.sample_prices)
        
        # Should have same length as input
        assert len(atr_result) == len(self.sample_prices)
        
        # First value should be None (no previous close)
        assert atr_result[0] is None
        
        # ATR values should be positive where they exist
        for atr_val in atr_result:
            if atr_val is not None:
                assert atr_val >= 0
        
        # Test with mismatched input lengths
        with pytest.raises(ValueError):
            self.ta.average_true_range([1, 2], [1, 2, 3], [1, 2])
    
    def test_calculate_all_indicators(self):
        """Test calculation of all indicators together."""
        all_indicators = self.ta.calculate_all_indicators(
            self.sample_highs, self.sample_lows, self.sample_prices
        )
        
        # Should contain all expected indicators
        expected_keys = [
            'sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi', 'macd', 
            'stochastic', 'bollinger_bands', 'atr'
        ]
        
        for key in expected_keys:
            assert key in all_indicators
        
        # MACD should be a dictionary
        assert isinstance(all_indicators['macd'], dict)
        assert 'macd' in all_indicators['macd']
        assert 'signal' in all_indicators['macd']
        assert 'histogram' in all_indicators['macd']
        
        # Stochastic should be a dictionary
        assert isinstance(all_indicators['stochastic'], dict)
        assert '%K' in all_indicators['stochastic']
        assert '%D' in all_indicators['stochastic']
        
        # Bollinger Bands should be a dictionary
        assert isinstance(all_indicators['bollinger_bands'], dict)
        assert 'upper' in all_indicators['bollinger_bands']
        assert 'middle' in all_indicators['bollinger_bands']
        assert 'lower' in all_indicators['bollinger_bands']
    
    def test_known_indicator_values(self):
        """Test with known values to validate calculation accuracy."""
        # Simple test case with known SMA result
        simple_prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma_3 = self.ta.simple_moving_average(simple_prices, 3)
        
        # Expected: [None, None, 2.0, 3.0, 4.0]
        assert sma_3[0] is None
        assert sma_3[1] is None
        assert abs(sma_3[2] - 2.0) < 0.001
        assert abs(sma_3[3] - 3.0) < 0.001
        assert abs(sma_3[4] - 4.0) < 0.001
        
        # Test RSI with extreme case (all gains)
        all_gains = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        rsi_gains = self.ta.relative_strength_index(all_gains, 14)
        
        # RSI should approach 100 for all gains
        assert rsi_gains[-1] > 95
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty price list
        empty_result = self.ta.simple_moving_average([], 5)
        assert empty_result == []
        
        # Single price
        single_price = [10.0]
        single_sma = self.ta.simple_moving_average(single_price, 5)
        assert single_sma == [None]
        
        # Period larger than data
        large_period_sma = self.ta.simple_moving_average([1, 2, 3], 10)
        assert large_period_sma == [None, None, None]
        
        # Zero period (should handle gracefully)
        try:
            zero_period = self.ta.simple_moving_average([1, 2, 3], 0)
            # Should either raise an error or handle gracefully
        except (ValueError, ZeroDivisionError):
            pass  # Expected behavior
    
    def test_data_consistency(self):
        """Test that indicators maintain data consistency."""
        # All moving averages should have same length as input
        sma_result = self.ta.simple_moving_average(self.sample_prices, 10)
        ema_result = self.ta.exponential_moving_average(self.sample_prices, 10)
        
        assert len(sma_result) == len(self.sample_prices)
        assert len(ema_result) == len(self.sample_prices)
        
        # RSI should be between 0 and 100
        rsi_result = self.ta.relative_strength_index(self.sample_prices)
        for rsi_val in rsi_result:
            if rsi_val is not None:
                assert 0 <= rsi_val <= 100
        
        # Stochastic %K and %D should be between 0 and 100
        stoch_result = self.ta.stochastic_oscillator(
            self.sample_highs, self.sample_lows, self.sample_prices
        )
        
        for k_val in stoch_result['%K']:
            if k_val is not None:
                assert 0 <= k_val <= 100
        
        for d_val in stoch_result['%D']:
            if d_val is not None:
                assert 0 <= d_val <= 100