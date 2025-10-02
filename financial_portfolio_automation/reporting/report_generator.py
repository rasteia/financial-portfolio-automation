"""
Report Generator - Unified interface for all report types.

This module provides a centralized report generation system that coordinates
different report types and manages output formatting and delivery.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import logging

from ..models.core import PortfolioSnapshot, Position, Order
from ..data.store import DataStore
from ..analysis.portfolio_analyzer import PortfolioAnalyzer
from ..execution.trade_logger import TradeLogger
from .types import ReportType, ReportFormat
from .performance_report import PerformanceReport
from .tax_report import TaxReport
from .transaction_report import TransactionReport


@dataclass
class ReportRequest:
    """Report generation request configuration."""
    report_type: ReportType
    start_date: date
    end_date: date
    format: ReportFormat = ReportFormat.PDF
    include_charts: bool = True
    include_details: bool = True
    symbols: Optional[List[str]] = None
    benchmark_symbol: Optional[str] = None
    output_path: Optional[str] = None
    email_recipients: Optional[List[str]] = None


@dataclass
class ReportMetadata:
    """Report generation metadata."""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    start_date: date
    end_date: date
    format: ReportFormat
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    generation_time_seconds: Optional[float] = None
    status: str = "pending"
    error_message: Optional[str] = None


class ReportGenerator:
    """
    Unified report generation system.
    
    Coordinates different report types and manages output formatting,
    template processing, and delivery mechanisms.
    """
    
    def __init__(
        self,
        data_store: DataStore,
        portfolio_analyzer: PortfolioAnalyzer,
        trade_logger: TradeLogger,
        export_manager: Optional['ExportManager'] = None
    ):
        """
        Initialize report generator.
        
        Args:
            data_store: Data storage interface
            portfolio_analyzer: Portfolio analysis engine
            trade_logger: Trade logging system
            export_manager: Export management system
        """
        self.data_store = data_store
        self.portfolio_analyzer = portfolio_analyzer
        self.trade_logger = trade_logger
        if export_manager is None:
            from .export_manager import ExportManager
            self.export_manager = ExportManager()
        else:
            self.export_manager = export_manager
        
        # Initialize report generators
        self.performance_report = PerformanceReport(
            data_store, portfolio_analyzer
        )
        self.tax_report = TaxReport(data_store, trade_logger)
        self.transaction_report = TransactionReport(
            data_store, trade_logger
        )
        
        self.logger = logging.getLogger(__name__)
        self._report_cache: Dict[str, ReportMetadata] = {}
    
    def generate_report(self, request: ReportRequest) -> ReportMetadata:
        """
        Generate a report based on the request configuration.
        
        Args:
            request: Report generation request
            
        Returns:
            Report metadata with generation results
            
        Raises:
            ValueError: If request parameters are invalid
            RuntimeError: If report generation fails
        """
        start_time = datetime.now()
        report_id = self._generate_report_id(request)
        
        metadata = ReportMetadata(
            report_id=report_id,
            report_type=request.report_type,
            generated_at=start_time,
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format
        )
        
        try:
            self.logger.info(f"Starting report generation: {report_id}")
            
            # Validate request
            self._validate_request(request)
            
            # Generate report data
            report_data = self._generate_report_data(request)
            
            # Format and export report
            file_path = self._export_report(request, report_data)
            
            # Update metadata
            end_time = datetime.now()
            metadata.file_path = file_path
            metadata.generation_time_seconds = (
                end_time - start_time
            ).total_seconds()
            metadata.status = "completed"
            
            # Handle delivery if requested
            if request.email_recipients:
                self._deliver_report(request, file_path)
            
            self._report_cache[report_id] = metadata
            self.logger.info(f"Report generation completed: {report_id}")
            
        except Exception as e:
            metadata.status = "failed"
            metadata.error_message = str(e)
            self._report_cache[report_id] = metadata
            self.logger.error(f"Report generation failed: {report_id} - {e}")
            raise RuntimeError(f"Report generation failed: {e}") from e
        
        return metadata
    
    def get_report_status(self, report_id: str) -> Optional[ReportMetadata]:
        """
        Get report generation status and metadata.
        
        Args:
            report_id: Report identifier
            
        Returns:
            Report metadata if found, None otherwise
        """
        return self._report_cache.get(report_id)
    
    def list_reports(
        self,
        report_type: Optional[ReportType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[ReportMetadata]:
        """
        List generated reports with optional filtering.
        
        Args:
            report_type: Filter by report type
            start_date: Filter by generation date (from)
            end_date: Filter by generation date (to)
            
        Returns:
            List of matching report metadata
        """
        reports = list(self._report_cache.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        if start_date:
            reports = [
                r for r in reports 
                if r.generated_at.date() >= start_date
            ]
        
        if end_date:
            reports = [
                r for r in reports 
                if r.generated_at.date() <= end_date
            ]
        
        return sorted(reports, key=lambda r: r.generated_at, reverse=True)
    
    def _validate_request(self, request: ReportRequest) -> None:
        """Validate report request parameters."""
        if request.start_date > request.end_date:
            raise ValueError("Start date must be before end date")
        
        if request.end_date > date.today():
            raise ValueError("End date cannot be in the future")
        
        # Validate date range based on report type
        date_range = (request.end_date - request.start_date).days
        
        if request.report_type == ReportType.TAX_SUMMARY and date_range > 366:
            raise ValueError("Tax reports limited to 1 year maximum")
        
        if request.symbols:
            # Validate symbol format
            for symbol in request.symbols:
                if not symbol or not symbol.isalnum():
                    raise ValueError(f"Invalid symbol format: {symbol}")
    
    def _generate_report_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate report data based on request type."""
        if request.report_type == ReportType.PERFORMANCE:
            return self.performance_report.generate_data(
                start_date=request.start_date,
                end_date=request.end_date,
                symbols=request.symbols,
                benchmark_symbol=request.benchmark_symbol,
                include_charts=request.include_charts
            )
        
        elif request.report_type == ReportType.TAX_SUMMARY:
            return self.tax_report.generate_data(
                start_date=request.start_date,
                end_date=request.end_date,
                symbols=request.symbols
            )
        
        elif request.report_type == ReportType.TRANSACTION_HISTORY:
            return self.transaction_report.generate_data(
                start_date=request.start_date,
                end_date=request.end_date,
                symbols=request.symbols,
                include_details=request.include_details
            )
        
        else:
            raise ValueError(f"Unsupported report type: {request.report_type}")
    
    def _export_report(
        self, 
        request: ReportRequest, 
        report_data: Dict[str, Any]
    ) -> str:
        """Export report data to specified format."""
        return self.export_manager.export_report(
            report_data=report_data,
            report_type=request.report_type,
            format=request.format,
            output_path=request.output_path,
            include_charts=request.include_charts
        )
    
    def _deliver_report(self, request: ReportRequest, file_path: str) -> None:
        """Deliver report to specified recipients."""
        # This would integrate with the notification system
        # For now, just log the delivery request
        self.logger.info(
            f"Report delivery requested to {request.email_recipients}: "
            f"{file_path}"
        )
    
    def _generate_report_id(self, request: ReportRequest) -> str:
        """Generate unique report identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{request.report_type.value}_{timestamp}"