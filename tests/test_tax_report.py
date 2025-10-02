"""
Unit tests for TaxReport.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from financial_portfolio_automation.reporting.tax_report import (
    TaxReport, TaxLot, RealizedGainLoss, WashSaleTransaction, TaxSummary,
    TaxLotMethod, GainLossType
)
from financial_portfolio_automation.models.core import Order, Position
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.execution.trade_logger import TradeLogger


class TestTaxReport:
    """Test cases for TaxReport class."""
    
    @pytest.fixture
    def mock_data_store(self):
        """Mock data store."""
        mock = Mock(spec=DataStore)
        mock.get_positions_at_date = Mock(return_value=[])
        mock.get_current_positions = Mock(return_value=[])
        mock.get_orders = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_trade_logger(self):
        """Mock trade logger."""
        return Mock(spec=TradeLogger)
    
    @pytest.fixture
    def tax_report(self, mock_data_store, mock_trade_logger):
        """Create TaxReport instance."""
        return TaxReport(
            data_store=mock_data_store,
            trade_logger=mock_trade_logger,
            tax_lot_method=TaxLotMethod.FIFO
        )
    
    @pytest.fixture
    def sample_positions(self):
        """Sample positions for initialization."""
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
    def sample_buy_order(self):
        """Sample buy order."""
        return Order(
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
        )
    
    @pytest.fixture
    def sample_sell_order(self):
        """Sample sell order."""
        return Order(
            order_id='SELL_001',
            symbol='AAPL',
            quantity=Decimal('50'),
            side='SELL',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('50'),
            average_fill_price=Decimal('160.00'),
            created_at=datetime(2024, 6, 15, 14, 0, 0),
            filled_at=datetime(2024, 6, 15, 14, 0, 5)
        )
    
    def test_init(self, mock_data_store, mock_trade_logger):
        """Test TaxReport initialization."""
        report = TaxReport(
            data_store=mock_data_store,
            trade_logger=mock_trade_logger,
            tax_lot_method=TaxLotMethod.LIFO
        )
        
        assert report.data_store == mock_data_store
        assert report.trade_logger == mock_trade_logger
        assert report.tax_lot_method == TaxLotMethod.LIFO
        assert report._tax_lots == {}
        assert report._realized_gains_losses == []
        assert report._wash_sales == []
    
    def test_generate_data_success(self, tax_report, sample_positions):
        """Test successful tax report data generation."""
        # Mock data store methods
        tax_report.data_store.get_positions_at_date.return_value = sample_positions
        tax_report.data_store.get_orders.return_value = []
        
        # Generate report data
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        
        report_data = tax_report.generate_data(
            start_date=start_date,
            end_date=end_date,
            symbols=['AAPL', 'GOOGL']
        )
        
        # Verify structure
        assert 'report_metadata' in report_data
        assert 'tax_summary' in report_data
        assert 'realized_gains_losses' in report_data
        assert 'wash_sales' in report_data
        assert 'detailed_transactions' in report_data
        assert 'form_8949_data' in report_data
        assert 'tax_loss_opportunities' in report_data
        assert 'current_tax_lots' in report_data
        
        # Verify metadata
        metadata = report_data['report_metadata']
        assert metadata['start_date'] == start_date
        assert metadata['end_date'] == end_date
        assert metadata['tax_year'] == start_date.year
        assert metadata['tax_lot_method'] == TaxLotMethod.FIFO.value
    
    def test_initialize_tax_lots(self, tax_report, sample_positions):
        """Test tax lot initialization."""
        tax_report.data_store.get_positions_at_date.return_value = sample_positions
        
        tax_report._initialize_tax_lots(date(2024, 1, 1), ['AAPL', 'GOOGL'])
        
        # Verify tax lots were created
        assert 'AAPL' in tax_report._tax_lots
        assert 'GOOGL' in tax_report._tax_lots
        
        aapl_lots = tax_report._tax_lots['AAPL']
        assert len(aapl_lots) == 1
        assert aapl_lots[0].symbol == 'AAPL'
        assert aapl_lots[0].quantity == Decimal('100')
        assert aapl_lots[0].cost_basis == Decimal('12000')
    
    def test_initialize_tax_lots_with_filter(self, tax_report, sample_positions):
        """Test tax lot initialization with symbol filter."""
        tax_report.data_store.get_positions_at_date.return_value = sample_positions
        
        tax_report._initialize_tax_lots(date(2024, 1, 1), ['AAPL'])
        
        # Only AAPL should be initialized
        assert 'AAPL' in tax_report._tax_lots
        assert 'GOOGL' not in tax_report._tax_lots
    
    def test_process_buy_transaction(self, tax_report, sample_buy_order):
        """Test processing buy transaction."""
        tax_report._process_buy_transaction(sample_buy_order)
        
        # Verify tax lot was created
        assert 'AAPL' in tax_report._tax_lots
        lots = tax_report._tax_lots['AAPL']
        assert len(lots) == 1
        
        lot = lots[0]
        assert lot.symbol == 'AAPL'
        assert lot.quantity == Decimal('100')
        assert lot.cost_basis == Decimal('15000')  # 100 * 150
        assert lot.acquisition_date == date(2024, 1, 15)
    
    def test_process_sell_transaction(self, tax_report, sample_buy_order, sample_sell_order):
        """Test processing sell transaction."""
        # First create a tax lot with buy
        tax_report._process_buy_transaction(sample_buy_order)
        
        # Then process sell
        tax_report._process_sell_transaction(sample_sell_order)
        
        # Verify realized gain/loss was created
        assert len(tax_report._realized_gains_losses) == 1
        
        gl = tax_report._realized_gains_losses[0]
        assert gl.symbol == 'AAPL'
        assert gl.quantity == Decimal('50')
        assert gl.sale_price == Decimal('160.00')
        assert gl.gain_loss == Decimal('500')  # 50 * (160 - 150)
        assert gl.gain_loss_type == GainLossType.SHORT_TERM  # < 1 year between dates
        
        # Verify tax lot was updated
        lots = tax_report._tax_lots['AAPL']
        assert len(lots) == 1
        assert lots[0].quantity == Decimal('50')  # Remaining quantity
    
    def test_process_sell_transaction_no_lots(self, tax_report, sample_sell_order):
        """Test processing sell transaction with no tax lots."""
        # Process sell without any existing lots
        tax_report._process_sell_transaction(sample_sell_order)
        
        # Should not create any realized gains/losses
        assert len(tax_report._realized_gains_losses) == 0
    
    def test_select_tax_lot_fifo(self, tax_report):
        """Test FIFO tax lot selection."""
        # Create multiple tax lots
        lot1 = TaxLot('AAPL', Decimal('100'), Decimal('10000'), date(2024, 1, 1), 'lot1')
        lot2 = TaxLot('AAPL', Decimal('100'), Decimal('11000'), date(2024, 2, 1), 'lot2')
        
        tax_report._tax_lots['AAPL'] = [lot1, lot2]
        
        selected_lot = tax_report._select_tax_lot('AAPL')
        
        # Should select the earliest lot (FIFO)
        assert selected_lot == lot1
    
    def test_select_tax_lot_lifo(self, tax_report):
        """Test LIFO tax lot selection."""
        tax_report.tax_lot_method = TaxLotMethod.LIFO
        
        # Create multiple tax lots
        lot1 = TaxLot('AAPL', Decimal('100'), Decimal('10000'), date(2024, 1, 1), 'lot1')
        lot2 = TaxLot('AAPL', Decimal('100'), Decimal('11000'), date(2024, 2, 1), 'lot2')
        
        tax_report._tax_lots['AAPL'] = [lot1, lot2]
        
        selected_lot = tax_report._select_tax_lot('AAPL')
        
        # Should select the latest lot (LIFO)
        assert selected_lot == lot2
    
    def test_select_tax_lot_no_lots(self, tax_report):
        """Test tax lot selection with no lots available."""
        selected_lot = tax_report._select_tax_lot('AAPL')
        assert selected_lot is None
    
    def test_detect_wash_sales(self, tax_report):
        """Test wash sale detection."""
        # Create a realized loss
        loss_gl = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('100'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('140.00'),
            cost_basis=Decimal('15000'),
            gain_loss=Decimal('-1000'),  # Loss
            gain_loss_type=GainLossType.SHORT_TERM
        )
        tax_report._realized_gains_losses.append(loss_gl)
        
        # Mock repurchase order within 30 days
        repurchase_order = Order(
            order_id='BUY_002',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('145.00'),
            created_at=datetime(2024, 6, 20, 10, 0, 0),
            filled_at=datetime(2024, 6, 20, 10, 0, 5)
        )
        
        tax_report.data_store.get_orders.return_value = [repurchase_order]
        
        # Detect wash sales
        tax_report._detect_wash_sales(date(2024, 1, 1), date(2024, 12, 31))
        
        # Verify wash sale was detected
        assert len(tax_report._wash_sales) == 1
        assert loss_gl.is_wash_sale == True
        assert loss_gl.gain_loss == Decimal('0')  # Loss disallowed
    
    def test_check_wash_sale_violation_found(self, tax_report):
        """Test wash sale violation detection."""
        loss_transaction = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('100'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('140.00'),
            cost_basis=Decimal('15000'),
            gain_loss=Decimal('-1000'),
            gain_loss_type=GainLossType.SHORT_TERM
        )
        
        # Mock repurchase order
        repurchase_order = Order(
            order_id='BUY_002',
            symbol='AAPL',
            quantity=Decimal('100'),
            side='BUY',
            order_type='MARKET',
            status='FILLED',
            filled_quantity=Decimal('100'),
            average_fill_price=Decimal('145.00'),
            created_at=datetime(2024, 6, 20, 10, 0, 0),
            filled_at=datetime(2024, 6, 20, 10, 0, 5)
        )
        
        tax_report.data_store.get_orders.return_value = [repurchase_order]
        
        wash_sale = tax_report._check_wash_sale_violation(
            loss_transaction, date(2024, 1, 1), date(2024, 12, 31)
        )
        
        assert wash_sale is not None
        assert isinstance(wash_sale, WashSaleTransaction)
        assert wash_sale.symbol == 'AAPL'
        assert wash_sale.disallowed_loss == Decimal('1000')
    
    def test_check_wash_sale_violation_not_found(self, tax_report):
        """Test wash sale violation when no repurchase found."""
        loss_transaction = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('100'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('140.00'),
            cost_basis=Decimal('15000'),
            gain_loss=Decimal('-1000'),
            gain_loss_type=GainLossType.SHORT_TERM
        )
        
        # No repurchase orders
        tax_report.data_store.get_orders.return_value = []
        
        wash_sale = tax_report._check_wash_sale_violation(
            loss_transaction, date(2024, 1, 1), date(2024, 12, 31)
        )
        
        assert wash_sale is None
    
    def test_generate_tax_summary(self, tax_report):
        """Test tax summary generation."""
        # Add some realized gains/losses
        short_term_gain = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('50'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('160.00'),
            cost_basis=Decimal('7500'),
            gain_loss=Decimal('500'),
            gain_loss_type=GainLossType.SHORT_TERM
        )
        
        long_term_loss = RealizedGainLoss(
            symbol='GOOGL',
            quantity=Decimal('25'),
            sale_date=date(2024, 8, 15),
            sale_price=Decimal('140.00'),
            cost_basis=Decimal('4000'),
            gain_loss=Decimal('-500'),
            gain_loss_type=GainLossType.LONG_TERM
        )
        
        tax_report._realized_gains_losses = [short_term_gain, long_term_loss]
        
        summary = tax_report._generate_tax_summary(2024)
        
        assert isinstance(summary, TaxSummary)
        assert summary.tax_year == 2024
        assert summary.total_short_term_gain_loss == Decimal('500')
        assert summary.total_long_term_gain_loss == Decimal('-500')
        assert summary.total_gain_loss == Decimal('0')
    
    def test_prepare_detailed_transactions(self, tax_report):
        """Test detailed transaction preparation."""
        # Add a realized gain/loss
        gl = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('100'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('160.00'),
            cost_basis=Decimal('15000'),
            gain_loss=Decimal('1000'),
            gain_loss_type=GainLossType.SHORT_TERM,
            acquisition_date=date(2024, 1, 15),
            holding_period_days=152
        )
        
        tax_report._realized_gains_losses = [gl]
        
        transactions = tax_report._prepare_detailed_transactions()
        
        assert len(transactions) == 1
        transaction = transactions[0]
        
        assert transaction['symbol'] == 'AAPL'
        assert transaction['quantity'] == 100.0
        assert transaction['sale_date'] == '2024-06-15'
        assert transaction['gain_loss'] == 1000.0
        assert transaction['gain_loss_type'] == 'short_term'
        assert transaction['holding_period_days'] == 152
    
    def test_prepare_form_8949_data(self, tax_report):
        """Test Form 8949 data preparation."""
        # Add short-term and long-term gains/losses
        short_term = RealizedGainLoss(
            symbol='AAPL',
            quantity=Decimal('100'),
            sale_date=date(2024, 6, 15),
            sale_price=Decimal('160.00'),
            cost_basis=Decimal('15000'),
            gain_loss=Decimal('1000'),
            gain_loss_type=GainLossType.SHORT_TERM,
            acquisition_date=date(2024, 1, 15)
        )
        
        long_term = RealizedGainLoss(
            symbol='GOOGL',
            quantity=Decimal('50'),
            sale_date=date(2024, 8, 15),
            sale_price=Decimal('180.00'),
            cost_basis=Decimal('8000'),
            gain_loss=Decimal('1000'),
            gain_loss_type=GainLossType.LONG_TERM,
            acquisition_date=date(2023, 1, 15)
        )
        
        tax_report._realized_gains_losses = [short_term, long_term]
        
        form_data = tax_report._prepare_form_8949_data()
        
        assert 'short_term' in form_data
        assert 'long_term' in form_data
        
        assert len(form_data['short_term']) == 1
        assert len(form_data['long_term']) == 1
        
        st_entry = form_data['short_term'][0]
        assert 'AAPL' in st_entry['description']
        assert st_entry['sale_date'] == '06/15/2024'
        assert st_entry['proceeds'] == 16000.0
        assert st_entry['gain_loss'] == 1000.0
    
    def test_identify_tax_loss_opportunities(self, tax_report):
        """Test tax-loss harvesting opportunity identification."""
        # Mock current positions with unrealized losses
        positions_with_losses = [
            Position(
                symbol='TSLA',
                quantity=Decimal('100'),
                market_value=Decimal('8000'),
                cost_basis=Decimal('10000'),
                unrealized_pnl=Decimal('-2000'),  # Unrealized loss
                day_pnl=Decimal('-50')
            )
        ]
        
        tax_report.data_store.get_current_positions.return_value = positions_with_losses
        
        opportunities = tax_report._identify_tax_loss_opportunities()
        
        assert len(opportunities) == 1
        opportunity = opportunities[0]
        
        assert opportunity['symbol'] == 'TSLA'
        assert opportunity['unrealized_loss'] == -2000.0
        assert opportunity['potential_tax_benefit'] > 0
    
    def test_get_current_tax_lots_summary(self, tax_report):
        """Test current tax lots summary."""
        # Add some tax lots
        lot1 = TaxLot('AAPL', Decimal('100'), Decimal('15000'), date(2024, 1, 15), 'lot1')
        lot2 = TaxLot('GOOGL', Decimal('50'), Decimal('8000'), date(2024, 2, 15), 'lot2')
        
        tax_report._tax_lots = {
            'AAPL': [lot1],
            'GOOGL': [lot2]
        }
        
        summary = tax_report._get_current_tax_lots_summary()
        
        assert 'AAPL' in summary
        assert 'GOOGL' in summary
        
        aapl_lots = summary['AAPL']
        assert len(aapl_lots) == 1
        assert aapl_lots[0]['lot_id'] == 'lot1'
        assert aapl_lots[0]['quantity'] == 100.0
        assert aapl_lots[0]['cost_basis'] == 15000.0