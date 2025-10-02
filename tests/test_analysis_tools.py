"""
Unit tests for Analysis Tools.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from financial_portfolio_automation.mcp.analysis_tools import AnalysisTools
from financial_portfolio_automation.exceptions import PortfolioAutomationError


class TestAnalysisTools:
    """Test cases for Analysis Tools."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            'alpaca_config': {
                'api_key': 'test_key',
                'secret_key': 'test_secret',
                'base_url': 'https://paper-api.alpaca.markets'
            }
        }
    
    @pytest.fixture
    def analysis_tools(self, mock_config):
        """Create analysis tools instance for testing."""
        with patch('financial_portfolio_automation.mcp.analysis_tools.TechnicalAnalysis'), \
             patch('financial_portfolio_automation.mcp.analysis_tools.PortfolioAnalyzer'), \
             patch('financial_portfolio_automation.mcp.analysis_tools.MarketDataClient'):
            return AnalysisTools(mock_config)
    
    @pytest.fixture
    def mock_price_data(self):
        """Mock price data for testing."""
        return [
            {'timestamp': '2024-01-01', 'open': 100, 'high': 105, 'low': 98, 'close': 103, 'volume': 1000000},
            {'timestamp': '2024-01-02', 'open': 103, 'high': 108, 'low': 102, 'close': 107, 'volume': 1200000},
            {'timestamp': '2024-01-03', 'open': 107, 'high': 110, 'low': 105, 'close': 109, 'volume': 900000},
            {'timestamp': '2024-01-04', 'open': 109, 'high': 112, 'low': 107, 'close': 111, 'volume': 1100000},
            {'timestamp': '2024-01-05', 'open': 111, 'high': 115, 'low': 110, 'close': 114, 'volume': 1300000}
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_technical_indicators_success(self, analysis_tools, mock_price_data):
        """Test successful technical indicators analysis."""
        symbols = ['AAPL', 'GOOGL']
        indicators = ['sma', 'rsi', 'macd']
        
        # Mock market data client
        analysis_tools.market_data_client.get_historical_data = AsyncMock(
            return_value=mock_price_data
        )
        
        # Mock technical analysis calculations
        mock_sma_result = {'sma_20': 105.5, 'sma_50': 102.3, 'sma_200': 98.7}
        mock_rsi_result = {'current_value': 65.2, 'overbought': False, 'oversold': False}
        mock_macd_result = {'macd_line': 2.1, 'signal': 1.8, 'histogram': 0.3}
        
        analysis_tools.technical_analysis.calculate_sma = AsyncMock(return_value=mock_sma_result)
        analysis_tools.technical_analysis.calculate_rsi = AsyncMock(return_value=mock_rsi_result)
        analysis_tools.technical_analysis.calculate_macd = AsyncMock(return_value=mock_macd_result)
        
        result = await analysis_tools.analyze_technical_indicators(
            symbols=symbols,
            indicators=indicators,
            period="1m"
        )
        
        assert result['period'] == "1m"
        assert result['indicators_requested'] == indicators
        assert result['symbols_analyzed'] == 2
        
        # Check AAPL results
        aapl_result = result['analysis_results']['AAPL']
        assert aapl_result['current_price'] == 114  # Last close price
        assert 'sma' in aapl_result['indicators']
        assert 'rsi' in aapl_result['indicators']
        assert 'macd' in aapl_result['indicators']
        assert 'signals' in aapl_result
    
    @pytest.mark.asyncio
    async def test_analyze_technical_indicators_no_data(self, analysis_tools):
        """Test technical indicators analysis with no price data."""
        symbols = ['INVALID']
        
        # Mock market data client to return empty data
        analysis_tools.market_data_client.get_historical_data = AsyncMock(return_value=[])
        
        result = await analysis_tools.analyze_technical_indicators(symbols=symbols)
        
        assert result['symbols_analyzed'] == 1
        assert 'INVALID' in result['analysis_results']
        assert 'error' in result['analysis_results']['INVALID']
        assert 'No price data available' in result['analysis_results']['INVALID']['error']
    
    @pytest.mark.asyncio
    async def test_compare_with_benchmark_success(self, analysis_tools):
        """Test successful benchmark comparison."""
        benchmarks = ['SPY', 'QQQ']
        metrics = ['return', 'volatility', 'sharpe']
        
        mock_portfolio_performance = {
            'return': 15.2,
            'volatility': 18.5,
            'sharpe': 1.35,
            'beta': 1.15
        }
        
        mock_spy_performance = {
            'return': 12.0,
            'volatility': 16.0,
            'sharpe': 1.20
        }
        
        mock_qqq_performance = {
            'return': 18.5,
            'volatility': 22.0,
            'sharpe': 1.45
        }
        
        analysis_tools.portfolio_analyzer.calculate_performance_metrics = AsyncMock(
            return_value=mock_portfolio_performance
        )
        
        def mock_benchmark_performance(benchmark_symbol, **kwargs):
            if benchmark_symbol == 'SPY':
                return mock_spy_performance
            elif benchmark_symbol == 'QQQ':
                return mock_qqq_performance
            return {}
        
        analysis_tools.portfolio_analyzer.get_benchmark_performance = AsyncMock(
            side_effect=mock_benchmark_performance
        )
        
        result = await analysis_tools.compare_with_benchmark(
            benchmarks=benchmarks,
            period="1y",
            metrics=metrics
        )
        
        assert result['period'] == "1y"
        assert result['benchmarks_analyzed'] == benchmarks
        assert result['metrics_compared'] == metrics
        
        # Check portfolio performance
        assert result['portfolio_performance']['return'] == 15.2
        
        # Check benchmark performance
        assert result['benchmark_performance']['SPY']['return'] == 12.0
        assert result['benchmark_performance']['QQQ']['return'] == 18.5
        
        # Check relative performance
        assert result['relative_performance']['SPY']['return'] == 3.2  # 15.2 - 12.0
        assert result['relative_performance']['QQQ']['return'] == -3.3  # 15.2 - 18.5
        
        # Check performance ranking
        assert 'performance_ranking' in result
    
    @pytest.mark.asyncio
    async def test_analyze_sector_performance_success(self, analysis_tools):
        """Test successful sector performance analysis."""
        sectors = ['XLK', 'XLF', 'XLV']
        
        # Mock price data for each sector
        def mock_sector_data(symbol, **kwargs):
            sector_data = {
                'XLK': [
                    {'close': 100}, {'close': 105}, {'close': 108}
                ],
                'XLF': [
                    {'close': 50}, {'close': 52}, {'close': 51}
                ],
                'XLV': [
                    {'close': 80}, {'close': 82}, {'close': 85}
                ]
            }
            return sector_data.get(symbol, [])
        
        analysis_tools.market_data_client.get_historical_data = AsyncMock(
            side_effect=mock_sector_data
        )
        
        result = await analysis_tools.analyze_sector_performance(
            sectors=sectors,
            period="1m"
        )
        
        assert result['period'] == "1m"
        assert result['sectors_analyzed'] == 3
        
        # Check sector performance calculations
        assert 'XLK' in result['sector_performance']
        assert 'XLF' in result['sector_performance']
        assert 'XLV' in result['sector_performance']
        
        # XLK should have 8% return (108-100)/100
        xlk_perf = result['sector_performance']['XLK']
        assert abs(xlk_perf['total_return'] - 8.0) < 0.1
        
        # Check sector rankings
        assert 'sector_rankings' in result
        assert 'by_return' in result['sector_rankings']
        assert 'best_performer' in result['sector_rankings']
        assert 'worst_performer' in result['sector_rankings']
        
        # Check rotation analysis
        assert 'rotation_analysis' in result
    
    @pytest.mark.asyncio
    async def test_calculate_indicator_sma(self, analysis_tools):
        """Test SMA indicator calculation."""
        mock_price_data = [{'close': 100}, {'close': 105}, {'close': 110}]
        
        mock_sma_result = {'sma_20': 105.0, 'sma_50': 102.0}
        analysis_tools.technical_analysis.calculate_sma = AsyncMock(return_value=mock_sma_result)
        
        result = await analysis_tools._calculate_indicator('sma', 'AAPL', mock_price_data)
        
        assert result == mock_sma_result
        analysis_tools.technical_analysis.calculate_sma.assert_called_once_with(
            mock_price_data, periods=[20, 50, 200]
        )
    
    @pytest.mark.asyncio
    async def test_calculate_indicator_rsi(self, analysis_tools):
        """Test RSI indicator calculation."""
        mock_price_data = [{'close': 100}, {'close': 105}, {'close': 110}]
        
        mock_rsi_result = {'current_value': 65.2}
        analysis_tools.technical_analysis.calculate_rsi = AsyncMock(return_value=mock_rsi_result)
        
        result = await analysis_tools._calculate_indicator('rsi', 'AAPL', mock_price_data)
        
        assert result == mock_rsi_result
        analysis_tools.technical_analysis.calculate_rsi.assert_called_once_with(
            mock_price_data, period=14
        )
    
    @pytest.mark.asyncio
    async def test_calculate_indicator_unsupported(self, analysis_tools):
        """Test unsupported indicator calculation."""
        mock_price_data = [{'close': 100}]
        
        result = await analysis_tools._calculate_indicator('unsupported', 'AAPL', mock_price_data)
        
        assert 'error' in result
        assert 'Unsupported indicator: unsupported' in result['error']
    
    @pytest.mark.asyncio
    async def test_analyze_signals(self, analysis_tools):
        """Test trading signal analysis."""
        indicators = {
            'rsi': {'current_value': 75},  # Overbought
            'macd': {'macd_line': 2.5, 'signal': 2.0},  # Bullish
            'sma': {'sma_20': 105, 'sma_50': 100}  # Bullish trend
        }
        
        signals = await analysis_tools._analyze_signals(indicators)
        
        assert signals['rsi'] == 'overbought'
        assert signals['macd'] == 'bullish'
        assert signals['trend'] == 'bullish'
    
    def test_calculate_volatility(self, analysis_tools):
        """Test volatility calculation."""
        returns = [0.01, -0.02, 0.015, -0.01, 0.005]
        
        volatility = analysis_tools._calculate_volatility(returns)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    def test_rank_performance(self, analysis_tools):
        """Test performance ranking."""
        portfolio_perf = {'return': 15.0, 'volatility': 18.0}
        benchmark_perf = {
            'SPY': {'return': 12.0, 'volatility': 16.0},
            'QQQ': {'return': 18.0, 'volatility': 22.0},
            'IWM': {'return': 10.0, 'volatility': 25.0}
        }
        metrics = ['return', 'volatility']
        
        rankings = analysis_tools._rank_performance(portfolio_perf, benchmark_perf, metrics)
        
        assert 'return' in rankings
        assert 'volatility' in rankings
        
        # Portfolio return (15%) should rank 2nd out of 4 (after QQQ's 18%)
        assert rankings['return']['rank'] == 2
        assert rankings['return']['total_compared'] == 4
        
        # Portfolio volatility (18%) should rank 2nd out of 4 (after SPY's 16%)
        assert rankings['volatility']['rank'] == 2
    
    @pytest.mark.asyncio
    async def test_analyze_sector_rotation(self, analysis_tools):
        """Test sector rotation analysis."""
        sector_returns = {
            'Technology': 15.0,
            'Healthcare': 8.0,
            'Financials': 5.0,
            'Energy': -2.0,
            'Utilities': -5.0
        }
        
        rotation_analysis = await analysis_tools._analyze_sector_rotation(sector_returns)
        
        assert 'momentum_sectors' in rotation_analysis
        assert 'value_sectors' in rotation_analysis
        assert 'rotation_signal' in rotation_analysis
        assert 'sector_dispersion' in rotation_analysis
        
        # Technology should be in momentum sectors (top 30%)
        assert 'Technology' in rotation_analysis['momentum_sectors']
        
        # Utilities should be in value sectors (bottom 30%)
        assert 'Utilities' in rotation_analysis['value_sectors']
        
        # Sector dispersion should be 20% (15% - (-5%))
        assert rotation_analysis['sector_dispersion'] == 20.0
    
    @pytest.mark.asyncio
    async def test_analysis_tools_error_handling(self, analysis_tools):
        """Test error handling in analysis tools."""
        # Mock market data client to raise exception
        analysis_tools.market_data_client.get_historical_data = AsyncMock(
            side_effect=Exception("Market data error")
        )
        
        with pytest.raises(PortfolioAutomationError) as exc_info:
            await analysis_tools.analyze_technical_indicators(['AAPL'])
        
        assert "Technical analysis failed" in str(exc_info.value)
        assert "Market data error" in str(exc_info.value)
    
    def test_health_check(self, analysis_tools):
        """Test health check functionality."""
        health_status = analysis_tools.health_check()
        
        assert health_status['status'] == 'healthy'
        assert 'services' in health_status
        assert 'last_check' in health_status
        
        services = health_status['services']
        assert 'technical_analysis' in services
        assert 'portfolio_analyzer' in services
        assert 'market_data_client' in services


if __name__ == '__main__':
    pytest.main([__file__])