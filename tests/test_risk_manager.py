"""
Unit tests for RiskManager class.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from financial_portfolio_automation.analysis.risk_manager import RiskManager
from financial_portfolio_automation.models.core import Position, PortfolioSnapshot, Order, OrderSide, OrderType, OrderStatus
from financial_portfolio_automation.models.config import RiskLimits


class TestRiskManager:
    """Test cases for RiskManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create custom risk limits for testing
        self.risk_limits = RiskLimits(
            max_position_size=Decimal('10000.00'),
            max_portfolio_concentration=0.25,  # 25%
            max_daily_loss=Decimal('1000.00'),
            max_drawdown=0.10,  # 10%
            stop_loss_percentage=0.05  # 5%
        )
        
        self.risk_manager = RiskManager(self.risk_limits)
        
        # Create sample positions
        self.sample_positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal('8000.00'),
                cost_basis=Decimal('7500.00'),
                unrealized_pnl=Decimal('500.00'),
                day_pnl=Decimal('100.00')
            ),
            Position(
                symbol="GOOGL",
                quantity=25,
                market_value=Decimal('6000.00'),
                cost_basis=Decimal('5800.00'),
                unrealized_pnl=Decimal('200.00'),
                day_pnl=Decimal('50.00')
            ),
            Position(
                symbol="TSLA",
                quantity=50,
                market_value=Decimal('4000.00'),
                cost_basis=Decimal('4200.00'),
                unrealized_pnl=Decimal('-200.00'),
                day_pnl=Decimal('-25.00')
            )
        ]
        
        # Create sample portfolio
        self.sample_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('18000.00'),
            buying_power=Decimal('2000.00'),
            day_pnl=Decimal('125.00'),
            total_pnl=Decimal('500.00'),
            positions=self.sample_positions
        )
    
    def test_default_risk_limits(self):
        """Test default risk limits initialization."""
        default_manager = RiskManager()
        assert default_manager.risk_limits is not None
        assert default_manager.risk_limits.max_position_size > 0
        assert default_manager.risk_limits.max_portfolio_concentration > 0
        assert default_manager.risk_limits.max_daily_loss > 0
        assert default_manager.risk_limits.max_drawdown > 0
    
    def test_set_risk_limits(self):
        """Test setting new risk limits."""
        new_limits = RiskLimits(
            max_position_size=Decimal('20000.00'),
            max_portfolio_concentration=0.30,
            max_daily_loss=Decimal('2000.00'),
            max_drawdown=0.15,
            stop_loss_percentage=0.08
        )
        
        self.risk_manager.set_risk_limits(new_limits)
        assert self.risk_manager.risk_limits.max_position_size == Decimal('20000.00')
        assert self.risk_manager.risk_limits.max_portfolio_concentration == 0.30
    
    def test_validate_position_size_valid(self):
        """Test position size validation for valid positions."""
        # Test valid position within limits (20 * 200 = 4000, which is 22.2% of 18000)
        result = self.risk_manager.validate_position_size(
            "MSFT", 20, Decimal('200.00'), self.sample_portfolio
        )
        
        assert result['is_valid'] is True
        assert result['symbol'] == "MSFT"
        assert result['proposed_quantity'] == 20
        assert result['proposed_value'] == 4000.0  # 20 * 200
        assert len(result['violations']) == 0
    
    def test_validate_position_size_exceeds_max_position(self):
        """Test position size validation when exceeding max position size."""
        # Test position exceeding max position size
        result = self.risk_manager.validate_position_size(
            "MSFT", 100, Decimal('200.00'), self.sample_portfolio
        )
        
        assert result['is_valid'] is False
        assert len(result['violations']) > 0
        assert any(v['type'] == 'max_position_size' for v in result['violations'])
    
    def test_validate_position_size_exceeds_concentration(self):
        """Test position size validation when exceeding concentration limit."""
        # Test position exceeding concentration limit (25% of 18000 = 4500)
        result = self.risk_manager.validate_position_size(
            "MSFT", 30, Decimal('200.00'), self.sample_portfolio
        )
        
        assert result['is_valid'] is False
        assert len(result['violations']) > 0
        assert any(v['type'] == 'max_concentration' for v in result['violations'])
    
    def test_validate_position_size_existing_position(self):
        """Test position size validation for existing positions."""
        # Test adding to existing AAPL position
        result = self.risk_manager.validate_position_size(
            "AAPL", 50, Decimal('80.00'), self.sample_portfolio
        )
        
        # Should calculate new total: existing 100 + new 50 = 150 shares
        assert result['current_quantity'] == 100
        assert result['new_total_quantity'] == 150
        assert result['new_position_value'] == 12000.0  # 150 * 80
    
    def test_validate_position_size_warnings(self):
        """Test position size validation warnings."""
        # Test position approaching limits (19 * 200 = 3800, which is 21.1% concentration - above 80% of 25% limit)
        result = self.risk_manager.validate_position_size(
            "MSFT", 19, Decimal('200.00'), self.sample_portfolio
        )
        
        # Should be valid but have warnings (21.1% is above 80% of 25% limit)
        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
    
    def test_monitor_portfolio_concentration(self):
        """Test portfolio concentration monitoring."""
        result = self.risk_manager.monitor_portfolio_concentration(self.sample_portfolio)
        
        # Check structure
        assert 'total_positions' in result
        assert 'concentration_violations' in result
        assert 'herfindahl_index' in result
        assert 'is_diversified' in result
        
        # Check values
        assert result['total_positions'] == 3
        
        # AAPL has 8000/18000 = 44.4% allocation, should violate 25% limit
        assert len(result['concentration_violations']) > 0
        assert any(v['symbol'] == 'AAPL' for v in result['concentration_violations'])
        
        # Should not be considered diversified due to concentration
        assert result['is_diversified'] is False
    
    def test_monitor_portfolio_concentration_empty(self):
        """Test concentration monitoring with empty portfolio."""
        empty_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('0.00'),
            buying_power=Decimal('1000.00'),
            day_pnl=Decimal('0.00'),
            total_pnl=Decimal('0.00'),
            positions=[]
        )
        
        result = self.risk_manager.monitor_portfolio_concentration(empty_portfolio)
        
        assert result['total_positions'] == 0
        assert len(result['concentration_violations']) == 0
        assert result['herfindahl_index'] == 0
        assert result['is_diversified'] is True
    
    def test_monitor_drawdown(self):
        """Test drawdown monitoring."""
        # Create portfolio history with drawdown
        portfolio_snapshots = []
        base_time = datetime.now(timezone.utc) - timedelta(days=10)
        
        # Values: 20000 -> 18000 -> 16000 -> 17000 (peak at 20000, trough at 16000)
        values = [20000, 19000, 18000, 16000, 17000]
        
        for i, value in enumerate(values):
            timestamp = base_time + timedelta(days=i * 2)
            snapshot = PortfolioSnapshot(
                timestamp=timestamp,
                total_value=Decimal(str(value)),
                buying_power=Decimal('2000.00'),
                day_pnl=Decimal('0.00'),
                total_pnl=Decimal('0.00'),
                positions=[]
            )
            portfolio_snapshots.append(snapshot)
        
        result = self.risk_manager.monitor_drawdown(portfolio_snapshots)
        
        # Check structure
        assert 'current_drawdown' in result
        assert 'max_drawdown' in result
        assert 'drawdown_violation' in result
        assert 'peak_value' in result
        
        # Max drawdown should be (20000 - 16000) / 20000 = 20%
        assert abs(result['max_drawdown'] - 0.20) < 0.01
        
        # Should violate 10% drawdown limit
        assert result['drawdown_violation'] is True
        assert result['peak_value'] == 20000
    
    def test_monitor_drawdown_insufficient_data(self):
        """Test drawdown monitoring with insufficient data."""
        result = self.risk_manager.monitor_drawdown([self.sample_portfolio])
        
        assert result['current_drawdown'] == 0
        assert result['max_drawdown'] == 0
        assert result['drawdown_violation'] is False
    
    def test_calculate_volatility_based_position_size(self):
        """Test volatility-based position sizing."""
        result = self.risk_manager.calculate_volatility_based_position_size(
            "MSFT", Decimal('200.00'), 0.25, Decimal('18000.00'), 0.02
        )
        
        # Check structure
        assert 'recommended_quantity' in result
        assert 'recommended_value' in result
        assert 'stop_loss_price' in result
        assert 'position_size_method' in result
        
        # Should have reasonable values
        assert result['recommended_quantity'] >= 0
        assert result['stop_loss_price'] > 0
        assert result['position_size_method'] == 'volatility_based'
        assert result['symbol'] == 'MSFT'
    
    def test_calculate_volatility_based_position_size_edge_cases(self):
        """Test volatility-based position sizing with edge cases."""
        # Test with zero volatility
        result = self.risk_manager.calculate_volatility_based_position_size(
            "MSFT", Decimal('200.00'), 0.0, Decimal('18000.00')
        )
        
        assert result['recommended_quantity'] == 0
        assert result['recommended_value'] == 0
        
        # Test with zero price
        result = self.risk_manager.calculate_volatility_based_position_size(
            "MSFT", Decimal('0.00'), 0.25, Decimal('18000.00')
        )
        
        assert result['recommended_quantity'] == 0
        assert result['recommended_value'] == 0
    
    def test_validate_order_risk_valid(self):
        """Test order risk validation for valid orders."""
        order = Order(
            order_id="TEST001",
            symbol="MSFT",
            quantity=20,  # Reduced to stay within limits
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal('200.00')
        )
        
        result = self.risk_manager.validate_order_risk(order, self.sample_portfolio)
        
        assert result['is_valid'] is True
        assert result['order_id'] == "TEST001"
        assert result['symbol'] == "MSFT"
        assert len(result['violations']) == 0
    
    def test_validate_order_risk_invalid(self):
        """Test order risk validation for invalid orders."""
        # Order that would exceed position size limit
        order = Order(
            order_id="TEST002",
            symbol="MSFT",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal('200.00')
        )
        
        result = self.risk_manager.validate_order_risk(order, self.sample_portfolio)
        
        assert result['is_valid'] is False
        assert len(result['violations']) > 0
    
    def test_validate_order_risk_missing_price(self):
        """Test order risk validation with missing price."""
        order = Order(
            order_id="TEST003",
            symbol="MSFT",
            quantity=25,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
        
        result = self.risk_manager.validate_order_risk(order, self.sample_portfolio)
        
        assert result['is_valid'] is False
        assert any(v['type'] == 'missing_price' for v in result['violations'])
    
    def test_validate_order_risk_daily_loss_limit(self):
        """Test order risk validation with daily loss limits."""
        # Create portfolio with significant daily loss
        portfolio_with_loss = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('18000.00'),
            buying_power=Decimal('2000.00'),
            day_pnl=Decimal('-800.00'),  # Already close to -1000 limit
            total_pnl=Decimal('500.00'),
            positions=self.sample_positions
        )
        
        # Large order that could push daily loss over limit
        # Current daily PnL is -800, limit is -1000, so we need potential loss > 200
        # Order value of 5000 * 5% = 250 potential loss, which should trigger violation
        order = Order(
            order_id="TEST004",
            symbol="MSFT",
            quantity=25,  # 25 * 200 = 5000 value, 5% loss = 250
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal('200.00')
        )
        
        result = self.risk_manager.validate_order_risk(order, portfolio_with_loss)
        
        # Should have daily loss violation (projected loss: -800 - 250 = -1050 > -1000 limit)
        daily_loss_violations = [v for v in result['violations'] if v['type'] == 'max_daily_loss']
        assert len(daily_loss_violations) > 0
    
    def test_generate_risk_report(self):
        """Test comprehensive risk report generation."""
        # Create portfolio history for drawdown analysis
        portfolio_history = []
        base_time = datetime.now(timezone.utc) - timedelta(days=5)
        
        for i in range(6):
            timestamp = base_time + timedelta(days=i)
            value = 18000 + (i * 100)  # Slight upward trend
            snapshot = PortfolioSnapshot(
                timestamp=timestamp,
                total_value=Decimal(str(value)),
                buying_power=Decimal('2000.00'),
                day_pnl=Decimal('50.00'),
                total_pnl=Decimal('500.00'),
                positions=self.sample_positions
            )
            portfolio_history.append(snapshot)
        
        result = self.risk_manager.generate_risk_report(
            self.sample_portfolio, portfolio_history
        )
        
        # Check main sections
        assert 'report_timestamp' in result
        assert 'risk_score' in result
        assert 'risk_level' in result
        assert 'concentration_analysis' in result
        assert 'drawdown_analysis' in result
        assert 'risk_compliance' in result
        assert 'recommendations' in result
        
        # Check risk score is reasonable
        assert 0 <= result['risk_score'] <= 100
        assert result['risk_level'] in ['Low', 'Moderate', 'High', 'Very High', 'Extreme']
        
        # Should have recommendations due to AAPL concentration
        assert len(result['recommendations']) > 0
    
    def test_generate_risk_report_no_history(self):
        """Test risk report generation without portfolio history."""
        result = self.risk_manager.generate_risk_report(self.sample_portfolio)
        
        # Should still work without history
        assert 'risk_score' in result
        assert 'concentration_analysis' in result
        assert result['drawdown_analysis'] == {}  # Empty without history
    
    def test_risk_score_calculation(self):
        """Test risk score calculation components."""
        # Create high-risk portfolio (concentrated, in drawdown, daily loss)
        high_risk_positions = [
            Position(
                symbol="AAPL",
                quantity=200,
                market_value=Decimal('16000.00'),  # 89% concentration
                cost_basis=Decimal('15000.00'),
                unrealized_pnl=Decimal('1000.00'),
                day_pnl=Decimal('-500.00')
            )
        ]
        
        high_risk_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('18000.00'),
            buying_power=Decimal('2000.00'),
            day_pnl=Decimal('-900.00'),  # Close to daily loss limit
            total_pnl=Decimal('1000.00'),
            positions=high_risk_positions
        )
        
        # Create drawdown history
        drawdown_history = []
        base_time = datetime.now(timezone.utc) - timedelta(days=5)
        values = [20000, 19000, 18000, 17000, 18000]  # 15% drawdown
        
        for i, value in enumerate(values):
            timestamp = base_time + timedelta(days=i)
            snapshot = PortfolioSnapshot(
                timestamp=timestamp,
                total_value=Decimal(str(value)),
                buying_power=Decimal('2000.00'),
                day_pnl=Decimal('-100.00'),
                total_pnl=Decimal('0.00'),
                positions=high_risk_positions
            )
            drawdown_history.append(snapshot)
        
        result = self.risk_manager.generate_risk_report(
            high_risk_portfolio, drawdown_history
        )
        
        # Should have high risk score due to multiple factors
        assert result['risk_score'] > 50  # Should be high risk
        assert result['risk_level'] in ['High', 'Very High', 'Extreme']
    
    def test_risk_recommendations(self):
        """Test risk recommendation generation."""
        result = self.risk_manager.generate_risk_report(self.sample_portfolio)
        
        recommendations = result['recommendations']
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should recommend reducing AAPL concentration
        concentration_rec = any(
            'concentration' in rec.lower() or 'reduce' in rec.lower() 
            for rec in recommendations
        )
        assert concentration_rec
    
    def test_edge_cases_and_error_handling(self):
        """Test edge cases and error handling."""
        # Test with zero portfolio value
        zero_portfolio = PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('0.00'),
            buying_power=Decimal('1000.00'),
            day_pnl=Decimal('0.00'),
            total_pnl=Decimal('0.00'),
            positions=[]
        )
        
        result = self.risk_manager.validate_position_size(
            "MSFT", 10, Decimal('100.00'), zero_portfolio
        )
        
        # Should handle zero portfolio value gracefully
        assert 'concentration_percent' in result
        
        # Test concentration monitoring with zero portfolio
        conc_result = self.risk_manager.monitor_portfolio_concentration(zero_portfolio)
        assert conc_result['total_positions'] == 0
        assert conc_result['is_diversified'] is True