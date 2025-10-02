"""
Unit tests for AnalyticsService.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from financial_portfolio_automation.analytics.analytics_service import (
    AnalyticsService, AnalyticsConfig, DashboardMetrics
)
from financial_portfolio_automation.models.core import PortfolioSnapshot, Position
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.monitoring.portfolio_monitor import PortfolioMonitor


class TestAnalyticsService:
    """Test cases for AnalyticsService class."""
    
    @pytest.fixture
    def mock_data_store(self):
        """Mock data store."""
        mock = Mock(spec=DataStore)
        mock.get_portfolio_snapshots = Mock(return_value=[])
        mock.get_latest_positions = Mock(return_value=[])
        mock.get_quotes = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_data_cache(self):
        """Mock data cache."""
        return Mock(spec=DataCache)
    
    @pytest.fixture
    def mock_portfolio_analyzer(self):
        """Mock portfolio analyzer."""
        mock = Mock(spec=PortfolioAnalyzer)
        mock.calculate_portfolio_value = Mock(return_value=Decimal('100000'))
        mock.calculate_day_pnl = Mock(return_value=Decimal('1000'))
        mock.calculate_total_pnl = Mock(return_value=Decimal('5000'))
        mock.calculate_performance_metrics = Mock(return_value={})
        mock.calculate_risk_metrics = Mock(return_value={})
        return mock
    
    @pytest.fixture
    def mock_portfolio_monitor(self):
        """Mock portfolio monitor."""
        return Mock(spec=PortfolioMonitor)
    
    @pytest.fixture
    def analytics_config(self):
        """Analytics configuration."""
        return AnalyticsConfig(
            refresh_interval_seconds=10,
            cache_ttl_seconds=60,
            enable_real_time=True
        )
    
    @pytest.fixture
    def analytics_service(self, mock_data_store, mock_data_cache, 
                         mock_portfolio_analyzer, mock_portfolio_monitor, 
                         analytics_config):
        """Create AnalyticsService instance."""
        with patch('financial_portfolio_automation.analytics.analytics_service.TrendAnalyzer') as mock_trend_analyzer_class:
            with patch('financial_portfolio_automation.analytics.analytics_service.MetricsCalculator') as mock_metrics_calculator_class:
                with patch('financial_portfolio_automation.analytics.analytics_service.DataAggregator') as mock_data_aggregator_class:
                    with patch('financial_portfolio_automation.analytics.analytics_service.DashboardSerializer') as mock_dashboard_serializer_class:
                        service = AnalyticsService(
                            data_store=mock_data_store,
                            data_cache=mock_data_cache,
                            portfolio_analyzer=mock_portfolio_analyzer,
                            portfolio_monitor=mock_portfolio_monitor,
                            config=analytics_config
                        )
                        # Configure the mocked components
                        service.trend_analyzer.analyze_trends = Mock(return_value={})
                        service.metrics_calculator.calculate_metrics = Mock(return_value={})
                        service.data_aggregator.aggregate_data = Mock(return_value={})
                        service.dashboard_serializer.serialize = Mock(return_value={})
                        return service
    
    @pytest.fixture
    def sample_snapshot(self):
        """Sample portfolio snapshot."""
        positions = [
            Position(
                symbol='AAPL',
                quantity=Decimal('100'),
                market_value=Decimal('15000'),
                cost_basis=Decimal('12000'),
                unrealized_pnl=Decimal('3000'),
                day_pnl=Decimal('150')
            ),
            Position(
                symbol='GOOGL',
                quantity=Decimal('50'),
                market_value=Decimal('8000'),
                cost_basis=Decimal('7500'),
                unrealized_pnl=Decimal('500'),
                day_pnl=Decimal('80')
            )
        ]
        
        return PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=Decimal('25000'),
            buying_power=Decimal('2000'),
            day_pnl=Decimal('230'),
            total_pnl=Decimal('3500'),
            positions=positions
        )
    
    def test_init(self, mock_data_store, mock_data_cache, mock_portfolio_analyzer):
        """Test AnalyticsService initialization."""
        service = AnalyticsService(
            data_store=mock_data_store,
            data_cache=mock_data_cache,
            portfolio_analyzer=mock_portfolio_analyzer
        )
        
        assert service.data_store == mock_data_store
        assert service.data_cache == mock_data_cache
        assert service.portfolio_analyzer == mock_portfolio_analyzer
        assert service.config is not None
        assert service.metrics_calculator is not None
        assert service.trend_analyzer is not None
        assert service.data_aggregator is not None
        assert service.dashboard_serializer is not None
    
    def test_init_with_config(self, mock_data_store, mock_data_cache, 
                             mock_portfolio_analyzer, analytics_config):
        """Test AnalyticsService initialization with custom config."""
        service = AnalyticsService(
            data_store=mock_data_store,
            data_cache=mock_data_cache,
            portfolio_analyzer=mock_portfolio_analyzer,
            config=analytics_config
        )
        
        assert service.config == analytics_config
        assert service.config.refresh_interval_seconds == 10
    
    def test_get_dashboard_data_from_cache(self, analytics_service):
        """Test getting dashboard data from cache."""
        # Mock cache hit
        cached_data = {'test': 'cached_data'}
        analytics_service.data_cache.get.return_value = cached_data
        analytics_service._is_cache_valid = Mock(return_value=True)
        
        result = analytics_service.get_dashboard_data()
        
        assert result == cached_data
        analytics_service.data_cache.get.assert_called_once_with('dashboard_data')
    
    def test_get_dashboard_data_fresh(self, analytics_service, sample_snapshot):
        """Test getting fresh dashboard data."""
        # Mock cache miss
        analytics_service.data_cache.get.return_value = None
        analytics_service._is_cache_valid = Mock(return_value=False)
        
        # Mock data retrieval
        analytics_service._get_current_snapshot = Mock(return_value=sample_snapshot)
        analytics_service.metrics_calculator.calculate_real_time_metrics = Mock(
            return_value={'test': 'metrics'}
        )
        analytics_service.trend_analyzer.analyze_trends = Mock(
            return_value={'test': 'trends'}
        )
        
        # Mock other methods
        analytics_service.get_performance_summary = Mock(return_value={'test': 'performance'})
        analytics_service.get_risk_analysis = Mock(return_value={'test': 'risk'})
        analytics_service.get_market_comparison = Mock(return_value={'test': 'market'})
        
        # Mock serializer
        serialized_data = {'serialized': 'data'}
        analytics_service.dashboard_serializer.serialize_dashboard_data = Mock(
            return_value=serialized_data
        )
        
        result = analytics_service.get_dashboard_data()
        
        assert result == serialized_data
        analytics_service.data_cache.set.assert_called_once()
    
    def test_get_real_time_metrics(self, analytics_service, sample_snapshot):
        """Test getting real-time metrics."""
        # Mock current snapshot
        analytics_service._get_current_snapshot = Mock(return_value=sample_snapshot)
        
        # Mock metrics calculation
        mock_metrics = {'portfolio_value': 25000.0}
        analytics_service.metrics_calculator.calculate_real_time_metrics = Mock(
            return_value=mock_metrics
        )
        analytics_service.metrics_calculator.calculate_risk_metrics = Mock(
            return_value={'risk': 'metrics'}
        )
        
        # Mock helper methods
        analytics_service._get_top_movers = Mock(return_value=([], []))
        analytics_service._get_sector_allocation = Mock(return_value={})
        
        result = analytics_service.get_real_time_metrics()
        
        assert isinstance(result, DashboardMetrics)
        assert result.portfolio_value == sample_snapshot.total_value
        assert result.day_pnl == sample_snapshot.day_pnl
    
    def test_get_real_time_metrics_no_snapshot(self, analytics_service):
        """Test getting real-time metrics with no current snapshot."""
        analytics_service._get_current_snapshot = Mock(return_value=None)
        
        with pytest.raises(ValueError, match="No current portfolio data available"):
            analytics_service.get_real_time_metrics()
    
    def test_get_historical_trends(self, analytics_service):
        """Test getting historical trends."""
        # Mock snapshots
        mock_snapshots = [Mock(), Mock(), Mock()]
        analytics_service.data_store.get_portfolio_snapshots.return_value = mock_snapshots
        
        # Mock trend analysis
        mock_trends = {'trend': 'data'}
        analytics_service.trend_analyzer.analyze_trends.return_value = mock_trends
        
        result = analytics_service.get_historical_trends(days=30)
        
        assert result == mock_trends
        analytics_service.data_store.get_portfolio_snapshots.assert_called_once()
        analytics_service.trend_analyzer.analyze_trends.assert_called_once_with(mock_snapshots)
    
    def test_get_historical_trends_no_data(self, analytics_service):
        """Test getting historical trends with no data."""
        analytics_service.data_store.get_portfolio_snapshots.return_value = []
        
        result = analytics_service.get_historical_trends()
        
        assert result == {}
    
    def test_get_performance_summary(self, analytics_service):
        """Test getting performance summary."""
        # Mock snapshots for different periods
        mock_snapshots = [Mock(), Mock()]
        analytics_service.data_store.get_portfolio_snapshots.return_value = mock_snapshots
        
        # Mock performance calculation
        mock_performance = {'return_pct': 5.0}
        analytics_service.metrics_calculator.calculate_period_performance.return_value = mock_performance
        
        result = analytics_service.get_performance_summary([1, 7])
        
        assert '1d' in result
        assert '7d' in result
        assert result['1d'] == mock_performance
    
    def test_get_risk_analysis(self, analytics_service):
        """Test getting risk analysis."""
        # Mock snapshots
        mock_snapshots = [Mock(), Mock()]
        analytics_service.data_store.get_portfolio_snapshots.return_value = mock_snapshots
        
        # Mock risk calculation
        mock_risk = {'volatility': 15.5}
        analytics_service.metrics_calculator.calculate_comprehensive_risk_metrics.return_value = mock_risk
        
        result = analytics_service.get_risk_analysis()
        
        assert result == mock_risk
    
    def test_get_risk_analysis_no_data(self, analytics_service):
        """Test getting risk analysis with no data."""
        analytics_service.data_store.get_portfolio_snapshots.return_value = []
        
        result = analytics_service.get_risk_analysis()
        
        assert result == {}
    
    def test_get_market_comparison(self, analytics_service):
        """Test getting market comparison."""
        # Mock snapshots
        mock_snapshots = [
            Mock(total_value=Decimal('20000')),
            Mock(total_value=Decimal('21000'))
        ]
        analytics_service.data_store.get_portfolio_snapshots.return_value = mock_snapshots
        
        # Mock benchmark return
        analytics_service._get_benchmark_return = Mock(return_value=Decimal('2.0'))
        
        result = analytics_service.get_market_comparison()
        
        assert 'portfolio_return' in result
        assert 'benchmark_return' in result
        assert 'excess_return' in result
        assert result['benchmark_symbol'] == 'SPY'
    
    def test_get_aggregated_data(self, analytics_service):
        """Test getting aggregated data."""
        # Mock aggregator
        mock_aggregated = {'aggregated': 'data'}
        analytics_service.data_aggregator.aggregate_data.return_value = mock_aggregated
        
        result = analytics_service.get_aggregated_data('daily', 30)
        
        assert result == mock_aggregated
        analytics_service.data_aggregator.aggregate_data.assert_called_once()
    
    def test_start_real_time_updates(self, analytics_service):
        """Test starting real-time updates."""
        analytics_service.start_real_time_updates()
        
        assert analytics_service._update_thread is not None
        assert analytics_service._update_thread.is_alive()
        
        # Clean up
        analytics_service.stop_real_time_updates()
    
    def test_start_real_time_updates_disabled(self, analytics_service):
        """Test starting real-time updates when disabled."""
        analytics_service.config.enable_real_time = False
        
        analytics_service.start_real_time_updates()
        
        assert analytics_service._update_thread is None
    
    def test_stop_real_time_updates(self, analytics_service):
        """Test stopping real-time updates."""
        # Start first
        analytics_service.start_real_time_updates()
        
        # Then stop
        analytics_service.stop_real_time_updates()
        
        assert analytics_service._stop_event.is_set()
    
    def test_get_current_snapshot(self, analytics_service, sample_snapshot):
        """Test getting current snapshot."""
        analytics_service.data_store.get_portfolio_snapshots.return_value = [sample_snapshot]
        
        result = analytics_service._get_current_snapshot()
        
        assert result == sample_snapshot
    
    def test_get_current_snapshot_no_data(self, analytics_service):
        """Test getting current snapshot with no data."""
        analytics_service.data_store.get_portfolio_snapshots.return_value = []
        
        result = analytics_service._get_current_snapshot()
        
        assert result is None
    
    def test_get_top_movers(self, analytics_service, sample_snapshot):
        """Test getting top movers."""
        top_gainers, top_losers = analytics_service._get_top_movers(sample_snapshot)
        
        assert isinstance(top_gainers, list)
        assert isinstance(top_losers, list)
        
        # Should have positions with P&L data
        if top_gainers:
            assert 'symbol' in top_gainers[0]
            assert 'day_pnl' in top_gainers[0]
            assert 'day_pnl_pct' in top_gainers[0]
    
    def test_get_sector_allocation(self, analytics_service, sample_snapshot):
        """Test getting sector allocation."""
        result = analytics_service._get_sector_allocation(sample_snapshot)
        
        assert isinstance(result, dict)
        
        # Should have sector percentages
        total_percentage = sum(result.values())
        assert abs(total_percentage - 100) < 1  # Allow for rounding
    
    def test_get_position_sector(self, analytics_service):
        """Test getting position sector."""
        # Test known tech stock
        sector = analytics_service._get_position_sector('AAPL')
        assert sector == 'Technology'
        
        # Test unknown stock
        sector = analytics_service._get_position_sector('UNKNOWN')
        assert sector == 'Other'
    
    def test_calculate_pnl_percentage(self, analytics_service):
        """Test P&L percentage calculation."""
        pnl = Decimal('500')
        total_value = Decimal('10000')
        
        result = analytics_service._calculate_pnl_percentage(pnl, total_value)
        
        assert result == Decimal('5')  # 5%
    
    def test_calculate_pnl_percentage_zero_value(self, analytics_service):
        """Test P&L percentage with zero total value."""
        pnl = Decimal('500')
        total_value = Decimal('0')
        
        result = analytics_service._calculate_pnl_percentage(pnl, total_value)
        
        assert result == Decimal('0')
    
    def test_calculate_total_pnl_percentage(self, analytics_service, sample_snapshot):
        """Test total P&L percentage calculation."""
        result = analytics_service._calculate_total_pnl_percentage(sample_snapshot)
        
        # Should calculate based on initial value
        initial_value = sample_snapshot.total_value - sample_snapshot.total_pnl
        expected = sample_snapshot.total_pnl / initial_value * 100
        
        assert abs(result - expected) < Decimal('0.01')
    
    def test_calculate_return_percentage(self, analytics_service):
        """Test return percentage calculation."""
        start_value = Decimal('10000')
        end_value = Decimal('11000')
        
        result = analytics_service._calculate_return_percentage(start_value, end_value)
        
        assert result == Decimal('10')  # 10% return
    
    def test_get_benchmark_return(self, analytics_service):
        """Test getting benchmark return."""
        result = analytics_service._get_benchmark_return(
            'SPY', date(2024, 1, 1), date(2024, 1, 31)
        )
        
        # Should return mock value
        assert result == Decimal('2.5')
    
    def test_is_cache_valid_true(self, analytics_service):
        """Test cache validity check - valid."""
        # Mock cache timestamp
        recent_time = datetime.now() - timedelta(seconds=30)
        analytics_service.data_cache.get.return_value = recent_time
        
        result = analytics_service._is_cache_valid()
        
        assert result == True
    
    def test_is_cache_valid_false(self, analytics_service):
        """Test cache validity check - invalid."""
        # Mock old cache timestamp
        old_time = datetime.now() - timedelta(seconds=400)
        analytics_service.data_cache.get.return_value = old_time
        
        result = analytics_service._is_cache_valid()
        
        assert result == False
    
    def test_is_cache_valid_no_cache(self, analytics_service):
        """Test cache validity check - no cache."""
        analytics_service.data_cache.get.return_value = None
        
        result = analytics_service._is_cache_valid()
        
        assert result == False
    
    def test_is_metrics_cache_valid_true(self, analytics_service, sample_snapshot):
        """Test metrics cache validity - valid."""
        # Set up cached metrics
        analytics_service._cached_metrics = DashboardMetrics(
            timestamp=datetime.now(),
            portfolio_value=Decimal('25000'),
            day_pnl=Decimal('230'),
            day_pnl_pct=Decimal('0.92'),
            total_pnl=Decimal('3500'),
            total_pnl_pct=Decimal('16.28'),
            buying_power=Decimal('2000'),
            positions_count=2,
            top_gainers=[],
            top_losers=[],
            sector_allocation={},
            risk_metrics={}
        )
        analytics_service._cache_timestamp = datetime.now() - timedelta(seconds=5)
        
        result = analytics_service._is_metrics_cache_valid()
        
        assert result == True
    
    def test_is_metrics_cache_valid_false(self, analytics_service):
        """Test metrics cache validity - invalid."""
        analytics_service._cached_metrics = None
        analytics_service._cache_timestamp = None
        
        result = analytics_service._is_metrics_cache_valid()
        
        assert result == False