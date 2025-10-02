"""
Unit tests for momentum strategy implementation.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from financial_portfolio_automation.strategy.momentum import MomentumStrategy
from financial_portfolio_automation.strategy.base import SignalType
from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot
from financial_portfolio_automation.models.config import StrategyConfig, StrategyType, RiskLimits


class TestMomentumStrategy:
    """Test cases for MomentumStrategy class."""
    
    @pytest.fixture
    def strategy_config(self):
        """Create test strategy configuration."""
        return StrategyConfig(
            strategy_id="test_momentum",
            strategy_type=StrategyType.MOMENTUM,
            name="Test Momentum Strategy",
            description="Test momentum strategy for unit testing",
            symbols=["AAPL", "GOOGL"],
            parameters={
                'lookback_period': 20,
                'momentum_threshold': 0.02,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'price_change_threshold': 0.02,
                'min_momentum_strength': 0.6
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
    def momentum_strategy(self, strategy_config):
        """Create momentum strategy instance."""
        return MomentumStrategy(strategy_config)
    
    @pytest.fixture
    def sample_quotes(self):
        """Create sample historical quotes."""
        base_time = datetime.now(timezone.utc)
        quotes = []
        
        # Create 25 quotes with upward trend
        for i in range(25):
            price = Decimal('100') + Decimal(str(i * 0.5))  # Gradual upward trend
            quotes.append(Quote(
                symbol="AAPL",
                timestamp=base_time,
                open=price - Decimal('0.5'),
                high=price + Decimal('1.0'),
                low=price - Decimal('1.0'),
                close=price,
                volume=1000000 + i * 10000
            ))
        
        return quotes
    
    @pytest.fixture
    def current_quote(self):
        """Create current market quote."""
        return Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('112.0'),
            high=Decimal('113.0'),
            low=Decimal('111.0'),
            close=Decimal('112.5'),
            volume=1500000
        )
    
    @pytest.fixture
    def portfolio_snapshot(self):
        """Create sample portfolio snapshot."""
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000'),
            positions=[
                Position(
                    symbol="AAPL",
                    quantity=100,
                    market_value=Decimal('11250'),
                    cost_basis=Decimal('11000'),
                    unrealized_pnl=Decimal('250'),
                    day_pnl=Decimal('50')
                )
            ]
        )
    
    def test_momentum_strategy_initialization(self, momentum_strategy):
        """Test momentum strategy initialization."""
        assert momentum_strategy.strategy_id == "test_momentum"
        assert momentum_strategy.strategy_type == "momentum"
        assert momentum_strategy.symbols == ["AAPL", "GOOGL"]
        assert momentum_strategy.lookback_period == 20
        assert momentum_strategy.min_momentum_strength == 0.6
    
    def test_generate_signals_no_historical_data(self, momentum_strategy, current_quote, portfolio_snapshot):
        """Test signal generation without historical data."""
        market_data = {"AAPL": current_quote}
        
        signals = momentum_strategy.generate_signals(market_data, portfolio_snapshot, None)
        
        assert len(signals) == 0
    
    def test_generate_signals_insufficient_data(self, momentum_strategy, current_quote, portfolio_snapshot):
        """Test signal generation with insufficient historical data."""
        market_data = {"AAPL": current_quote}
        historical_data = {"AAPL": [current_quote] * 5}  # Only 5 quotes, need 20
        
        signals = momentum_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 0
    
    def test_generate_bullish_momentum_signal(self, momentum_strategy, current_quote, 
                                            sample_quotes, portfolio_snapshot):
        """Test generation of bullish momentum signal."""
        # Mock technical analysis results for bullish momentum
        mock_ta_instance = Mock()
        momentum_strategy.technical_analysis = mock_ta_instance
        
        mock_ta_instance.calculate_rsi.return_value = [None] * 19 + [60.0]  # Bullish RSI with enough history
        mock_ta_instance.calculate_macd.return_value = (
            [None] * 18 + [0.3, 0.5],  # MACD line with bullish crossover
            [None] * 18 + [0.4, 0.3],  # Signal line 
            [None] * 18 + [-0.1, 0.2]  # Histogram
        )
        mock_ta_instance.calculate_sma.side_effect = [
            [None] * 9 + [110.0] * 11,   # Short SMA with enough history
            [None] * 19 + [108.0]        # Long SMA (short > long = bullish)
        ]
        
        market_data = {"AAPL": current_quote}
        historical_data = {"AAPL": sample_quotes}
        
        signals = momentum_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 1
        signal = signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength >= momentum_strategy.min_momentum_strength
        assert signal.price == current_quote.close
    
    def test_generate_bearish_momentum_signal(self, momentum_strategy, current_quote, 
                                            sample_quotes, portfolio_snapshot):
        """Test generation of bearish momentum signal."""
        # Mock technical analysis results for bearish momentum
        mock_ta_instance = Mock()
        momentum_strategy.technical_analysis = mock_ta_instance
        
        mock_ta_instance.calculate_rsi.return_value = [None] * 19 + [75.0]  # Overbought RSI with enough history
        mock_ta_instance.calculate_macd.return_value = (
            [None] * 18 + [-0.3, -0.5],  # MACD line with bearish crossover
            [None] * 18 + [-0.2, -0.3],  # Signal line 
            [None] * 18 + [-0.1, -0.2]   # Histogram
        )
        mock_ta_instance.calculate_sma.side_effect = [
            [None] * 9 + [108.0] * 11,   # Short SMA with enough history
            [None] * 19 + [110.0]        # Long SMA (short < long = bearish)
        ]
        
        # Create a quote with negative price change
        bearish_quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            open=Decimal('110.0'),
            high=Decimal('110.5'),
            low=Decimal('108.0'),
            close=Decimal('108.5'),  # Lower close
            volume=1500000
        )
        
        # Add a position to sell
        from financial_portfolio_automation.models.core import Position
        position = Position(
            symbol="AAPL",
            quantity=Decimal('100'),
            cost_basis=Decimal('10500.0'),
            market_value=Decimal('10850.0'),
            unrealized_pnl=Decimal('350.0'),
            day_pnl=Decimal('50.0')
        )
        momentum_strategy.state.positions["AAPL"] = position
        
        market_data = {"AAPL": bearish_quote}
        historical_data = {"AAPL": sample_quotes}
        
        signals = momentum_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
        
        assert len(signals) == 1
        signal = signals[0]
        assert signal.symbol == "AAPL"
        assert signal.signal_type == SignalType.SELL
        assert signal.strength >= momentum_strategy.min_momentum_strength
    
    def test_analyze_momentum_with_insufficient_data(self, momentum_strategy, current_quote):
        """Test momentum analysis with insufficient data."""
        short_history = [current_quote] * 5  # Less than lookback period
        
        signal = momentum_strategy._analyze_momentum("AAPL", current_quote, short_history)
        
        assert signal is None
    
    def test_update_state(self, momentum_strategy, portfolio_snapshot):
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
        
        momentum_strategy.update_state(market_data, portfolio_snapshot)
        
        # Check that position was updated
        assert "AAPL" in momentum_strategy.state.positions
        assert momentum_strategy.state.positions["AAPL"].quantity == 100
        
        # Check metadata update
        assert 'last_market_update' in momentum_strategy.state.metadata
        assert 'portfolio_value' in momentum_strategy.state.metadata
    
    def test_momentum_strategy_parameters(self, strategy_config):
        """Test strategy parameter handling."""
        # Test with custom parameters
        custom_params = {
            'lookback_period': 30,
            'momentum_threshold': 0.02,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'price_change_threshold': 0.03,
            'min_momentum_strength': 0.7
        }
        strategy_config.parameters = custom_params
        
        strategy = MomentumStrategy(strategy_config)
        
        assert strategy.lookback_period == 30
        assert strategy.rsi_oversold == 25
        assert strategy.rsi_overbought == 75
        assert strategy.price_change_threshold == 0.03
        assert strategy.min_momentum_strength == 0.7
    
    def test_momentum_signal_validation(self, momentum_strategy, current_quote, sample_quotes):
        """Test momentum signal validation."""
        # Test with mock technical analysis that produces weak signals
        with patch('financial_portfolio_automation.strategy.momentum.TechnicalAnalysis') as mock_ta:
            mock_ta_instance = Mock()
            mock_ta.return_value = mock_ta_instance
            
            # Weak momentum indicators
            mock_ta_instance.calculate_rsi.return_value = [55.0]  # Neutral RSI
            mock_ta_instance.calculate_macd.return_value = ([0.1], [0.1], [0.0])  # Weak MACD
            mock_ta_instance.calculate_sma.side_effect = [
                [110.0],  # Short SMA
                [109.8]   # Long SMA (minimal difference)
            ]
            
            market_data = {"AAPL": current_quote}
            historical_data = {"AAPL": sample_quotes}
            portfolio_snapshot = PortfolioSnapshot(
                timestamp=datetime.now(timezone.utc),
                total_value=Decimal('100000'),
                buying_power=Decimal('50000'),
                day_pnl=Decimal('0'),
                total_pnl=Decimal('0'),
                positions=[]
            )
            
            signals = momentum_strategy.generate_signals(market_data, portfolio_snapshot, historical_data)
            
            # Should not generate signals due to weak momentum
            assert len(signals) == 0
    
    def test_momentum_strategy_multiple_symbols(self, momentum_strategy, sample_quotes, portfolio_snapshot):
        """Test momentum strategy with multiple symbols."""
        # Create quotes for second symbol
        googl_quotes = []
        for quote in sample_quotes:
            googl_quote = Quote(
                symbol="GOOGL",
                timestamp=quote.timestamp,
                open=quote.open * 10,  # Different price scale
                high=quote.high * 10,
                low=quote.low * 10,
                close=quote.close * 10,
                volume=quote.volume
            )
            googl_quotes.append(googl_quote)
        
        current_quotes = {
            "AAPL": Quote(
                symbol="AAPL",
                timestamp=datetime.now(timezone.utc),
                open=Decimal('112.0'),
                high=Decimal('113.0'),
                low=Decimal('111.0'),
                close=Decimal('112.5'),
                volume=1500000
            ),
            "GOOGL": Quote(
                symbol="GOOGL",
                timestamp=datetime.now(timezone.utc),
                open=Decimal('1120.0'),
                high=Decimal('1130.0'),
                low=Decimal('1110.0'),
                close=Decimal('1125.0'),
                volume=500000
            )
        }
        
        historical_data = {
            "AAPL": sample_quotes,
            "GOOGL": googl_quotes
        }
        
        # Mock technical analysis results for bullish momentum
        mock_ta_instance = Mock()
        momentum_strategy.technical_analysis = mock_ta_instance
        
        # Strong bullish signals for both symbols
        mock_ta_instance.calculate_rsi.return_value = [None] * 19 + [65.0]
        mock_ta_instance.calculate_macd.return_value = (
            [None] * 18 + [0.5, 0.8],  # MACD line with bullish crossover
            [None] * 18 + [0.6, 0.5],  # Signal line 
            [None] * 18 + [-0.1, 0.3]  # Histogram
        )
        mock_ta_instance.calculate_sma.side_effect = [
            [None] * 9 + [112.0] * 11,   # AAPL Short SMA
            [None] * 19 + [110.0],       # AAPL Long SMA
            [None] * 9 + [1125.0] * 11,  # GOOGL Short SMA
            [None] * 19 + [1120.0]       # GOOGL Long SMA
        ]
        
        signals = momentum_strategy.generate_signals(current_quotes, portfolio_snapshot, historical_data)
        
        # Should generate signals for both symbols
        assert len(signals) == 2
        symbols = {signal.symbol for signal in signals}
        assert symbols == {"AAPL", "GOOGL"}