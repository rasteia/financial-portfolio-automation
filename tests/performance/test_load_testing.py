"""
Load Testing for Financial Portfolio Automation System

Tests system performance under various load conditions including
concurrent users, high-frequency data processing, and stress scenarios.
"""

import pytest
import pytest_asyncio
import asyncio
import time
import statistics
import psutil
import os
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient

from financial_portfolio_automation.models.core import Quote, Position, Order, OrderSide, OrderType
from financial_portfolio_automation.models.config import AlpacaConfig, RiskLimits, DataFeed
from financial_portfolio_automation.api.app import app as api_app
from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.api.market_data_client import MarketDataClient
from financial_portfolio_automation.analysis.portfolio_analyzer import PortfolioAnalyzer


class TestLoadTesting:
    """Load testing for system performance validation"""

    @pytest_asyncio.fixture
    async def load_test_system(self):
        """Initialize system for load testing"""
        # Use in-memory database for faster testing
        data_store = DataStore(":memory:")
        
        cache = DataCache()
        
        config = AlpacaConfig(
            api_key="test_key_12345",
            secret_key="test_secret_12345",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX
        )
        
        return {
            'data_store': data_store,
            'cache': cache,
            'config': config
        }

    @pytest.fixture
    def api_client(self, load_test_system):
        """FastAPI test client for load testing"""
        with patch('financial_portfolio_automation.api.app.get_data_store', return_value=load_test_system['data_store']):
            with patch('financial_portfolio_automation.api.app.get_cache', return_value=load_test_system['cache']):
                with patch('financial_portfolio_automation.api.app.get_config', return_value=load_test_system['config']):
                    return TestClient(api_app)

    def generate_test_quotes(self, count: int, symbols: list = None):
        """Generate test quotes for load testing"""
        if symbols is None:
            symbols = [f"TEST{i:03d}" for i in range(min(count, 100))]
        
        quotes = []
        base_time = datetime.now()
        
        for i in range(count):
            symbol = symbols[i % len(symbols)]
            quote = Quote(
                symbol=symbol,
                timestamp=base_time + timedelta(seconds=i),
                bid=Decimal(f"{100 + (i % 50)}.{i % 100:02d}"),
                ask=Decimal(f"{100 + (i % 50)}.{(i % 100) + 5:02d}"),
                bid_size=100 + (i % 500),
                ask_size=100 + ((i + 1) % 500)
            )
            quotes.append(quote)
        
        return quotes

    @pytest.mark.asyncio
    async def test_high_frequency_data_ingestion(self, load_test_system):
        """Test high-frequency data ingestion performance"""
        
        data_store = load_test_system['data_store']
        cache = load_test_system['cache']
        
        # Generate large number of quotes
        quote_count = 10000
        test_quotes = self.generate_test_quotes(quote_count)
        
        # Measure ingestion performance
        start_time = time.time()
        
        # Batch insert for better performance
        batch_size = 100
        for i in range(0, len(test_quotes), batch_size):
            batch = test_quotes[i:i + batch_size]
            
            # Store quotes in database
            tasks = [data_store.store_quote(quote) for quote in batch]
            await asyncio.gather(*tasks)
            
            # Cache recent quotes
            for quote in batch:
                cache.set(f"quote:{quote.symbol}", quote, ttl=60)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        quotes_per_second = quote_count / total_time
        
        print(f"Processed {quote_count} quotes in {total_time:.2f} seconds")
        print(f"Throughput: {quotes_per_second:.2f} quotes/second")
        
        # Should process at least 1000 quotes per second
        assert quotes_per_second > 1000, f"Throughput too low: {quotes_per_second:.2f} quotes/second"
        
        # Verify data integrity
        sample_quotes = test_quotes[:10]
        for quote in sample_quotes:
            stored_quote = await data_store.get_latest_quote(quote.symbol)
            cached_quote = cache.get(f"quote:{quote.symbol}")
            
            assert stored_quote is not None
            assert cached_quote is not None
            assert stored_quote.symbol == quote.symbol

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, api_client):
        """Test API performance under concurrent request load"""
        
        # Mock data for API responses
        mock_quotes = self.generate_test_quotes(100)
        mock_positions = [
            {
                "symbol": f"TEST{i:03d}",
                "qty": str(100 + i),
                "market_value": str(10000 + i * 100),
                "unrealized_pl": str(i * 10),
                "cost_basis": str(9900 + i * 100)
            }
            for i in range(50)
        ]
        
        # Define concurrent request scenarios
        async def make_concurrent_requests(endpoint_configs, concurrent_users=10):
            """Make concurrent requests to various endpoints"""
            
            def make_request(endpoint_config):
                endpoint, method, expected_status = endpoint_config
                
                start_time = time.time()
                
                if method == "GET":
                    response = api_client.get(endpoint)
                elif method == "POST":
                    response = api_client.post(endpoint, json={})
                else:
                    response = api_client.get(endpoint)  # Default to GET
                
                end_time = time.time()
                
                return {
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'expected_status': expected_status
                }
            
            # Create concurrent requests
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                # Submit multiple requests for each endpoint
                futures = []
                
                for _ in range(concurrent_users):
                    for config in endpoint_configs:
                        future = executor.submit(make_request, config)
                        futures.append(future)
                
                # Collect results
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=30)  # 30 second timeout
                        results.append(result)
                    except Exception as e:
                        print(f"Request failed: {e}")
                
                return results
        
        # Test various API endpoints
        with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_market_client:
            with patch('financial_portfolio_automation.api.routes.portfolio.get_alpaca_client') as mock_alpaca_client:
                
                # Setup mocks
                mock_market_client.return_value.get_quote.return_value = mock_quotes[0]
                mock_alpaca_client.return_value.get_positions.return_value = mock_positions
                mock_alpaca_client.return_value.get_account.return_value = {
                    "account_id": "test_account",
                    "buying_power": "50000.00",
                    "portfolio_value": "100000.00"
                }
                
                endpoint_configs = [
                    ("/api/v1/portfolio/quotes/TEST001", "GET", 200),
                    ("/api/v1/portfolio/positions", "GET", 200),
                    ("/api/v1/portfolio/account", "GET", 200),
                    ("/api/v1/system/health", "GET", 200),
                ]
                
                # Test with different concurrency levels
                concurrency_levels = [5, 10, 20]
                
                for concurrent_users in concurrency_levels:
                    print(f"\nTesting with {concurrent_users} concurrent users...")
                    
                    results = await make_concurrent_requests(endpoint_configs, concurrent_users)
                    
                    # Analyze results
                    successful_requests = [r for r in results if r['status_code'] == r['expected_status']]
                    failed_requests = [r for r in results if r['status_code'] != r['expected_status']]
                    
                    success_rate = len(successful_requests) / len(results) * 100
                    response_times = [r['response_time'] for r in successful_requests]
                    
                    if response_times:
                        avg_response_time = statistics.mean(response_times)
                        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                        
                        print(f"Success rate: {success_rate:.1f}%")
                        print(f"Average response time: {avg_response_time:.3f}s")
                        print(f"95th percentile response time: {p95_response_time:.3f}s")
                        
                        # Performance assertions
                        assert success_rate >= 95, f"Success rate too low: {success_rate:.1f}%"
                        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time:.3f}s"
                        assert p95_response_time < 2.0, f"95th percentile response time too high: {p95_response_time:.3f}s"
                    
                    if failed_requests:
                        print(f"Failed requests: {len(failed_requests)}")
                        for req in failed_requests[:5]:  # Show first 5 failures
                            print(f"  {req['endpoint']}: {req['status_code']} (expected {req['expected_status']})")

    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, load_test_system):
        """Test memory usage under sustained load"""
        
        data_store = load_test_system['data_store']
        cache = load_test_system['cache']
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Simulate sustained load
        total_quotes = 50000
        batch_size = 1000
        memory_samples = []
        
        for batch_num in range(0, total_quotes, batch_size):
            # Generate and process batch
            batch_quotes = self.generate_test_quotes(batch_size)
            
            # Store quotes
            tasks = [data_store.store_quote(quote) for quote in batch_quotes]
            await asyncio.gather(*tasks)
            
            # Cache quotes
            for quote in batch_quotes:
                cache.set(f"quote:{quote.symbol}:{batch_num}", quote, ttl=300)
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(current_memory)
            
            if batch_num % (batch_size * 5) == 0:  # Print every 5 batches
                print(f"Processed {batch_num + batch_size} quotes, Memory: {current_memory:.2f} MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"Final memory usage: {final_memory:.2f} MB")
        print(f"Memory growth: {memory_growth:.2f} MB")
        
        # Memory usage assertions
        assert memory_growth < 500, f"Memory growth too high: {memory_growth:.2f} MB"  # Should not grow more than 500MB
        
        # Check for memory leaks (memory should stabilize)
        if len(memory_samples) >= 10:
            recent_samples = memory_samples[-10:]
            memory_trend = statistics.linear_regression(range(len(recent_samples)), recent_samples).slope
            
            print(f"Recent memory trend: {memory_trend:.2f} MB per batch")
            
            # Memory trend should be minimal (< 1MB per batch)
            assert abs(memory_trend) < 1.0, f"Potential memory leak detected: {memory_trend:.2f} MB/batch"

    @pytest.mark.asyncio
    async def test_database_performance_under_load(self, load_test_system):
        """Test database performance under heavy load"""
        
        data_store = load_test_system['data_store']
        
        # Test various database operations under load
        test_symbols = [f"PERF{i:03d}" for i in range(100)]
        
        # Test 1: Bulk insert performance
        print("Testing bulk insert performance...")
        
        insert_quotes = self.generate_test_quotes(20000, test_symbols)
        
        start_time = time.time()
        
        # Insert in batches for better performance
        batch_size = 500
        for i in range(0, len(insert_quotes), batch_size):
            batch = insert_quotes[i:i + batch_size]
            tasks = [data_store.store_quote(quote) for quote in batch]
            await asyncio.gather(*tasks)
        
        insert_time = time.time() - start_time
        insert_rate = len(insert_quotes) / insert_time
        
        print(f"Inserted {len(insert_quotes)} quotes in {insert_time:.2f}s ({insert_rate:.2f} quotes/s)")
        
        # Test 2: Query performance under load
        print("Testing query performance...")
        
        query_start = time.time()
        query_results = []
        
        # Perform various queries
        for symbol in test_symbols[:50]:  # Test 50 symbols
            # Recent quotes query
            recent_quotes = await data_store.get_recent_quotes(symbol, limit=100)
            query_results.append(len(recent_quotes))
            
            # Latest quote query
            latest_quote = await data_store.get_latest_quote(symbol)
            if latest_quote:
                query_results.append(1)
        
        query_time = time.time() - query_start
        queries_per_second = len(query_results) / query_time
        
        print(f"Executed {len(query_results)} queries in {query_time:.2f}s ({queries_per_second:.2f} queries/s)")
        
        # Test 3: Concurrent read/write performance
        print("Testing concurrent read/write performance...")
        
        async def write_worker():
            """Worker that continuously writes data"""
            write_quotes = self.generate_test_quotes(1000, test_symbols[:10])
            for quote in write_quotes:
                await data_store.store_quote(quote)
                await asyncio.sleep(0.001)  # Small delay to simulate real-world conditions
        
        async def read_worker():
            """Worker that continuously reads data"""
            read_count = 0
            for _ in range(500):
                symbol = test_symbols[read_count % len(test_symbols)]
                quote = await data_store.get_latest_quote(symbol)
                if quote:
                    read_count += 1
                await asyncio.sleep(0.002)  # Small delay
            return read_count
        
        # Run concurrent workers
        concurrent_start = time.time()
        
        write_task = asyncio.create_task(write_worker())
        read_tasks = [asyncio.create_task(read_worker()) for _ in range(5)]
        
        await write_task
        read_results = await asyncio.gather(*read_tasks)
        
        concurrent_time = time.time() - concurrent_start
        total_reads = sum(read_results)
        
        print(f"Concurrent operations completed in {concurrent_time:.2f}s")
        print(f"Total reads: {total_reads}")
        
        # Performance assertions
        assert insert_rate > 1000, f"Insert rate too low: {insert_rate:.2f} quotes/s"
        assert queries_per_second > 50, f"Query rate too low: {queries_per_second:.2f} queries/s"
        assert total_reads > 1000, f"Concurrent read performance too low: {total_reads} reads"

    @pytest.mark.asyncio
    async def test_cache_performance_under_load(self, load_test_system):
        """Test cache performance under high load"""
        
        cache = load_test_system['cache']
        
        # Test cache operations under load
        test_data = {}
        cache_keys = []
        
        # Generate test data
        for i in range(10000):
            key = f"test_key_{i}"
            value = {
                'symbol': f"TEST{i % 100:03d}",
                'price': 100 + (i % 1000) * 0.01,
                'timestamp': datetime.now().isoformat(),
                'data': f"test_data_{i}" * 10  # Some bulk data
            }
            test_data[key] = value
            cache_keys.append(key)
        
        # Test 1: Cache write performance
        print("Testing cache write performance...")
        
        write_start = time.time()
        
        for key, value in test_data.items():
            cache.set(key, value, ttl=300)
        
        write_time = time.time() - write_start
        write_rate = len(test_data) / write_time
        
        print(f"Cache writes: {len(test_data)} items in {write_time:.2f}s ({write_rate:.2f} writes/s)")
        
        # Test 2: Cache read performance
        print("Testing cache read performance...")
        
        read_start = time.time()
        hit_count = 0
        miss_count = 0
        
        # Read all keys
        for key in cache_keys:
            value = cache.get(key)
            if value is not None:
                hit_count += 1
            else:
                miss_count += 1
        
        read_time = time.time() - read_start
        read_rate = len(cache_keys) / read_time
        hit_rate = hit_count / len(cache_keys) * 100
        
        print(f"Cache reads: {len(cache_keys)} items in {read_time:.2f}s ({read_rate:.2f} reads/s)")
        print(f"Cache hit rate: {hit_rate:.1f}%")
        
        # Test 3: Mixed read/write performance
        print("Testing mixed cache operations...")
        
        async def cache_worker(worker_id, operation_count):
            """Worker performing mixed cache operations"""
            operations = 0
            hits = 0
            
            for i in range(operation_count):
                if i % 3 == 0:  # Write operation
                    key = f"worker_{worker_id}_key_{i}"
                    value = {'worker': worker_id, 'operation': i, 'timestamp': time.time()}
                    cache.set(key, value, ttl=60)
                else:  # Read operation
                    key = cache_keys[i % len(cache_keys)]
                    value = cache.get(key)
                    if value is not None:
                        hits += 1
                
                operations += 1
                
                # Small delay to simulate real-world usage
                if i % 100 == 0:
                    await asyncio.sleep(0.001)
            
            return operations, hits
        
        # Run multiple workers concurrently
        mixed_start = time.time()
        
        workers = [cache_worker(i, 2000) for i in range(10)]
        results = await asyncio.gather(*workers)
        
        mixed_time = time.time() - mixed_start
        
        total_operations = sum(ops for ops, hits in results)
        total_hits = sum(hits for ops, hits in results)
        operations_per_second = total_operations / mixed_time
        
        print(f"Mixed operations: {total_operations} ops in {mixed_time:.2f}s ({operations_per_second:.2f} ops/s)")
        print(f"Total cache hits: {total_hits}")
        
        # Performance assertions
        assert write_rate > 5000, f"Cache write rate too low: {write_rate:.2f} writes/s"
        assert read_rate > 10000, f"Cache read rate too low: {read_rate:.2f} reads/s"
        assert hit_rate > 90, f"Cache hit rate too low: {hit_rate:.1f}%"
        assert operations_per_second > 2000, f"Mixed operations rate too low: {operations_per_second:.2f} ops/s"

    @pytest.mark.asyncio
    async def test_system_stability_under_sustained_load(self, load_test_system, api_client):
        """Test system stability under sustained load over time"""
        
        data_store = load_test_system['data_store']
        cache = load_test_system['cache']
        
        print("Starting sustained load test...")
        
        # Track system metrics over time
        metrics = {
            'timestamps': [],
            'memory_usage': [],
            'response_times': [],
            'error_rates': [],
            'throughput': []
        }
        
        # Mock API dependencies
        with patch('financial_portfolio_automation.api.routes.portfolio.get_market_data_client') as mock_market_client:
            with patch('financial_portfolio_automation.api.routes.portfolio.get_alpaca_client') as mock_alpaca_client:
                
                mock_market_client.return_value.get_quote.return_value = self.generate_test_quotes(1)[0]
                mock_alpaca_client.return_value.get_account.return_value = {
                    "account_id": "test_account",
                    "buying_power": "50000.00"
                }
                
                # Run sustained load for a shorter duration in tests
                test_duration = 60  # 60 seconds
                measurement_interval = 5  # Measure every 5 seconds
                
                start_time = time.time()
                
                async def background_load():
                    """Generate background load"""
                    while time.time() - start_time < test_duration:
                        # Generate data load
                        quotes = self.generate_test_quotes(100)
                        tasks = [data_store.store_quote(quote) for quote in quotes]
                        await asyncio.gather(*tasks)
                        
                        # Cache operations
                        for quote in quotes:
                            cache.set(f"quote:{quote.symbol}", quote, ttl=60)
                        
                        await asyncio.sleep(0.1)
                
                async def api_load():
                    """Generate API load"""
                    while time.time() - start_time < test_duration:
                        # Make API requests
                        response = api_client.get("/api/v1/portfolio/account")
                        await asyncio.sleep(0.2)
                
                async def measure_metrics():
                    """Measure system metrics periodically"""
                    process = psutil.Process(os.getpid())
                    
                    while time.time() - start_time < test_duration:
                        current_time = time.time() - start_time
                        
                        # Memory usage
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        
                        # API response time
                        api_start = time.time()
                        response = api_client.get("/api/v1/system/health")
                        api_time = time.time() - api_start
                        
                        # Error rate (simplified)
                        error_rate = 0 if response.status_code == 200 else 100
                        
                        # Store metrics
                        metrics['timestamps'].append(current_time)
                        metrics['memory_usage'].append(memory_mb)
                        metrics['response_times'].append(api_time)
                        metrics['error_rates'].append(error_rate)
                        
                        await asyncio.sleep(measurement_interval)
                
                # Start all load generators
                load_tasks = [
                    asyncio.create_task(background_load()),
                    asyncio.create_task(api_load()),
                    asyncio.create_task(measure_metrics())
                ]
                
                # Wait for test completion
                await asyncio.gather(*load_tasks)
        
        # Analyze stability metrics
        if metrics['memory_usage']:
            avg_memory = statistics.mean(metrics['memory_usage'])
            max_memory = max(metrics['memory_usage'])
            memory_growth = max_memory - metrics['memory_usage'][0] if len(metrics['memory_usage']) > 1 else 0
            
            print(f"Average memory usage: {avg_memory:.2f} MB")
            print(f"Maximum memory usage: {max_memory:.2f} MB")
            print(f"Memory growth: {memory_growth:.2f} MB")
            
            # Stability assertions
            assert memory_growth < 200, f"Memory growth too high: {memory_growth:.2f} MB"
        
        if metrics['response_times']:
            avg_response_time = statistics.mean(metrics['response_times'])
            max_response_time = max(metrics['response_times'])
            
            print(f"Average API response time: {avg_response_time:.3f}s")
            print(f"Maximum API response time: {max_response_time:.3f}s")
            
            assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time:.3f}s"
            assert max_response_time < 5.0, f"Maximum response time too high: {max_response_time:.3f}s"
        
        if metrics['error_rates']:
            avg_error_rate = statistics.mean(metrics['error_rates'])
            
            print(f"Average error rate: {avg_error_rate:.1f}%")
            
            assert avg_error_rate < 5.0, f"Error rate too high: {avg_error_rate:.1f}%"
        
        print("Sustained load test completed successfully")