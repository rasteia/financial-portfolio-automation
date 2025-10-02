"""
Concurrent Users Performance Tests

Tests system behavior and performance when multiple users access
the system simultaneously through different interfaces.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import threading
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
from click.testing import CliRunner

from financial_portfolio_automation.models.core import Quote, Position, OrderSide, OrderType
from financial_portfolio_automation.models.config import AlpacaConfig, RiskLimits, DataFeed
from financial_portfolio_automation.api.app import app as api_app
from financial_portfolio_automation.cli.main import cli as cli_app
from financial_portfolio_automation.mcp.mcp_server import MCPToolServer
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache


class TestConcurrentUsers:
    """Test system performance with concurrent users"""

    @pytest_asyncio.fixture
    async def concurrent_test_system(self):
        """Initialize system for concurrent user testing"""
        # Shared data store and cache
        data_store = DataStore(":memory:")
        
        cache = DataCache()
        
        config = AlpacaConfig(
            api_key="test_key_12345",
            secret_key="test_secret_12345",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX
        )
        
        # Populate with test data
        test_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        for i, symbol in enumerate(test_symbols):
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                bid=Decimal(f"{100 + i * 50}.00"),
                ask=Decimal(f"{100 + i * 50}.05"),
                bid_size=100,
                ask_size=100
            )
            data_store.save_quote(quote)
            cache.set(f"quote:{symbol}", quote, ttl=300)
        
        return {
            'data_store': data_store,
            'cache': cache,
            'config': config,
            'test_symbols': test_symbols
        }

    @pytest.fixture
    def api_clients(self, concurrent_test_system):
        """Create multiple API clients for concurrent testing"""
        clients = []
        
        for i in range(10):  # Create 10 clients
            with patch('financial_portfolio_automation.api.app.get_data_store', return_value=concurrent_test_system['data_store']):
                with patch('financial_portfolio_automation.api.app.get_cache', return_value=concurrent_test_system['cache']):
                    with patch('financial_portfolio_automation.api.app.get_config', return_value=concurrent_test_system['config']):
                        client = TestClient(api_app)
                        clients.append(client)
        
        return clients

    @pytest_asyncio.fixture
    async def mcp_servers(self, concurrent_test_system):
        """Create multiple MCP server instances for concurrent testing"""
        servers = []
        
        for i in range(5):  # Create 5 MCP servers
            server = MCPToolServer()
            server.data_store = concurrent_test_system['data_store']
            server.cache = concurrent_test_system['cache']
            server.config = concurrent_test_system['config']
            servers.append(server)
        
        return servers

    def test_concurrent_api_users(self, api_clients, concurrent_test_system):
        """Test concurrent API users accessing the system"""
        
        test_symbols = concurrent_test_system['test_symbols']
        
        # Mock API dependencies
        with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_market_client:
            with patch('financial_portfolio_automation.api.routes.portfolio.get_alpaca_client') as mock_alpaca_client:
                
                # Setup mocks
                def mock_get_quote(symbol):
                    return Quote(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        bid=Decimal("150.00"),
                        ask=Decimal("150.05"),
                        bid_size=100,
                        ask_size=100
                    )
                
                mock_market_client.return_value.get_quote.side_effect = mock_get_quote
                mock_alpaca_client.return_value.get_account.return_value = {
                    "account_id": "test_account",
                    "buying_power": "50000.00",
                    "portfolio_value": "100000.00"
                }
                mock_alpaca_client.return_value.get_positions.return_value = []
                
                def simulate_user_session(client_id, client, operations_per_user=50):
                    """Simulate a user session with multiple operations"""
                    results = {
                        'client_id': client_id,
                        'successful_requests': 0,
                        'failed_requests': 0,
                        'response_times': [],
                        'errors': []
                    }
                    
                    for i in range(operations_per_user):
                        try:
                            # Mix of different operations
                            if i % 4 == 0:
                                # Get account info
                                start_time = time.time()
                                response = client.get("/api/v1/portfolio/account")
                                response_time = time.time() - start_time
                                
                            elif i % 4 == 1:
                                # Get positions
                                start_time = time.time()
                                response = client.get("/api/v1/portfolio/positions")
                                response_time = time.time() - start_time
                                
                            elif i % 4 == 2:
                                # Get quote
                                symbol = test_symbols[i % len(test_symbols)]
                                start_time = time.time()
                                response = client.get(f"/api/v1/portfolio/quotes/{symbol}")
                                response_time = time.time() - start_time
                                
                            else:
                                # Health check
                                start_time = time.time()
                                response = client.get("/api/v1/system/health")
                                response_time = time.time() - start_time
                            
                            results['response_times'].append(response_time)
                            
                            if response.status_code == 200:
                                results['successful_requests'] += 1
                            else:
                                results['failed_requests'] += 1
                                results['errors'].append(f"Status {response.status_code}")
                        
                        except Exception as e:
                            results['failed_requests'] += 1
                            results['errors'].append(str(e))
                        
                        # Small delay between requests
                        time.sleep(0.01)
                    
                    return results
                
                # Run concurrent user sessions
                print(f"Testing {len(api_clients)} concurrent API users...")
                
                start_time = time.time()
                
                with ThreadPoolExecutor(max_workers=len(api_clients)) as executor:
                    futures = [
                        executor.submit(simulate_user_session, i, client)
                        for i, client in enumerate(api_clients)
                    ]
                    
                    results = []
                    for future in as_completed(futures):
                        try:
                            result = future.result(timeout=60)  # 60 second timeout
                            results.append(result)
                        except Exception as e:
                            print(f"User session failed: {e}")
                
                total_time = time.time() - start_time
                
                # Analyze results
                total_requests = sum(r['successful_requests'] + r['failed_requests'] for r in results)
                total_successful = sum(r['successful_requests'] for r in results)
                total_failed = sum(r['failed_requests'] for r in results)
                
                all_response_times = []
                for r in results:
                    all_response_times.extend(r['response_times'])
                
                success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
                avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
                requests_per_second = total_requests / total_time
                
                print(f"Total requests: {total_requests}")
                print(f"Successful requests: {total_successful}")
                print(f"Failed requests: {total_failed}")
                print(f"Success rate: {success_rate:.1f}%")
                print(f"Average response time: {avg_response_time:.3f}s")
                print(f"Requests per second: {requests_per_second:.2f}")
                
                # Performance assertions
                assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
                assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time:.3f}s"
                assert requests_per_second > 50, f"Throughput too low: {requests_per_second:.2f} req/s"
                
                # Check for errors
                all_errors = []
                for r in results:
                    all_errors.extend(r['errors'])
                
                if all_errors:
                    print(f"Errors encountered: {len(all_errors)}")
                    unique_errors = list(set(all_errors))
                    for error in unique_errors[:5]:  # Show first 5 unique errors
                        print(f"  {error}")

    @pytest.mark.asyncio
    async def test_concurrent_mcp_users(self, mcp_servers, concurrent_test_system):
        """Test concurrent MCP users accessing the system"""
        
        test_symbols = concurrent_test_system['test_symbols']
        
        async def simulate_mcp_user_session(server_id, server, operations_per_user=30):
            """Simulate an MCP user session"""
            results = {
                'server_id': server_id,
                'successful_operations': 0,
                'failed_operations': 0,
                'response_times': [],
                'errors': []
            }
            
            # Mock dependencies for MCP server
            with patch.object(server, 'get_market_data_client') as mock_market_client:
                with patch.object(server, 'get_alpaca_client') as mock_alpaca_client:
                    
                    def mock_get_quote(symbol):
                        return Quote(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            bid=Decimal("150.00"),
                            ask=Decimal("150.05"),
                            bid_size=100,
                            ask_size=100
                        )
                    
                    mock_market_client.return_value.get_quote.side_effect = mock_get_quote
                    mock_alpaca_client.return_value.get_account.return_value = {
                        "account_id": "test_account",
                        "buying_power": "50000.00"
                    }
                    mock_alpaca_client.return_value.get_positions.return_value = []
                    
                    for i in range(operations_per_user):
                        try:
                            start_time = time.time()
                            
                            # Mix of different MCP operations
                            if i % 3 == 0:
                                # Get portfolio quote
                                symbol = test_symbols[i % len(test_symbols)]
                                result = await server.get_portfolio_quote(symbol)
                                
                            elif i % 3 == 1:
                                # Get portfolio positions
                                result = await server.get_portfolio_positions()
                                
                            else:
                                # Analyze portfolio performance
                                result = await server.analyze_portfolio_performance()
                            
                            response_time = time.time() - start_time
                            results['response_times'].append(response_time)
                            results['successful_operations'] += 1
                            
                        except Exception as e:
                            results['failed_operations'] += 1
                            results['errors'].append(str(e))
                        
                        # Small delay between operations
                        await asyncio.sleep(0.02)
            
            return results
        
        # Run concurrent MCP user sessions
        print(f"Testing {len(mcp_servers)} concurrent MCP users...")
        
        start_time = time.time()
        
        tasks = [
            simulate_mcp_user_session(i, server)
            for i, server in enumerate(mcp_servers)
        ]
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        total_operations = sum(r['successful_operations'] + r['failed_operations'] for r in results)
        total_successful = sum(r['successful_operations'] for r in results)
        total_failed = sum(r['failed_operations'] for r in results)
        
        all_response_times = []
        for r in results:
            all_response_times.extend(r['response_times'])
        
        success_rate = (total_successful / total_operations * 100) if total_operations > 0 else 0
        avg_response_time = statistics.mean(all_response_times) if all_response_times else 0
        operations_per_second = total_operations / total_time
        
        print(f"Total MCP operations: {total_operations}")
        print(f"Successful operations: {total_successful}")
        print(f"Failed operations: {total_failed}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Operations per second: {operations_per_second:.2f}")
        
        # Performance assertions
        assert success_rate >= 95, f"MCP success rate too low: {success_rate:.1f}%"
        assert avg_response_time < 2.0, f"MCP average response time too high: {avg_response_time:.3f}s"
        assert operations_per_second > 20, f"MCP throughput too low: {operations_per_second:.2f} ops/s"

    def test_mixed_interface_concurrent_users(self, api_clients, concurrent_test_system):
        """Test concurrent users across different interfaces (API + CLI)"""
        
        test_symbols = concurrent_test_system['test_symbols']
        
        def simulate_api_user(client_id, client, operations=25):
            """Simulate API user"""
            results = {'type': 'api', 'client_id': client_id, 'operations': 0, 'errors': 0}
            
            with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_client:
                mock_client.return_value.get_quote.return_value = Quote(
                    symbol="TEST",
                    timestamp=datetime.now(),
                    bid=Decimal("150.00"),
                    ask=Decimal("150.05"),
                    bid_size=100,
                    ask_size=100
                )
                
                for i in range(operations):
                    try:
                        symbol = test_symbols[i % len(test_symbols)]
                        response = client.get(f"/api/v1/portfolio/quotes/{symbol}")
                        if response.status_code == 200:
                            results['operations'] += 1
                        else:
                            results['errors'] += 1
                    except Exception:
                        results['errors'] += 1
                    
                    time.sleep(0.02)
            
            return results
        
        def simulate_cli_user(user_id, operations=25):
            """Simulate CLI user"""
            results = {'type': 'cli', 'user_id': user_id, 'operations': 0, 'errors': 0}
            
            runner = CliRunner()
            
            # Create temporary config
            import tempfile
            import json
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                config_data = {
                    'alpaca': {
                        'api_key': 'test_key_12345',
                        'secret_key': 'test_secret_12345',
                        'base_url': 'https://paper-api.alpaca.markets',
                        'data_feed': 'iex'
                    }
                }
                json.dump(config_data, f)
                config_file = f.name
            
            try:
                with patch('financial_portfolio_automation.cli.portfolio_commands.get_market_data_client') as mock_client:
                    mock_client.return_value.get_quote.return_value = Quote(
                        symbol="TEST",
                        timestamp=datetime.now(),
                        bid=Decimal("150.00"),
                        ask=Decimal("150.05"),
                        bid_size=100,
                        ask_size=100
                    )
                    
                    for i in range(operations):
                        try:
                            symbol = test_symbols[i % len(test_symbols)]
                            result = runner.invoke(cli_app, ['--config', config_file, 'portfolio', 'quote', symbol])
                            if result.exit_code == 0:
                                results['operations'] += 1
                            else:
                                results['errors'] += 1
                        except Exception:
                            results['errors'] += 1
                        
                        time.sleep(0.03)
            finally:
                os.unlink(config_file)
            
            return results
        
        # Run mixed concurrent users
        print("Testing mixed interface concurrent users (API + CLI)...")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            
            # Submit API user tasks
            for i, client in enumerate(api_clients[:5]):  # Use 5 API clients
                future = executor.submit(simulate_api_user, i, client)
                futures.append(future)
            
            # Submit CLI user tasks
            for i in range(5):  # 5 CLI users
                future = executor.submit(simulate_cli_user, i)
                futures.append(future)
            
            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=120)  # 2 minute timeout
                    results.append(result)
                except Exception as e:
                    print(f"User simulation failed: {e}")
        
        total_time = time.time() - start_time
        
        # Analyze results by interface type
        api_results = [r for r in results if r['type'] == 'api']
        cli_results = [r for r in results if r['type'] == 'cli']
        
        api_operations = sum(r['operations'] for r in api_results)
        api_errors = sum(r['errors'] for r in api_results)
        cli_operations = sum(r['operations'] for r in cli_results)
        cli_errors = sum(r['errors'] for r in cli_results)
        
        total_operations = api_operations + cli_operations
        total_errors = api_errors + cli_errors
        
        api_success_rate = (api_operations / (api_operations + api_errors) * 100) if (api_operations + api_errors) > 0 else 0
        cli_success_rate = (cli_operations / (cli_operations + cli_errors) * 100) if (cli_operations + cli_errors) > 0 else 0
        overall_success_rate = (total_operations / (total_operations + total_errors) * 100) if (total_operations + total_errors) > 0 else 0
        
        operations_per_second = total_operations / total_time
        
        print(f"API operations: {api_operations}, errors: {api_errors}, success rate: {api_success_rate:.1f}%")
        print(f"CLI operations: {cli_operations}, errors: {cli_errors}, success rate: {cli_success_rate:.1f}%")
        print(f"Overall success rate: {overall_success_rate:.1f}%")
        print(f"Total operations per second: {operations_per_second:.2f}")
        
        # Performance assertions
        assert api_success_rate >= 90, f"API success rate too low: {api_success_rate:.1f}%"
        assert cli_success_rate >= 80, f"CLI success rate too low: {cli_success_rate:.1f}%"  # CLI might be slower
        assert overall_success_rate >= 85, f"Overall success rate too low: {overall_success_rate:.1f}%"
        assert operations_per_second > 10, f"Mixed interface throughput too low: {operations_per_second:.2f} ops/s"

    @pytest.mark.asyncio
    async def test_data_consistency_under_concurrent_access(self, concurrent_test_system):
        """Test data consistency when multiple users access and modify data concurrently"""
        
        data_store = concurrent_test_system['data_store']
        cache = concurrent_test_system['cache']
        test_symbols = concurrent_test_system['test_symbols']
        
        # Shared counters for tracking operations
        operation_counts = {
            'reads': 0,
            'writes': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Lock for thread-safe counter updates
        counter_lock = threading.Lock()
        
        async def concurrent_reader(reader_id, read_operations=100):
            """Concurrent reader that reads data"""
            local_reads = 0
            local_cache_hits = 0
            local_cache_misses = 0
            
            for i in range(read_operations):
                symbol = test_symbols[i % len(test_symbols)]
                
                # Try cache first
                cached_quote = cache.get(f"quote:{symbol}")
                if cached_quote:
                    local_cache_hits += 1
                else:
                    local_cache_misses += 1
                    # Read from database
                    stored_quote = await data_store.get_latest_quote(symbol)
                    if stored_quote:
                        # Update cache
                        cache.set(f"quote:{symbol}", stored_quote, ttl=60)
                
                local_reads += 1
                await asyncio.sleep(0.001)  # Small delay
            
            # Update shared counters
            with counter_lock:
                operation_counts['reads'] += local_reads
                operation_counts['cache_hits'] += local_cache_hits
                operation_counts['cache_misses'] += local_cache_misses
            
            return local_reads
        
        async def concurrent_writer(writer_id, write_operations=50):
            """Concurrent writer that updates data"""
            local_writes = 0
            
            for i in range(write_operations):
                symbol = test_symbols[i % len(test_symbols)]
                
                # Create updated quote
                quote = Quote(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    bid=Decimal(f"{100 + writer_id + i}.{i % 100:02d}"),
                    ask=Decimal(f"{100 + writer_id + i}.{(i % 100) + 5:02d}"),
                    bid_size=100 + i,
                    ask_size=100 + i + 1
                )
                
                # Write to database
                data_store.save_quote(quote)
                
                # Update cache
                cache.set(f"quote:{symbol}", quote, ttl=60)
                
                local_writes += 1
                await asyncio.sleep(0.002)  # Small delay
            
            # Update shared counter
            with counter_lock:
                operation_counts['writes'] += local_writes
            
            return local_writes
        
        # Run concurrent readers and writers
        print("Testing data consistency under concurrent access...")
        
        start_time = time.time()
        
        # Create tasks
        reader_tasks = [concurrent_reader(i) for i in range(10)]  # 10 readers
        writer_tasks = [concurrent_writer(i) for i in range(3)]   # 3 writers
        
        # Run all tasks concurrently
        all_tasks = reader_tasks + writer_tasks
        results = await asyncio.gather(*all_tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        total_reads = operation_counts['reads']
        total_writes = operation_counts['writes']
        cache_hit_rate = (operation_counts['cache_hits'] / total_reads * 100) if total_reads > 0 else 0
        
        operations_per_second = (total_reads + total_writes) / total_time
        
        print(f"Total reads: {total_reads}")
        print(f"Total writes: {total_writes}")
        print(f"Cache hit rate: {cache_hit_rate:.1f}%")
        print(f"Operations per second: {operations_per_second:.2f}")
        
        # Verify data consistency
        consistency_errors = 0
        
        for symbol in test_symbols:
            # Get data from both cache and database
            cached_quote = cache.get(f"quote:{symbol}")
            stored_quote = await data_store.get_latest_quote(symbol)
            
            if cached_quote and stored_quote:
                # Check if they match (allowing for small timing differences)
                if (cached_quote.symbol != stored_quote.symbol or
                    abs(cached_quote.bid - stored_quote.bid) > Decimal("0.01")):
                    consistency_errors += 1
        
        print(f"Data consistency errors: {consistency_errors}")
        
        # Performance and consistency assertions
        assert operations_per_second > 100, f"Concurrent operations throughput too low: {operations_per_second:.2f} ops/s"
        assert cache_hit_rate > 50, f"Cache hit rate too low: {cache_hit_rate:.1f}%"
        assert consistency_errors == 0, f"Data consistency errors detected: {consistency_errors}"

    def test_resource_contention_under_concurrent_load(self, concurrent_test_system):
        """Test system behavior under resource contention scenarios"""
        
        data_store = concurrent_test_system['data_store']
        cache = concurrent_test_system['cache']
        
        # Simulate resource-intensive operations
        def cpu_intensive_task(task_id, iterations=1000):
            """CPU-intensive task"""
            result = 0
            for i in range(iterations):
                # Simulate complex calculations
                result += sum(j * j for j in range(100))
                if i % 100 == 0:
                    time.sleep(0.001)  # Small yield
            return result
        
        def memory_intensive_task(task_id, data_size=1000):
            """Memory-intensive task"""
            # Create large data structures
            large_data = []
            for i in range(data_size):
                data_item = {
                    'id': i,
                    'data': f"large_data_item_{i}" * 100,  # Large string
                    'timestamp': datetime.now().isoformat(),
                    'values': list(range(100))
                }
                large_data.append(data_item)
            
            # Process the data
            processed = sum(len(item['data']) for item in large_data)
            return processed
        
        async def io_intensive_task(task_id, operations=100):
            """I/O-intensive task (database operations)"""
            quotes_created = 0
            
            for i in range(operations):
                quote = Quote(
                    symbol=f"IO_TEST_{task_id}_{i}",
                    timestamp=datetime.now(),
                    bid=Decimal(f"{100 + i}.00"),
                    ask=Decimal(f"{100 + i}.05"),
                    bid_size=100,
                    ask_size=100
                )
                
                data_store.save_quote(quote)
                cache.set(f"quote:{quote.symbol}", quote, ttl=60)
                quotes_created += 1
                
                if i % 10 == 0:
                    await asyncio.sleep(0.001)  # Small yield
            
            return quotes_created
        
        print("Testing resource contention under concurrent load...")
        
        start_time = time.time()
        
        # Run different types of tasks concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit CPU-intensive tasks
            cpu_futures = [executor.submit(cpu_intensive_task, i) for i in range(5)]
            
            # Submit memory-intensive tasks
            memory_futures = [executor.submit(memory_intensive_task, i) for i in range(3)]
            
            # Submit I/O-intensive tasks (run in asyncio)
            async def run_io_tasks():
                io_tasks = [io_intensive_task(i) for i in range(5)]
                return await asyncio.gather(*io_tasks)
            
            # Run I/O tasks
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            io_results = loop.run_until_complete(run_io_tasks())
            loop.close()
            
            # Collect CPU and memory task results
            cpu_results = [future.result() for future in cpu_futures]
            memory_results = [future.result() for future in memory_futures]
        
        total_time = time.time() - start_time
        
        # Analyze results
        cpu_tasks_completed = len([r for r in cpu_results if r > 0])
        memory_tasks_completed = len([r for r in memory_results if r > 0])
        io_operations_completed = sum(io_results)
        
        print(f"CPU tasks completed: {cpu_tasks_completed}/5")
        print(f"Memory tasks completed: {memory_tasks_completed}/3")
        print(f"I/O operations completed: {io_operations_completed}")
        print(f"Total execution time: {total_time:.2f}s")
        
        # Check system responsiveness during contention
        responsiveness_start = time.time()
        
        # Test basic operations during resource contention
        test_quote = Quote(
            symbol="RESPONSIVENESS_TEST",
            timestamp=datetime.now(),
            bid=Decimal("200.00"),
            ask=Decimal("200.05"),
            bid_size=100,
            ask_size=100
        )
        
        # This should complete quickly even under load
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data_store.save_quote(test_quote)
        loop.close()
        
        cache.set("quote:RESPONSIVENESS_TEST", test_quote, ttl=60)
        cached_quote = cache.get("quote:RESPONSIVENESS_TEST")
        
        responsiveness_time = time.time() - responsiveness_start
        
        print(f"System responsiveness during contention: {responsiveness_time:.3f}s")
        
        # Performance assertions
        assert cpu_tasks_completed >= 4, f"Too many CPU tasks failed: {cpu_tasks_completed}/5"
        assert memory_tasks_completed >= 2, f"Too many memory tasks failed: {memory_tasks_completed}/3"
        assert io_operations_completed >= 400, f"Too few I/O operations completed: {io_operations_completed}"
        assert responsiveness_time < 1.0, f"System not responsive during contention: {responsiveness_time:.3f}s"
        assert cached_quote is not None, "Cache operations failed during resource contention"