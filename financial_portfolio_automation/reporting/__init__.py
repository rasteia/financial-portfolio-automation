"""
Reporting module for portfolio performance, tax, and transaction reports.

This module provides comprehensive reporting capabilities including:
- Portfolio performance reports with risk-adjusted metrics
- Tax reporting with realized gains/losses and wash sale detection
- Transaction history reports with execution analysis
- Multi-format export capabilities (PDF, HTML, CSV, JSON)
"""

from .types import ReportType, ReportFormat
from .report_generator import ReportGenerator
from .performance_report import PerformanceReport
from .tax_report import TaxReport
from .transaction_report import TransactionReport
from .export_manager import ExportManager

__all__ = [
    'ReportType',
    'ReportFormat',
    'ReportGenerator',
    'PerformanceReport', 
    'TaxReport',
    'TransactionReport',
    'ExportManager'
]