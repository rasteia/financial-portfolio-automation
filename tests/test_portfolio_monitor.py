"""
Unit tests for the PortfolioMonitor class.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from financial_portfolio_automation.monitoring.portfolio_monitor import (
    PortfolioMonitor, MonitoringThresholds, MonitoringAlert, AlertSeverity
)
from financial_portfolio_automation.models.core import Position, Quote, PortfolioSnapshot
from financial_portfolio_automation.exceptions import MonitoringError


@pytest.fixture
def mock_portfolio_analyzer():
    """Create a mock portfolio analyzer."""
    analyzer = Mock()
    analyzer.create_portfolio_snapshot.return_value = PortfolioSnapshot(
        timestamp=datetime.now(),
        total_value=Decimal('100000'),
        buying_power=Decimal('50000'),
        day_pnl=Decimal('1000'),
        total_pnl=Decimal('5000'),
        positions=[]
    )
    analyzer.calculate_portfolio_metrics.return_value = {
        'total_value': 100000,
        'max_drawdown': 5.0,
        'volatility': 0.15
    }
    return analyzer


@pytest.fixture
def mock_technical_analysis():
    """Create a mock technical analysis engine."""
    analysis = Mock()
    analysis.calculate_volatility.return_value = 0.25
    return analysis


@pytest.fixture
def mock_data_cache():
    """Create a mock data cache."""
    cache = Mock()
    cache.get.return_value = {
        'symbol': 'AAPL',
        'timestamp': datetime.now(),
        'bid': Decimal('150.00'),
        'ask': Decimal('150.05'),
        'bid_size': 100,
        'ask_size': 100
    }
    return cache


@pytest.fixture
def monitoring_thresholds():
    """Create test monitoring thresholds."""
    return MonitoringThresholds(
        position_change_percent=5.0,
        portfolio_change_percent=2.0,
        volatility_threshold=0.3,
        monitoring_interval=1  # 1 second for faster tests
    )


@pytest.fixture
def portfolio_monitor(mock_portfolio_analyzer, mock_technical_analysis, 
                     mock_data_cache, monitoring_thresholds):
    """Create a PortfolioMonitor instance for testing."""
    return PortfolioMonitor(
        portfolio_analyzer=mock_portfolio_analyzer,
        technical_analysis=mock_technical_analysis,
        data_cache=mock_data_cache,
        thresholds=monitoring_thresholds
    )


class TestPortfolioMonitor:
    """Test cases for PortfolioMonitor class."""
    
    def test_initialization(self, portfolio_monitor):
        """Test PortfolioMonitor initialization."""
        assert not portfolio_monitor.is_monitoring
        assert len(portfolio_monitor.alert_callbacks) == 0
        assert portfolio_monitor._last_portfolio_snapshot is None
        assert len(portfolio_monitor._position_baselines) == 0
    
    def test_add_remove_alert_callback(self, portfolio_monitor):
        """Test adding and removing alert callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        # Add callbacks
        portfolio_monitor.add_alert_callback(callback1)
        portfolio_monitor.add_alert_callback(callback2)
        assert len(portfolio_monitor.alert_callbacks) == 2
        
        # Remove callback
        portfolio_monitor.remove_alert_callback(callback1)
        assert len(portfolio_monitor.alert_callbacks) == 1
        assert callback2 in portfolio_monitor.alert_callbacks
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, portfolio_monitor):
        """Test starting and stopping monitoring."""
        symbols = ['AAPL', 'GOOGL']
        
        # Mock the initialization method
        portfolio_monitor._initialize_baselines = AsyncMock()
        
        # Start monitoring
        await portfolio_monitor.start_monitoring(symbols)
        assert portfolio_monitor.is_monitoring
        assert portfolio_monitor._monitoring_task is not None
        
        # Stop monitoring
        await portfolio_monitor.stop_monitoring()
        assert not portfolio_monitor.is_monitoring
    
    @pytest.mark.asyncio
    async def test_initialize_baselines(self, portfolio_monitor):
        """Test baseline initialization."""
        symbols = ['AAPL', 'GOOGL']
        
        # Mock methods
        portfolio_monitor._get_current_positions = AsyncMock(return_value=[
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            )
        ])
        portfolio_monitor._get_latest_quote = AsyncMock(return_value=Quote(
            symbol='AAPL',
            timestamp=datetime.now(),
            bid=Decimal('150.00'),
            ask=Decimal('150.05'),
            bid_size=100,
            ask_size=100
        ))
        
        await portfolio_monitor._initialize_baselines(symbols)
        
        # Check baselines were set
        assert 'AAPL' in portfolio_monitor._position_baselines
        assert portfolio_monitor._position_baselines['AAPL'] == Decimal('15000')
        assert 'AAPL' in portfolio_monitor._price_baselines
        assert portfolio_monitor._last_portfolio_snapshot is not None
    
    @pytest.mark.asyncio
    async def test_initialize_baselines_error(self, portfolio_monitor):
        """Test baseline initialization error handling."""
        symbols = ['AAPL']
        
        # Mock method to raise exception
        portfolio_monitor._get_current_positions = AsyncMock(side_effect=Exception("Test error"))
        
        with pytest.raises(MonitoringError):
            await portfolio_monitor._initialize_baselines(symbols)
    
    @pytest.mark.asyncio
    async def test_monitor_portfolio_changes_value_change(self, portfolio_monitor):
        """Test portfolio value change monitoring."""
        # Set up initial snapshot
        portfolio_monitor._last_portfolio_snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000'),
            positions=[]
        )
        
        # Mock current positions with different value - need at least one position
        test_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            )
        ]
        portfolio_monitor._get_current_positions = AsyncMock(return_value=test_positions)
        portfolio_monitor.portfolio_analyzer.create_portfolio_snapshot.return_value = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('103000'),  # 3% increase
            buying_power=Decimal('50000'),
            day_pnl=Decimal('3000'),
            total_pnl=Decimal('8000'),
            positions=test_positions
        )
        
        # Mock alert generation
        portfolio_monitor._generate_alert = AsyncMock()
        
        await portfolio_monitor._monitor_portfolio_changes()
        
        # Check that alert was generated for portfolio value change
        portfolio_monitor._generate_alert.assert_called()
        call_args = portfolio_monitor._generate_alert.call_args
        assert call_args[1]['alert_type'] == 'portfolio_value_change'
        assert call_args[1]['severity'] == AlertSeverity.WARNING
    
    @pytest.mark.asyncio
    async def test_monitor_portfolio_changes_daily_pnl(self, portfolio_monitor):
        """Test daily P&L threshold monitoring."""
        # Set up initial snapshot
        portfolio_monitor._last_portfolio_snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000'),
            positions=[]
        )
        
        # Mock current positions with high daily P&L - need at least one position
        test_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            )
        ]
        portfolio_monitor._get_current_positions = AsyncMock(return_value=test_positions)
        portfolio_monitor.portfolio_analyzer.create_portfolio_snapshot.return_value = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('6000'),  # Above threshold
            total_pnl=Decimal('11000'),
            positions=test_positions
        )
        
        # Mock alert generation
        portfolio_monitor._generate_alert = AsyncMock()
        
        await portfolio_monitor._monitor_portfolio_changes()
        
        # Check that alert was generated for daily P&L
        portfolio_monitor._generate_alert.assert_called()
        call_args = portfolio_monitor._generate_alert.call_args
        assert call_args[1]['alert_type'] == 'daily_pnl_threshold'
    
    @pytest.mark.asyncio
    async def test_monitor_position_changes(self, portfolio_monitor):
        """Test position change monitoring."""
        # Set up position baselines
        portfolio_monitor._position_baselines = {'AAPL': Decimal('15000')}
        
        # Mock current positions with significant change
        portfolio_monitor._get_current_positions = AsyncMock(return_value=[
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('16000'),  # 6.67% increase
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('2000'),
                day_pnl=Decimal('1000')
            )
        ])
        
        # Mock alert generation
        portfolio_monitor._generate_alert = AsyncMock()
        
        await portfolio_monitor._monitor_position_changes()
        
        # Check that alert was generated for position change
        portfolio_monitor._generate_alert.assert_called()
        call_args = portfolio_monitor._generate_alert.call_args
        assert call_args[1]['alert_type'] == 'position_value_change'
        assert call_args[1]['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_monitor_price_movement(self, portfolio_monitor):
        """Test price movement monitoring."""
        # Set up price baselines
        portfolio_monitor._price_baselines = {'AAPL': Decimal('150.00')}
        
        # Mock quote with significant price change
        portfolio_monitor._get_latest_quote = AsyncMock(return_value=Quote(
            symbol='AAPL',
            timestamp=datetime.now(),
            bid=Decimal('165.00'),  # 10% increase
            ask=Decimal('165.05'),
            bid_size=100,
            ask_size=100
        ))
        
        # Mock alert generation
        portfolio_monitor._generate_alert = AsyncMock()
        
        await portfolio_monitor._monitor_price_movement('AAPL')
        
        # Check that alert was generated for price movement
        portfolio_monitor._generate_alert.assert_called()
        call_args = portfolio_monitor._generate_alert.call_args
        assert call_args[1]['alert_type'] == 'price_movement'
        assert call_args[1]['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_monitor_volatility(self, portfolio_monitor):
        """Test volatility monitoring."""
        # Mock historical data and high volatility
        portfolio_monitor._get_historical_prices = AsyncMock(return_value=[150.0] * 20)
        portfolio_monitor.technical_analysis.calculate_volatility.return_value = 0.35  # Above threshold
        
        # Mock alert generation
        portfolio_monitor._generate_alert = AsyncMock()
        
        await portfolio_monitor._monitor_volatility('AAPL')
        
        # Check that alert was generated for high volatility
        portfolio_monitor._generate_alert.assert_called()
        call_args = portfolio_monitor._generate_alert.call_args
        assert call_args[1]['alert_type'] == 'high_volatility'
        assert call_args[1]['symbol'] == 'AAPL'
    
    @pytest.mark.asyncio
    async def test_generate_alert(self, portfolio_monitor):
        """Test alert generation and callback dispatch."""
        callback1 = Mock()
        callback2 = Mock()
        portfolio_monitor.add_alert_callback(callback1)
        portfolio_monitor.add_alert_callback(callback2)
        
        await portfolio_monitor._generate_alert(
            alert_type='test_alert',
            severity=AlertSeverity.WARNING,
            message='Test alert message',
            symbol='AAPL',
            data={'test_key': 'test_value'}
        )
        
        # Check that both callbacks were called
        callback1.assert_called_once()
        callback2.assert_called_once()
        
        # Check alert structure
        alert = callback1.call_args[0][0]
        assert isinstance(alert, MonitoringAlert)
        assert alert.alert_type == 'test_alert'
        assert alert.severity == AlertSeverity.WARNING
        assert alert.symbol == 'AAPL'
        assert alert.message == 'Test alert message'
        assert alert.data['test_key'] == 'test_value'
    
    @pytest.mark.asyncio
    async def test_generate_alert_callback_error(self, portfolio_monitor):
        """Test alert generation with callback error."""
        # Add callback that raises exception
        error_callback = Mock(side_effect=Exception("Callback error"))
        good_callback = Mock()
        
        portfolio_monitor.add_alert_callback(error_callback)
        portfolio_monitor.add_alert_callback(good_callback)
        
        # Should not raise exception despite callback error
        await portfolio_monitor._generate_alert(
            alert_type='test_alert',
            severity=AlertSeverity.INFO,
            message='Test message'
        )
        
        # Good callback should still be called
        good_callback.assert_called_once()
    
    def test_get_monitoring_status(self, portfolio_monitor):
        """Test monitoring status retrieval."""
        # Set up some state
        portfolio_monitor.is_monitoring = True
        portfolio_monitor._price_baselines = {'AAPL': Decimal('150.00'), 'GOOGL': Decimal('2500.00')}
        portfolio_monitor.add_alert_callback(Mock())
        portfolio_monitor._last_portfolio_snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('100000'),
            buying_power=Decimal('50000'),
            day_pnl=Decimal('1000'),
            total_pnl=Decimal('5000'),
            positions=[]
        )
        
        status = portfolio_monitor.get_monitoring_status()
        
        assert status['is_monitoring'] is True
        assert len(status['monitored_symbols']) == 2
        assert 'AAPL' in status['monitored_symbols']
        assert 'GOOGL' in status['monitored_symbols']
        assert status['alert_callbacks_count'] == 1
        assert status['last_portfolio_value'] == 100000.0
        assert 'thresholds' in status


class TestMonitoringThresholds:
    """Test cases for MonitoringThresholds class."""
    
    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = MonitoringThresholds()
        
        assert thresholds.position_change_percent == 5.0
        assert thresholds.portfolio_change_percent == 2.0
        assert thresholds.daily_pnl_threshold == Decimal('5000')
        assert thresholds.drawdown_threshold == 10.0
        assert thresholds.volatility_threshold == 0.3
        assert thresholds.price_movement_percent == 10.0
        assert thresholds.monitoring_interval == 5
    
    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = MonitoringThresholds(
            position_change_percent=3.0,
            portfolio_change_percent=1.5,
            daily_pnl_threshold=Decimal('2000'),
            monitoring_interval=10
        )
        
        assert thresholds.position_change_percent == 3.0
        assert thresholds.portfolio_change_percent == 1.5
        assert thresholds.daily_pnl_threshold == Decimal('2000')
        assert thresholds.monitoring_interval == 10


class TestMonitoringAlert:
    """Test cases for MonitoringAlert class."""
    
    def test_alert_creation(self):
        """Test monitoring alert creation."""
        alert = MonitoringAlert(
            alert_id='test_alert_001',
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            alert_type='price_movement',
            symbol='AAPL',
            message='AAPL price moved 5%',
            data={'change_percent': 5.0}
        )
        
        assert alert.alert_id == 'test_alert_001'
        assert alert.severity == AlertSeverity.WARNING
        assert alert.alert_type == 'price_movement'
        assert alert.symbol == 'AAPL'
        assert alert.message == 'AAPL price moved 5%'
        assert alert.data['change_percent'] == 5.0
    
    def test_alert_without_symbol(self):
        """Test alert creation without symbol."""
        alert = MonitoringAlert(
            alert_id='test_alert_002',
            timestamp=datetime.now(),
            severity=AlertSeverity.CRITICAL,
            alert_type='portfolio_drawdown',
            symbol=None,
            message='Portfolio drawdown exceeded limit'
        )
        
        assert alert.symbol is None
        assert alert.alert_type == 'portfolio_drawdown'
        assert alert.severity == AlertSeverity.CRITICAL


class TestAlertSeverity:
    """Test cases for AlertSeverity enum."""
    
    def test_severity_values(self):
        """Test alert severity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"