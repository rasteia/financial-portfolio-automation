"""
Unit tests for PerformanceReport.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from financial_portfolio_automation.reporting.performance_report import (
    PerformanceReport, PerformanceMetrics, PeriodPerformance, AssetAllocation
)
from financial_portfolio_automation.models.core import PortfolioSnapshot, Position
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer


class TestPerformanceReport:
    """Test cases for PerformanceReport class."""
    
    @pytest.fixture
    def mock_data_store(self):
        """Mock data store."""
        return Mock(spec=DataStore)
    
    @pytest.fixture
    def mock_portfolio_analyzer(self):
        """Mock portfolio analyzer."""
        return Mock(spec=PortfolioAnalyzer)
    
    @pytest.fixture
    def performance_report(self, mock_data_store, mock_portfolio_analyzer):
        """Create PerformanceReport instance."""
        return PerformanceReport(
            data_store=mock_data_store,
            portfolio_analyzer=mock_portfolio_analyzer
        )
    
    @pytest.fixture
    def sample_positions(self):
        """Sample positions."""
        return [
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
    
    @pytest.fixture
    def sample_snapshots(self, sample_positions):
        """Sample portfolio snapshots."""
        base_date = date(2024, 1, 1)
        snapshots = []
        
        for i in range(10):
            snapshot_date = base_date + timedelta(days=i)
            total_value = Decimal('20000') + Decimal(str(i * 100))  # Growing portfolio
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.combine(snapshot_date, datetime.min.time()),
                total_value=total_value,
                buying_power=Decimal('5000'),
                day_pnl=Decimal('100'),
                total_pnl=Decimal(str(i * 100)),
                positions=sample_positions
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    def test_init(self, mock_data_store, mock_portfolio_analyzer):
        """Test PerformanceReport initialization."""
        report = PerformanceReport(
            data_store=mock_data_store,
            portfolio_analyzer=mock_portfolio_analyzer
        )
        
        assert report.data_store == mock_data_store
        assert report.portfolio_analyzer == mock_portfolio_analyzer
    
    def test_generate_data_success(self, performance_report, sample_snapshots):
        """Test successful performance report data generation."""
        # Mock data store
        performance_report.data_store.get_portfolio_snapshots.return_value = sample_snapshots
        
        # Generate report data
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 10)
        
        report_data = performance_report.generate_data(
            start_date=start_date,
            end_date=end_date,
            benchmark_symbol='SPY'
        )
        
        # Verify structure
        assert 'report_metadata' in report_data
        assert 'portfolio_summary' in report_data
        assert 'performance_metrics' in report_data
        assert 'period_performance' in report_data
        assert 'asset_allocation' in report_data
        assert 'drawdown_analysis' in report_data
        assert 'chart_data' in report_data
        
        # Verify metadata
        metadata = report_data['report_metadata']
        assert metadata['start_date'] == start_date
        assert metadata['end_date'] == end_date
        assert metadata['benchmark_symbol'] == 'SPY'
        
        # Verify portfolio summary
        summary = report_data['portfolio_summary']
        assert summary['start_value'] == sample_snapshots[0].total_value
        assert summary['end_value'] == sample_snapshots[-1].total_value
        assert 'total_return' in summary
        assert 'total_return_pct' in summary
    
    def test_generate_data_no_snapshots(self, performance_report):
        """Test report generation with no portfolio snapshots."""
        # Mock empty snapshots
        performance_report.data_store.get_portfolio_snapshots.return_value = []
        
        with pytest.raises(ValueError, match="No portfolio data found"):
            performance_report.generate_data(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10)
            )
    
    def test_calculate_performance_metrics(self, performance_report, sample_snapshots):
        """Test performance metrics calculation."""
        metrics = performance_report._calculate_performance_metrics(sample_snapshots)
        
        assert isinstance(metrics, PerformanceMetrics)
        assert metrics.total_return > 0  # Portfolio grew
        assert metrics.annualized_return is not None
        assert metrics.volatility >= 0
        assert metrics.max_drawdown >= 0
        assert metrics.sharpe_ratio is not None
        assert metrics.calmar_ratio is not None
        assert metrics.sortino_ratio is not None
    
    def test_calculate_performance_metrics_insufficient_data(self, performance_report):
        """Test performance metrics with insufficient data."""
        single_snapshot = [
            PortfolioSnapshot(
                timestamp=datetime(2024, 1, 1),
                total_value=Decimal('20000'),
                buying_power=Decimal('5000'),
                day_pnl=Decimal('0'),
                total_pnl=Decimal('0'),
                positions=[]
            )
        ]
        
        with pytest.raises(ValueError, match="Insufficient data"):
            performance_report._calculate_performance_metrics(single_snapshot)
    
    def test_calculate_period_performance(self, performance_report, sample_snapshots):
        """Test period performance calculation."""
        periods = performance_report._calculate_period_performance(sample_snapshots)
        
        assert isinstance(periods, list)
        assert len(periods) > 0
        
        for period in periods:
            assert isinstance(period, PeriodPerformance)
            assert period.period_name in ['1 Month', '3 Months', '6 Months', '1 Year', 'YTD']
            assert period.start_date <= period.end_date
            assert isinstance(period.return_pct, Decimal)
    
    def test_calculate_asset_allocation(self, performance_report, sample_snapshots):
        """Test asset allocation calculation."""
        latest_snapshot = sample_snapshots[-1]
        allocation = performance_report._calculate_asset_allocation(latest_snapshot)
        
        assert isinstance(allocation, list)
        assert len(allocation) == len(latest_snapshot.positions)
        
        for asset in allocation:
            assert isinstance(asset, AssetAllocation)
            assert asset.symbol in ['AAPL', 'GOOGL']
            assert asset.weight > 0
            assert asset.value > 0
        
        # Verify weights sum to approximately 100%
        total_weight = sum(asset.weight for asset in allocation)
        assert abs(total_weight - 100) < 1  # Allow for rounding
    
    def test_calculate_asset_allocation_with_filter(self, performance_report, sample_snapshots):
        """Test asset allocation with symbol filter."""
        latest_snapshot = sample_snapshots[-1]
        allocation = performance_report._calculate_asset_allocation(
            latest_snapshot, 
            symbols_filter=['AAPL']
        )
        
        assert len(allocation) == 1
        assert allocation[0].symbol == 'AAPL'
    
    def test_calculate_drawdown_analysis(self, performance_report, sample_snapshots):
        """Test drawdown analysis calculation."""
        drawdown_data = performance_report._calculate_drawdown_analysis(sample_snapshots)
        
        assert 'max_drawdown_pct' in drawdown_data
        assert 'max_drawdown_date' in drawdown_data
        assert 'current_drawdown_pct' in drawdown_data
        assert 'drawdown_periods' in drawdown_data
        assert 'avg_drawdown_duration' in drawdown_data
        
        assert drawdown_data['max_drawdown_pct'] >= 0
        assert drawdown_data['current_drawdown_pct'] >= 0
        assert isinstance(drawdown_data['drawdown_periods'], list)
    
    def test_prepare_chart_data(self, performance_report, sample_snapshots):
        """Test chart data preparation."""
        chart_data = performance_report._prepare_chart_data(sample_snapshots)
        
        assert 'portfolio_value' in chart_data
        assert 'daily_returns' in chart_data
        
        portfolio_data = chart_data['portfolio_value']
        assert 'dates' in portfolio_data
        assert 'values' in portfolio_data
        assert 'normalized_values' in portfolio_data
        
        assert len(portfolio_data['dates']) == len(sample_snapshots)
        assert len(portfolio_data['values']) == len(sample_snapshots)
        assert len(portfolio_data['normalized_values']) == len(sample_snapshots)
        
        # First normalized value should be 100
        assert portfolio_data['normalized_values'][0] == 100
    
    def test_prepare_chart_data_with_benchmark(self, performance_report, sample_snapshots):
        """Test chart data preparation with benchmark."""
        # Mock benchmark data
        performance_report._get_benchmark_data = Mock(return_value=[100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        
        chart_data = performance_report._prepare_chart_data(
            sample_snapshots, 
            benchmark_symbol='SPY'
        )
        
        assert 'benchmark' in chart_data
        benchmark_data = chart_data['benchmark']
        assert 'dates' in benchmark_data
        assert 'normalized_values' in benchmark_data
    
    def test_calculate_returns(self, performance_report, sample_snapshots):
        """Test daily returns calculation."""
        returns = performance_report._calculate_returns(sample_snapshots)
        
        assert len(returns) == len(sample_snapshots) - 1
        
        # All returns should be positive for our growing portfolio
        for ret in returns:
            assert ret > 0
    
    def test_annualize_return(self, performance_report):
        """Test return annualization."""
        total_return = Decimal('1000')
        initial_value = Decimal('10000')
        days = 365
        
        annualized = performance_report._annualize_return(
            total_return, initial_value, days
        )
        
        assert isinstance(annualized, Decimal)
        assert annualized > 0  # Positive return
    
    def test_annualize_return_zero_days(self, performance_report):
        """Test return annualization with zero days."""
        total_return = Decimal('1000')
        initial_value = Decimal('10000')
        days = 0
        
        annualized = performance_report._annualize_return(
            total_return, initial_value, days
        )
        
        assert annualized == Decimal('0')
    
    def test_calculate_volatility(self, performance_report):
        """Test volatility calculation."""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        
        volatility = performance_report._calculate_volatility(returns)
        
        assert isinstance(volatility, Decimal)
        assert volatility > 0
    
    def test_calculate_volatility_insufficient_data(self, performance_report):
        """Test volatility calculation with insufficient data."""
        returns = [0.01]  # Only one return
        
        volatility = performance_report._calculate_volatility(returns)
        
        assert volatility == Decimal('0')
    
    def test_calculate_max_drawdown(self, performance_report, sample_snapshots):
        """Test maximum drawdown calculation."""
        max_dd = performance_report._calculate_max_drawdown(sample_snapshots)
        
        assert isinstance(max_dd, Decimal)
        assert max_dd >= 0
    
    def test_calculate_sharpe_ratio(self, performance_report):
        """Test Sharpe ratio calculation."""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015]
        volatility = Decimal('15.5')
        
        sharpe = performance_report._calculate_sharpe_ratio(returns, volatility)
        
        assert isinstance(sharpe, Decimal)
    
    def test_calculate_sharpe_ratio_zero_volatility(self, performance_report):
        """Test Sharpe ratio with zero volatility."""
        returns = [0.01, 0.01, 0.01]  # Constant returns
        volatility = Decimal('0')
        
        sharpe = performance_report._calculate_sharpe_ratio(returns, volatility)
        
        assert sharpe == Decimal('0')
    
    def test_calculate_calmar_ratio(self, performance_report):
        """Test Calmar ratio calculation."""
        annualized_return = Decimal('12.5')
        max_drawdown = Decimal('5.0')
        
        calmar = performance_report._calculate_calmar_ratio(
            annualized_return, max_drawdown
        )
        
        assert isinstance(calmar, Decimal)
        assert calmar > 0
    
    def test_calculate_calmar_ratio_zero_drawdown(self, performance_report):
        """Test Calmar ratio with zero drawdown."""
        annualized_return = Decimal('12.5')
        max_drawdown = Decimal('0')
        
        calmar = performance_report._calculate_calmar_ratio(
            annualized_return, max_drawdown
        )
        
        assert calmar == Decimal('0')
    
    def test_calculate_sortino_ratio(self, performance_report):
        """Test Sortino ratio calculation."""
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008]
        
        sortino = performance_report._calculate_sortino_ratio(returns)
        
        assert isinstance(sortino, Decimal)
    
    def test_calculate_sortino_ratio_no_downside(self, performance_report):
        """Test Sortino ratio with no downside returns."""
        returns = [0.01, 0.005, 0.02, 0.01, 0.015]  # All positive
        
        sortino = performance_report._calculate_sortino_ratio(returns)
        
        assert sortino == Decimal('0')
    
    def test_get_symbol_sector(self, performance_report):
        """Test symbol sector lookup."""
        sector = performance_report._get_symbol_sector('AAPL')
        # Currently returns None, but test the interface
        assert sector is None
    
    def test_get_asset_class(self, performance_report):
        """Test asset class lookup."""
        asset_class = performance_report._get_asset_class('AAPL')
        assert asset_class == "Equity"
    
    def test_get_benchmark_data_not_implemented(self, performance_report):
        """Test benchmark data retrieval (not implemented)."""
        benchmark_data = performance_report._get_benchmark_data(
            'SPY', date(2024, 1, 1), date(2024, 1, 10)
        )
        assert benchmark_data is None