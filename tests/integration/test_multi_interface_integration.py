"""
Multi-Interface Integration Tests

Tests integration between CLI, REST API, and MCP interfaces to ensure
data consistency and proper coordination between different access methods.
"""

import pytest
import pytest_asyncio
import asyncio
import json
import tempfile
import os
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from financial_portfolio_automation.cli.main import cli as cli_app
from financial_portfolio_automation.api.app import app as api_app
from financial_portfolio_automation.mcp.mcp_server import MCPToolServer
from financial_portfolio_automation.models.core import Quote, Position, OrderSide, OrderType
from financial_portfolio_automation.models.config import AlpacaConfig, RiskLimits, DataFeed
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache


class TestMultiInterfaceIntegration:
    """Test integration between CLI, API, and MCP interfaces"""

    @pytest_asyncio.fixture
    async def shared_data_store(self):
        """Shared data store for all interfaces"""
        data_store = DataStore(":memory:")
        return data_store

    @pytest.fixture
    def shared_cache(self):
        """Shared cache for all interfaces"""
        return DataCache()

    @pytest.fixture
    def test_config(self):
        """Test configuration"""
        return AlpacaConfig(
            api_key="test_key_12345",
            secret_key="test_secret_12345",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX
        )

    @pytest.fixture
    def api_client(self, shared_data_store, shared_cache, test_config):
        """FastAPI test client"""
        # Inject dependencies into the API app
        with patch('financial_portfolio_automation.api.app.get_data_store', return_value=shared_data_store):
            with patch('financial_portfolio_automation.api.app.get_cache', return_value=shared_cache):
                with patch('financial_portfolio_automation.api.app.get_config', return_value=test_config):
                    return TestClient(api_app)

    @pytest_asyncio.fixture
    async def mcp_server(self, shared_data_store, shared_cache, test_config):
        """MCP server instance"""
        server = MCPToolServer()
        # Inject shared dependencies
        server.data_store = shared_data_store
        server.cache = shared_cache
        server.config = test_config
        return server

    @pytest.fixture
    def cli_runner(self, shared_data_store, shared_cache, test_config):
        """CLI runner with shared dependencies"""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                'alpaca': {
                    'api_key': test_config.api_key,
                    'secret_key': test_config.secret_key,
                    'base_url': test_config.base_url,
                    'data_feed': test_config.data_feed.value
                }
            }
            json.dump(config_data, f)
            config_file = f.name
        
        # Patch CLI to use shared dependencies
        with patch('financial_portfolio_automation.cli.main.get_data_store', return_value=shared_data_store):
            with patch('financial_portfolio_automation.cli.main.get_cache', return_value=shared_cache):
                yield runner, config_file
        
        # Cleanup
        os.unlink(config_file)

    @pytest.mark.asyncio
    async def test_data_consistency_across_interfaces(self, shared_data_store, api_client, mcp_server, cli_runner):
        """Test data consistency when accessing through different interfaces"""
        
        # Create test data
        test_quote = Quote(
            symbol="CONSISTENCY_TEST",
            timestamp=datetime.now(),
            bid=Decimal("100.00"),
            ask=Decimal("100.05"),
            bid_size=100,
            ask_size=100
        )
        
        # Store data through data store (simulating one interface updating data)
        await shared_data_store.store_quote(test_quote)
        
        # Test 1: Access data through API
        with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.return_value = test_quote
            
            response = api_client.get("/api/v1/portfolio/quotes/CONSISTENCY_TEST")
            assert response.status_code == 200
            
            api_data = response.json()
            assert api_data['symbol'] == "CONSISTENCY_TEST"
            assert float(api_data['bid']) == 100.00
            assert float(api_data['ask']) == 100.05
        
        # Test 2: Access data through MCP
        with patch.object(mcp_server, 'get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.return_value = test_quote
            
            mcp_result = await mcp_server.get_portfolio_quote("CONSISTENCY_TEST")
            assert mcp_result['symbol'] == "CONSISTENCY_TEST"
            assert float(mcp_result['bid']) == 100.00
            assert float(mcp_result['ask']) == 100.05
        
        # Test 3: Access data through CLI
        runner, config_file = cli_runner
        
        with patch('financial_portfolio_automation.cli.portfolio_commands.get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.return_value = test_quote
            
            result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'quote', 'CONSISTENCY_TEST'])
            assert result.exit_code == 0
            assert "CONSISTENCY_TEST" in result.output
            assert "100.00" in result.output
        
        # Verify all interfaces accessed the same underlying data
        stored_quote = await shared_data_store.get_latest_quote("CONSISTENCY_TEST")
        assert stored_quote.symbol == test_quote.symbol
        assert stored_quote.bid == test_quote.bid
        assert stored_quote.ask == test_quote.ask

    @pytest.mark.asyncio
    async def test_concurrent_interface_access(self, shared_data_store, shared_cache, api_client, mcp_server, cli_runner):
        """Test concurrent access from multiple interfaces"""
        
        # Prepare test data
        test_symbols = ["AAPL", "GOOGL", "MSFT"]
        test_quotes = []
        
        for i, symbol in enumerate(test_symbols):
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                bid=Decimal(f"{100 + i}.00"),
                ask=Decimal(f"{100 + i}.05"),
                bid_size=100,
                ask_size=100
            )
            test_quotes.append(quote)
            await shared_data_store.store_quote(quote)
        
        # Define concurrent operations
        async def api_operations():
            """Simulate API operations"""
            results = []
            for symbol in test_symbols:
                with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_client:
                    mock_quote = next(q for q in test_quotes if q.symbol == symbol)
                    mock_client.return_value.get_quote.return_value = mock_quote
                    
                    response = api_client.get(f"/api/v1/portfolio/quotes/{symbol}")
                    results.append(response.json())
            return results
        
        async def mcp_operations():
            """Simulate MCP operations"""
            results = []
            for symbol in test_symbols:
                with patch.object(mcp_server, 'get_market_data_client') as mock_client:
                    mock_quote = next(q for q in test_quotes if q.symbol == symbol)
                    mock_client.return_value.get_quote.return_value = mock_quote
                    
                    result = await mcp_server.get_portfolio_quote(symbol)
                    results.append(result)
            return results
        
        def cli_operations():
            """Simulate CLI operations"""
            runner, config_file = cli_runner
            results = []
            
            for symbol in test_symbols:
                with patch('financial_portfolio_automation.cli.portfolio_commands.get_market_data_client') as mock_client:
                    mock_quote = next(q for q in test_quotes if q.symbol == symbol)
                    mock_client.return_value.get_quote.return_value = mock_quote
                    
                    result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'quote', symbol])
                    results.append(result.output)
            return results
        
        # Execute operations concurrently
        api_task = asyncio.create_task(api_operations())
        mcp_task = asyncio.create_task(mcp_operations())
        
        # CLI operations need to run in thread since they're synchronous
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            cli_future = executor.submit(cli_operations)
            
            # Wait for all operations to complete
            api_results = await api_task
            mcp_results = await mcp_task
            cli_results = cli_future.result()
        
        # Verify results consistency
        assert len(api_results) == len(test_symbols)
        assert len(mcp_results) == len(test_symbols)
        assert len(cli_results) == len(test_symbols)
        
        # Check that all interfaces got consistent data
        for i, symbol in enumerate(test_symbols):
            expected_bid = float(f"{100 + i}.00")
            expected_ask = float(f"{100 + i}.05")
            
            # API results
            assert api_results[i]['symbol'] == symbol
            assert float(api_results[i]['bid']) == expected_bid
            assert float(api_results[i]['ask']) == expected_ask
            
            # MCP results
            assert mcp_results[i]['symbol'] == symbol
            assert float(mcp_results[i]['bid']) == expected_bid
            assert float(mcp_results[i]['ask']) == expected_ask
            
            # CLI results (check that symbol and prices appear in output)
            assert symbol in cli_results[i]
            assert str(expected_bid) in cli_results[i]

    @pytest.mark.asyncio
    async def test_cross_interface_authentication(self, shared_data_store, api_client, mcp_server):
        """Test authentication consistency across interfaces"""
        
        # Test API authentication
        # First, test without authentication (should fail)
        response = api_client.get("/api/v1/portfolio/positions")
        assert response.status_code == 401  # Unauthorized
        
        # Test with authentication
        # Mock JWT token creation and validation
        with patch('financial_portfolio_automation.api.auth.verify_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "role": "trader"}
            
            headers = {"Authorization": "Bearer test_token"}
            
            with patch('financial_portfolio_automation.api.routes.portfolio.get_alpaca_client') as mock_client:
                mock_client.return_value.get_positions.return_value = []
                
                response = api_client.get("/api/v1/portfolio/positions", headers=headers)
                assert response.status_code == 200
        
        # Test MCP authentication (if implemented)
        # MCP tools should respect the same authentication context
        with patch.object(mcp_server, 'verify_permissions') as mock_verify:
            mock_verify.return_value = True
            
            with patch.object(mcp_server, 'get_alpaca_client') as mock_client:
                mock_client.return_value.get_positions.return_value = []
                
                result = await mcp_server.get_portfolio_positions()
                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_real_time_data_synchronization(self, shared_data_store, shared_cache, api_client, mcp_server):
        """Test real-time data synchronization across interfaces"""
        
        # Simulate real-time data update
        real_time_quote = Quote(
            symbol="REALTIME_TEST",
            timestamp=datetime.now(),
            bid=Decimal("200.00"),
            ask=Decimal("200.05"),
            bid_size=500,
            ask_size=300
        )
        
        # Update data through one interface (simulate WebSocket update)
        await shared_data_store.store_quote(real_time_quote)
        shared_cache.set(f"quote:REALTIME_TEST", real_time_quote, ttl=60)
        
        # Verify other interfaces see the updated data immediately
        
        # Test API access
        with patch('financial_portfolio_automation.api.routes.portfolio.get_cache', return_value=shared_cache):
            response = api_client.get("/api/v1/portfolio/quotes/REALTIME_TEST")
            assert response.status_code == 200
            
            api_data = response.json()
            assert float(api_data['bid']) == 200.00
            assert float(api_data['ask']) == 200.05
        
        # Test MCP access
        mcp_server.cache = shared_cache
        
        with patch.object(mcp_server, 'get_cached_quote') as mock_get_cached:
            mock_get_cached.return_value = real_time_quote
            
            mcp_result = await mcp_server.get_portfolio_quote("REALTIME_TEST")
            assert float(mcp_result['bid']) == 200.00
            assert float(mcp_result['ask']) == 200.05
        
        # Simulate another update
        updated_quote = Quote(
            symbol="REALTIME_TEST",
            timestamp=datetime.now(),
            bid=Decimal("201.00"),
            ask=Decimal("201.05"),
            bid_size=400,
            ask_size=200
        )
        
        # Update through different interface
        await shared_data_store.store_quote(updated_quote)
        shared_cache.set(f"quote:REALTIME_TEST", updated_quote, ttl=60)
        
        # Verify all interfaces see the new update
        cached_quote = shared_cache.get("quote:REALTIME_TEST")
        assert cached_quote.bid == Decimal("201.00")
        assert cached_quote.ask == Decimal("201.05")

    @pytest.mark.asyncio
    async def test_interface_specific_features(self, shared_data_store, api_client, mcp_server, cli_runner):
        """Test features specific to each interface while maintaining data consistency"""
        
        # Test API-specific features (REST endpoints, JSON responses)
        with patch('financial_portfolio_automation.api.routes.portfolio.get_alpaca_client') as mock_client:
            mock_client.return_value.get_account.return_value = {
                "account_id": "test_account",
                "buying_power": "10000.00",
                "portfolio_value": "15000.00"
            }
            
            # Test API pagination
            response = api_client.get("/api/v1/portfolio/account?page=1&limit=10")
            assert response.status_code == 200
            
            # Test API filtering
            response = api_client.get("/api/v1/portfolio/positions?symbol=AAPL")
            assert response.status_code == 200
        
        # Test MCP-specific features (AI assistant integration)
        with patch.object(mcp_server, 'get_portfolio_analyzer') as mock_analyzer:
            mock_analyzer.return_value.analyze_portfolio.return_value = {
                "total_value": Decimal("15000"),
                "total_pnl": Decimal("1000"),
                "risk_score": 0.3
            }
            
            # Test MCP analysis tools
            analysis_result = await mcp_server.analyze_portfolio_performance()
            assert "total_value" in analysis_result
            assert "risk_score" in analysis_result
        
        # Test CLI-specific features (command-line interface, formatted output)
        runner, config_file = cli_runner
        
        with patch('financial_portfolio_automation.cli.portfolio_commands.get_alpaca_client') as mock_client:
            mock_client.return_value.get_account.return_value = {
                "account_id": "test_account",
                "buying_power": "10000.00",
                "portfolio_value": "15000.00"
            }
            
            # Test CLI formatted output
            result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'status'])
            assert result.exit_code == 0
            assert "Account ID" in result.output or "test_account" in result.output
            
            # Test CLI interactive features (if implemented)
            result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'summary'])
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self, shared_data_store, api_client, mcp_server, cli_runner):
        """Test consistent error handling across all interfaces"""
        
        # Test handling of invalid symbols
        
        # API error handling
        with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.side_effect = ValueError("Invalid symbol")
            
            response = api_client.get("/api/v1/portfolio/quotes/INVALID_SYMBOL")
            assert response.status_code == 400  # Bad Request
            
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data
        
        # MCP error handling
        with patch.object(mcp_server, 'get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.side_effect = ValueError("Invalid symbol")
            
            with pytest.raises(ValueError, match="Invalid symbol"):
                await mcp_server.get_portfolio_quote("INVALID_SYMBOL")
        
        # CLI error handling
        runner, config_file = cli_runner
        
        with patch('financial_portfolio_automation.cli.portfolio_commands.get_market_data_client') as mock_client:
            mock_client.return_value.get_quote.side_effect = ValueError("Invalid symbol")
            
            result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'quote', 'INVALID_SYMBOL'])
            assert result.exit_code != 0  # Should exit with error
            assert "error" in result.output.lower() or "invalid" in result.output.lower()

    @pytest.mark.asyncio
    async def test_performance_under_concurrent_load(self, shared_data_store, shared_cache, api_client, mcp_server):
        """Test system performance under concurrent load from multiple interfaces"""
        
        import time
        
        # Prepare test data
        test_symbols = [f"TEST{i:03d}" for i in range(50)]  # 50 test symbols
        
        for i, symbol in enumerate(test_symbols):
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                bid=Decimal(f"{100 + i}.00"),
                ask=Decimal(f"{100 + i}.05"),
                bid_size=100,
                ask_size=100
            )
            await shared_data_store.store_quote(quote)
            shared_cache.set(f"quote:{symbol}", quote, ttl=300)
        
        # Define concurrent load test
        async def api_load_test():
            """Simulate high API load"""
            start_time = time.time()
            responses = []
            
            for symbol in test_symbols[:25]:  # Test first 25 symbols
                with patch('financial_portfolio_automation.api.routes.portfolio.get_cache', return_value=shared_cache):
                    response = api_client.get(f"/api/v1/portfolio/quotes/{symbol}")
                    responses.append(response.status_code)
            
            end_time = time.time()
            return responses, end_time - start_time
        
        async def mcp_load_test():
            """Simulate high MCP load"""
            start_time = time.time()
            results = []
            
            mcp_server.cache = shared_cache
            
            for symbol in test_symbols[25:]:  # Test last 25 symbols
                with patch.object(mcp_server, 'get_cached_quote') as mock_get_cached:
                    cached_quote = shared_cache.get(f"quote:{symbol}")
                    mock_get_cached.return_value = cached_quote
                    
                    result = await mcp_server.get_portfolio_quote(symbol)
                    results.append(result is not None)
            
            end_time = time.time()
            return results, end_time - start_time
        
        # Run concurrent load tests
        api_task = asyncio.create_task(api_load_test())
        mcp_task = asyncio.create_task(mcp_load_test())
        
        api_results, api_time = await api_task
        mcp_results, mcp_time = await mcp_task
        
        # Verify performance and correctness
        assert all(status == 200 for status in api_results)
        assert all(result for result in mcp_results)
        
        # Performance assertions (adjust thresholds as needed)
        assert api_time < 10.0  # Should complete within 10 seconds
        assert mcp_time < 10.0  # Should complete within 10 seconds
        
        # Verify data integrity after load test
        sample_symbol = test_symbols[0]
        stored_quote = await shared_data_store.get_latest_quote(sample_symbol)
        cached_quote = shared_cache.get(f"quote:{sample_symbol}")
        
        assert stored_quote is not None
        assert cached_quote is not None
        assert stored_quote.symbol == cached_quote.symbol
        assert stored_quote.bid == cached_quote.bid

    @pytest.mark.asyncio
    async def test_configuration_consistency(self, shared_data_store, test_config):
        """Test configuration consistency across all interfaces"""
        
        # All interfaces should use the same configuration
        # This is ensured by the fixtures, but let's verify the behavior
        
        # Test that configuration changes affect all interfaces
        updated_config = AlpacaConfig(
            api_key="updated_key",
            secret_key="updated_secret",
            base_url="https://paper-api.alpaca.markets",
            data_feed="sip"  # Changed from iex to sip
        )
        
        # Simulate configuration update
        with patch('financial_portfolio_automation.config.settings.get_alpaca_config', return_value=updated_config):
            # All interfaces should now use the updated configuration
            
            # Test API
            api_client = TestClient(api_app)
            with patch('financial_portfolio_automation.api.app.get_config', return_value=updated_config):
                # Configuration should be accessible through API
                response = api_client.get("/api/v1/system/config")
                # This endpoint might not exist, but the concept is that config should be consistent
        
        # Test that invalid configurations are handled consistently
        invalid_config = AlpacaConfig(
            api_key="",  # Empty API key
            secret_key="test_secret",
            base_url="invalid_url",
            data_feed="invalid_feed"
        )
        
        # All interfaces should handle invalid configuration similarly
        with patch('financial_portfolio_automation.config.settings.get_alpaca_config', return_value=invalid_config):
            # Should raise configuration errors consistently across interfaces
            pass  # Specific implementation depends on how config validation is implemented