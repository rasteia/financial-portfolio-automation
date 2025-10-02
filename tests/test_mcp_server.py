"""
Unit tests for MCP Tool Server.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from financial_portfolio_automation.mcp.mcp_server import MCPToolServer, MCPResponse, MCPToolDefinition
from financial_portfolio_automation.exceptions import PortfolioAutomationError


class TestMCPToolServer:
    """Test cases for MCP Tool Server."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'alpaca_config': {
                'api_key': 'test_key',
                'secret_key': 'test_secret',
                'base_url': 'https://paper-api.alpaca.markets'
            },
            'risk_limits': {
                'max_position_size': 10000,
                'max_portfolio_concentration': 0.2
            },
            'auth_config': {
                'enabled': True
            },
            'tool_config': {
                'rate_limit': 100
            }
        }
    
    @pytest.fixture
    def mcp_server(self, mock_config):
        """Create MCP server instance for testing."""
        with patch('financial_portfolio_automation.mcp.mcp_server.PortfolioTools'), \
             patch('financial_portfolio_automation.mcp.mcp_server.AnalysisTools'), \
             patch('financial_portfolio_automation.mcp.mcp_server.MarketDataTools'), \
             patch('financial_portfolio_automation.mcp.mcp_server.ReportingTools'), \
             patch('financial_portfolio_automation.mcp.mcp_server.StrategyTools'):
            return MCPToolServer(mock_config)
    
    def test_mcp_server_initialization(self, mcp_server):
        """Test MCP server initialization."""
        assert mcp_server.config is not None
        assert len(mcp_server.tools) > 0
        assert mcp_server.portfolio_tools is not None
        assert mcp_server.analysis_tools is not None
        assert mcp_server.market_data_tools is not None
        assert mcp_server.reporting_tools is not None
        assert mcp_server.strategy_tools is not None
    
    def test_tool_registration(self, mcp_server):
        """Test that tools are properly registered."""
        # Check that portfolio tools are registered
        assert 'get_portfolio_summary' in mcp_server.tools
        assert 'get_portfolio_performance' in mcp_server.tools
        assert 'analyze_portfolio_risk' in mcp_server.tools
        
        # Check that analysis tools are registered
        assert 'analyze_technical_indicators' in mcp_server.tools
        assert 'compare_with_benchmark' in mcp_server.tools
        
        # Check that market data tools are registered
        assert 'get_market_data' in mcp_server.tools
        assert 'get_market_trends' in mcp_server.tools
        
        # Check that reporting tools are registered
        assert 'generate_performance_report' in mcp_server.tools
        assert 'generate_tax_report' in mcp_server.tools
        
        # Check that strategy tools are registered
        assert 'backtest_strategy' in mcp_server.tools
        assert 'optimize_strategy_parameters' in mcp_server.tools
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self, mcp_server):
        """Test successful tool execution."""
        # Mock the portfolio tools method
        mock_result = {'portfolio_value': 100000, 'positions': []}
        mcp_server.portfolio_tools.get_portfolio_summary = AsyncMock(return_value=mock_result)
        
        # Create session
        session_id = mcp_server.create_session('test_token')
        
        # Execute tool
        response = await mcp_server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True},
            session_id=session_id
        )
        
        assert response.success is True
        assert response.data == mock_result
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, mcp_server):
        """Test execution of non-existent tool."""
        session_id = mcp_server.create_session('test_token')
        
        response = await mcp_server.execute_tool(
            tool_name='non_existent_tool',
            parameters={},
            session_id=session_id
        )
        
        assert response.success is False
        assert "Tool 'non_existent_tool' not found" in response.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_authentication_required(self, mcp_server):
        """Test tool execution without authentication."""
        response = await mcp_server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True},
            session_id=None
        )
        
        assert response.success is False
        assert "Authentication required" in response.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_missing_parameters(self, mcp_server):
        """Test tool execution with missing required parameters."""
        session_id = mcp_server.create_session('test_token')
        
        response = await mcp_server.execute_tool(
            tool_name='analyze_technical_indicators',
            parameters={},  # Missing required 'symbols' parameter
            session_id=session_id
        )
        
        assert response.success is False
        assert "Required parameter 'symbols' missing" in response.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_handler_exception(self, mcp_server):
        """Test tool execution when handler raises exception."""
        # Mock the portfolio tools method to raise exception
        mcp_server.portfolio_tools.get_portfolio_summary = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        session_id = mcp_server.create_session('test_token')
        
        response = await mcp_server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True},
            session_id=session_id
        )
        
        assert response.success is False
        assert "Tool execution failed: Test error" in response.error
    
    def test_create_session(self, mcp_server):
        """Test session creation."""
        session_id = mcp_server.create_session('test_token')
        
        assert session_id in mcp_server.sessions
        assert mcp_server.sessions[session_id]['auth_token'] == 'test_token'
        assert 'created_at' in mcp_server.sessions[session_id]
        assert 'last_activity' in mcp_server.sessions[session_id]
    
    def test_get_tool_definitions(self, mcp_server):
        """Test getting tool definitions."""
        definitions = mcp_server.get_tool_definitions()
        
        assert isinstance(definitions, list)
        assert len(definitions) > 0
        
        # Check structure of first definition
        first_def = definitions[0]
        assert 'name' in first_def
        assert 'description' in first_def
        assert 'parameters' in first_def
        assert 'category' in first_def
        assert 'risk_level' in first_def
    
    def test_get_tool_categories(self, mcp_server):
        """Test getting tools organized by category."""
        categories = mcp_server.get_tool_categories()
        
        assert isinstance(categories, dict)
        assert 'portfolio' in categories
        assert 'analysis' in categories
        assert 'market_data' in categories
        assert 'reporting' in categories
        assert 'strategy' in categories
        
        # Check that each category has tools
        for category, tools in categories.items():
            assert isinstance(tools, list)
            assert len(tools) > 0
    
    def test_health_check(self, mcp_server):
        """Test health check functionality."""
        # Mock health check methods
        mcp_server.portfolio_tools.health_check = Mock(return_value={'status': 'healthy'})
        mcp_server.analysis_tools.health_check = Mock(return_value={'status': 'healthy'})
        mcp_server.market_data_tools.health_check = Mock(return_value={'status': 'healthy'})
        mcp_server.reporting_tools.health_check = Mock(return_value={'status': 'healthy'})
        mcp_server.strategy_tools.health_check = Mock(return_value={'status': 'healthy'})
        
        health_status = mcp_server.health_check()
        
        assert health_status['status'] == 'healthy'
        assert 'tools_registered' in health_status
        assert 'active_sessions' in health_status
        assert 'timestamp' in health_status
        assert 'services' in health_status
        
        # Check that all services are included
        services = health_status['services']
        assert 'portfolio_tools' in services
        assert 'analysis_tools' in services
        assert 'market_data_tools' in services
        assert 'reporting_tools' in services
        assert 'strategy_tools' in services


class TestMCPResponse:
    """Test cases for MCP Response."""
    
    def test_mcp_response_creation(self):
        """Test MCP response creation."""
        response = MCPResponse(success=True, data={'test': 'data'})
        
        assert response.success is True
        assert response.data == {'test': 'data'}
        assert response.error is None
        assert response.timestamp is not None
    
    def test_mcp_response_to_dict(self):
        """Test MCP response serialization."""
        response = MCPResponse(success=False, error='Test error')
        response_dict = response.to_dict()
        
        assert response_dict['success'] is False
        assert response_dict['error'] == 'Test error'
        assert response_dict['data'] is None
        assert 'timestamp' in response_dict
        assert isinstance(response_dict['timestamp'], str)


class TestMCPToolDefinition:
    """Test cases for MCP Tool Definition."""
    
    def test_tool_definition_creation(self):
        """Test tool definition creation."""
        def mock_handler():
            return "test"
        
        tool_def = MCPToolDefinition(
            name="test_tool",
            description="Test tool description",
            parameters={"type": "object"},
            handler=mock_handler,
            category="test",
            requires_auth=True,
            risk_level="low"
        )
        
        assert tool_def.name == "test_tool"
        assert tool_def.description == "Test tool description"
        assert tool_def.parameters == {"type": "object"}
        assert tool_def.handler == mock_handler
        assert tool_def.category == "test"
        assert tool_def.requires_auth is True
        assert tool_def.risk_level == "low"


if __name__ == '__main__':
    pytest.main([__file__])