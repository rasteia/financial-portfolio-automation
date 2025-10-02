"""
MCP (Model Context Protocol) integration module for AI assistant access.

This module provides MCP tool integration that enables AI assistants to:
- Access real-time portfolio data and analysis
- Execute trades with comprehensive safety controls
- Monitor portfolio performance and risk metrics
- Generate reports and perform backtesting
- Optimize strategies and manage risk
"""

from .mcp_server import MCPToolServer
from .portfolio_tools import PortfolioTools
from .analysis_tools import AnalysisTools
from .market_data_tools import MarketDataTools
from .reporting_tools import ReportingTools
from .strategy_tools import StrategyTools

__all__ = [
    'MCPToolServer',
    'PortfolioTools',
    'AnalysisTools',
    'MarketDataTools',
    'ReportingTools',
    'StrategyTools'
]