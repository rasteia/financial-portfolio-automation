"""
Unit tests for the backtesting engine.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from financial_portfolio_automation.strategy.backtester import (
    Backtester, BacktestResults, BacktestTrade, TransactionCosts
)
from financial_portfolio_automation.strategy.base import Strategy, StrategySignal, SignalType
from financial_portfolio_automation.models.core import Quote, Position, PortfolioSnapshot, OrderSide
from financial_portfolio_automation.models.config import StrategyConfig, StrategyType, RiskLimits


class MockStrategy(Strategy):
    """Mock strategy for testing."""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.signals_to_generate = []
    
    def generate_signals(self, market_data, portfolio, historical_data=None):
        """Generate predefined signals."""
        return self.signals_to_generate.copy()
    
    def update_state(self, market_data, portfolio):
        """Update strategy state."""
        pass


@pytest.fixture
def transaction_costs():
    """Create transaction costs configuration."""
    return TransactionCosts(
        commission_per_share=Decimal('0.005'),
        commission_minimum=Decimal('1.00'),
        commission_maximum=Decimal('5.00'),
        spread_cost_factor=Decimal('0.5'),
        market_impact_factor=Decimal('0.001'),
        slippage_factor=Decimal('0.0005')
    )


@pytest.fixture
def backtester(transaction_costs):
    """Create backtester instance."""
    return Backtester(
        transaction_costs=transaction_costs,
        initial_capital=Decimal('100000')
    )


@pytest.fixture
def mock_strategy():
    """Create mock strategy."""
    config = StrategyConfig(
        strategy_id="test_strategy",
        strategy_type=StrategyType.MOMENTUM,
        name="Test Strategy",
        description="A test strategy for backtesting",
        symbols=["AAPL", "GOOGL"],
        risk_limits=RiskLimits(
            max_position_size=Decimal('10000'),
            max_portfolio_concentration=0.2,
            max_daily_loss=Decimal('1000'),
            max_drawdown=0.1,
            stop_loss_percentage=0.05
        ),
        parameters={
            'lookback_period': 20,
            'momentum_threshold': 0.02
        }
    )
    return MockStrategy(config)


@pytest.fixture
def sample_historical_data():
    """Create sample historical data."""
    base_date = datetime(2023, 1, 1)
    data = {}
    
    for i, symbol in enumerate(["AAPL", "GOOGL"]):
        quotes = []
        base_price = 150.0 + i * 50  # AAPL starts at 150, GOOGL at 200
        
        for day in range(30):  # 30 days of data
            date = base_date + timedelta(days=day)
            # Add some price movement
            price_change = np.random.normal(0, 0.02)  # 2% daily volatility
            price = base_price * (1 + price_change)
            
            quote = Quote(
                symbol=symbol,
                timestamp=date,
                bid=Decimal(str(price - 0.05)),
                ask=Decimal(str(price + 0.05)),
                bid_size=1000,
                ask_size=1000
            )
            quotes.append(quote)
            base_price = price
        
        data[symbol] = quotes
    
    return data


class TestTransactionCosts:
    """Test transaction costs configuration."""
    
    def test_transaction_costs_creation(self):
        """Test transaction costs creation with defaults."""
        costs = TransactionCosts()
        
        assert costs.commission_per_share == Decimal('0.005')
        assert costs.commission_minimum == Decimal('1.00')
        assert costs.commission_maximum == Decimal('5.00')
        assert costs.spread_cost_factor == Decimal('0.5')
        assert costs.market_impact_factor == Decimal('0.001')
        assert costs.slippage_factor == Decimal('0.0005')
    
    def test_transaction_costs_custom_values(self):
        """Test transaction costs with custom values."""
        costs = TransactionCosts(
            commission_per_share=Decimal('0.01'),
            commission_minimum=Decimal('2.00')
        )
        
        assert costs.commission_per_share == Decimal('0.01')
        assert costs.commission_minimum == Decimal('2.00')


class TestBacktestTrade:
    """Test backtest trade data structure."""
    
    def test_backtest_trade_creation(self):
        """Test backtest trade creation."""
        trade = BacktestTrade(
            timestamp=datetime.now(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        assert trade.symbol == "AAPL"
        assert trade.side == OrderSide.BUY
        assert trade.quantity == 100
        assert trade.price == Decimal('150.00')
    
    def test_total_cost_calculation(self):
        """Test total cost calculation."""
        trade = BacktestTrade(
            timestamp=datetime.now(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        expected_total_cost = Decimal('1.75')  # 1.00 + 0.50 + 0.25
        assert trade.total_cost == expected_total_cost
    
    def test_net_amount_buy(self):
        """Test net amount calculation for buy order."""
        trade = BacktestTrade(
            timestamp=datetime.now(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        gross_amount = Decimal('15000.00')  # 100 * 150.00
        total_cost = Decimal('1.75')
        expected_net = gross_amount + total_cost
        
        assert trade.net_amount == expected_net
    
    def test_net_amount_sell(self):
        """Test net amount calculation for sell order."""
        trade = BacktestTrade(
            timestamp=datetime.now(),
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        gross_amount = Decimal('15000.00')  # 100 * 150.00
        total_cost = Decimal('1.75')
        expected_net = gross_amount - total_cost
        
        assert trade.net_amount == expected_net


class TestBacktester:
    """Test backtester functionality."""
    
    def test_backtester_initialization(self, transaction_costs):
        """Test backtester initialization."""
        backtester = Backtester(
            transaction_costs=transaction_costs,
            initial_capital=Decimal('50000')
        )
        
        assert backtester.transaction_costs == transaction_costs
        assert backtester.initial_capital == Decimal('50000')
        assert backtester._cash_balance == Decimal('50000')
    
    def test_backtester_default_initialization(self):
        """Test backtester with default parameters."""
        backtester = Backtester()
        
        assert backtester.initial_capital == Decimal('100000')
        assert isinstance(backtester.transaction_costs, TransactionCosts)
    
    def test_reset_state(self, backtester):
        """Test state reset functionality."""
        # Modify state
        backtester._cash_balance = Decimal('50000')
        backtester._current_positions = {"AAPL": Mock()}
        backtester._trades = [Mock()]
        
        # Reset state
        backtester._reset_state()
        
        assert backtester._cash_balance == backtester.initial_capital
        assert len(backtester._current_positions) == 0
        assert len(backtester._trades) == 0
        assert len(backtester._portfolio_history) == 0
    
    def test_validate_backtest_inputs_valid(self, backtester, sample_historical_data):
        """Test input validation with valid data."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        # Should not raise any exception
        backtester._validate_backtest_inputs(sample_historical_data, start_date, end_date)
    
    def test_validate_backtest_inputs_empty_data(self, backtester):
        """Test input validation with empty data."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        with pytest.raises(ValueError, match="Historical data cannot be empty"):
            backtester._validate_backtest_inputs({}, start_date, end_date)
    
    def test_validate_backtest_inputs_invalid_dates(self, backtester, sample_historical_data):
        """Test input validation with invalid dates."""
        start_date = datetime(2023, 1, 31)
        end_date = datetime(2023, 1, 1)
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            backtester._validate_backtest_inputs(sample_historical_data, start_date, end_date)
    
    def test_get_trading_dates(self, backtester, sample_historical_data):
        """Test trading dates extraction."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        
        trading_dates = backtester._get_trading_dates(sample_historical_data, start_date, end_date)
        
        assert len(trading_dates) == 10  # 10 days
        assert all(isinstance(date, datetime) for date in trading_dates)
        assert trading_dates == sorted(trading_dates)  # Should be sorted
    
    def test_get_market_data_for_date(self, backtester, sample_historical_data):
        """Test market data retrieval for specific date."""
        target_date = datetime(2023, 1, 5)
        
        market_data = backtester._get_market_data_for_date(sample_historical_data, target_date)
        
        assert "AAPL" in market_data
        assert "GOOGL" in market_data
        assert isinstance(market_data["AAPL"], Quote)
        assert market_data["AAPL"].timestamp.date() == target_date.date()
    
    def test_calculate_commission(self, backtester):
        """Test commission calculation."""
        # Test normal commission
        commission = backtester._calculate_commission(100, Decimal('150.00'))
        expected = Decimal('100') * Decimal('0.005')  # 100 * 0.005 = 0.50
        assert commission == max(expected, Decimal('1.00'))  # Should be minimum $1.00
        
        # Test minimum commission
        commission = backtester._calculate_commission(10, Decimal('150.00'))
        assert commission == Decimal('1.00')  # Should be minimum
        
        # Test maximum commission
        commission = backtester._calculate_commission(2000, Decimal('150.00'))
        assert commission == Decimal('5.00')  # Should be maximum
    
    def test_calculate_execution_price_buy(self, backtester):
        """Test execution price calculation for buy orders."""
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal('149.95'),
            ask=Decimal('150.05'),
            bid_size=1000,
            ask_size=1000
        )
        
        execution_price = backtester._calculate_execution_price(quote, OrderSide.BUY, 100)
        
        # Should be ask price plus slippage
        assert execution_price > quote.ask
    
    def test_calculate_execution_price_sell(self, backtester):
        """Test execution price calculation for sell orders."""
        quote = Quote(
            symbol="AAPL",
            timestamp=datetime.now(),
            bid=Decimal('149.95'),
            ask=Decimal('150.05'),
            bid_size=1000,
            ask_size=1000
        )
        
        execution_price = backtester._calculate_execution_price(quote, OrderSide.SELL, 100)
        
        # Should be bid price minus slippage
        assert execution_price < quote.bid
    
    def test_execute_trade_buy(self, backtester):
        """Test trade execution for buy orders."""
        initial_cash = backtester._cash_balance
        
        backtester._execute_trade(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        # Check cash balance decreased
        expected_cost = Decimal('100') * Decimal('150.00') + Decimal('1.75')
        assert backtester._cash_balance == initial_cash - expected_cost
        
        # Check position created
        assert "AAPL" in backtester._current_positions
        position = backtester._current_positions["AAPL"]
        assert position.quantity == 100
        assert position.symbol == "AAPL"
        
        # Check trade recorded
        assert len(backtester._trades) == 1
        trade = backtester._trades[0]
        assert trade.symbol == "AAPL"
        assert trade.side == OrderSide.BUY
        assert trade.quantity == 100
    
    def test_execute_trade_sell_existing_position(self, backtester):
        """Test trade execution for sell orders with existing position."""
        # First create a position
        backtester._execute_trade(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        initial_cash = backtester._cash_balance
        
        # Now sell part of the position
        backtester._execute_trade(
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=50,
            price=Decimal('155.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        # Check cash balance increased
        expected_proceeds = Decimal('50') * Decimal('155.00') - Decimal('1.75')
        assert backtester._cash_balance == initial_cash + expected_proceeds
        
        # Check position updated
        position = backtester._current_positions["AAPL"]
        assert position.quantity == 50  # 100 - 50
        
        # Check trades recorded
        assert len(backtester._trades) == 2
    
    def test_execute_trade_close_position(self, backtester):
        """Test closing a position completely."""
        # Create a position
        backtester._execute_trade(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal('150.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        # Close the position completely
        backtester._execute_trade(
            symbol="AAPL",
            side=OrderSide.SELL,
            quantity=100,
            price=Decimal('155.00'),
            commission=Decimal('1.00'),
            slippage=Decimal('0.50'),
            market_impact=Decimal('0.25'),
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            signal_strength=0.8
        )
        
        # Position should be removed
        assert "AAPL" not in backtester._current_positions
    
    def test_run_backtest_basic(self, backtester, mock_strategy, sample_historical_data):
        """Test basic backtest execution."""
        # Configure strategy to generate a simple buy signal
        buy_signal = StrategySignal(
            symbol="AAPL",
            signal_type=SignalType.BUY,
            strength=0.8,
            quantity=100
        )
        mock_strategy.signals_to_generate = [buy_signal]
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        
        results = backtester.run_backtest(
            strategy=mock_strategy,
            historical_data=sample_historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(results, BacktestResults)
        assert results.strategy_id == "test_strategy"
        assert results.start_date == start_date
        assert results.end_date == end_date
        assert results.initial_capital == backtester.initial_capital
        assert results.total_trades >= 0
        assert len(results.portfolio_history) > 0
    
    def test_run_backtest_no_signals(self, backtester, mock_strategy, sample_historical_data):
        """Test backtest with no signals generated."""
        # Strategy generates no signals
        mock_strategy.signals_to_generate = []
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        
        results = backtester.run_backtest(
            strategy=mock_strategy,
            historical_data=sample_historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        assert results.total_trades == 0
        assert results.final_value == results.initial_capital
        assert results.total_return == 0.0
    
    def test_run_backtest_invalid_inputs(self, backtester, mock_strategy):
        """Test backtest with invalid inputs."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        
        with pytest.raises(ValueError):
            backtester.run_backtest(
                strategy=mock_strategy,
                historical_data={},  # Empty data
                start_date=start_date,
                end_date=end_date
            )
    
    @patch('financial_portfolio_automation.strategy.backtester.random.choices')
    def test_generate_randomized_datasets(self, mock_choices, backtester, sample_historical_data):
        """Test randomized dataset generation for Monte Carlo."""
        # Mock random.choices to return predictable results
        mock_choices.side_effect = lambda population, k: population[:k]
        
        datasets = backtester._generate_randomized_datasets(sample_historical_data, 2)
        
        assert len(datasets) == 2
        assert all("AAPL" in dataset for dataset in datasets)
        assert all("GOOGL" in dataset for dataset in datasets)
        
        # Verify mock was called
        assert mock_choices.call_count > 0
    
    def test_walk_forward_analysis_basic(self, backtester, mock_strategy, sample_historical_data):
        """Test basic walk-forward analysis."""
        mock_strategy.signals_to_generate = []  # No signals for simplicity
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 20)
        
        results = backtester.run_walk_forward_analysis(
            strategy=mock_strategy,
            historical_data=sample_historical_data,
            start_date=start_date,
            end_date=end_date,
            training_period_months=1,
            testing_period_months=1,
            step_months=1
        )
        
        assert 'period_results' in results
        assert 'aggregate_statistics' in results
        assert 'parameters' in results
        assert isinstance(results['period_results'], list)
    
    def test_monte_carlo_simulation_basic(self, backtester, mock_strategy, sample_historical_data):
        """Test basic Monte Carlo simulation."""
        mock_strategy.signals_to_generate = []  # No signals for simplicity
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        
        with patch.object(backtester, '_run_single_simulation') as mock_sim:
            # Mock simulation results
            mock_result = BacktestResults(
                strategy_id="test_strategy",
                start_date=start_date,
                end_date=end_date,
                initial_capital=Decimal('100000'),
                final_value=Decimal('105000'),
                total_return=0.05,
                annual_return=0.05,
                max_drawdown=0.02,
                sharpe_ratio=1.5,
                sortino_ratio=2.0,
                calmar_ratio=2.5,
                win_rate=0.6,
                profit_factor=1.8,
                total_trades=10,
                winning_trades=6,
                losing_trades=4,
                total_commission=Decimal('50'),
                total_slippage=Decimal('25')
            )
            mock_sim.return_value = mock_result
            
            results = backtester.run_monte_carlo_simulation(
                strategy=mock_strategy,
                historical_data=sample_historical_data,
                start_date=start_date,
                end_date=end_date,
                num_simulations=5
            )
            
            assert 'statistics' in results
            assert 'var_analysis' in results
            assert 'simulation_results' in results
            assert 'parameters' in results
            
            # Check that simulations were run
            assert mock_sim.call_count == 5


class TestBacktestResults:
    """Test backtest results data structure."""
    
    def test_backtest_results_creation(self):
        """Test backtest results creation."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 31)
        
        results = BacktestResults(
            strategy_id="test_strategy",
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal('100000'),
            final_value=Decimal('105000'),
            total_return=0.05,
            annual_return=0.05,
            max_drawdown=0.02,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            calmar_ratio=2.5,
            win_rate=0.6,
            profit_factor=1.8,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            total_commission=Decimal('50'),
            total_slippage=Decimal('25')
        )
        
        assert results.strategy_id == "test_strategy"
        assert results.start_date == start_date
        assert results.end_date == end_date
        assert results.total_return == 0.05
        assert results.win_rate == 0.6
        assert results.total_trades == 10
        assert len(results.trades) == 0  # Default empty
        assert len(results.portfolio_history) == 0  # Default empty


if __name__ == "__main__":
    pytest.main([__file__])