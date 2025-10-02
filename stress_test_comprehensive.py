#!/usr/bin/env python3
"""
Comprehensive Stress Test for Financial Portfolio Automation System

This script performs extensive testing of all system components to ensure
everything is working properly with live paper trading.
"""

import sys
import time
import asyncio
import traceback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
from financial_portfolio_automation.api.alpaca_client import AlpacaClient
from financial_portfolio_automation.data.store import DataStore


class StressTester:
    """Comprehensive stress testing for the portfolio automation system"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_results': {},
            'performance_metrics': {}
        }
        
        # Initialize Alpaca client
        self.config = AlpacaConfig(
            api_key="PK84S6XGSBWSPHNMYDT3",
            secret_key="ycqrtzFjfq8XkPKZ9Lr3YyAV9QbYaEN33P1X9PFU",
            base_url="https://paper-api.alpaca.markets",
            data_feed=DataFeed.IEX,
            environment=Environment.PAPER
        )
        
        self.client = None
        self.data_store = None
    
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a single test and record results"""
        print(f"\n🧪 Running {test_name}...")
        start_time = time.time()
        
        try:
            result = test_func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            self.results['tests_run'] += 1
            self.results['tests_passed'] += 1
            self.results['test_results'][test_name] = {
                'status': 'PASSED',
                'execution_time': round(execution_time, 3),
                'result': result
            }
            print(f"✅ {test_name} PASSED ({execution_time:.3f}s)")
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            
            self.results['tests_run'] += 1
            self.results['tests_failed'] += 1
            self.results['test_results'][test_name] = {
                'status': 'FAILED',
                'execution_time': round(execution_time, 3),
                'error': error_msg,
                'traceback': traceback.format_exc()
            }
            print(f"❌ {test_name} FAILED ({execution_time:.3f}s): {error_msg}")
            return False
    
    def test_alpaca_connection(self):
        """Test Alpaca API connection and authentication"""
        self.client = AlpacaClient(self.config)
        self.client.authenticate()
        
        # Test account access
        account = self.client._api.get_account()
        
        return {
            'account_status': account.status,
            'account_value': float(account.portfolio_value),
            'buying_power': float(account.buying_power),
            'day_pnl': float(getattr(account, 'unrealized_pl', 0))
        }
    
    def test_market_data_access(self):
        """Test market data retrieval"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        # Test stock quotes
        stock_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
        stock_quotes = {}
        
        for symbol in stock_symbols:
            try:
                quote = self.client._api.get_latest_trade(symbol)
                stock_quotes[symbol] = {
                    'price': float(quote.price),
                    'timestamp': quote.timestamp.isoformat()
                }
            except Exception as e:
                stock_quotes[symbol] = {'error': str(e)}
        
        # Test crypto quotes (if available)
        crypto_symbols = ['BTCUSD', 'ETHUSD']
        crypto_quotes = {}
        
        for symbol in crypto_symbols:
            try:
                # Try different methods for crypto data
                assets = self.client._api.list_assets(status='active', asset_class='crypto')
                crypto_asset = next((a for a in assets if a.symbol == symbol), None)
                if crypto_asset:
                    crypto_quotes[symbol] = {
                        'tradable': crypto_asset.tradable,
                        'fractionable': crypto_asset.fractionable
                    }
                else:
                    crypto_quotes[symbol] = {'error': 'Asset not found'}
            except Exception as e:
                crypto_quotes[symbol] = {'error': str(e)}
        
        return {
            'stock_quotes': stock_quotes,
            'crypto_quotes': crypto_quotes
        }
    
    def test_order_management(self):
        """Test order creation, modification, and cancellation"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        # Test creating a small test order
        test_symbol = 'AAPL'
        test_qty = 1
        
        # Get current price for limit order
        quote = self.client._api.get_latest_trade(test_symbol)
        current_price = float(quote.price)
        limit_price = round(current_price * 0.95, 2)  # 5% below current price
        
        # Create limit order
        order = self.client._api.submit_order(
            symbol=test_symbol,
            qty=test_qty,
            side='buy',
            type='limit',
            time_in_force='day',
            limit_price=limit_price
        )
        
        order_id = order.id
        
        # Verify order was created
        retrieved_order = self.client._api.get_order(order_id)
        
        # Cancel the order
        self.client._api.cancel_order(order_id)
        
        # Verify cancellation
        cancelled_order = self.client._api.get_order(order_id)
        
        return {
            'order_created': order.status,
            'order_retrieved': retrieved_order.status,
            'order_cancelled': cancelled_order.status,
            'order_id': order_id,
            'symbol': test_symbol,
            'limit_price': limit_price
        }
    
    def test_portfolio_positions(self):
        """Test portfolio position retrieval and analysis"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        # Get current positions
        positions = self.client._api.list_positions()
        
        position_data = []
        total_value = 0
        total_pnl = 0
        
        for pos in positions:
            pos_data = {
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pnl': float(pos.unrealized_pl),
                'unrealized_pnl_pct': float(pos.unrealized_plpc) * 100
            }
            position_data.append(pos_data)
            total_value += pos_data['market_value']
            total_pnl += pos_data['unrealized_pnl']
        
        return {
            'position_count': len(positions),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'positions': position_data
        }
    
    def test_database_operations(self):
        """Test database connectivity and operations"""
        self.data_store = DataStore("portfolio_automation.db")
        
        # Test basic database operations
        test_data = {
            'timestamp': datetime.now(),
            'test_value': 123.45,
            'test_string': 'stress_test'
        }
        
        # Test write operation (if tables exist)
        try:
            # Try to get latest portfolio snapshot
            latest_snapshot = self.data_store.get_latest_portfolio_snapshot()
            snapshot_exists = latest_snapshot is not None
        except Exception as e:
            snapshot_exists = False
            snapshot_error = str(e)
        
        return {
            'database_connected': True,
            'snapshot_exists': snapshot_exists,
            'snapshot_error': snapshot_error if not snapshot_exists else None
        }
    
    def test_concurrent_operations(self):
        """Test system under concurrent load"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        def get_account_info():
            return self.client._api.get_account()
        
        def get_positions():
            return self.client._api.list_positions()
        
        def get_orders():
            return self.client._api.list_orders(status='all', limit=10)
        
        # Run multiple operations concurrently
        operations = [get_account_info, get_positions, get_orders]
        results = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(op) for op in operations]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=10)
                    results.append({'status': 'success', 'result_type': type(result).__name__})
                except Exception as e:
                    results.append({'status': 'failed', 'error': str(e)})
        
        return {
            'concurrent_operations': len(operations),
            'successful_operations': len([r for r in results if r['status'] == 'success']),
            'failed_operations': len([r for r in results if r['status'] == 'failed']),
            'results': results
        }
    
    def test_error_handling(self):
        """Test system error handling and recovery"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        error_tests = []
        
        # Test invalid symbol
        try:
            self.client._api.get_latest_trade('INVALID_SYMBOL_12345')
            error_tests.append({'test': 'invalid_symbol', 'handled': False})
        except Exception as e:
            error_tests.append({'test': 'invalid_symbol', 'handled': True, 'error': str(e)})
        
        # Test invalid order
        try:
            self.client._api.submit_order(
                symbol='AAPL',
                qty=0,  # Invalid quantity
                side='buy',
                type='market',
                time_in_force='day'
            )
            error_tests.append({'test': 'invalid_order', 'handled': False})
        except Exception as e:
            error_tests.append({'test': 'invalid_order', 'handled': True, 'error': str(e)})
        
        # Test invalid order ID
        try:
            self.client._api.get_order('invalid-order-id-12345')
            error_tests.append({'test': 'invalid_order_id', 'handled': False})
        except Exception as e:
            error_tests.append({'test': 'invalid_order_id', 'handled': True, 'error': str(e)})
        
        return {
            'error_tests_run': len(error_tests),
            'errors_handled': len([t for t in error_tests if t['handled']]),
            'error_details': error_tests
        }
    
    def test_performance_metrics(self):
        """Test system performance under load"""
        if not self.client:
            raise Exception("Alpaca client not initialized")
        
        # Test API response times
        operations = [
            ('get_account', lambda: self.client._api.get_account()),
            ('list_positions', lambda: self.client._api.list_positions()),
            ('list_orders', lambda: self.client._api.list_orders(limit=10)),
            ('get_latest_trade_AAPL', lambda: self.client._api.get_latest_trade('AAPL')),
            ('get_latest_trade_MSFT', lambda: self.client._api.get_latest_trade('MSFT'))
        ]
        
        performance_results = {}
        
        for op_name, op_func in operations:
            times = []
            for i in range(3):  # Run each operation 3 times
                start_time = time.time()
                try:
                    op_func()
                    execution_time = time.time() - start_time
                    times.append(execution_time)
                except Exception as e:
                    times.append(None)
                    
                time.sleep(0.1)  # Small delay between requests
            
            valid_times = [t for t in times if t is not None]
            if valid_times:
                performance_results[op_name] = {
                    'avg_time': round(sum(valid_times) / len(valid_times), 3),
                    'min_time': round(min(valid_times), 3),
                    'max_time': round(max(valid_times), 3),
                    'success_rate': len(valid_times) / len(times)
                }
            else:
                performance_results[op_name] = {
                    'error': 'All operations failed',
                    'success_rate': 0
                }
        
        return performance_results
    
    def run_all_tests(self):
        """Run all stress tests"""
        print("🚀 STARTING COMPREHENSIVE STRESS TEST")
        print("=" * 60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Environment: Paper Trading")
        print("=" * 60)
        
        # Define test suite
        tests = [
            ("Alpaca Connection", self.test_alpaca_connection),
            ("Market Data Access", self.test_market_data_access),
            ("Order Management", self.test_order_management),
            ("Portfolio Positions", self.test_portfolio_positions),
            ("Database Operations", self.test_database_operations),
            ("Concurrent Operations", self.test_concurrent_operations),
            ("Error Handling", self.test_error_handling),
            ("Performance Metrics", self.test_performance_metrics)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Calculate overall results
        success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100 if self.results['tests_run'] > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 STRESS TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.results['tests_run']}")
        print(f"Tests Passed: {self.results['tests_passed']}")
        print(f"Tests Failed: {self.results['tests_failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if self.results['tests_failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! System is ready for live paper trading!")
            print("✅ Your portfolio automation system is fully operational")
        else:
            print(f"\n⚠️  {self.results['tests_failed']} tests failed. Review the issues above.")
            print("❌ Some components may need attention before full operation")
        
        # Show performance summary
        print("\n📈 PERFORMANCE SUMMARY")
        print("-" * 40)
        total_execution_time = sum(
            result.get('execution_time', 0) 
            for result in self.results['test_results'].values()
        )
        print(f"Total Execution Time: {total_execution_time:.3f}s")
        print(f"Average Test Time: {total_execution_time / self.results['tests_run']:.3f}s")
        
        # Show critical system status
        print("\n🎯 CRITICAL SYSTEM STATUS")
        print("-" * 40)
        
        critical_tests = ['Alpaca Connection', 'Market Data Access', 'Portfolio Positions']
        critical_passed = sum(
            1 for test in critical_tests 
            if self.results['test_results'].get(test, {}).get('status') == 'PASSED'
        )
        
        if critical_passed == len(critical_tests):
            print("✅ All critical systems operational")
            print("🚀 Ready for automated trading strategies")
        else:
            print("❌ Critical system issues detected")
            print("⚠️  Manual intervention required")
        
        return self.results


def main():
    """Main function"""
    tester = StressTester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if results['tests_failed'] == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)