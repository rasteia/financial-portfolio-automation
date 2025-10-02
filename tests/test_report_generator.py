"""
Unit tests for ReportGenerator.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from financial_portfolio_automation.reporting.report_generator import (
    ReportGenerator, ReportRequest, ReportMetadata
)
from financial_portfolio_automation.reporting.types import ReportType, ReportFormat
from financial_portfolio_automation.models.core import PortfolioSnapshot, Position
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer
from financial_portfolio_automation.execution.trade_logger import TradeLogger
from financial_portfolio_automation.reporting.export_manager import ExportManager


class TestReportGenerator:
    """Test cases for ReportGenerator class."""
    
    @pytest.fixture
    def mock_data_store(self):
        """Mock data store."""
        return Mock(spec=DataStore)
    
    @pytest.fixture
    def mock_portfolio_analyzer(self):
        """Mock portfolio analyzer."""
        return Mock(spec=PortfolioAnalyzer)
    
    @pytest.fixture
    def mock_trade_logger(self):
        """Mock trade logger."""
        return Mock(spec=TradeLogger)
    
    @pytest.fixture
    def mock_export_manager(self):
        """Mock export manager."""
        return Mock(spec=ExportManager)
    
    @pytest.fixture
    def report_generator(self, mock_data_store, mock_portfolio_analyzer, 
                        mock_trade_logger, mock_export_manager):
        """Create ReportGenerator instance."""
        return ReportGenerator(
            data_store=mock_data_store,
            portfolio_analyzer=mock_portfolio_analyzer,
            trade_logger=mock_trade_logger,
            export_manager=mock_export_manager
        )
    
    @pytest.fixture
    def sample_report_request(self):
        """Sample report request."""
        return ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.PDF,
            symbols=['AAPL', 'GOOGL']
        )
    
    def test_init(self, mock_data_store, mock_portfolio_analyzer, 
                  mock_trade_logger):
        """Test ReportGenerator initialization."""
        generator = ReportGenerator(
            data_store=mock_data_store,
            portfolio_analyzer=mock_portfolio_analyzer,
            trade_logger=mock_trade_logger
        )
        
        assert generator.data_store == mock_data_store
        assert generator.portfolio_analyzer == mock_portfolio_analyzer
        assert generator.trade_logger == mock_trade_logger
        assert generator.export_manager is not None
        assert generator.performance_report is not None
        assert generator.tax_report is not None
        assert generator.transaction_report is not None
    
    def test_generate_report_success(self, report_generator, sample_report_request):
        """Test successful report generation."""
        # Mock report data generation
        mock_report_data = {'test': 'data'}
        report_generator.performance_report.generate_data.return_value = mock_report_data
        
        # Mock export
        mock_file_path = '/path/to/report.pdf'
        report_generator.export_manager.export_report.return_value = mock_file_path
        
        # Generate report
        metadata = report_generator.generate_report(sample_report_request)
        
        # Verify results
        assert isinstance(metadata, ReportMetadata)
        assert metadata.report_type == ReportType.PERFORMANCE
        assert metadata.status == "completed"
        assert metadata.file_path == mock_file_path
        assert metadata.generation_time_seconds is not None
        
        # Verify method calls
        report_generator.performance_report.generate_data.assert_called_once()
        report_generator.export_manager.export_report.assert_called_once()
    
    def test_generate_report_validation_error(self, report_generator):
        """Test report generation with validation error."""
        # Invalid date range
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 12, 31),
            end_date=date(2024, 1, 1),  # End before start
            format=ReportFormat.PDF
        )
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_generate_report_future_end_date(self, report_generator):
        """Test report generation with future end date."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date.today() + timedelta(days=1),  # Future date
            format=ReportFormat.PDF
        )
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_generate_report_tax_date_range_limit(self, report_generator):
        """Test tax report date range validation."""
        request = ReportRequest(
            report_type=ReportType.TAX_SUMMARY,
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),  # More than 1 year
            format=ReportFormat.PDF
        )
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_generate_report_invalid_symbols(self, report_generator):
        """Test report generation with invalid symbols."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.PDF,
            symbols=['AAPL', '']  # Empty symbol
        )
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_generate_tax_report(self, report_generator):
        """Test tax report generation."""
        request = ReportRequest(
            report_type=ReportType.TAX_SUMMARY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.CSV
        )
        
        # Mock tax report data
        mock_report_data = {'tax_data': 'test'}
        report_generator.tax_report.generate_data.return_value = mock_report_data
        
        # Mock export
        mock_file_path = '/path/to/tax_report.csv'
        report_generator.export_manager.export_report.return_value = mock_file_path
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify results
        assert metadata.report_type == ReportType.TAX_SUMMARY
        assert metadata.status == "completed"
        
        # Verify tax report was called
        report_generator.tax_report.generate_data.assert_called_once_with(
            start_date=request.start_date,
            end_date=request.end_date,
            symbols=request.symbols
        )
    
    def test_generate_transaction_report(self, report_generator):
        """Test transaction report generation."""
        request = ReportRequest(
            report_type=ReportType.TRANSACTION_HISTORY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.JSON,
            include_details=False
        )
        
        # Mock transaction report data
        mock_report_data = {'transaction_data': 'test'}
        report_generator.transaction_report.generate_data.return_value = mock_report_data
        
        # Mock export
        mock_file_path = '/path/to/transaction_report.json'
        report_generator.export_manager.export_report.return_value = mock_file_path
        
        # Generate report
        metadata = report_generator.generate_report(request)
        
        # Verify results
        assert metadata.report_type == ReportType.TRANSACTION_HISTORY
        assert metadata.status == "completed"
        
        # Verify transaction report was called
        report_generator.transaction_report.generate_data.assert_called_once_with(
            start_date=request.start_date,
            end_date=request.end_date,
            symbols=request.symbols,
            include_details=request.include_details
        )
    
    def test_generate_report_unsupported_type(self, report_generator):
        """Test report generation with unsupported type."""
        # Create a mock request with unsupported type
        request = ReportRequest(
            report_type=ReportType.PORTFOLIO_SUMMARY,  # Not implemented
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.PDF
        )
        
        with pytest.raises(RuntimeError, match="Report generation failed"):
            report_generator.generate_report(request)
    
    def test_get_report_status(self, report_generator, sample_report_request):
        """Test getting report status."""
        # Generate a report first
        mock_report_data = {'test': 'data'}
        report_generator.performance_report.generate_data.return_value = mock_report_data
        report_generator.export_manager.export_report.return_value = '/path/to/report.pdf'
        
        metadata = report_generator.generate_report(sample_report_request)
        
        # Get status
        status = report_generator.get_report_status(metadata.report_id)
        
        assert status is not None
        assert status.report_id == metadata.report_id
        assert status.status == "completed"
    
    def test_get_report_status_not_found(self, report_generator):
        """Test getting status for non-existent report."""
        status = report_generator.get_report_status("non_existent_id")
        assert status is None
    
    def test_list_reports_empty(self, report_generator):
        """Test listing reports when none exist."""
        reports = report_generator.list_reports()
        assert reports == []
    
    def test_list_reports_with_filter(self, report_generator, sample_report_request):
        """Test listing reports with filters."""
        # Generate multiple reports
        mock_report_data = {'test': 'data'}
        report_generator.performance_report.generate_data.return_value = mock_report_data
        report_generator.export_manager.export_report.return_value = '/path/to/report.pdf'
        
        # Performance report
        perf_metadata = report_generator.generate_report(sample_report_request)
        
        # Tax report
        tax_request = ReportRequest(
            report_type=ReportType.TAX_SUMMARY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.CSV
        )
        report_generator.tax_report.generate_data.return_value = mock_report_data
        tax_metadata = report_generator.generate_report(tax_request)
        
        # List all reports
        all_reports = report_generator.list_reports()
        assert len(all_reports) == 2
        
        # Filter by type
        perf_reports = report_generator.list_reports(report_type=ReportType.PERFORMANCE)
        assert len(perf_reports) == 1
        assert perf_reports[0].report_type == ReportType.PERFORMANCE
        
        tax_reports = report_generator.list_reports(report_type=ReportType.TAX_SUMMARY)
        assert len(tax_reports) == 1
        assert tax_reports[0].report_type == ReportType.TAX_SUMMARY
    
    def test_generate_report_id(self, report_generator, sample_report_request):
        """Test report ID generation."""
        report_id = report_generator._generate_report_id(sample_report_request)
        
        assert isinstance(report_id, str)
        assert sample_report_request.report_type.value in report_id
        assert len(report_id) > len(sample_report_request.report_type.value)
    
    def test_validate_request_valid(self, report_generator, sample_report_request):
        """Test request validation with valid request."""
        # Should not raise any exception
        report_generator._validate_request(sample_report_request)
    
    def test_export_report_call(self, report_generator, sample_report_request):
        """Test export report method call."""
        mock_report_data = {'test': 'data'}
        
        file_path = report_generator._export_report(
            sample_report_request, mock_report_data
        )
        
        # Verify export manager was called
        report_generator.export_manager.export_report.assert_called_once_with(
            report_data=mock_report_data,
            report_type=sample_report_request.report_type,
            format=sample_report_request.format,
            output_path=sample_report_request.output_path,
            include_charts=sample_report_request.include_charts
        )
    
    def test_deliver_report(self, report_generator, sample_report_request):
        """Test report delivery logging."""
        sample_report_request.email_recipients = ['test@example.com']
        
        # Should not raise exception, just log
        report_generator._deliver_report(sample_report_request, '/path/to/report.pdf')
    
    @patch('financial_portfolio_automation.reporting.report_generator.datetime')
    def test_generate_report_timing(self, mock_datetime, report_generator, 
                                   sample_report_request):
        """Test report generation timing calculation."""
        # Mock datetime to control timing
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 0, 5)  # 5 seconds later
        
        mock_datetime.now.side_effect = [start_time, end_time]
        
        # Mock dependencies
        mock_report_data = {'test': 'data'}
        report_generator.performance_report.generate_data.return_value = mock_report_data
        report_generator.export_manager.export_report.return_value = '/path/to/report.pdf'
        
        # Generate report
        metadata = report_generator.generate_report(sample_report_request)
        
        # Verify timing
        assert metadata.generation_time_seconds == 5.0