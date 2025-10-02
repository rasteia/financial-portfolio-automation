"""
Integration tests for the reporting system.
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

from financial_portfolio_automation.reporting.report_generator import (
    ReportGenerator, ReportRequest, ReportType, ReportFormat
)
from financial_portfolio_automation.reporting.export_manager import ExportManager
from financial_portfolio_automation.models.core import PortfolioSnapshot, Position, Order
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.execution.trade_logger import TradeLogger


class TestReportingIntegration:
    """Integration tests for the complete reporting system."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def sample_portfolio_data(self):
        """Create sample portfolio data for testing."""
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
        
        # Create portfolio snapshots over time
        snapshots = []
        base_date = date(2024, 1, 1)
        base_value = Decimal('20000')
        
        for i in range(30):  # 30 days of data
            snapshot_date = base_date + timedelta(days=i)
            # Simulate portfolio growth with some volatility
            daily_change = Decimal(str((i % 5 - 2) * 100))  # -200 to +200
            total_value = base_value + Decimal(str(i * 50)) + daily_change
            
            snapshot = PortfolioSnapshot(
                timestamp=datetime.combine(snapshot_date, datetime.min.time()),
                total_value=total_value,
                buying_power=Decimal('5000'),
                day_pnl=daily_change,
                total_pnl=total_value - base_value,
                positions=positions
            )
            snapshots.append(snapshot)
        
        return snapshots
    
    @pytest.fixture
    def sample_orders(self):
        """Create sample orders for testing."""
        return [
            Order(
                order_id='BUY_001',
                symbol='AAPL',
                quantity=Decimal('100'),
                side='BUY',
                order_type='MARKET',
                status='FILLED',
                filled_quantity=Decimal('100'),
                average_fill_price=Decimal('120.00'),
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
                average_fill_price=Decimal('150.00'),
                created_at=datetime(2024, 6, 15, 14, 0, 0),
                filled_at=datetime(2024, 6, 15, 14, 0, 10)
            ),
            Order(
                order_id='BUY_002',
                symbol='GOOGL',
                quantity=Decimal('50'),
                side='BUY',
                order_type='MARKET',
                status='FILLED',
                filled_quantity=Decimal('50'),
                average_fill_price=Decimal('150.00'),
                created_at=datetime(2024, 2, 15, 11, 30, 0),
                filled_at=datetime(2024, 2, 15, 11, 30, 2)
            )
        ]
    
    @pytest.fixture
    def mock_data_store(self, sample_portfolio_data, sample_orders):
        """Create mock data store with sample data."""
        class MockDataStore:
            def get_portfolio_snapshots(self, start_date, end_date):
                return [
                    s for s in sample_portfolio_data
                    if start_date <= s.timestamp.date() <= end_date
                ]
            
            def get_orders(self, start_date=None, end_date=None, status=None, **kwargs):
                orders = sample_orders
                if start_date:
                    orders = [o for o in orders if o.created_at.date() >= start_date]
                if end_date:
                    orders = [o for o in orders if o.created_at.date() <= end_date]
                if status:
                    orders = [o for o in orders if o.status == status]
                return orders
            
            def get_positions_at_date(self, date):
                return sample_portfolio_data[0].positions
            
            def get_current_positions(self):
                return sample_portfolio_data[-1].positions
        
        return MockDataStore()
    
    @pytest.fixture
    def mock_portfolio_analyzer(self):
        """Create mock portfolio analyzer."""
        class MockPortfolioAnalyzer:
            pass
        
        return MockPortfolioAnalyzer()
    
    @pytest.fixture
    def mock_trade_logger(self):
        """Create mock trade logger."""
        class MockTradeLogger:
            pass
        
        return MockTradeLogger()
    
    @pytest.fixture
    def report_generator(self, mock_data_store, mock_portfolio_analyzer, 
                        mock_trade_logger, temp_dir):
        """Create report generator with mocked dependencies."""
        export_manager = ExportManager(output_directory=temp_dir)
        
        return ReportGenerator(
            data_store=mock_data_store,
            portfolio_analyzer=mock_portfolio_analyzer,
            trade_logger=mock_trade_logger,
            export_manager=export_manager
        )
    
    def test_performance_report_generation_json(self, report_generator, temp_dir):
        """Test complete performance report generation in JSON format."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.JSON,
            symbols=['AAPL', 'GOOGL'],
            benchmark_symbol='SPY'
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify metadata
        assert metadata.status == "completed"
        assert metadata.report_type == ReportType.PERFORMANCE
        assert metadata.format == ReportFormat.JSON
        assert metadata.file_path is not None
        assert metadata.generation_time_seconds is not None
        
        # Verify file was created
        assert os.path.exists(metadata.file_path)
        
        # Verify file content
        with open(metadata.file_path, 'r') as f:
            import json
            report_data = json.load(f)
            
            assert 'report_metadata' in report_data
            assert 'portfolio_summary' in report_data
            assert 'performance_metrics' in report_data
            assert 'asset_allocation' in report_data
    
    def test_performance_report_generation_csv(self, report_generator, temp_dir):
        """Test performance report generation in CSV format."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.CSV,
            symbols=['AAPL']
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify metadata
        assert metadata.status == "completed"
        assert metadata.format == ReportFormat.CSV
        
        # Verify file was created and has content
        assert os.path.exists(metadata.file_path)
        
        with open(metadata.file_path, 'r') as f:
            content = f.read()
            assert 'Performance Report' in content
            assert 'Portfolio Summary' in content
            assert 'AAPL' in content
    
    def test_performance_report_generation_html(self, report_generator, temp_dir):
        """Test performance report generation in HTML format."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.HTML,
            include_charts=True
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify metadata
        assert metadata.status == "completed"
        assert metadata.format == ReportFormat.HTML
        
        # Verify file was created and has HTML content
        assert os.path.exists(metadata.file_path)
        
        with open(metadata.file_path, 'r') as f:
            content = f.read()
            assert '<!DOCTYPE html>' in content
            assert 'Performance Report' in content
            assert '<table' in content
    
    def test_tax_report_generation(self, report_generator, temp_dir):
        """Test tax report generation."""
        request = ReportRequest(
            report_type=ReportType.TAX_SUMMARY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.JSON
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify metadata
        assert metadata.status == "completed"
        assert metadata.report_type == ReportType.TAX_SUMMARY
        
        # Verify file was created
        assert os.path.exists(metadata.file_path)
        
        # Verify file content
        with open(metadata.file_path, 'r') as f:
            import json
            report_data = json.load(f)
            
            assert 'report_metadata' in report_data
            assert 'tax_summary' in report_data
            assert 'realized_gains_losses' in report_data
            assert 'wash_sales' in report_data
            assert 'form_8949_data' in report_data
    
    def test_transaction_report_generation(self, report_generator, temp_dir):
        """Test transaction report generation."""
        request = ReportRequest(
            report_type=ReportType.TRANSACTION_HISTORY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.CSV,
            include_details=True
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify metadata
        assert metadata.status == "completed"
        assert metadata.report_type == ReportType.TRANSACTION_HISTORY
        
        # Verify file was created
        assert os.path.exists(metadata.file_path)
        
        # Verify file content
        with open(metadata.file_path, 'r') as f:
            content = f.read()
            assert 'Transaction Report' in content
            assert 'BUY_001' in content or 'SELL_001' in content
    
    def test_multiple_report_generation(self, report_generator, temp_dir):
        """Test generating multiple reports."""
        requests = [
            ReportRequest(
                report_type=ReportType.PERFORMANCE,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 30),
                format=ReportFormat.JSON
            ),
            ReportRequest(
                report_type=ReportType.TAX_SUMMARY,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                format=ReportFormat.CSV
            ),
            ReportRequest(
                report_type=ReportType.TRANSACTION_HISTORY,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                format=ReportFormat.HTML
            )
        ]
        
        metadata_list = []
        
        # Generate all reports
        for request in requests:
            metadata = report_generator.generate_report(request)
            metadata_list.append(metadata)
            assert metadata.status == "completed"
        
        # Verify all reports were generated
        assert len(metadata_list) == 3
        
        # Verify all files exist
        for metadata in metadata_list:
            assert os.path.exists(metadata.file_path)
        
        # Verify report listing
        all_reports = report_generator.list_reports()
        assert len(all_reports) == 3
        
        # Test filtering
        perf_reports = report_generator.list_reports(
            report_type=ReportType.PERFORMANCE
        )
        assert len(perf_reports) == 1
        assert perf_reports[0].report_type == ReportType.PERFORMANCE
    
    def test_report_with_custom_output_path(self, report_generator, temp_dir):
        """Test report generation with custom output path."""
        custom_path = os.path.join(temp_dir, 'custom_report.json')
        
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.JSON,
            output_path=custom_path
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify custom path was used
        assert metadata.file_path == custom_path
        assert os.path.exists(custom_path)
    
    def test_report_generation_error_handling(self, report_generator):
        """Test error handling in report generation."""
        # Invalid date range
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),  # End before start
            format=ReportFormat.JSON
        )
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_export_manager_standalone(self, temp_dir):
        """Test export manager functionality standalone."""
        export_manager = ExportManager(output_directory=temp_dir)
        
        # Sample report data
        report_data = {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 1, 30)
            },
            'portfolio_summary': {
                'start_value': 20000.0,
                'end_value': 21500.0,
                'total_return': 1500.0
            }
        }
        
        # Test JSON export
        json_path = export_manager.export_report(
            report_data=report_data,
            report_type=ReportType.PERFORMANCE,
            format=ReportFormat.JSON
        )
        
        assert os.path.exists(json_path)
        
        # Test CSV export
        csv_path = export_manager.export_report(
            report_data=report_data,
            report_type=ReportType.PERFORMANCE,
            format=ReportFormat.CSV
        )
        
        assert os.path.exists(csv_path)
        
        # Test HTML export
        html_path = export_manager.export_report(
            report_data=report_data,
            report_type=ReportType.PERFORMANCE,
            format=ReportFormat.HTML
        )
        
        assert os.path.exists(html_path)
    
    def test_report_status_tracking(self, report_generator):
        """Test report status tracking functionality."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.JSON
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        report_id = metadata.report_id
        
        # Check status
        status = report_generator.get_report_status(report_id)
        assert status is not None
        assert status.report_id == report_id
        assert status.status == "completed"
        
        # Check non-existent report
        non_existent_status = report_generator.get_report_status("non_existent")
        assert non_existent_status is None
    
    def test_performance_metrics_calculation(self, report_generator):
        """Test that performance metrics are calculated correctly."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 30),
            format=ReportFormat.JSON
        )
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Read and verify the report data
        with open(metadata.file_path, 'r') as f:
            import json
            report_data = json.load(f)
        
        # Verify performance metrics exist and are reasonable
        metrics = report_data['performance_metrics']
        assert 'total_return' in metrics
        assert 'annualized_return' in metrics
        assert 'volatility' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        
        # Verify portfolio summary
        summary = report_data['portfolio_summary']
        assert summary['start_value'] > 0
        assert summary['end_value'] > 0
        assert 'total_return_pct' in summary