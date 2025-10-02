"""
Integration tests for portfolio monitoring system.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from financial_portfolio_automation.monitoring.portfolio_monitor import (
    PortfolioMonitor, MonitoringThresholds, AlertSeverity
)
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.analysis.technical_analysis import TechnicalAnalysis
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.models.core import Position, Quote, PortfolioSnapshot


@pytest.fixture
def integration_data_cache():
    """Create a data cache with test data for integration testing."""
    cache = DataCache(default_ttl=300)
    
    # Add test quote data
    test_quotes = {
        'AAPL': {
            'symbol': 'AAPL',
            'timestamp': datetime.now(),
            'bid': Decimal('150.00'),
            'ask': Decimal('150.05'),
            'bid_size': 100,
            'ask_size': 100
        },
        'GOOGL': {
            'symbol': 'GOOGL',
            'timestamp': datetime.now(),
            'bid': Decimal('2500.00'),
            'ask': Decimal('2500.10'),
            'bid_size': 50,
            'ask_size': 50
        }
    }
    
    for symbol, quote_data in test_quotes.items():
        cache.set(f"quote:{symbol}", quote_data)
    
    return cache


@pytest.fixture
def integration_portfolio_analyzer():
    """Create a portfolio analyzer for integration testing."""
    analyzer = PortfolioAnalyzer()
    return analyzer


@pytest.fixture
def integration_technical_analysis():
    """Create a technical analysis engine for integration testing."""
    return TechnicalAnalysis()


@pytest.fixture
def integration_portfolio_monitor(integration_portfolio_analyzer, 
                                integration_technical_analysis, 
                                integration_data_cache):
    """Create a portfolio monitor for integration testing."""
    thresholds = MonitoringThresholds(
        position_change_percent=3.0,
        portfolio_change_percent=1.5,
        volatility_threshold=0.25,
        monitoring_interval=0.5  # Fast monitoring for tests
    )
    
    return PortfolioMonitor(
        portfolio_analyzer=integration_portfolio_analyzer,
        technical_analysis=integration_technical_analysis,
        data_cache=integration_data_cache,
        thresholds=thresholds
    )


class TestPortfolioMonitoringIntegration:
    """Integration tests for portfolio monitoring system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(self, integration_portfolio_monitor):
        """Test complete monitoring workflow from start to alert generation."""
        monitor = integration_portfolio_monitor
        
        # Set up test positions
        test_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            ),
            Position(
                symbol='GOOGL',
                quantity=10,
                market_value=Decimal('25000'),
                cost_basis=Decimal('24000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('200')
            )
        ]
        
        # Mock position retrieval
        monitor._get_current_positions = AsyncMock(return_value=test_positions)
        monitor._get_historical_prices = AsyncMock(return_value=[150.0] * 20)
        
        # Set up alert collection
        received_alerts = []
        
        def alert_collector(alert):
            received_alerts.append(alert)
        
        monitor.add_alert_callback(alert_collector)
        
        # Start monitoring
        symbols = ['AAPL', 'GOOGL']
        await monitor.start_monitoring(symbols)
        
        # Let monitoring run for a short time
        await asyncio.sleep(1.0)
        
        # Simulate price changes by updating cache
        monitor.data_cache.set('quote:AAPL', {
            'symbol': 'AAPL',
            'timestamp': datetime.now(),
            'bid': Decimal('165.00'),  # 10% increase
            'ask': Decimal('165.05'),
            'bid_size': 100,
            'ask_size': 100
        })
        
        # Let monitoring detect the change
        await asyncio.sleep(1.0)
        
        # Stop monitoring
        await monitor.stop_monitoring()
        
        # Verify monitoring status
        status = monitor.get_monitoring_status()
        assert not status['is_monitoring']
        assert len(status['monitored_symbols']) == 2
        
        # Should have received some alerts during monitoring
        assert len(received_alerts) > 0
    
    @pytest.mark.asyncio
    async def test_real_time_price_movement_detection(self, integration_portfolio_monitor):
        """Test real-time price movement detection and alerting."""
        monitor = integration_portfolio_monitor
        
        # Mock position data
        monitor._get_current_positions = AsyncMock(return_value=[])
        monitor._get_historical_prices = AsyncMock(return_value=[150.0] * 20)
        
        # Set up alert collection
        price_alerts = []
        
        def price_alert_filter(alert):
            if alert.alert_type == 'price_movement':
                price_alerts.append(alert)
        
        monitor.add_alert_callback(price_alert_filter)
        
        # Initialize monitoring
        await monitor._initialize_baselines(['AAPL'])
        
        # Simulate significant price movement
        monitor.data_cache.set('quote:AAPL', {
            'symbol': 'AAPL',
            'timestamp': datetime.now(),
            'bid': Decimal('135.00'),  # 10% decrease
            'ask': Decimal('135.05'),
            'bid_size': 100,
            'ask_size': 100
        })
        
        # Trigger price monitoring
        await monitor._monitor_price_movement('AAPL')
        
        # Verify price movement alert was generated
        assert len(price_alerts) == 1
        alert = price_alerts[0]
        assert alert.alert_type == 'price_movement'
        assert alert.symbol == 'AAPL'
        assert alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
        assert 'change_percent' in alert.data
    
    @pytest.mark.asyncio
    async def test_portfolio_value_monitoring(self, integration_portfolio_monitor):
        """Test portfolio value change monitoring."""
        monitor = integration_portfolio_monitor
        
        # Set up initial portfolio state
        initial_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            )
        ]
        
        # Set up changed portfolio state
        changed_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('16000'),  # Significant increase
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('2000'),
                day_pnl=Decimal('1500')
            )
        ]
        
        # Mock position retrieval to return different values over time
        position_calls = [initial_positions, changed_positions]
        monitor._get_current_positions = AsyncMock(side_effect=position_calls)
        
        # Set up alert collection
        portfolio_alerts = []
        
        def portfolio_alert_filter(alert):
            if alert.alert_type in ['portfolio_value_change', 'position_value_change']:
                portfolio_alerts.append(alert)
        
        monitor.add_alert_callback(portfolio_alert_filter)
        
        # Initialize with first set of positions
        await monitor._initialize_baselines(['AAPL'])
        
        # Monitor portfolio changes (will use second set of positions)
        await monitor._monitor_portfolio_changes()
        await monitor._monitor_position_changes()
        
        # Verify alerts were generated
        assert len(portfolio_alerts) > 0
        
        # Check for position change alert
        position_alerts = [a for a in portfolio_alerts if a.alert_type == 'position_value_change']
        assert len(position_alerts) > 0
        
        position_alert = position_alerts[0]
        assert position_alert.symbol == 'AAPL'
        assert 'change_percent' in position_alert.data
    
    @pytest.mark.asyncio
    async def test_volatility_monitoring_integration(self, integration_portfolio_monitor):
        """Test volatility monitoring with technical analysis integration."""
        monitor = integration_portfolio_monitor
        
        # Mock historical price data with high volatility
        volatile_prices = [
            150.0, 155.0, 148.0, 160.0, 145.0, 165.0, 140.0, 170.0, 135.0, 175.0,
            130.0, 180.0, 125.0, 185.0, 120.0, 190.0, 115.0, 195.0, 110.0, 200.0
        ]
        monitor._get_historical_prices = AsyncMock(return_value=volatile_prices)
        
        # Set up alert collection
        volatility_alerts = []
        
        def volatility_alert_filter(alert):
            if alert.alert_type == 'high_volatility':
                volatility_alerts.append(alert)
        
        monitor.add_alert_callback(volatility_alert_filter)
        
        # Monitor volatility
        await monitor._monitor_volatility('AAPL')
        
        # Verify volatility alert was generated (high volatility data should trigger alert)
        assert len(volatility_alerts) == 1
        alert = volatility_alerts[0]
        assert alert.alert_type == 'high_volatility'
        assert alert.symbol == 'AAPL'
        assert 'volatility' in alert.data
        assert 'threshold' in alert.data
    
    @pytest.mark.asyncio
    async def test_multiple_symbol_monitoring(self, integration_portfolio_monitor):
        """Test monitoring multiple symbols simultaneously."""
        monitor = integration_portfolio_monitor
        
        # Set up positions for multiple symbols
        test_positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            ),
            Position(
                symbol='GOOGL',
                quantity=10,
                market_value=Decimal('25000'),
                cost_basis=Decimal('24000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('200')
            )
        ]
        
        monitor._get_current_positions = AsyncMock(return_value=test_positions)
        monitor._get_historical_prices = AsyncMock(return_value=[150.0] * 20)
        
        # Set up alert collection
        all_alerts = []
        monitor.add_alert_callback(lambda alert: all_alerts.append(alert))
        
        # Initialize monitoring for multiple symbols
        symbols = ['AAPL', 'GOOGL']
        await monitor._initialize_baselines(symbols)
        
        # Verify baselines were set for both symbols
        status = monitor.get_monitoring_status()
        assert len(status['monitored_symbols']) == 2
        assert 'AAPL' in status['monitored_symbols']
        assert 'GOOGL' in status['monitored_symbols']
        
        # Simulate price changes for both symbols
        monitor.data_cache.set('quote:AAPL', {
            'symbol': 'AAPL',
            'timestamp': datetime.now(),
            'bid': Decimal('165.00'),  # 10% increase
            'ask': Decimal('165.05'),
            'bid_size': 100,
            'ask_size': 100
        })
        
        monitor.data_cache.set('quote:GOOGL', {
            'symbol': 'GOOGL',
            'timestamp': datetime.now(),
            'bid': Decimal('2250.00'),  # 10% decrease
            'ask': Decimal('2250.10'),
            'bid_size': 50,
            'ask_size': 50
        })
        
        # Monitor market conditions for both symbols
        await monitor._monitor_market_conditions(symbols)
        
        # Verify alerts were generated for both symbols
        symbol_alerts = {}
        for alert in all_alerts:
            if alert.symbol:
                if alert.symbol not in symbol_alerts:
                    symbol_alerts[alert.symbol] = []
                symbol_alerts[alert.symbol].append(alert)
        
        # Should have alerts for both symbols
        assert len(symbol_alerts) == 2
        assert 'AAPL' in symbol_alerts
        assert 'GOOGL' in symbol_alerts
    
    @pytest.mark.asyncio
    async def test_monitoring_error_handling(self, integration_portfolio_monitor):
        """Test error handling during monitoring operations."""
        monitor = integration_portfolio_monitor
        
        # Set up error conditions
        monitor._get_current_positions = AsyncMock(side_effect=Exception("Position fetch error"))
        
        # Set up alert collection
        error_logged = []
        
        # Patch logger to capture errors
        with patch.object(monitor.logger, 'error') as mock_logger:
            # Attempt to monitor portfolio changes (should handle error gracefully)
            await monitor._monitor_portfolio_changes()
            
            # Verify error was logged
            mock_logger.assert_called()
            assert "Error monitoring portfolio changes" in str(mock_logger.call_args)
    
    @pytest.mark.asyncio
    async def test_alert_callback_resilience(self, integration_portfolio_monitor):
        """Test that monitoring continues even if alert callbacks fail."""
        monitor = integration_portfolio_monitor
        
        # Set up callbacks - one that works, one that fails
        working_alerts = []
        
        def working_callback(alert):
            working_alerts.append(alert)
        
        def failing_callback(alert):
            raise Exception("Callback failure")
        
        monitor.add_alert_callback(working_callback)
        monitor.add_alert_callback(failing_callback)
        
        # Generate an alert
        await monitor._generate_alert(
            alert_type='test_alert',
            severity=AlertSeverity.INFO,
            message='Test message'
        )
        
        # Working callback should still receive the alert
        assert len(working_alerts) == 1
        assert working_alerts[0].alert_type == 'test_alert'
    
    @pytest.mark.asyncio
    async def test_monitoring_performance(self, integration_portfolio_monitor):
        """Test monitoring performance with multiple rapid updates."""
        monitor = integration_portfolio_monitor
        
        # Set up rapid position updates
        positions = [
            Position(
                symbol='AAPL',
                quantity=100,
                market_value=Decimal('15000'),
                cost_basis=Decimal('14000'),
                unrealized_pnl=Decimal('1000'),
                day_pnl=Decimal('500')
            )
        ]
        
        monitor._get_current_positions = AsyncMock(return_value=positions)
        monitor._get_historical_prices = AsyncMock(return_value=[150.0] * 20)
        
        # Set up alert collection
        performance_alerts = []
        monitor.add_alert_callback(lambda alert: performance_alerts.append(alert))
        
        # Initialize monitoring
        await monitor._initialize_baselines(['AAPL'])
        
        # Perform multiple rapid monitoring cycles
        start_time = datetime.now()
        
        for i in range(10):
            await monitor._perform_monitoring_cycle(['AAPL'])
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Monitoring should complete quickly (under 1 second for 10 cycles)
        assert execution_time < 1.0
        
        # Verify monitoring completed without errors
        status = monitor.get_monitoring_status()
        assert len(status['monitored_symbols']) == 1