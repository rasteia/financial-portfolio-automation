"""
MCP Tool Server implementation for portfolio management AI assistant integration.

This module implements the Model Context Protocol (MCP) server that exposes
portfolio management functions as tools for AI assistants.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import asyncio

from ..exceptions import PortfolioAutomationError
from .portfolio_tools import PortfolioTools
from .analysis_tools import AnalysisTools
from .market_data_tools import MarketDataTools
from .reporting_tools import ReportingTools
from .strategy_tools import StrategyTools


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool with metadata."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    category: str
    requires_auth: bool = True
    risk_level: str = "low"  # low, medium, high


@dataclass
class MCPResponse:
    """Standard MCP response format."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class MCPToolServer:
    """
    MCP Tool Server for portfolio management AI assistant integration.
    
    Provides a comprehensive set of tools for AI assistants to:
    - Access real-time portfolio data and analysis
    - Execute trades with safety controls
    - Monitor portfolio performance and risk
    - Generate reports and perform backtesting
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP Tool Server.
        
        Args:
            config: Configuration dictionary containing:
                - alpaca_config: Alpaca API configuration
                - risk_limits: Risk management limits
                - auth_config: Authentication configuration
                - tool_config: Tool-specific configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, MCPToolDefinition] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize tool modules
        self.portfolio_tools = PortfolioTools(config)
        self.analysis_tools = AnalysisTools(config)
        self.market_data_tools = MarketDataTools(config)
        self.reporting_tools = ReportingTools(config)
        self.strategy_tools = StrategyTools(config)
        
        # Register all tools
        self._register_tools()
        
        self.logger.info(f"MCP Tool Server initialized with {len(self.tools)} tools")
    
    def _register_tools(self):
        """Register all available tools with the MCP server."""
        # Portfolio management tools
        self._register_portfolio_tools()
        
        # Analysis tools
        self._register_analysis_tools()
        
        # Market data tools
        self._register_market_data_tools()
        
        # Reporting tools
        self._register_reporting_tools()
        
        # Strategy tools
        self._register_strategy_tools()
    
    def _register_portfolio_tools(self):
        """Register portfolio management tools."""
        tools = [
            MCPToolDefinition(
                name="get_portfolio_summary",
                description="Get current portfolio summary including value, positions, and allocation",
                parameters={
                    "type": "object",
                    "properties": {
                        "include_positions": {
                            "type": "boolean",
                            "description": "Include detailed position information",
                            "default": True
                        },
                        "include_performance": {
                            "type": "boolean", 
                            "description": "Include performance metrics",
                            "default": True
                        }
                    }
                },
                handler=self.portfolio_tools.get_portfolio_summary,
                category="portfolio",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="get_portfolio_performance",
                description="Get portfolio performance metrics for specified time period",
                parameters={
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "description": "Time period (1d, 1w, 1m, 3m, 6m, 1y, ytd, all)",
                            "default": "1m"
                        },
                        "benchmark": {
                            "type": "string",
                            "description": "Benchmark symbol for comparison (e.g., SPY)",
                            "default": "SPY"
                        }
                    }
                },
                handler=self.portfolio_tools.get_portfolio_performance,
                category="portfolio",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="analyze_portfolio_risk",
                description="Analyze portfolio risk metrics including VaR, concentration, and volatility",
                parameters={
                    "type": "object",
                    "properties": {
                        "confidence_level": {
                            "type": "number",
                            "description": "Confidence level for VaR calculation (0.90, 0.95, 0.99)",
                            "default": 0.95
                        },
                        "time_horizon": {
                            "type": "integer",
                            "description": "Time horizon in days for risk calculation",
                            "default": 1
                        }
                    }
                },
                handler=self.portfolio_tools.analyze_portfolio_risk,
                category="portfolio",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="get_asset_allocation",
                description="Get detailed asset allocation breakdown by sector, asset type, and geography",
                parameters={
                    "type": "object",
                    "properties": {
                        "breakdown_type": {
                            "type": "string",
                            "description": "Type of breakdown (sector, asset_type, geography, all)",
                            "default": "all"
                        }
                    }
                },
                handler=self.portfolio_tools.get_asset_allocation,
                category="portfolio",
                risk_level="low"
            )
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
    
    def _register_analysis_tools(self):
        """Register analysis tools."""
        tools = [
            MCPToolDefinition(
                name="analyze_technical_indicators",
                description="Calculate technical indicators for specified symbols",
                parameters={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of symbols to analyze"
                        },
                        "indicators": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of indicators (sma, ema, rsi, macd, bollinger, etc.)",
                            "default": ["sma", "rsi", "macd"]
                        },
                        "period": {
                            "type": "string",
                            "description": "Time period for analysis (1d, 1w, 1m)",
                            "default": "1m"
                        }
                    },
                    "required": ["symbols"]
                },
                handler=self.analysis_tools.analyze_technical_indicators,
                category="analysis",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="compare_with_benchmark",
                description="Compare portfolio performance with benchmark indices",
                parameters={
                    "type": "object",
                    "properties": {
                        "benchmarks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of benchmark symbols",
                            "default": ["SPY", "QQQ", "IWM"]
                        },
                        "period": {
                            "type": "string",
                            "description": "Comparison period",
                            "default": "1y"
                        },
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to compare",
                            "default": ["return", "volatility", "sharpe", "beta"]
                        }
                    }
                },
                handler=self.analysis_tools.compare_with_benchmark,
                category="analysis",
                risk_level="low"
            )
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
    
    def _register_market_data_tools(self):
        """Register market data tools."""
        tools = [
            MCPToolDefinition(
                name="get_market_data",
                description="Get real-time and historical market data for symbols",
                parameters={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of symbols"
                        },
                        "data_type": {
                            "type": "string",
                            "description": "Type of data (quotes, trades, bars, all)",
                            "default": "quotes"
                        },
                        "timeframe": {
                            "type": "string",
                            "description": "Timeframe for historical data (1min, 5min, 15min, 1hour, 1day)",
                            "default": "1day"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of data points to retrieve",
                            "default": 100
                        }
                    },
                    "required": ["symbols"]
                },
                handler=self.market_data_tools.get_market_data,
                category="market_data",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="get_market_trends",
                description="Analyze market trends and identify patterns",
                parameters={
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of symbols to analyze"
                        },
                        "analysis_type": {
                            "type": "string",
                            "description": "Type of trend analysis (momentum, mean_reversion, breakout)",
                            "default": "momentum"
                        },
                        "period": {
                            "type": "string",
                            "description": "Analysis period",
                            "default": "1m"
                        }
                    },
                    "required": ["symbols"]
                },
                handler=self.market_data_tools.get_market_trends,
                category="market_data",
                risk_level="low"
            )
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
    
    def _register_reporting_tools(self):
        """Register reporting tools."""
        tools = [
            MCPToolDefinition(
                name="generate_performance_report",
                description="Generate comprehensive portfolio performance report",
                parameters={
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Report format (json, html, pdf, csv)",
                            "default": "json"
                        },
                        "period": {
                            "type": "string",
                            "description": "Report period",
                            "default": "1m"
                        },
                        "include_charts": {
                            "type": "boolean",
                            "description": "Include performance charts",
                            "default": False
                        }
                    }
                },
                handler=self.reporting_tools.generate_performance_report,
                category="reporting",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="generate_tax_report",
                description="Generate tax report with realized gains/losses",
                parameters={
                    "type": "object",
                    "properties": {
                        "tax_year": {
                            "type": "integer",
                            "description": "Tax year for report",
                            "default": datetime.now().year
                        },
                        "format": {
                            "type": "string",
                            "description": "Report format",
                            "default": "json"
                        }
                    }
                },
                handler=self.reporting_tools.generate_tax_report,
                category="reporting",
                risk_level="low"
            ),
            MCPToolDefinition(
                name="get_dashboard_data",
                description="Get real-time dashboard data optimized for AI consumption",
                parameters={
                    "type": "object",
                    "properties": {
                        "refresh_cache": {
                            "type": "boolean",
                            "description": "Force refresh of cached data",
                            "default": False
                        }
                    }
                },
                handler=self.reporting_tools.get_dashboard_data,
                category="reporting",
                risk_level="low"
            )
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
    
    def _register_strategy_tools(self):
        """Register strategy tools."""
        tools = [
            MCPToolDefinition(
                name="backtest_strategy",
                description="Backtest trading strategy with historical data",
                parameters={
                    "type": "object",
                    "properties": {
                        "strategy_config": {
                            "type": "object",
                            "description": "Strategy configuration parameters"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Backtest start date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Backtest end date (YYYY-MM-DD)"
                        },
                        "initial_capital": {
                            "type": "number",
                            "description": "Initial capital for backtest",
                            "default": 100000
                        }
                    },
                    "required": ["strategy_config", "start_date", "end_date"]
                },
                handler=self.strategy_tools.backtest_strategy,
                category="strategy",
                risk_level="medium"
            ),
            MCPToolDefinition(
                name="optimize_strategy_parameters",
                description="Optimize strategy parameters using historical data",
                parameters={
                    "type": "object",
                    "properties": {
                        "strategy_type": {
                            "type": "string",
                            "description": "Type of strategy to optimize"
                        },
                        "parameter_ranges": {
                            "type": "object",
                            "description": "Parameter ranges for optimization"
                        },
                        "optimization_metric": {
                            "type": "string",
                            "description": "Metric to optimize (sharpe, return, max_drawdown)",
                            "default": "sharpe"
                        }
                    },
                    "required": ["strategy_type", "parameter_ranges"]
                },
                handler=self.strategy_tools.optimize_strategy_parameters,
                category="strategy",
                risk_level="medium"
            )
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                          session_id: Optional[str] = None) -> MCPResponse:
        """
        Execute an MCP tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            session_id: Optional session ID for authentication
            
        Returns:
            MCPResponse with execution results
        """
        try:
            # Validate tool exists
            if tool_name not in self.tools:
                return MCPResponse(
                    success=False,
                    error=f"Tool '{tool_name}' not found"
                )
            
            tool = self.tools[tool_name]
            
            # Validate authentication if required
            if tool.requires_auth and not self._validate_session(session_id):
                return MCPResponse(
                    success=False,
                    error="Authentication required"
                )
            
            # Validate parameters
            validation_error = self._validate_parameters(tool, parameters)
            if validation_error:
                return MCPResponse(
                    success=False,
                    error=validation_error
                )
            
            # Execute tool
            self.logger.info(f"Executing tool: {tool_name}")
            result = await self._execute_tool_handler(tool, parameters)
            
            return MCPResponse(
                success=True,
                data=result
            )
            
        except Exception as e:
            self.logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return MCPResponse(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )
    
    async def _execute_tool_handler(self, tool: MCPToolDefinition, 
                                   parameters: Dict[str, Any]) -> Any:
        """Execute the tool handler function."""
        try:
            if asyncio.iscoroutinefunction(tool.handler):
                result = await tool.handler(**parameters)
            else:
                result = tool.handler(**parameters)
            
            # If result is a coroutine that wasn't awaited, await it
            if asyncio.iscoroutine(result):
                result = await result
                
            return result
        except Exception as e:
            self.logger.error(f"Tool handler execution failed: {str(e)}")
            raise
    
    def _validate_session(self, session_id: Optional[str]) -> bool:
        """Validate session authentication."""
        if not session_id:
            return False
        
        # For now, simple session validation
        # In production, implement proper JWT or session token validation
        return session_id in self.sessions
    
    def _validate_parameters(self, tool: MCPToolDefinition, 
                           parameters: Dict[str, Any]) -> Optional[str]:
        """Validate tool parameters against schema."""
        # Basic parameter validation
        # In production, use jsonschema for comprehensive validation
        required_params = tool.parameters.get("required", [])
        
        for param in required_params:
            if param not in parameters:
                return f"Required parameter '{param}' missing"
        
        return None
    
    def create_session(self, auth_token: str) -> str:
        """Create authenticated session."""
        # Simple session creation - in production use proper authentication
        session_id = f"session_{len(self.sessions)}"
        self.sessions[session_id] = {
            "auth_token": auth_token,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        return session_id
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for MCP client discovery."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "category": tool.category,
                "risk_level": tool.risk_level
            }
            for tool in self.tools.values()
        ]
    
    def get_tool_categories(self) -> Dict[str, List[str]]:
        """Get tools organized by category."""
        categories = {}
        for tool in self.tools.values():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool.name)
        return categories
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of MCP server and connected services."""
        return {
            "status": "healthy",
            "tools_registered": len(self.tools),
            "active_sessions": len(self.sessions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "portfolio_tools": self.portfolio_tools.health_check(),
                "analysis_tools": self.analysis_tools.health_check(),
                "market_data_tools": self.market_data_tools.health_check(),
                "reporting_tools": self.reporting_tools.health_check(),
                "strategy_tools": self.strategy_tools.health_check()
            }
        }