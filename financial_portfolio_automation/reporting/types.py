"""
Common types and enums for the reporting module.
"""

from enum import Enum


class ReportType(Enum):
    """Available report types."""
    PERFORMANCE = "performance"
    TAX_SUMMARY = "tax_summary"
    TRANSACTION_HISTORY = "transaction_history"
    PORTFOLIO_SUMMARY = "portfolio_summary"
    RISK_ANALYSIS = "risk_analysis"


class ReportFormat(Enum):
    """Available report output formats."""
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"