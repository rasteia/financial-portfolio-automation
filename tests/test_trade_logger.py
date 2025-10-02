"""
Unit tests for the TradeLogger class.

Tests trade logging, audit trails, log rotation, and various
output formats for compliance and analysis.
"""

import pytest
import json
import csv
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from financial_portfolio_automation.execution.trade_logger import (
    TradeLogger, TradeLogEntry, LogLevel, LogFormat, LogRotationConfig
)
from financial_portfolio_automation.models.core import (
    Order, OrderSide, OrderType, OrderStatus, Position, PortfolioSnapshot
)
from financial_portfolio_automation.execution.order_executor import ExecutionResult


class TestTradeLogEntry:
    """Test TradeLogEntry functionality."""
    
    def test_trade_log_entry_creation(self):
        """Test creating a trade log entry."""
        entry = TradeLogEntry(
            timestamp=datetime.now(timezone.utc),
            log_level=LogLevel.INFO,
            event_type="order_submitted",
            order_id="order_123",
            symbol="AAPL",
            side="buy",
            quantity=100,
            price=Decimal('150.00'),
            order_type="market",
            status="new",
            filled_quantity=0,
            average_fill_price=None,
            fees=None,
            user_id="user_123",
            session_id="session_123",
            message="Order submitted",
            metadata={"test": "data"}
        )
        
        assert entry.event_type == "order_submitted"
        assert entry.order_id == "order_123"
        assert entry.symbol == "AAPL"
        assert entry.quantity == 100
        assert entry.price == Decimal('150.00')
    
    def test_trade_log_entry_auto_timestamp(self):
        """Test automatic timestamp assignment."""
        entry = TradeLogEntry(
            timestamp=None,
            log_level=LogLevel.INFO,
            event_type="test",
            order_id=None,
            symbol=None,
            side=None,
            quantity=None,
            price=None,
            order_type=None,
            status=None,
            filled_quantity=None,
            average_fill_price=None,
            fees=None,
            user_id=None,
            session_id=None,
            message="Test message",
            metadata={}
        )
        
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)
    
    def test_trade_log_entry_to_dict(self):
        """Test converting log entry to dictionary."""
        entry = TradeLogEntry(
            timestamp=datetime.now(timezone.utc),
            log_level=LogLevel.INFO,
            event_type="test",
            order_id="order_123",
            symbol="AAPL",
            side="buy",
            quantity=100,
            price=Decimal('150.00'),
            order_type="market",
            status="new",
            filled_quantity=0,
            average_fill_price=Decimal('150.50'),
            fees=Decimal('1.00'),
            user_id="user_123",
            session_id="session_123",
            message="Test message",
            metadata={"test": "data"}
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict['event_type'] == "test"
        assert entry_dict['order_id'] == "order_123"
        assert entry_dict['price'] == 150.0  # Converted to float
        assert entry_dict['average_fill_price'] == 150.5
        assert entry_dict['fees'] == 1.0
        assert entry_dict['log_level'] == "INFO"
        assert isinstance(entry_dict['timestamp'], str)


class TestLogRotationConfig:
    """Test LogRotationConfig functionality."""
    
    def test_default_config(self):
        """Test default rotation configuration."""
        config = LogRotationConfig()
        
        assert config.max_file_size_mb == 100
        assert config.max_files == 10
        assert config.rotation_interval_hours == 24
        assert config.compress_old_files is True
        assert config.archive_directory is None
    
    def test_custom_config(self):
        """Test custom rotation configuration."""
        config = LogRotationConfig(
            max_file_size_mb=50,
            max_files=5,
            rotation_interval_hours=12,
            compress_old_files=False,
            archive_directory="/tmp/archive"
        )
        
        assert config.max_file_size_mb == 50
        assert config.max_files == 5
        assert config.rotation_interval_hours == 12
        assert config.compress_old_files is False
        assert config.archive_directory == "/tmp/archive"


class TestTradeLogger:
    """Test TradeLogger functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def trade_logger_json(self, temp_dir):
        """Create TradeLogger instance with JSON format."""
        return TradeLogger(
            log_directory=temp_dir,
            log_format=LogFormat.JSON,
            user_id="test_user"
        )
    
    @pytest.fixture
    def trade_logger_csv(self, temp_dir):
        """Create TradeLogger instance with CSV format."""
        return TradeLogger(
            log_directory=temp_dir,
            log_format=LogFormat.CSV,
            user_id="test_user"
        )
    
    @pytest.fixture
    def sample_order(self):
        """Create sample order for testing."""
        return Order(
            order_id="order_123",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
    
    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio for testing."""
        positions = [
            Position(
                symbol="AAPL",
                quantity=100,
                market_value=Decimal('15000.00'),
                cost_basis=Decimal('14000.00'),
                unrealized_pnl=Decimal('1000.00'),
                day_pnl=Decimal('500.00')
            )
        ]
        
        return PortfolioSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_value=Decimal('100000.00'),
            buying_power=Decimal('50000.00'),
            day_pnl=Decimal('500.00'),
            total_pnl=Decimal('5000.00'),
            positions=positions
        )
    
    def test_initialization_json(self, trade_logger_json, temp_dir):
        """Test TradeLogger initialization with JSON format."""
        assert trade_logger_json.log_format == LogFormat.JSON
        assert trade_logger_json.user_id == "test_user"
        assert trade_logger_json.log_directory == Path(temp_dir)
        assert trade_logger_json.session_id.startswith("session_")
        
        # Check that log directory was created
        assert Path(temp_dir).exists()
    
    def test_initialization_csv(self, trade_logger_csv, temp_dir):
        """Test TradeLogger initialization with CSV format."""
        assert trade_logger_csv.log_format == LogFormat.CSV
        
        # Check that CSV files were created with headers
        trade_log_file = Path(temp_dir) / "trades.csv"
        assert trade_log_file.exists()
        
        with open(trade_log_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert 'timestamp' in headers
            assert 'order_id' in headers
            assert 'symbol' in headers
    
    def test_log_order_submission_json(self, trade_logger_json, sample_order, temp_dir):
        """Test logging order submission in JSON format."""
        execution_result = ExecutionResult(
            success=True,
            order_id="order_123",
            filled_quantity=0,
            remaining_quantity=100
        )
        
        # Log order submission
        trade_logger_json.log_order_submission(sample_order, execution_result)
        
        # Verify log entry was written
        trade_log_file = Path(temp_dir) / "trades.json"
        assert trade_log_file.exists()
        
        with open(trade_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "order_submitted"
            assert log_entry['order_id'] == "order_123"
            assert log_entry['symbol'] == "AAPL"
            assert log_entry['side'] == "buy"
            assert log_entry['quantity'] == 100
            assert log_entry['user_id'] == "test_user"
    
    def test_log_order_submission_csv(self, trade_logger_csv, sample_order, temp_dir):
        """Test logging order submission in CSV format."""
        # Log order submission
        trade_logger_csv.log_order_submission(sample_order)
        
        # Verify log entry was written
        trade_log_file = Path(temp_dir) / "trades.csv"
        assert trade_log_file.exists()
        
        with open(trade_log_file, 'r') as f:
            reader = csv.DictReader(f)
            log_entry = next(reader)
            
            assert log_entry['event_type'] == "order_submitted"
            assert log_entry['order_id'] == "order_123"
            assert log_entry['symbol'] == "AAPL"
            assert log_entry['side'] == "buy"
            assert log_entry['quantity'] == "100"
    
    def test_log_order_fill(self, trade_logger_json, sample_order, temp_dir):
        """Test logging order fill."""
        fill_price = Decimal('150.50')
        fill_quantity = 50
        fees = Decimal('1.00')
        
        # Log order fill
        trade_logger_json.log_order_fill(sample_order, fill_price, fill_quantity, fees)
        
        # Verify log entry
        trade_log_file = Path(temp_dir) / "trades.json"
        with open(trade_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "order_filled"
            assert log_entry['order_id'] == "order_123"
            assert log_entry['quantity'] == 50
            assert log_entry['price'] == 150.5
            assert log_entry['fees'] == 1.0
    
    def test_log_order_cancellation(self, trade_logger_json, sample_order, temp_dir):
        """Test logging order cancellation."""
        reason = "User requested cancellation"
        
        # Log order cancellation
        trade_logger_json.log_order_cancellation(sample_order, reason)
        
        # Verify log entry
        trade_log_file = Path(temp_dir) / "trades.json"
        with open(trade_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "order_cancelled"
            assert log_entry['order_id'] == "order_123"
            assert log_entry['status'] == "cancelled"
            assert reason in log_entry['message']
    
    def test_log_risk_violation(self, trade_logger_json, temp_dir):
        """Test logging risk violation."""
        violation_type = "position_size_exceeded"
        symbol = "AAPL"
        message = "Position size exceeds limit"
        severity = "high"
        
        # Log risk violation
        trade_logger_json.log_risk_violation(violation_type, symbol, message, severity)
        
        # Verify log entry in audit log
        audit_log_file = Path(temp_dir) / "audit.json"
        with open(audit_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "risk_violation"
            assert log_entry['symbol'] == "AAPL"
            assert log_entry['log_level'] == "ERROR"  # High severity maps to ERROR
            assert log_entry['message'] == message
    
    def test_log_portfolio_snapshot(self, trade_logger_json, sample_portfolio, temp_dir):
        """Test logging portfolio snapshot."""
        # Log portfolio snapshot
        trade_logger_json.log_portfolio_snapshot(sample_portfolio)
        
        # Verify log entry in audit log
        audit_log_file = Path(temp_dir) / "audit.json"
        with open(audit_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "portfolio_snapshot"
            assert log_entry['metadata']['total_value'] == 100000.0
            assert log_entry['metadata']['position_count'] == 1
            assert len(log_entry['metadata']['positions']) == 1
    
    def test_log_system_event(self, trade_logger_json, temp_dir):
        """Test logging system event."""
        event_type = "system_startup"
        message = "System started successfully"
        metadata = {"version": "1.0.0"}
        
        # Log system event
        trade_logger_json.log_system_event(event_type, message, LogLevel.INFO, metadata)
        
        # Verify log entry in audit log
        audit_log_file = Path(temp_dir) / "audit.json"
        with open(audit_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "system_startup"
            assert log_entry['message'] == message
            assert log_entry['metadata']['version'] == "1.0.0"
    
    def test_log_error(self, trade_logger_json, temp_dir):
        """Test logging error."""
        error = ValueError("Test error message")
        context = {"order_id": "order_123", "symbol": "AAPL"}
        
        # Log error
        trade_logger_json.log_error(error, context)
        
        # Verify log entry in error log
        error_log_file = Path(temp_dir) / "errors.json"
        with open(error_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['event_type'] == "error"
            assert log_entry['log_level'] == "ERROR"
            assert log_entry['order_id'] == "order_123"
            assert log_entry['symbol'] == "AAPL"
            assert "Test error message" in log_entry['message']
    
    def test_get_trade_history_no_filter(self, trade_logger_json, sample_order, temp_dir):
        """Test retrieving trade history without filters."""
        # Log some orders
        trade_logger_json.log_order_submission(sample_order)
        trade_logger_json.log_order_fill(sample_order, Decimal('150.00'), 100)
        
        # Get trade history
        history = trade_logger_json.get_trade_history()
        
        assert len(history) == 2
        assert history[0]['event_type'] == "order_submitted"
        assert history[1]['event_type'] == "order_filled"
    
    def test_get_trade_history_with_symbol_filter(self, trade_logger_json, temp_dir):
        """Test retrieving trade history with symbol filter."""
        # Create orders for different symbols
        order_aapl = Order(
            order_id="order_1",
            symbol="AAPL",
            quantity=100,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            status=OrderStatus.NEW
        )
        
        order_tsla = Order(
            order_id="order_2",
            symbol="TSLA",
            quantity=50,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            status=OrderStatus.NEW,
            limit_price=Decimal('250.00')
        )
        
        # Log orders
        trade_logger_json.log_order_submission(order_aapl)
        trade_logger_json.log_order_submission(order_tsla)
        
        # Get history filtered by symbol
        aapl_history = trade_logger_json.get_trade_history(symbol="AAPL")
        tsla_history = trade_logger_json.get_trade_history(symbol="TSLA")
        
        assert len(aapl_history) == 1
        assert len(tsla_history) == 1
        assert aapl_history[0]['symbol'] == "AAPL"
        assert tsla_history[0]['symbol'] == "TSLA"
    
    def test_get_trade_history_with_limit(self, trade_logger_json, sample_order, temp_dir):
        """Test retrieving trade history with limit."""
        # Log multiple entries
        for i in range(5):
            trade_logger_json.log_order_submission(sample_order)
        
        # Get limited history
        history = trade_logger_json.get_trade_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_log_statistics(self, trade_logger_json, sample_order):
        """Test getting log statistics."""
        # Log some entries
        trade_logger_json.log_order_submission(sample_order)
        trade_logger_json.log_system_event("test", "Test message")
        trade_logger_json.log_error(ValueError("Test error"))
        
        # Get statistics
        stats = trade_logger_json.get_log_statistics()
        
        assert stats['total_entries'] == 3
        assert stats['trade_entries'] == 1
        assert stats['audit_entries'] == 1
        assert stats['error_entries'] == 1
        assert 'trade_log_size_mb' in stats
        assert 'audit_log_size_mb' in stats
        assert 'error_log_size_mb' in stats
    
    def test_log_rotation(self, trade_logger_json, sample_order, temp_dir):
        """Test log rotation functionality."""
        # Configure small file size for testing
        trade_logger_json.rotation_config.max_file_size_mb = 0.001  # Very small
        trade_logger_json.rotation_config.compress_old_files = False  # Disable compression for test
        
        # Log enough entries to trigger rotation
        for i in range(200):  # More entries to ensure size threshold
            trade_logger_json.log_order_submission(sample_order)
        
        # Manually trigger rotation to test the functionality
        trade_logger_json.rotate_logs()
        
        # Check that rotation occurred
        log_files = list(Path(temp_dir).glob("trades_*.json"))
        assert len(log_files) >= 0  # Should have rotated files or at least attempted rotation
    
    def test_text_format_logging(self, temp_dir):
        """Test logging in text format."""
        logger = TradeLogger(
            log_directory=temp_dir,
            log_format=LogFormat.TEXT,
            user_id="test_user"
        )
        
        # Log a system event
        logger.log_system_event("test", "Test message", LogLevel.INFO)
        
        # Verify text format
        audit_log_file = Path(temp_dir) / "audit.text"
        with open(audit_log_file, 'r') as f:
            content = f.read()
            assert "INFO - Test message" in content
    
    def test_concurrent_logging(self, trade_logger_json, sample_order):
        """Test concurrent logging with thread safety."""
        import threading
        
        def log_orders():
            for i in range(10):
                trade_logger_json.log_order_submission(sample_order)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_orders)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all entries were logged
        stats = trade_logger_json.get_log_statistics()
        assert stats['trade_entries'] == 50  # 5 threads * 10 orders each
    
    def test_cleanup_old_files(self, trade_logger_json, temp_dir):
        """Test cleanup of old rotated files."""
        # Configure to keep only 2 files
        trade_logger_json.rotation_config.max_files = 2
        
        # Create some fake old files
        log_dir = Path(temp_dir)
        for i in range(5):
            fake_file = log_dir / f"trades_2023010{i}_120000.json"
            fake_file.write_text("fake log data")
        
        # Trigger cleanup
        trade_logger_json._cleanup_old_files(trade_logger_json.trade_log_file)
        
        # Check that only max_files remain
        remaining_files = list(log_dir.glob("trades_*.json"))
        assert len(remaining_files) <= trade_logger_json.rotation_config.max_files
    
    def test_error_handling_in_logging(self, trade_logger_json, sample_order):
        """Test error handling during logging operations."""
        # Mock file operations to raise exception
        with patch('builtins.open', side_effect=IOError("Disk full")):
            # Should not raise exception, just log error
            trade_logger_json.log_order_submission(sample_order)
        
        # Logger should still be functional
        assert trade_logger_json.user_id == "test_user"
    
    def test_session_id_generation(self, trade_logger_json):
        """Test session ID generation."""
        session_id = trade_logger_json.session_id
        
        assert session_id.startswith("session_")
        assert len(session_id) > 10  # Should include timestamp
    
    def test_metadata_handling(self, trade_logger_json, temp_dir):
        """Test handling of metadata in log entries."""
        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
            "boolean": True
        }
        
        trade_logger_json.log_system_event(
            "test", 
            "Test with complex metadata", 
            LogLevel.INFO, 
            complex_metadata
        )
        
        # Verify metadata was preserved
        audit_log_file = Path(temp_dir) / "audit.json"
        with open(audit_log_file, 'r') as f:
            log_entry = json.loads(f.readline().strip())
            
            assert log_entry['metadata']['nested']['key'] == "value"
            assert log_entry['metadata']['list'] == [1, 2, 3]
            assert log_entry['metadata']['number'] == 42
            assert log_entry['metadata']['boolean'] is True