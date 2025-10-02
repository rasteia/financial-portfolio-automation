"""
Integration tests for MCP Tool Server.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from financial_portfolio_automation.mcp.mcp_server import MCPToolServer
from financial_portfolio_automation.exceptions import PortfolioAutomationError


class TestMCPIntegration:
    """Integration test cases for MCP Tool Server."""
    
    @pytest.fixture
    def integration_config(self):
        """Integration test configuration."""
        return {
            'alpaca_config': {
                'api_key': 'test_key',
                'secret_key': 'test_secret',
                'base_url': 'https://paper-api.alpaca.markets'
            },
            'risk_limits': {
                'max_position_size': 10000,
                'max_portfolio_concentration': 0.2,
                'max_daily_loss': 5000
            },
            'auth_config': {
                'enabled': True,
                'session_timeout': 3600
            },
            'tool_config': {
                'rate_limit': 100,
                'cache_ttl': 300
            },
            'cache_config': {
                'ttl': 300,
                'max_size': 1000
            }
        }
    
    @pytest.fixture
    def mcp_server_integration(self, integration_config):
        """Create MCP server for integration testing."""
        with patch('financial_portfolio_automation.mcp.portfolio_tools.AnalyticsService'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.PortfolioAnalyzer'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.RiskManager'), \
             patch('financial_portfolio_automation.mcp.portfolio_tools.AlpacaClient'), \
             patch('financial_portfolio_automation.mcp.analysis_tools.TechnicalAnalysis'), \
             patch('financial_portfolio_automation.mcp.analysis_tools.PortfolioAnalyzer'), \
             patch('financial_portfolio_automation.mcp.analysis_tools.MarketDataClient'), \
             patch('financial_portfolio_automation.mcp.market_data_tools.MarketDataClient'), \
             patch('financial_portfolio_automation.mcp.market_data_tools.WebSocketHandler'), \
             patch('financial_portfolio_automation.mcp.market_data_tools.DataCache'), \
             patch('financial_portfolio_automation.mcp.reporting_tools.ReportGenerator'), \
             patch('financial_portfolio_automation.mcp.reporting_tools.PerformanceReport'), \
             patch('financial_portfolio_automation.mcp.reporting_tools.TaxReport'), \
             patch('financial_portfolio_automation.mcp.reporting_tools.TransactionReport'), \
             patch('financial_portfolio_automation.mcp.reporting_tools.AnalyticsService'), \
             patch('financial_portfolio_automation.mcp.strategy_tools.Backtester'), \
             patch('financial_portfolio_automation.mcp.strategy_tools.StrategyExecutor'), \
             patch('financial_portfolio_automation.mcp.strategy_tools.StrategyRegistry'), \
             patch('financial_portfolio_automation.mcp.strategy_tools.StrategyFactory'):
            return MCPToolServer(integration_config)
    
    @pytest.mark.asyncio
    async def test_end_to_end_portfolio_analysis_workflow(self, mcp_server_integration):
        """Test complete portfolio analysis workflow through MCP."""
        server = mcp_server_integration
        
        # Create authenticated session
        session_id = server.create_session('integration_test_token')
        
        # Mock portfolio data
        mock_portfolio_summary = {
            'portfolio_value': 150000.0,
            'buying_power': 50000.0,
            'day_pnl': 2500.0,
            'position_count': 5,
            'positions': [
                {'symbol': 'AAPL', 'quantity': 100, 'market_value': 15000},
                {'symbol': 'GOOGL', 'quantity': 50, 'market_value': 12000},
                {'symbol': 'MSFT', 'quantity': 75, 'market_value': 10000}
            ]
        }
        
        mock_performance_data = {
            'period': '1m',
            'portfolio_performance': {
                'total_return': 8.5,
                'sharpe_ratio': 1.35,
                'max_drawdown': 6.2,
                'volatility': 16.8
            },
            'benchmark_performance': {
                'total_return': 6.2,
                'sharpe_ratio': 1.15,
                'max_drawdown': 8.1
            }
        }
        
        mock_risk_analysis = {
            'risk_metrics': {
                'value_at_risk': 3500.0,
                'portfolio_volatility': 16.8,
                'portfolio_beta': 1.15
            },
            'concentration_risk': {
                'largest_position_weight': 15.0,
                'top_5_concentration': 65.0
            },
            'risk_warnings': []
        }
        
        # Set up mocks
        server.portfolio_tools.get_portfolio_summary = AsyncMock(return_value=mock_portfolio_summary)
        server.portfolio_tools.get_portfolio_performance = AsyncMock(return_value=mock_performance_data)
        server.portfolio_tools.analyze_portfolio_risk = AsyncMock(return_value=mock_risk_analysis)
        
        # Step 1: Get portfolio summary
        summary_response = await server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True, 'include_performance': True},
            session_id=session_id
        )
        
        assert summary_response.success is True
        assert summary_response.data['portfolio_value'] == 150000.0
        assert len(summary_response.data['positions']) == 3
        
        # Step 2: Get performance analysis
        performance_response = await server.execute_tool(
            tool_name='get_portfolio_performance',
            parameters={'period': '1m', 'benchmark': 'SPY'},
            session_id=session_id
        )
        
        assert performance_response.success is True
        assert performance_response.data['portfolio_performance']['total_return'] == 8.5
        
        # Step 3: Analyze risk
        risk_response = await server.execute_tool(
            tool_name='analyze_portfolio_risk',
            parameters={'confidence_level': 0.95, 'time_horizon': 1},
            session_id=session_id
        )
        
        assert risk_response.success is True
        assert risk_response.data['risk_metrics']['value_at_risk'] == 3500.0
        
        # Verify all tools were called with correct parameters
        server.portfolio_tools.get_portfolio_summary.assert_called_once()
        server.portfolio_tools.get_portfolio_performance.assert_called_once()
        server.portfolio_tools.analyze_portfolio_risk.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_technical_analysis_workflow(self, mcp_server_integration):
        """Test technical analysis workflow through MCP."""
        server = mcp_server_integration
        session_id = server.create_session('integration_test_token')
        
        # Mock technical analysis data
        mock_technical_analysis = {
            'symbols_analyzed': 2,
            'analysis_results': {
                'AAPL': {
                    'current_price': 150.25,
                    'indicators': {
                        'sma': {'sma_20': 148.5, 'sma_50': 145.2},
                        'rsi': {'current_value': 65.2},
                        'macd': {'macd_line': 2.1, 'signal': 1.8}
                    },
                    'signals': {
                        'rsi': 'neutral',
                        'macd': 'bullish',
                        'trend': 'bullish'
                    }
                },
                'GOOGL': {
                    'current_price': 2750.80,
                    'indicators': {
                        'sma': {'sma_20': 2745.3, 'sma_50': 2720.1},
                        'rsi': {'current_value': 58.7},
                        'macd': {'macd_line': 15.2, 'signal': 18.1}
                    },
                    'signals': {
                        'rsi': 'neutral',
                        'macd': 'bearish',
                        'trend': 'bullish'
                    }
                }
            }
        }
        
        mock_benchmark_comparison = {
            'benchmarks_analyzed': ['SPY', 'QQQ'],
            'portfolio_performance': {'return': 12.5, 'sharpe': 1.35},
            'benchmark_performance': {
                'SPY': {'return': 10.2, 'sharpe': 1.15},
                'QQQ': {'return': 15.8, 'sharpe': 1.42}
            },
            'performance_ranking': {
                'return': {'rank': 2, 'percentile': 66.7}
            }
        }
        
        # Set up mocks
        server.analysis_tools.analyze_technical_indicators = AsyncMock(return_value=mock_technical_analysis)
        server.analysis_tools.compare_with_benchmark = AsyncMock(return_value=mock_benchmark_comparison)
        
        # Execute technical analysis
        tech_response = await server.execute_tool(
            tool_name='analyze_technical_indicators',
            parameters={
                'symbols': ['AAPL', 'GOOGL'],
                'indicators': ['sma', 'rsi', 'macd'],
                'period': '1m'
            },
            session_id=session_id
        )
        
        assert tech_response.success is True
        assert tech_response.data['symbols_analyzed'] == 2
        assert 'AAPL' in tech_response.data['analysis_results']
        assert 'GOOGL' in tech_response.data['analysis_results']
        
        # Execute benchmark comparison
        benchmark_response = await server.execute_tool(
            tool_name='compare_with_benchmark',
            parameters={
                'benchmarks': ['SPY', 'QQQ'],
                'period': '1y',
                'metrics': ['return', 'sharpe']
            },
            session_id=session_id
        )
        
        assert benchmark_response.success is True
        assert len(benchmark_response.data['benchmarks_analyzed']) == 2
        assert benchmark_response.data['portfolio_performance']['return'] == 12.5
    
    @pytest.mark.asyncio
    async def test_reporting_workflow(self, mcp_server_integration):
        """Test reporting workflow through MCP."""
        server = mcp_server_integration
        session_id = server.create_session('integration_test_token')
        
        # Mock reporting data
        mock_performance_report = {
            'report_type': 'performance',
            'format': 'json',
            'data': {
                'performance_metrics': {
                    'total_return': 15.2,
                    'sharpe_ratio': 1.45,
                    'max_drawdown': 8.3
                }
            },
            'summary': {
                'overall_performance': 'positive',
                'key_metrics': {'total_return': 15.2},
                'highlights': ['Strong positive returns']
            }
        }
        
        mock_dashboard_data = {
            'portfolio_overview': {
                'total_value': 150000,
                'position_count': 5
            },
            'performance_metrics': {
                'day_pnl': 2500,
                'day_pnl_percent': 1.67
            },
            'insights': ['Portfolio is up significantly today'],
            'quick_facts': {
                'portfolio_value': 150000,
                'day_change': 2500
            }
        }
        
        # Set up mocks
        server.reporting_tools.generate_performance_report = AsyncMock(return_value=mock_performance_report)
        server.reporting_tools.get_dashboard_data = AsyncMock(return_value=mock_dashboard_data)
        
        # Generate performance report
        report_response = await server.execute_tool(
            tool_name='generate_performance_report',
            parameters={'format': 'json', 'period': '1m'},
            session_id=session_id
        )
        
        assert report_response.success is True
        assert report_response.data['report_type'] == 'performance'
        assert 'summary' in report_response.data
        
        # Get dashboard data
        dashboard_response = await server.execute_tool(
            tool_name='get_dashboard_data',
            parameters={'refresh_cache': False},
            session_id=session_id
        )
        
        assert dashboard_response.success is True
        assert dashboard_response.data['portfolio_overview']['total_value'] == 150000
        assert len(dashboard_response.data['insights']) > 0
    
    @pytest.mark.asyncio
    async def test_strategy_backtesting_workflow(self, mcp_server_integration):
        """Test strategy backtesting workflow through MCP."""
        server = mcp_server_integration
        session_id = server.create_session('integration_test_token')
        
        # Mock strategy data
        mock_backtest_result = {
            'strategy_name': 'Momentum Strategy',
            'strategy_type': 'momentum',
            'final_value': 125000,
            'performance_metrics': {
                'total_return': 25.0,
                'sharpe_ratio': 1.65,
                'max_drawdown': 12.3,
                'win_rate': 0.62
            },
            'summary': {
                'overall_performance': 'positive',
                'risk_level': 'moderate',
                'recommendation': 'recommended'
            }
        }
        
        mock_optimization_result = {
            'strategy_type': 'momentum',
            'best_parameters': {
                'lookback_period': 20,
                'momentum_threshold': 0.05
            },
            'best_score': 1.75,
            'insights': ['Optimization found excellent parameter combination']
        }
        
        # Set up mocks
        server.strategy_tools.backtest_strategy = AsyncMock(return_value=mock_backtest_result)
        server.strategy_tools.optimize_strategy_parameters = AsyncMock(return_value=mock_optimization_result)
        
        # Run backtest
        backtest_response = await server.execute_tool(
            tool_name='backtest_strategy',
            parameters={
                'strategy_config': {
                    'type': 'momentum',
                    'name': 'Test Momentum',
                    'parameters': {'lookback_period': 15}
                },
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'initial_capital': 100000
            },
            session_id=session_id
        )
        
        assert backtest_response.success is True
        assert backtest_response.data['final_value'] == 125000
        assert backtest_response.data['performance_metrics']['total_return'] == 25.0
        
        # Optimize parameters
        optimization_response = await server.execute_tool(
            tool_name='optimize_strategy_parameters',
            parameters={
                'strategy_type': 'momentum',
                'parameter_ranges': {
                    'lookback_period': [10, 30],
                    'momentum_threshold': [0.02, 0.08]
                },
                'optimization_metric': 'sharpe'
            },
            session_id=session_id
        )
        
        assert optimization_response.success is True
        assert optimization_response.data['best_score'] == 1.75
        assert 'best_parameters' in optimization_response.data
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, mcp_server_integration):
        """Test error handling and recovery in MCP workflows."""
        server = mcp_server_integration
        session_id = server.create_session('integration_test_token')
        
        # Test tool execution with service error
        server.portfolio_tools.get_portfolio_summary = AsyncMock(
            side_effect=Exception("Service temporarily unavailable")
        )
        
        error_response = await server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True},
            session_id=session_id
        )
        
        assert error_response.success is False
        assert "Tool execution failed" in error_response.error
        assert "Service temporarily unavailable" in error_response.error
        
        # Test recovery after fixing the service
        mock_portfolio_data = {'portfolio_value': 100000, 'positions': []}
        server.portfolio_tools.get_portfolio_summary = AsyncMock(return_value=mock_portfolio_data)
        
        recovery_response = await server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True},
            session_id=session_id
        )
        
        assert recovery_response.success is True
        assert recovery_response.data['portfolio_value'] == 100000
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, mcp_server_integration):
        """Test concurrent execution of multiple tools."""
        server = mcp_server_integration
        session_id = server.create_session('integration_test_token')
        
        # Mock responses for different tools
        server.portfolio_tools.get_portfolio_summary = AsyncMock(
            return_value={'portfolio_value': 150000}
        )
        server.market_data_tools.get_market_data = AsyncMock(
            return_value={'market_data': {'AAPL': {'quote': {'bid': 149.5, 'ask': 150.0}}}}
        )
        server.analysis_tools.analyze_technical_indicators = AsyncMock(
            return_value={'analysis_results': {'AAPL': {'current_price': 150.0}}}
        )
        
        # Execute multiple tools concurrently
        tasks = [
            server.execute_tool('get_portfolio_summary', {'include_positions': False}, session_id),
            server.execute_tool('get_market_data', {'symbols': ['AAPL'], 'data_type': 'quotes'}, session_id),
            server.execute_tool('analyze_technical_indicators', {'symbols': ['AAPL']}, session_id)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all executions succeeded
        assert all(response.success for response in responses)
        assert responses[0].data['portfolio_value'] == 150000
        assert 'AAPL' in responses[1].data['market_data']
        assert 'AAPL' in responses[2].data['analysis_results']
    
    def test_tool_discovery_and_metadata(self, mcp_server_integration):
        """Test tool discovery and metadata functionality."""
        server = mcp_server_integration
        
        # Test tool definitions
        definitions = server.get_tool_definitions()
        assert len(definitions) > 10  # Should have multiple tools registered
        
        # Verify each definition has required fields
        for definition in definitions:
            assert 'name' in definition
            assert 'description' in definition
            assert 'parameters' in definition
            assert 'category' in definition
            assert 'risk_level' in definition
        
        # Test tool categories
        categories = server.get_tool_categories()
        expected_categories = ['portfolio', 'analysis', 'market_data', 'reporting', 'strategy']
        
        for category in expected_categories:
            assert category in categories
            assert len(categories[category]) > 0
        
        # Test health check
        health_status = server.health_check()
        assert health_status['status'] == 'healthy'
        assert 'tools_registered' in health_status
        assert health_status['tools_registered'] == len(server.tools)


if __name__ == '__main__':
    pytest.main([__file__])