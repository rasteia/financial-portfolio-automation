"""
Integration tests for the backtesting engine with realistic market data and strategies.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from financial_portfolio_automation.strategy.backtester import Backtester, TransactionCosts
from financial_portfolio_automation.strategy.momentum import MomentumStrategy
from financial_portfolio_automation.strategy.mean_reversion import MeanReversionStrategy
from financial_portfolio_automation.models.core import Quote, PortfolioSnapshot
from financial_portfolio_automation.models.config import StrategyConfig, StrategyType, RiskLimits


def generate_realistic_market_data(symbols: List[str], 
                                   start_date: datetime, 
                                   days: int,
                                   initial_prices: Dict[str, float] = None) -> Dict[str, List[Quote]]:
    """
    Generate realistic market data with trends, volatility, and correlations.
    
    Args:
        symbols: List of symbols to generate data for
        start_date: Starting date for data generation
        days: Number of days to generate
        initial_prices: Initial prices for each symbol
        
    Returns:
        Dictionary mapping symbols to quote lists
    """
    if initial_prices is None:
        initial_prices = {symbol: 100.0 + i * 50 for i, symbol in enumerate(symbols)}
    
    data = {}
    
    # Set random seed for reproducible tests
    np.random.seed(42)
    
    for symbol in symbols:
        quotes = []
        current_price = initial_prices[symbol]
        
        # Generate correlated random walks with different characteristics
        if symbol == "AAPL":
            # Tech stock with higher volatility and growth trend
            daily_return_mean = 0.0008  # Slight positive trend
            daily_volatility = 0.025   # 2.5% daily volatility
        elif symbol == "GOOGL":
            # Another tech stock, correlated with AAPL
            daily_return_mean = 0.0006
            daily_volatility = 0.028
        elif symbol == "SPY":
            # Market ETF with lower volatility
            daily_return_mean = 0.0005
            daily_volatility = 0.015
        else:
            # Default parameters
            daily_return_mean = 0.0003
            daily_volatility = 0.020
        
        for day in range(days):
            date = start_date + timedelta(days=day)
            
            # Generate price movement
            daily_return = np.random.normal(daily_return_mean, daily_volatility)
            current_price *= (1 + daily_return)
            
            # Ensure price doesn't go negative
            current_price = max(current_price, 1.0)
            
            # Create realistic bid-ask spread (0.1% of price)
            spread = current_price * 0.001
            bid = current_price - spread / 2
            ask = current_price + spread / 2
            
            quote = Quote(
                symbol=symbol,
                timestamp=date.replace(hour=16, minute=0, second=0),  # Market close
                bid=Decimal(str(round(bid, 2))),
                ask=Decimal(str(round(ask, 2))),
                bid_size=np.random.randint(500, 2000),
                ask_size=np.random.randint(500, 2000)
            )
            quotes.append(quote)
        
        data[symbol] = quotes
    
    return data


@pytest.fixture
def realistic_transaction_costs():
    """Create realistic transaction costs."""
    return TransactionCosts(
        commission_per_share=Decimal('0.005'),  # $0.005 per share
        commission_minimum=Decimal('1.00'),     # $1.00 minimum
        commission_maximum=Decimal('6.95'),     # $6.95 maximum (typical broker)
        spread_cost_factor=Decimal('0.5'),      # 50% of spread
        market_impact_factor=Decimal('0.0005'), # 0.05% market impact
        slippage_factor=Decimal('0.0002')       # 0.02% slippage
    )


@pytest.fixture
def backtester_with_realistic_costs(realistic_transaction_costs):
    """Create backtester with realistic transaction costs."""
    return Backtester(
        transaction_costs=realistic_transaction_costs,
        initial_capital=Decimal('100000')  # $100k starting capital
    )


@pytest.fixture
def momentum_strategy():
    """Create momentum strategy for testing."""
    config = StrategyConfig(
        strategy_id="momentum_test",
        strategy_type=StrategyType.MOMENTUM,
        name="Momentum Test Strategy",
        description="A momentum strategy for backtesting integration tests",
        symbols=["AAPL", "GOOGL", "SPY"],
        risk_limits=RiskLimits(
            max_position_size=Decimal('20000'),      # Max $20k per position
            max_portfolio_concentration=0.3,          # Max 30% in one position
            max_daily_loss=Decimal('2000'),          # Max $2k daily loss
            max_drawdown=0.15,                       # Max 15% drawdown
            stop_loss_percentage=0.05                # 5% stop loss
        ),
        parameters={
            'lookback_period': 20,
            'momentum_threshold': 0.02,
            'short_window': 10,
            'long_window': 30,
            'min_signal_strength': 0.6
        }
    )
    return MomentumStrategy(config)


@pytest.fixture
def mean_reversion_strategy():
    """Create mean reversion strategy for testing."""
    config = StrategyConfig(
        strategy_id="mean_reversion_test",
        strategy_type=StrategyType.MEAN_REVERSION,
        name="Mean Reversion Test Strategy",
        description="A mean reversion strategy for backtesting integration tests",
        symbols=["AAPL", "GOOGL", "SPY"],
        risk_limits=RiskLimits(
            max_position_size=Decimal('15000'),      # Max $15k per position
            max_portfolio_concentration=0.25,         # Max 25% in one position
            max_daily_loss=Decimal('1500'),          # Max $1.5k daily loss
            max_drawdown=0.12,                       # Max 12% drawdown
            stop_loss_percentage=0.04                # 4% stop loss
        ),
        parameters={
            'lookback_period': 20,
            'deviation_threshold': 2.0,
            'std_dev_threshold': 2.0,
            'mean_reversion_threshold': 0.015,
            'min_signal_strength': 0.7
        }
    )
    return MeanReversionStrategy(config)


class TestBacktesterIntegration:
    """Integration tests for backtester with realistic scenarios."""
    
    def test_momentum_strategy_backtest(self, backtester_with_realistic_costs, momentum_strategy):
        """Test backtesting with momentum strategy on realistic data."""
        # Generate 6 months of data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 6, 30)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL", "GOOGL", "SPY"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0, "GOOGL": 2500.0, "SPY": 400.0}
        )
        
        # Run backtest
        results = backtester_with_realistic_costs.run_backtest(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Validate results
        assert results.strategy_id == "momentum_test"
        assert results.initial_capital == Decimal('100000')
        assert results.final_value > 0
        assert isinstance(results.total_return, float)
        assert isinstance(results.annual_return, float)
        assert isinstance(results.max_drawdown, float)
        assert isinstance(results.sharpe_ratio, float)
        assert results.total_trades >= 0
        assert len(results.portfolio_history) > 0
        assert len(results.trades) == results.total_trades
        
        # Check that transaction costs were applied
        if results.total_trades > 0:
            assert results.total_commission > 0
            assert results.total_slippage >= 0
        
        print(f"Momentum Strategy Results:")
        print(f"  Total Return: {results.total_return:.2%}")
        print(f"  Annual Return: {results.annual_return:.2%}")
        print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {results.max_drawdown:.2%}")
        print(f"  Total Trades: {results.total_trades}")
        print(f"  Win Rate: {results.win_rate:.2%}")
    
    def test_mean_reversion_strategy_backtest(self, backtester_with_realistic_costs, mean_reversion_strategy):
        """Test backtesting with mean reversion strategy on realistic data."""
        # Generate 4 months of data with more volatility for mean reversion opportunities
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 4, 30)
        days = (end_date - start_date).days
        
        # Set seed for reproducible results
        np.random.seed(123)
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL", "GOOGL", "SPY"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 160.0, "GOOGL": 2600.0, "SPY": 410.0}
        )
        
        # Run backtest
        results = backtester_with_realistic_costs.run_backtest(
            strategy=mean_reversion_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Validate results
        assert results.strategy_id == "mean_reversion_test"
        assert results.initial_capital == Decimal('100000')
        assert results.final_value > 0
        assert isinstance(results.total_return, float)
        assert results.total_trades >= 0
        assert len(results.portfolio_history) > 0
        
        print(f"Mean Reversion Strategy Results:")
        print(f"  Total Return: {results.total_return:.2%}")
        print(f"  Annual Return: {results.annual_return:.2%}")
        print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {results.max_drawdown:.2%}")
        print(f"  Total Trades: {results.total_trades}")
        print(f"  Win Rate: {results.win_rate:.2%}")
    
    def test_walk_forward_analysis_integration(self, backtester_with_realistic_costs, momentum_strategy):
        """Test walk-forward analysis with realistic data."""
        # Generate 1 year of data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL", "GOOGL"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0, "GOOGL": 2500.0}
        )
        
        # Run walk-forward analysis
        results = backtester_with_realistic_costs.run_walk_forward_analysis(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date,
            training_period_months=3,  # 3 months training
            testing_period_months=1,   # 1 month testing
            step_months=1              # 1 month step
        )
        
        # Validate results
        assert 'period_results' in results
        assert 'aggregate_statistics' in results
        assert 'parameters' in results
        
        period_results = results['period_results']
        assert len(period_results) > 0
        
        # Check that each period has required fields
        for period in period_results:
            assert 'period_start' in period
            assert 'period_end' in period
            assert 'total_return' in period
            assert 'sharpe_ratio' in period
            assert 'max_drawdown' in period
            assert 'total_trades' in period
        
        # Check aggregate statistics
        agg_stats = results['aggregate_statistics']
        if agg_stats:  # Only check if we have results
            assert 'periods_tested' in agg_stats
            assert 'average_return' in agg_stats
            assert 'consistency_ratio' in agg_stats
            
            print(f"Walk-Forward Analysis Results:")
            print(f"  Periods Tested: {agg_stats['periods_tested']}")
            print(f"  Average Return: {agg_stats['average_return']:.2%}")
            print(f"  Consistency Ratio: {agg_stats['consistency_ratio']:.2%}")
    
    def test_monte_carlo_simulation_integration(self, backtester_with_realistic_costs, momentum_strategy):
        """Test Monte Carlo simulation with realistic data."""
        # Generate 3 months of data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL", "SPY"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0, "SPY": 400.0}
        )
        
        # Run Monte Carlo simulation with fewer simulations for faster testing
        results = backtester_with_realistic_costs.run_monte_carlo_simulation(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date,
            num_simulations=10,  # Reduced for testing speed
            confidence_levels=[0.05, 0.95]
        )
        
        # Validate results
        assert 'statistics' in results
        assert 'var_analysis' in results
        assert 'simulation_results' in results
        assert 'parameters' in results
        
        # Check statistics
        stats = results['statistics']
        assert 'simulations_completed' in stats
        assert 'mean_return' in stats
        assert 'std_return' in stats
        assert 'positive_returns_pct' in stats
        
        # Check VaR analysis
        var_analysis = results['var_analysis']
        assert 'var_5' in var_analysis
        assert 'var_95' in var_analysis
        assert 'cvar_5' in var_analysis
        assert 'cvar_95' in var_analysis
        
        # Check simulation results
        sim_results = results['simulation_results']
        assert len(sim_results) <= 10  # Should have up to 10 results
        assert all(hasattr(result, 'total_return') for result in sim_results)
        
        print(f"Monte Carlo Simulation Results:")
        print(f"  Simulations Completed: {stats['simulations_completed']}")
        print(f"  Mean Return: {stats['mean_return']:.2%}")
        print(f"  Return Std Dev: {stats['std_return']:.2%}")
        print(f"  Positive Returns: {stats['positive_returns_pct']:.1f}%")
        print(f"  VaR (5%): {var_analysis['var_5']:.2%}")
        print(f"  VaR (95%): {var_analysis['var_95']:.2%}")
    
    def test_transaction_cost_impact(self, momentum_strategy):
        """Test the impact of different transaction cost models."""
        # Generate data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0}
        )
        
        # Test with low costs
        low_costs = TransactionCosts(
            commission_per_share=Decimal('0.001'),
            commission_minimum=Decimal('0.50'),
            commission_maximum=Decimal('2.00'),
            spread_cost_factor=Decimal('0.1'),
            market_impact_factor=Decimal('0.0001'),
            slippage_factor=Decimal('0.0001')
        )
        
        backtester_low = Backtester(
            transaction_costs=low_costs,
            initial_capital=Decimal('100000')
        )
        
        results_low = backtester_low.run_backtest(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Test with high costs
        high_costs = TransactionCosts(
            commission_per_share=Decimal('0.01'),
            commission_minimum=Decimal('5.00'),
            commission_maximum=Decimal('20.00'),
            spread_cost_factor=Decimal('1.0'),
            market_impact_factor=Decimal('0.002'),
            slippage_factor=Decimal('0.001')
        )
        
        backtester_high = Backtester(
            transaction_costs=high_costs,
            initial_capital=Decimal('100000')
        )
        
        results_high = backtester_high.run_backtest(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Compare results
        print(f"Transaction Cost Impact Analysis:")
        print(f"  Low Costs - Return: {results_low.total_return:.2%}, "
              f"Commission: ${results_low.total_commission:.2f}")
        print(f"  High Costs - Return: {results_high.total_return:.2%}, "
              f"Commission: ${results_high.total_commission:.2f}")
        
        # High costs should generally result in lower returns (if there are trades)
        if results_low.total_trades > 0 and results_high.total_trades > 0:
            assert results_high.total_commission >= results_low.total_commission
    
    def test_strategy_comparison(self, backtester_with_realistic_costs, 
                                momentum_strategy, mean_reversion_strategy):
        """Compare performance of different strategies on the same data."""
        # Generate data with mixed market conditions
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 6, 30)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL", "GOOGL"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0, "GOOGL": 2500.0}
        )
        
        # Test momentum strategy
        momentum_results = backtester_with_realistic_costs.run_backtest(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Reset backtester state and test mean reversion strategy
        backtester_with_realistic_costs._reset_state()
        
        mean_reversion_results = backtester_with_realistic_costs.run_backtest(
            strategy=mean_reversion_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Compare results
        print(f"Strategy Comparison:")
        print(f"  Momentum - Return: {momentum_results.total_return:.2%}, "
              f"Sharpe: {momentum_results.sharpe_ratio:.2f}, "
              f"Trades: {momentum_results.total_trades}")
        print(f"  Mean Reversion - Return: {mean_reversion_results.total_return:.2%}, "
              f"Sharpe: {mean_reversion_results.sharpe_ratio:.2f}, "
              f"Trades: {mean_reversion_results.total_trades}")
        
        # Both strategies should produce valid results
        assert momentum_results.final_value > 0
        assert mean_reversion_results.final_value > 0
        assert isinstance(momentum_results.total_return, float)
        assert isinstance(mean_reversion_results.total_return, float)
    
    def test_portfolio_evolution_tracking(self, backtester_with_realistic_costs, momentum_strategy):
        """Test that portfolio evolution is properly tracked throughout backtest."""
        # Generate data
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 2, 28)
        days = (end_date - start_date).days
        
        historical_data = generate_realistic_market_data(
            symbols=["AAPL"],
            start_date=start_date,
            days=days,
            initial_prices={"AAPL": 150.0}
        )
        
        # Run backtest
        results = backtester_with_realistic_costs.run_backtest(
            strategy=momentum_strategy,
            historical_data=historical_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Validate portfolio history
        portfolio_history = results.portfolio_history
        assert len(portfolio_history) > 0
        
        # Check that portfolio values are tracked over time
        portfolio_values = [float(snapshot.total_value) for snapshot in portfolio_history]
        assert len(portfolio_values) > 0
        assert all(value > 0 for value in portfolio_values)
        
        # Check that timestamps are in chronological order
        timestamps = [snapshot.timestamp for snapshot in portfolio_history]
        assert timestamps == sorted(timestamps)
        
        # Verify final portfolio value matches results
        final_portfolio_value = portfolio_history[-1].total_value
        assert abs(final_portfolio_value - results.final_value) < Decimal('0.01')
        
        print(f"Portfolio Evolution Tracking:")
        print(f"  Initial Value: ${portfolio_values[0]:,.2f}")
        print(f"  Final Value: ${portfolio_values[-1]:,.2f}")
        print(f"  Min Value: ${min(portfolio_values):,.2f}")
        print(f"  Max Value: ${max(portfolio_values):,.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])