"""
Unit tests for PortfolioAnalyzer class.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.models.core import Position, PortfolioSnapshot


class TestPortfolioAnalyzer:
    """Test cases for PortfolioAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = PortfolioAnalyzer()
        
        # Create sample positions
        self.sample_positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal('15000.00'),
                cost_basis=Decimal('14000.00'),
                unrealized_pnl=Decimal('1000.00'),
                day_pnl=Decimal('200.00')
            ),
            Position(
                symbol="GOOGL",
                quantity=50,
                market_value=Decimal('10000.00'),
                cost_basis=Decimal('9500.00'),
                unrealized_pnl=Decimal('500.00'),
                day_pnl=Decimal('100.00')
            ),
            Position(
                symbol="TSLA",
                quantity=-25,  # Short position
                market_value=Decimal('5000.00'),  # Market value is always positive
                cost_basis=Decimal('5200.00'),
                unrealized_pnl=Decimal('200.00'),
                day_pnl=Decimal('-50.00')
            )
        ]
        
        # Create sample portfolio snapshot
        # Total value should be 15000 + 10000 - 5000 = 20000 (short position reduces total)
        self.sample_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('20000.00'),
            buying_power=Decimal('5000.00'),
            day_pnl=Decimal('250.00'),
            total_pnl=Decimal('1700.00'),
            positions=self.sample_positions
        )
        
        # Create time series of portfolio snapshots
        self.portfolio_snapshots = []
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        for i in range(31):  # 31 days of data
            timestamp = base_time + timedelta(days=i)
            # Simulate portfolio value growth with some volatility
            base_value = 18000 + (i * 50)  # Growing trend
            volatility = np.random.normal(0, 200)  # Add some noise
            total_value = max(base_value + volatility, 1000)  # Ensure positive
            
            snapshot = PortfolioSnapshot(
                timestamp=timestamp,
                total_value=Decimal(str(total_value)),
                buying_power=Decimal('5000.00'),
                day_pnl=Decimal(str(np.random.normal(0, 100))),
                total_pnl=Decimal(str(total_value - 18000)),
                positions=self.sample_positions.copy()
            )
            self.portfolio_snapshots.append(snapshot)
    
    def test_set_risk_free_rate(self):
        """Test setting risk-free rate."""
        self.analyzer.set_risk_free_rate(0.03)
        assert self.analyzer.risk_free_rate == 0.03
        
        # Test negative rate should raise error
        with pytest.raises(ValueError):
            self.analyzer.set_risk_free_rate(-0.01)
    
    def test_calculate_portfolio_value_and_allocation(self):
        """Test portfolio value and allocation calculation."""
        result = self.analyzer.calculate_portfolio_value_and_allocation(self.sample_portfolio)
        
        # Check basic structure
        assert 'total_value' in result
        assert 'allocations' in result
        assert 'position_count' in result
        
        # Check values
        assert result['total_value'] == 20000.00
        assert result['position_count'] == 3
        assert result['long_position_count'] == 2
        assert result['short_position_count'] == 1
        
        # Check allocations
        allocations = result['allocations']
        assert 'AAPL' in allocations
        assert 'GOOGL' in allocations
        assert 'TSLA' in allocations
        
        # AAPL should have 75% allocation (15000/20000)
        assert abs(allocations['AAPL']['allocation_percent'] - 75.0) < 0.01
        
        # Check concentration metrics
        assert 'max_allocation_percent' in result
        assert 'concentration_hhi' in result
        assert result['max_allocation_percent'] == 75.0  # AAPL is largest
    
    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation."""
        # Test with insufficient data
        with pytest.raises(ValueError):
            self.analyzer.calculate_risk_metrics([self.sample_portfolio])
        
        # Test with sufficient data
        result = self.analyzer.calculate_risk_metrics(self.portfolio_snapshots)
        
        # Check required metrics
        required_metrics = [
            'mean_daily_return', 'daily_volatility', 'annual_return',
            'annual_volatility', 'sharpe_ratio', 'var_95_daily',
            'max_drawdown', 'sortino_ratio', 'calmar_ratio'
        ]
        
        for metric in required_metrics:
            assert metric in result
        
        # Check that volatility is positive
        assert result['daily_volatility'] >= 0
        assert result['annual_volatility'] >= 0
        
        # Check that max drawdown is between 0 and 1
        assert 0 <= result['max_drawdown'] <= 1
    
    def test_calculate_risk_metrics_with_market_data(self):
        """Test risk metrics calculation with market returns for beta."""
        # Create mock market returns
        market_returns = [np.random.normal(0.001, 0.02) for _ in range(30)]
        
        result = self.analyzer.calculate_risk_metrics(self.portfolio_snapshots, market_returns)
        
        # Should now include beta and correlation
        assert 'beta' in result
        assert 'correlation_with_market' in result
        assert result['beta'] is not None
        assert result['correlation_with_market'] is not None
    
    def test_max_drawdown_calculation(self):
        """Test maximum drawdown calculation."""
        # Test with simple declining values
        declining_values = [100, 90, 80, 85, 75, 70, 80]
        max_dd = self.analyzer._calculate_max_drawdown(declining_values)
        
        # Maximum drawdown should be 30% (from 100 to 70)
        assert abs(max_dd - 0.30) < 0.01
        
        # Test with no drawdown (increasing values)
        increasing_values = [100, 110, 120, 130]
        max_dd_none = self.analyzer._calculate_max_drawdown(increasing_values)
        assert max_dd_none == 0.0
        
        # Test with insufficient data
        single_value = [100]
        max_dd_single = self.analyzer._calculate_max_drawdown(single_value)
        assert max_dd_single == 0.0
    
    def test_calculate_performance_attribution(self):
        """Test performance attribution calculation."""
        # Test with insufficient data
        with pytest.raises(ValueError):
            self.analyzer.calculate_performance_attribution([self.sample_portfolio])
        
        # Test with sufficient data
        result = self.analyzer.calculate_performance_attribution(self.portfolio_snapshots)
        
        # Check structure
        assert 'total_return' in result
        assert 'position_contributions' in result
        assert 'top_contributors' in result
        assert 'worst_contributors' in result
        
        # Check that all positions are included
        contributions = result['position_contributions']
        assert 'AAPL' in contributions
        assert 'GOOGL' in contributions
        assert 'TSLA' in contributions
        
        # Check contribution structure
        for symbol, contrib in contributions.items():
            assert 'initial_value' in contrib
            assert 'final_value' in contrib
            assert 'position_return' in contrib
            assert 'contribution_to_return' in contrib
    
    def test_calculate_correlation_analysis(self):
        """Test correlation analysis calculation."""
        # Create sample position returns
        position_returns = {
            'AAPL': [0.01, -0.02, 0.015, -0.01, 0.02],
            'GOOGL': [0.008, -0.015, 0.012, -0.008, 0.018],
            'TSLA': [-0.02, 0.03, -0.025, 0.02, -0.015]
        }
        
        result = self.analyzer.calculate_correlation_analysis(position_returns)
        
        # Check structure
        assert 'correlation_matrix' in result
        assert 'average_correlation' in result
        assert 'max_correlation' in result
        assert 'most_correlated_pair' in result
        assert 'diversification_benefit' in result
        
        # Check correlation matrix
        corr_matrix = result['correlation_matrix']
        assert 'AAPL' in corr_matrix
        assert 'GOOGL' in corr_matrix
        assert 'TSLA' in corr_matrix
        
        # Diagonal should be 1.0
        assert corr_matrix['AAPL']['AAPL'] == 1.0
        assert corr_matrix['GOOGL']['GOOGL'] == 1.0
        assert corr_matrix['TSLA']['TSLA'] == 1.0
        
        # Test with insufficient positions
        single_position = {'AAPL': [0.01, 0.02, 0.03]}
        result_single = self.analyzer.calculate_correlation_analysis(single_position)
        assert result_single['average_correlation'] == 0
    
    def test_generate_comprehensive_analysis(self):
        """Test comprehensive analysis generation."""
        # Create position returns for correlation analysis
        position_returns = {
            'AAPL': [0.01, -0.02, 0.015, -0.01, 0.02],
            'GOOGL': [0.008, -0.015, 0.012, -0.008, 0.018],
            'TSLA': [-0.02, 0.03, -0.025, 0.02, -0.015]
        }
        
        # Create market returns
        market_returns = [np.random.normal(0.001, 0.02) for _ in range(30)]
        
        result = self.analyzer.generate_comprehensive_analysis(
            self.portfolio_snapshots,
            market_returns,
            position_returns
        )
        
        # Check main sections
        assert 'analysis_timestamp' in result
        assert 'current_portfolio' in result
        assert 'value_and_allocation' in result
        assert 'risk_metrics' in result
        assert 'performance_attribution' in result
        assert 'correlation_analysis' in result
        assert 'summary' in result
        
        # Check summary section
        summary = result['summary']
        assert 'is_diversified' in summary
        assert 'risk_level' in summary
        assert 'performance_rating' in summary
        assert 'concentration_warning' in summary
        
        # Test with single snapshot (should work but with limited metrics)
        result_single = self.analyzer.generate_comprehensive_analysis([self.sample_portfolio])
        assert 'value_and_allocation' in result_single
        assert result_single['risk_metrics'] == {}  # Should be empty
    
    def test_risk_level_categorization(self):
        """Test risk level categorization."""
        assert self.analyzer._categorize_risk_level(0.05) == "Low"
        assert self.analyzer._categorize_risk_level(0.15) == "Moderate"
        assert self.analyzer._categorize_risk_level(0.25) == "High"
        assert self.analyzer._categorize_risk_level(0.35) == "Very High"
    
    def test_performance_rating(self):
        """Test performance rating based on Sharpe ratio."""
        assert self.analyzer._rate_performance(2.5) == "Excellent"
        assert self.analyzer._rate_performance(1.5) == "Good"
        assert self.analyzer._rate_performance(0.7) == "Fair"
        assert self.analyzer._rate_performance(0.2) == "Poor"
        assert self.analyzer._rate_performance(-0.5) == "Very Poor"
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Empty portfolio snapshots
        with pytest.raises(ValueError):
            self.analyzer.generate_comprehensive_analysis([])
        
        # Portfolio with zero total value
        zero_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('0.00'),
            buying_power=Decimal('5000.00'),
            day_pnl=Decimal('0.00'),
            total_pnl=Decimal('0.00'),
            positions=[]
        )
        
        result = self.analyzer.calculate_portfolio_value_and_allocation(zero_portfolio)
        assert result['total_value'] == 0.0
        assert result['position_count'] == 0
    
    def test_data_validation(self):
        """Test data validation and error handling."""
        # Test with invalid position (zero quantity)
        with pytest.raises(ValueError, match="Position quantity cannot be zero"):
            Position(
                symbol="AAPL",
                quantity=0,  # This should cause validation error
                market_value=Decimal('1000.00'),
                cost_basis=Decimal('1000.00'),
                unrealized_pnl=Decimal('0.00'),
                day_pnl=Decimal('0.00')
            )
        
        # Test with invalid symbol format
        with pytest.raises(ValueError, match="Invalid symbol format"):
            Position(
                symbol="INVALID",
                quantity=100,
                market_value=Decimal('1000.00'),
                cost_basis=Decimal('1000.00'),
                unrealized_pnl=Decimal('0.00'),
                day_pnl=Decimal('0.00')
            )
    
    def test_numerical_stability(self):
        """Test numerical stability with extreme values."""
        # Create portfolio with very small values
        small_positions = [
            Position(
                symbol="SMALL",
                quantity=1,
                market_value=Decimal('0.01'),
                cost_basis=Decimal('0.01'),
                unrealized_pnl=Decimal('0.00'),
                day_pnl=Decimal('0.00')
            )
        ]
        
        small_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('0.01'),
            buying_power=Decimal('1000.00'),
            day_pnl=Decimal('0.00'),
            total_pnl=Decimal('0.00'),
            positions=small_positions
        )
        
        result = self.analyzer.calculate_portfolio_value_and_allocation(small_portfolio)
        assert result['total_value'] == 0.01
        assert not np.isnan(result['allocations']['SMALL']['allocation_percent'])
        
        # Create portfolio with very large values
        large_positions = [
            Position(
                symbol="LARGE",
                quantity=1000000,
                market_value=Decimal('1000000000.00'),
                cost_basis=Decimal('900000000.00'),
                unrealized_pnl=Decimal('100000000.00'),
                day_pnl=Decimal('1000000.00')
            )
        ]
        
        large_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('1000000000.00'),
            buying_power=Decimal('50000000.00'),
            day_pnl=Decimal('1000000.00'),
            total_pnl=Decimal('100000000.00'),
            positions=large_positions
        )
        
        result_large = self.analyzer.calculate_portfolio_value_and_allocation(large_portfolio)
        assert result_large['total_value'] == 1000000000.00
        assert not np.isnan(result_large['allocations']['LARGE']['allocation_percent'])