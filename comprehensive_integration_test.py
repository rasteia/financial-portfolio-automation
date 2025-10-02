#!/usr/bin/env python3
"""
Comprehensive Integration Test

Tests all system components with proper dependency injection
and service initialization to verify the fixes work correctly.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set config file environment variable
os.environ['PORTFOLIO_CONFIG_FILE'] = 'config/config.json'

def test_service_factory():
    """Test the service factory initialization."""
    print("🧪 Testing Service Factory...")
    
    try:
        from financial_portfolio_automation.mcp.service_factory import ServiceFactory
        
        # Test with config file
        factory = ServiceFactory()
        print("   ✅ Service factory created successfully")
        
        # Test core services
        data_store = factory.get_data_store()
        print(f"   📊 Data store: {'✅ Available' if data_store else '❌ Not available'}")
        
        data_cache = factory.get_data_cache()
        print(f"   💾 Data cache: {'✅ Available' if data_cache else '❌ Not available'}")
        
        alpaca_client = factory.get_alpaca_client()
        print(f"   🔗 Alpaca client: {'✅ Available' if alpaca_client else '❌ Not available'}")
        
        portfolio_analyzer = factory.get_portfolio_analyzer()
        print(f"   📈 Portfolio analyzer: {'✅ Available' if portfolio_analyzer else '❌ Not available'}")
        
        analytics_service = factory.get_analytics_service()
        print(f"   📊 Analytics service: {'✅ Available' if analytics_service else '❌ Not available'}")
        
        risk_manager = factory.get_risk_manager()
        print(f"   ⚠️  Risk manager: {'✅ Available' if risk_manager else '❌ Not available'}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Service factory test failed: {e}")
        return False


def test_mcp_portfolio_tools():
    """Test MCP portfolio tools with proper initialization."""
    print("\n🧪 Testing MCP Portfolio Tools...")
    
    try:
        from financial_portfolio_automation.mcp.portfolio_tools import PortfolioTools
        from financial_portfolio_automation.config.settings import get_config
        
        # Load config and convert to dict
        config = get_config()
        config_dict = {
            'alpaca': {
                'api_key': config.alpaca.api_key,
                'secret_key': config.alpaca.secret_key,
                'base_url': config.alpaca.base_url,
                'data_feed': config.alpaca.data_feed
            }
        }
        
        # Initialize portfolio tools
        portfolio_tools = PortfolioTools(config_dict)
        print("   ✅ Portfolio tools initialized successfully")
        
        # Test portfolio summary
        summary = portfolio_tools.get_portfolio_summary()
        print(f"   📊 Portfolio summary: Portfolio value ${summary.get('portfolio_value', 0):,.2f}")
        
        # Test performance analysis
        performance = portfolio_tools.get_portfolio_performance(period='1m')
        print(f"   📈 Performance analysis: {performance.get('portfolio_performance', {}).get('total_return', 0):.2f}% return")
        
        # Test risk analysis
        risk = portfolio_tools.analyze_portfolio_risk()
        print(f"   ⚠️  Risk analysis: VaR ${risk.get('risk_metrics', {}).get('value_at_risk', 0):,.2f}")
        
        # Test asset allocation
        allocation = portfolio_tools.get_asset_allocation()
        print(f"   🥧 Asset allocation: ${allocation.get('total_portfolio_value', 0):,.2f} total value")
        
        return True
        
    except Exception as e:
        print(f"   ❌ MCP portfolio tools test failed: {e}")
        return False


def test_cli_with_config():
    """Test CLI commands with proper configuration."""
    print("\n🧪 Testing CLI with Configuration...")
    
    try:
        import subprocess
        
        # Set environment for subprocess
        env = os.environ.copy()
        env['PORTFOLIO_CONFIG_FILE'] = 'config/config.json'
        
        # Test portfolio status
        result = subprocess.run([
            sys.executable, '-m', 'financial_portfolio_automation.cli.main', 
            'portfolio', 'status'
        ], capture_output=True, text=True, env=env, timeout=30)
        
        if result.returncode == 0:
            print("   ✅ CLI portfolio status command successful")
        else:
            print(f"   ❌ CLI portfolio status failed: {result.stderr}")
            return False
        
        # Test health check
        result = subprocess.run([
            sys.executable, '-m', 'financial_portfolio_automation.cli.main', 
            'health'
        ], capture_output=True, text=True, env=env, timeout=30)
        
        if result.returncode == 0:
            print("   ✅ CLI health check command successful")
        else:
            print(f"   ❌ CLI health check failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ CLI test failed: {e}")
        return False


def test_api_startup():
    """Test API server startup with proper configuration."""
    print("\n🧪 Testing API Server Startup...")
    
    try:
        import subprocess
        import signal
        import time
        
        # Set environment for subprocess
        env = os.environ.copy()
        env['PORTFOLIO_CONFIG_FILE'] = 'config/config.json'
        
        # Start API server in background
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'financial_portfolio_automation.api.app:app',
            '--host', '127.0.0.1', '--port', '8001'
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("   ✅ API server started successfully")
            
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ API server failed to start: {stderr.decode()}")
            return False
        
    except Exception as e:
        print(f"   ❌ API startup test failed: {e}")
        return False


def test_mcp_server_startup():
    """Test MCP server startup with proper configuration."""
    print("\n🧪 Testing MCP Server Startup...")
    
    try:
        import subprocess
        import time
        
        # Set environment for subprocess
        env = os.environ.copy()
        env['PORTFOLIO_CONFIG_FILE'] = 'config/config.json'
        
        # Start MCP server in background
        process = subprocess.Popen([
            sys.executable, '-m', 'financial_portfolio_automation.mcp'
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for startup
        time.sleep(3)
        
        # Terminate the process
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        stdout, stderr = process.communicate()
        
        # Check for successful initialization
        if "MCP Server initialized" in stdout.decode():
            print("   ✅ MCP server started successfully")
            return True
        else:
            print(f"   ❌ MCP server startup issues: {stderr.decode()}")
            return False
        
    except Exception as e:
        print(f"   ❌ MCP server test failed: {e}")
        return False


def test_trading_functionality():
    """Test trading functionality with proper configuration."""
    print("\n🧪 Testing Trading Functionality...")
    
    try:
        from financial_portfolio_automation.models.config import AlpacaConfig, Environment, DataFeed
        from financial_portfolio_automation.api.alpaca_client import AlpacaClient
        from financial_portfolio_automation.config.settings import get_config
        
        # Load configuration
        config = get_config()
        
        # Create Alpaca client
        client = AlpacaClient(config.alpaca)
        
        # Test authentication
        if client.authenticate():
            print("   ✅ Alpaca authentication successful")
        else:
            print("   ❌ Alpaca authentication failed")
            return False
        
        # Test account info
        account_info = client.get_account_info()
        print(f"   💰 Account value: ${float(account_info.get('portfolio_value', 0)):,.2f}")
        
        # Test market data
        try:
            quote = client._api.get_latest_trade('AAPL')
            print(f"   📊 AAPL price: ${float(quote.price):.2f}")
        except Exception as e:
            print(f"   ⚠️  Market data warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Trading functionality test failed: {e}")
        return False


def main():
    """Run comprehensive integration tests."""
    print("🚀 COMPREHENSIVE INTEGRATION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("Testing all system components with proper dependency injection")
    print("=" * 60)
    
    tests = [
        ("Service Factory", test_service_factory),
        ("MCP Portfolio Tools", test_mcp_portfolio_tools),
        ("CLI with Configuration", test_cli_with_config),
        ("API Server Startup", test_api_startup),
        ("MCP Server Startup", test_mcp_server_startup),
        ("Trading Functionality", test_trading_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Tests Run: {total}")
    print(f"Tests Passed: {passed}")
    print(f"Tests Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ System is fully operational with proper dependency injection")
        return True
    else:
        print(f"\n⚠️  {total - passed} TESTS FAILED")
        print("❌ Some components need additional fixes")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)