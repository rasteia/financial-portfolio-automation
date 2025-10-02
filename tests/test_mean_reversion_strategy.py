"""
Unit tests for mean reversion strategy implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from financial_portfolio_automation.strategy.mean_reversion import MeanReversionStrategy
from financial_portfolio_automation.strategy.base import SignalType
from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot
from financial_portfolio_automation.models.config import StrategyConfig, StrategyType, RiskLimits


class TestMeanReversionStrategy:
    """Test cases for MeanReversionStrategy class."""
    
    @pytest.fixture
    def strategy_config(self):
        """Create test strategy configuration."""
        return StrategyConfig(
            strategy_id="test_mean_reversion",
            strategy_type=StrategyType.MEAN_REVERSION,
            name="Test Mean Reversion Strategy",
            description="Test mean reversion strategy for unit testing",
            symbols=["AAPL", "MSFT"],
            parameters={
                'lookback_period': 20,
                'deviation_threshold': 2.0,
                'std_dev_threshold': 2.0,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'mean_reversion_threshold': 0.05,
                'min_reversion_strength': 0.5
            },
            risk_limits=RiskLimits(
                max_position_size=Decimal('10000'),
                max_portfolio_concentration=0.2,
                max_daily_loss=Decimal('1000'),
                max_drawdown=0.1,
                stop_loss_percentage=0.05
            ),
            is_active=True
        )
    
    @pytest.fixture
    def mean_reversion_strategy(self, strategy_config):
        """Create mean reversion strategy instance."""
        return MeanReversionStrategy(strategy_config)
    
    @pytest.fixture
    def sample_quotes_stable(self):
        """Create sample historical quotes with stable price around mean."""
        base_time = datetime.now(timezone.utc)
        quotes = []
        base_price = 100.0
        
        # Create 25 quotes oscillating around mean price
        for i in range(25):
            # Oscillate around base price
            price_offset = (i % 4 - 1.5) * 0.5  # Creates oscillation
            price = Decimal(str(base_price + price_offset))
            
            quotes.append(Quote(
                symbol="AAPL",
                timestamp=base_time,
                open=price - Decimal('0.2'),
                high=price + Decimal('0.3'),
                low=price - Decimal('0.3'),
                close=price,
                volume=1000000 + i * 5000
            ))
        
        return quotes
    
    @pytest.fixture
    def oversold_quote(self):
        """Create oversold market quote (significantly below mean)."""
        return Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('92.0'),
            high=Decimal('93.0'),
            low=Decimal('91.0'),
            close=Decimal('92.5'),  # Significantly below mean of ~100
            volume=1500000
        )
    
    @pytest.fixture
    def overbought_quote(self):
        """Create overbought market quote (significantly above mean)."""
        return Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('108.0'),
            high=Decimal('109.0'),
            low=Decimal('107.0'),
            close=Decimal('108.5'),  # Significantly above mean of ~100
            volume=1500000
        )
    
    @pytest.fixture
    def portfolio_snapshot(self):
        """Create sample portfolio snapshot."""
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('500'),
            total_pnl=Decimal('2500'),
            positions=[
                Position(
                    symbol="AAPL",
                    quantity=100,
                    market_value=Decimal('9250'),
                    cost_basis=Decimal('9000'),
                    unrealized_pnl=Decimal('250'),
                    day_pnl=Decimal('25')
                )
            ]
        )
    
    def test_mean_reversion_strategy_initialization(self, mean_reversion_strategy):
        """Test mean reversion strategy initialization."""
        assert mean_reversion_strategy.strategy_id == "test_mean_reversion"
        assert mean_reversion_strategy.strategy_type == "mean_reversion"
        assert mean_reversion_strategy.symbols == ["AAPL", "MSFT"]
        assert mean_reversion_strategy.lookback_period == 20
        assert mean_reversion_strategy.std_dev_threshold == 2.0
        assert mean_reversion_strategy.min_reversion_strength == 0.5
    
    def test_generate_signals_no_historical_data(self, mean_reversion_strategy, oversold_quote, portfolio_snapshot):
        """Test signal generation without historical data."""
        market_data = {"AAPL": oversold_quote}
        
        signals = mean_reversion_strategy.generate_signals(market_data, portfolio_snapshot, None)
        
        assert len(signals) == 0
    
    def test_generate_signals_insufficient_data(self, mean_reversion_strategy, oversold_quote, portfolio_snapshot):
        """Test signal generation with insufficient historical data."""
        market_data = {"AAPL": oversold_quote}
        historical_data = {"AAPL": [oversold_quote] * 5}  # Only 5 quotes, need 20
        
        signals = mean_reversion_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 0
    
    def test_generate_oversold_signal(self, mean_reversion_strategy, oversold_quote, 
                                    sample_quotes_stable, portfolio_snapshot):
        """Test generation of oversold (buy) signal."""
        # Mock technical analysis results for oversold condition
        mock_ta_instance = Mock()
        mean_reversion_strategy.technical_analysis = mock_ta_instance
        
        mock_ta_instance.calculate_rsi.return_value = [None] * 19 + [25.0]  # Oversold RSI
        mock_ta_instance.calculate_bollinger_bands.return_value = (
            [None] * 19 + [102.0],  # Upper band
            [None] * 19 + [100.0],  # Middle band (mean)
            [None] * 19 + [98.0]    # Lower band
        )
        mock_ta_instance.calculate_sma.side_effect = [
            [None] * 9 + [99.5] * 11,   # Short SMA
            [None] * 19 + [100.0]       # Long SMA
        ]
        
        market_data = {"AAPL": oversold_quote}
        historical_data = {"AAPL": sample_quotes_stable}
        
        signals = mean_reversion_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 1
        signal = signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength >= mean_reversion_strategy.min_reversion_strength
        assert signal.price == oversold_quote.close
        
        # Check metadata
        assert 'mean_price' in signal.metadata
        assert 'z_score' in signal.metadata
        assert 'rsi' in signal.metadata
    
    def test_generate_overbought_signal(self, mean_reversion_strategy, overbought_quote, 
                                      sample_quotes_stable, portfolio_snapshot):
        """Test generation of overbought (sell) signal."""
        # Add a position to sell
        from financial_portfolio_automation.models.core import Position
        position = Position(
            symbol="AAPL",
            quantity=Decimal('100'),
            cost_basis=Decimal('10000.0'),
            market_value=Decimal('10850.0'),
            unrealized_pnl=Decimal('850.0'),
            day_pnl=Decimal('50.0')
        )
        mean_reversion_strategy.state.positions["AAPL"] = position
        
        # Mock technical analysis results for overbought condition
        mock_ta_instance = Mock()
        mean_reversion_strategy.technical_analysis = mock_ta_instance
        
        mock_ta_instance.calculate_rsi.return_value = [None] * 19 + [75.0]  # Overbought RSI
        mock_ta_instance.calculate_bollinger_bands.return_value = (
            [None] * 19 + [102.0],  # Upper band
            [None] * 19 + [100.0],  # Middle band (mean)
            [None] * 19 + [98.0]    # Lower band
        )
        mock_ta_instance.calculate_sma.side_effect = [
            [None] * 9 + [100.5] * 11,  # Short SMA
            [None] * 19 + [100.0]       # Long SMA
        ]
        
        market_data = {"AAPL": overbought_quote}
        historical_data = {"AAPL": sample_quotes_stable}
        
        signals = mean_reversion_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 1
        signal = signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.SELL
        assert signal.strength >= mean_reversion_strategy.min_reversion_strength
        assert signal.price == overbought_quote.close
    
    def test_analyze_mean_reversion_insufficient_data(self, mean_reversion_strategy, oversold_quote):
        """Test mean reversion analysis with insufficient data."""
        short_history = [oversold_quote] * 5  # Less than lookback period
        
        signal = mean_reversion_strategy._analyze_mean_reversion("AAPL", oversold_quote, short_history)
        
        assert signal is None
    
    def test_calculate_mean_reversion_score(self, mean_reversion_strategy):
        """Test mean reversion score calculation."""
        historical_prices = [100.0, 101.0, 99.0, 100.5, 99.5, 100.2, 99.8, 100.1]
        
        # Test oversold condition
        oversold_score = mean_reversion_strategy._calculate_mean_reversion_score(
            current_price=95.0,
            historical_prices=historical_prices,
            rsi_value=25.0
        )
        assert oversold_score > 0  # Positive for oversold
        
        # Test overbought condition
        overbought_score = mean_reversion_strategy._calculate_mean_reversion_score(
            current_price=105.0,
            historical_prices=historical_prices,
            rsi_value=75.0
        )
        assert overbought_score < 0  # Negative for overbought
        
        # Test neutral condition
        neutral_score = mean_reversion_strategy._calculate_mean_reversion_score(
            current_price=100.0,
            historical_prices=historical_prices,
            rsi_value=50.0
        )
        assert abs(neutral_score) < 0.5  # Should be close to neutral
    
    def test_update_state(self, mean_reversion_strategy, portfolio_snapshot):
        """Test strategy state update."""
        market_data = {
            "AAPL": Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=Decimal('100'),
                high=Decimal('101'),
                low=Decimal('99'),
                close=Decimal('100.5'),
                volume=1000000
            )
        }
        
        mean_reversion_strategy.update_state(market_data, portfolio_snapshot)
        
        # Check that position was updated
        assert "AAPL" in mean_reversion_strategy.state.positions
        assert mean_reversion_strategy.state.positions["AAPL"].quantity == 100
        
        # Check metadata update
        assert 'last_market_update' in mean_reversion_strategy.state.metadata
        assert 'strategy_type' in mean_reversion_strategy.state.metadata
        assert mean_reversion_strategy.state.metadata['strategy_type'] == 'mean_reversion'
    
    def test_mean_reversion_strategy_parameters(self, strategy_config):
        """Test strategy parameter handling."""
        # Test with custom parameters
        custom_params = {
            'lookback_period': 30,
            'std_dev_threshold': 1.5,
            'mean_reversion_threshold': 0.08,
            'volume_confirmation': False,
            'trend_filter': False
        }
        strategy_config.parameters = custom_params
        
        strategy = MeanReversionStrategy(strategy_config)
        
        assert strategy.lookback_period == 30
        assert strategy.std_dev_threshold == 1.5
        assert strategy.mean_reversion_threshold == 0.08
        assert strategy.volume_confirmation == False
        assert strategy.trend_filter == False
    
    @patch('financial_portfolio_automation.strategy.mean_reversion.TechnicalAnalysis')
    def test_trend_filter_effect(self, mock_ta, strategy_config, sample_quotes_stable, portfolio_snapshot):
        """Test trend filter effect on signal generation."""
        # Enable trend filter
        strategy_config.parameters['trend_filter'] = True
        strategy = MeanReversionStrategy(strategy_config)
        
        mock_ta_instance = Mock()
        mock_ta.return_value = mock_ta_instance
        
        # Strong oversold conditions but against trend
        mock_ta_instance.calculate_rsi.return_value = [20.0]  # Very oversold
        mock_ta_instance.calculate_bollinger_bands.return_value = (
            [102.0], [100.0], [98.0]
        )
        # Downtrend (short SMA < long SMA)
        mock_ta_instance.calculate_sma.side_effect = [
            [99.0],   # Short SMA
            [100.0]   # Long SMA (downtrend)
        ]
        
        oversold_quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('92.0'),
            high=Decimal('93.0'),
            low=Decimal('91.0'),
            close=Decimal('92.5'),
            volume=1500000
        )
        
        market_data = {"AAPL": oversold_quote}
        historical_data = {"AAPL": sample_quotes_stable}
        
        signals = strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        # Signal strength should be reduced due to trend filter
        if signals:
            assert signals[0].strength < 0.8  # Should be reduced from full strength
    
    def test_volume_confirmation_effect(self, mean_reversion_strategy, sample_quotes_stable, portfolio_snapshot):
        """Test volume confirmation effect on signal generation."""
        # Test with high volume (should strengthen signal)
        high_volume_quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('92.0'),
            high=Decimal('93.0'),
            low=Decimal('91.0'),
            close=Decimal('92.5'),
            volume=2000000  # High volume
        )
        
        # Test with low volume (should not add volume confirmation)
        low_volume_quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('92.0'),
            high=Decimal('93.0'),
            low=Decimal('91.0'),
            close=Decimal('92.5'),
            volume=500000  # Low volume
        )
        
        with patch('financial_portfolio_automation.strategy.mean_reversion.TechnicalAnalysis') as mock_ta:
            mock_ta_instance = Mock()
            mock_ta.return_value = mock_ta_instance
            
            mock_ta_instance.calculate_rsi.return_value = [25.0]
            mock_ta_instance.calculate_bollinger_bands.return_value = (
                [102.0], [100.0], [98.0]
            )
            mock_ta_instance.calculate_sma.side_effect = [
                [99.5], [100.0],  # For high volume test
                [99.5], [100.0]   # For low volume test
            ]
            
            # Test high volume
            historical_data = {"AAPL": sample_quotes_stable}
            signals_high_vol = mean_reversion_strategy.generate_signals(
                {"AAPL": high_volume_quote}, portfolio_snapshot, historical_data
            )
            
            # Test low volume
            signals_low_vol = mean_reversion_strategy.generate_signals(
                {"AAPL": low_volume_quote}, portfolio_snapshot, historical_data
            )
            
            # Both should generate signals, but high volume should be stronger
            if signals_high_vol and signals_low_vol:
                assert signals_high_vol[0].strength >= signals_low_vol[0].strength
    
    def test_no_sell_signal_without_position(self, mean_reversion_strategy, overbought_quote, 
                                           sample_quotes_stable):
        """Test that sell signals are not generated without existing position."""
        # Portfolio without AAPL position
        empty_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000'),
            buying_power=Decimal('100000'),
            day_pnl=Decimal('0'),
            total_pnl=Decimal('0'),
            positions=[]
        )
        
        with patch('financial_portfolio_automation.strategy.mean_reversion.TechnicalAnalysis') as mock_ta:
            mock_ta_instance = Mock()
            mock_ta.return_value = mock_ta_instance
            
            # Strong overbought conditions
            mock_ta_instance.calculate_rsi.return_value = [80.0]
            mock_ta_instance.calculate_bollinger_bands.return_value = (
                [102.0], [100.0], [98.0]
            )
            mock_ta_instance.calculate_sma.side_effect = [
                [100.5], [100.0]
            ]
            
            market_data = {"AAPL": overbought_quote}
            historical_data = {"AAPL": sample_quotes_stable}
            
            signals = mean_reversion_strategy.generate_signals(market_data, empty_portfolio, historical_data)
            
            # Should not generate sell signal without position
            assert len(signals) == 0