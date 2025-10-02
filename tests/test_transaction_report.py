"""
Unit tests for TransactionReport.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from financial_portfolio_automation.reporting.transaction_report import (
    TransactionReport, TransactionSummary, ExecutionAnalysis, CommissionAnalysis,
    TransactionType, ExecutionQuality
)
from financial_portfolio_automation.models.core import Order
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.execution.trade_logger import TradeLogger


class TestTransactionReport:
    """Test cases for TransactionReport class."""
    
    @pytest.fixture
    def mock_data_store(self):
        """Mock data store."""
        return Mock(spec=DataStore)
    
    @pytest.fixture
    def mock_trade_logger(self):
        """Mock trade logger."""
        return Mock(spec=TradeLogger)
    
    @pytest.fixture
    def transaction_report(self, mock_data_store, mock_trade_logger):
        """Create TransactionReport instance."""
        return TransactionReport(
            data_store=mock_data_store,
            trade_logger=mock_trade_logger
        )
    
    @pytest.fixture
    def sample_orders(self):
        """Sample orders for testing."""
        return [
            Order(
                order_id='BUY_001',
                symbol='AAPL',
                quantity=Decimal('100'),
                side='BUY',
                order_type='MARKET',
                status='FILLED',
                filled_quantity=Decimal('100'),
                average_fill_price=Decimal('150.00'),
                created_at=datetime(2024, 1, 15, 10, 0, 0),
                filled_at=datetime(2024, 1, 15, 10, 0, 5)
            ),
            Order(
                order_id='SELL_001',
                symbol='AAPL',
                quantity=Decimal('50'),
                side='SELL',
                order_type='LIMIT',
                status='FILLED',
                filled_quantity=Decimal('50'),
                average_fill_price=Decimal('160.00'),
                created_at=datetime(2024, 2, 15, 14, 0, 0),
                filled_at=datetime(2024, 2, 15, 14, 0, 10)
            ),
            Order(
                order_id='BUY_002',
                symbol='GOOGL',
                quantity=Decimal('25'),
                side='BUY',
                order_type='MARKET',
                status='FILLED',
                filled_quantity=Decimal('25'),
                average_fill_price=Decimal('2800.00'),
                created_at=datetime(2024, 3, 15, 11, 30, 0),
                filled_at=datetime(2024, 3, 15, 11, 30, 2)
            )
        ]
    
    def test_init(self, mock_data_store, mock_trade_logger):
        """Test TransactionReport initialization."""
        report = TransactionReport(
            data_store=mock_data_store,
            trade_logger=mock_trade_logger
        )
        
        assert report.data_store == mock_data_store
        assert report.trade_logger == mock_trade_logger
    
    def test_generate_data_success(self, transaction_report, sample_orders):
        """Test successful transaction report data generation."""
        # Mock data store
        transaction_report.data_store.get_orders.return_value = sample_orders
        
        # Generate report data
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        
        report_data = transaction_report.generate_data(
            start_date=start_date,
            end_date=end_date,
            symbols=['AAPL', 'GOOGL'],
            include_details=True
        )
        
        # Verify structure
        assert 'report_metadata' in report_data
        assert 'transaction_summary' in report_data
        assert 'transaction_details' in report_data
        assert 'execution_analysis' in report_data
        assert 'commission_analysis' in report_data
        assert 'performance_attribution' in report_data
        assert 'trading_patterns' in report_data
        
        # Verify metadata
        metadata = report_data['report_metadata']
        assert metadata['start_date'] == start_date
        assert metadata['end_date'] == end_date
        assert metadata['symbols_filter'] == ['AAPL', 'GOOGL']
        assert metadata['include_details'] == True
    
    def test_generate_data_no_transactions(self, transaction_report):
        """Test report generation with no transactions."""
        # Mock empty transactions
        transaction_report.data_store.get_orders.return_value = []
        
        report_data = transaction_report.generate_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        
        # Should return empty report structure
        assert report_data['transaction_summary'].total_transactions == 0
        assert report_data['transaction_details'] == []
        assert report_data['execution_analysis'] == []
        assert report_data['commission_analysis'] is None
    
    def test_generate_data_without_details(self, transaction_report, sample_orders):
        """Test report generation without detailed analysis."""
        transaction_report.data_store.get_orders.return_value = sample_orders
        
        report_data = transaction_report.generate_data(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_details=False
        )
        
        # Should not include detailed analysis
        assert report_data['execution_analysis'] == []
        assert report_data['commission_analysis'] is None
    
    def test_calculate_transaction_summary(self, transaction_report, sample_orders):
        """Test transaction summary calculation."""
        summary = transaction_report._calculate_transaction_summary(sample_orders)
        
        assert isinstance(summary, TransactionSummary)
        assert summary.total_transactions == 3
        assert summary.buy_transactions == 2
        assert summary.sell_transactions == 1
        
        # Calculate expected total volume
        expected_volume = (
            Decimal('100') * Decimal('150.00') +  # AAPL buy
            Decimal('50') * Decimal('160.00') +   # AAPL sell
            Decimal('25') * Decimal('2800.00')    # GOOGL buy
        )
        assert summary.total_volume == expected_volume
        
        assert summary.average_trade_size == expected_volume / 3
        assert summary.largest_trade > summary.smallest_trade
    
    def test_calculate_transaction_summary_empty(self, transaction_report):
        """Test transaction summary with empty transactions."""
        summary = transaction_report._calculate_transaction_summary([])
        
        assert summary.total_transactions == 0
        assert summary.total_volume == Decimal('0')
        assert summary.buy_transactions == 0
        assert summary.sell_transactions == 0
        assert summary.average_trade_size == Decimal('0')
    
    def test_prepare_transaction_details(self, transaction_report, sample_orders):
        """Test transaction details preparation."""
        details = transaction_report._prepare_transaction_details(sample_orders)
        
        assert len(details) == 3
        
        # Check first transaction
        first_tx = details[0]
        assert first_tx['order_id'] == 'BUY_001'
        assert first_tx['symbol'] == 'AAPL'
        assert first_tx['side'] == 'BUY'
        assert first_tx['quantity'] == 100.0
        assert first_tx['price'] == 150.0
        assert first_tx['value'] == 15000.0
        assert first_tx['order_type'] == 'MARKET'
    
    def test_analyze_execution_quality(self, transaction_report, sample_orders):
        """Test execution quality analysis."""
        analysis = transaction_report._analyze_execution_quality(sample_orders)
        
        assert len(analysis) == 3
        
        for exec_analysis in analysis:
            assert isinstance(exec_analysis, ExecutionAnalysis)
            assert exec_analysis.order_id in ['BUY_001', 'SELL_001', 'BUY_002']
            assert exec_analysis.execution_quality in ExecutionQuality
            assert exec_analysis.fill_rate >= 0
    
    def test_analyze_commissions(self, transaction_report, sample_orders):
        """Test commission analysis."""
        # Add commission attributes to orders
        for order in sample_orders:
            order.commission = Decimal('1.00')
            order.fees = Decimal('0.50')
        
        analysis = transaction_report._analyze_commissions(sample_orders)
        
        assert isinstance(analysis, CommissionAnalysis)
        assert analysis.total_commissions == Decimal('3.00')  # 3 orders * $1
        assert analysis.commission_per_share > 0
        assert analysis.commission_percentage > 0
        assert analysis.total_fees > analysis.total_commissions  # Includes SEC fees
    
    def test_calculate_performance_attribution(self, transaction_report, sample_orders):
        """Test performance attribution calculation."""
        attribution = transaction_report._calculate_performance_attribution(sample_orders)
        
        assert 'AAPL' in attribution
        assert 'GOOGL' in attribution
        
        aapl_attr = attribution['AAPL']
        assert aapl_attr['transactions'] == 2  # 1 buy + 1 sell
        assert aapl_attr['total_bought'] == 100.0
        assert aapl_attr['total_sold'] == 50.0
        assert aapl_attr['realized_pnl'] > 0  # Sold at higher price
        
        googl_attr = attribution['GOOGL']
        assert googl_attr['transactions'] == 1  # 1 buy only
        assert googl_attr['total_bought'] == 25.0
        assert googl_attr['total_sold'] == 0.0
        assert googl_attr['realized_pnl'] == 0.0  # No sales
    
    def test_analyze_trading_patterns(self, transaction_report, sample_orders):
        """Test trading patterns analysis."""
        patterns = transaction_report._analyze_trading_patterns(sample_orders)
        
        assert 'hourly_distribution' in patterns
        assert 'daily_distribution' in patterns
        assert 'size_distribution' in patterns
        assert 'frequency_analysis' in patterns
        
        # Check hourly distribution
        hourly = patterns['hourly_distribution']
        assert isinstance(hourly, dict)
        assert len(hourly) == 24  # 24 hours
        
        # Check daily distribution
        daily = patterns['daily_distribution']
        assert isinstance(daily, dict)
        assert len(daily) == 7  # 7 days of week
        
        # Check frequency analysis
        frequency = patterns['frequency_analysis']
        assert frequency['total_transactions'] == 3
        assert frequency['transactions_per_day'] > 0
    
    def test_assess_execution_quality_market_order(self, transaction_report):
        """Test execution quality assessment for market order."""
        market_order = Order(
            order_id='TEST_001',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)
        )
        
        quality = transaction_report._assess_execution_quality(market_order)
        assert quality == ExecutionQuality.GOOD
    
    def test_assess_execution_quality_limit_order(self, transaction_report):
        """Test execution quality assessment for limit order."""
        limit_order = Order(
            order_id='TEST_001',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='LIMIT',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)
        )
        
        quality = transaction_report._assess_execution_quality(limit_order)
        assert quality == ExecutionQuality.EXCELLENT
    
    def test_calculate_market_impact(self, transaction_report):
        """Test market impact calculation."""
        # Large trade
        large_order = Order(
            order_id='LARGE_001',
            symbol='AAPL',
            quantity=Decimal('1000'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('1000'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)
        )
        
        impact = transaction_report._calculate_market_impact(large_order)
        assert impact == Decimal('0.05')  # 5 bps for large trade
        
        # Small trade
        small_order = Order(
            order_id='SMALL_001',
            symbol='AAPL',
            quantity=Decimal('10'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('10'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)
        )
        
        impact = transaction_report._calculate_market_impact(small_order)
        assert impact == Decimal('0.01')  # 1 bp for small trade
    
    def test_calculate_fill_rate(self, transaction_report):
        """Test fill rate calculation."""
        partial_fill_order = Order(
            order_id='PARTIAL_001',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='LIMIT',
            status='FILLED',
            filled_quantity=Decimal('75'),  # Partial fill
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)
        )
        
        fill_rate = transaction_report._calculate_fill_rate(partial_fill_order)
        assert fill_rate == Decimal('75')  # 75%
    
    def test_calculate_time_to_fill(self, transaction_report):
        """Test time to fill calculation."""
        order = Order(
            order_id='TIME_001',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=datetime(2024, 1, 15, 10, 0, 5)  # 5 seconds later
        )
        
        time_to_fill = transaction_report._calculate_time_to_fill(order)
        assert time_to_fill == 5
    
    def test_calculate_time_to_fill_no_fill_time(self, transaction_report):
        """Test time to fill with no fill time."""
        order = Order(
            order_id='NO_FILL_001',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('150.00'),
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            filled_at=None  # No fill time
        )
        
        time_to_fill = transaction_report._calculate_time_to_fill(order)
        assert time_to_fill is None
    
    def test_analyze_hourly_distribution(self, transaction_report, sample_orders):
        """Test hourly distribution analysis."""
        hourly_dist = transaction_report._analyze_hourly_distribution(sample_orders)
        
        assert isinstance(hourly_dist, dict)
        assert len(hourly_dist) == 24
        
        # Check that transactions are counted in correct hours
        assert hourly_dist[10] >= 1  # 10 AM transactions
        assert hourly_dist[14] >= 1  # 2 PM transaction
        assert hourly_dist[11] >= 1  # 11:30 AM transaction
    
    def test_analyze_daily_distribution(self, transaction_report, sample_orders):
        """Test daily distribution analysis."""
        daily_dist = transaction_report._analyze_daily_distribution(sample_orders)
        
        assert isinstance(daily_dist, dict)
        assert len(daily_dist) == 7
        
        # All sample orders are on weekdays, so weekday counts should be > 0
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        total_weekday_count = sum(daily_dist[day] for day in weekdays)
        assert total_weekday_count == 3  # All 3 transactions
    
    def test_analyze_size_distribution(self, transaction_report, sample_orders):
        """Test size distribution analysis."""
        size_dist = transaction_report._analyze_size_distribution(sample_orders)
        
        assert isinstance(size_dist, dict)
        assert len(size_dist) == 4
        
        # AAPL transactions are medium size, GOOGL is very large
        assert size_dist['Medium ($1K-$10K)'] >= 2  # AAPL transactions
        assert size_dist['Very Large (>$100K)'] >= 1  # GOOGL transaction
    
    def test_analyze_trading_frequency(self, transaction_report, sample_orders):
        """Test trading frequency analysis."""
        frequency = transaction_report._analyze_trading_frequency(sample_orders)
        
        assert frequency['total_transactions'] == 3
        assert frequency['total_days'] > 0
        assert frequency['trading_days'] > 0
        assert frequency['transactions_per_day'] > 0
        assert frequency['transactions_per_trading_day'] > 0
        assert 0 <= frequency['trading_day_percentage'] <= 100
    
    def test_analyze_trading_frequency_empty(self, transaction_report):
        """Test trading frequency analysis with empty transactions."""
        frequency = transaction_report._analyze_trading_frequency([])
        
        assert frequency == {}
    
    def test_empty_report(self, transaction_report):
        """Test empty report generation."""
        empty_report = transaction_report._empty_report(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            symbols=['AAPL']
        )
        
        assert empty_report['transaction_summary'].total_transactions == 0
        assert empty_report['transaction_details'] == []
        assert empty_report['execution_analysis'] == []
        assert empty_report['commission_analysis'] is None
        assert empty_report['performance_attribution'] == {}
        assert empty_report['trading_patterns'] == {}