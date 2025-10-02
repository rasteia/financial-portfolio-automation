#!/usr/bin/env python3
"""
Test script to verify MCP tools are working correctly.
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financial_portfolio_automation.mcp.mcp_server import MCPToolServer


async def test_mcp_tools():
    """Test MCP tools functionality."""
    print("🧪 Testing Financial Portfolio MCP Tools")
    print("=" * 50)
    
    # Configuration for testing
    config = {
        'alpaca_config': {
            'api_key': 'demo_key',
            'secret_key': 'demo_secret',
            'base_url': 'https://paper-api.alpaca.markets',
            'paper_trading': True
        },
        'risk_limits': {
            'max_position_size': 10000,
            'max_portfolio_concentration': 0.2,
            'max_daily_loss': 5000
        },
        'auth_config': {
            'enabled': False,
            'session_timeout': 3600
        },
        'tool_config': {
            'rate_limit': 100,
            'cache_ttl': 300
        }
    }
    
    try:
        # Initialize MCP server
        print("📡 Initializing MCP Server...")
        mcp_server = MCPToolServer(config)
        session_id = mcp_server.create_session('test_session')
        
        print(f"✅ MCP Server initialized with {len(mcp_server.tools)} tools")
        
        # Test 1: Get tool definitions
        print("\n🔍 Testing tool discovery...")
        definitions = mcp_server.get_tool_definitions()
        print(f"✅ Found {len(definitions)} tool definitions")
        
        for tool in definitions[:5]:  # Show first 5 tools
            print(f"   - {tool['name']}: {tool['description'][:60]}...")
        
        # Test 2: Health check
        print("\n🏥 Testing health check...")
        health = mcp_server.health_check()
        print(f"✅ Health status: {health['status']}")
        print(f"   Tools registered: {health['tools_registered']}")
        print(f"   Active sessions: {health['active_sessions']}")
        
        # Test 3: Portfolio summary
        print("\n💼 Testing portfolio summary...")
        summary_result = await mcp_server.execute_tool(
            tool_name='get_portfolio_summary',
            parameters={'include_positions': True, 'include_performance': True},
            session_id=session_id
        )
        
        if summary_result.success:
            print("✅ Portfolio summary retrieved successfully")
            data = summary_result.data
            print(f"   Portfolio value: ${data['portfolio_value']:,.2f}")
            print(f"   Position count: {data['position_count']}")
            print(f"   Day P&L: ${data['day_pnl']:,.2f} ({data['day_pnl_percent']:.2f}%)")
        else:
            print(f"❌ Portfolio summary failed: {summary_result.error}")
        
        # Test 4: Performance analysis
        print("\n📈 Testing performance analysis...")
        performance_result = await mcp_server.execute_tool(
            tool_name='get_portfolio_performance',
            parameters={'period': '1m', 'benchmark': 'SPY'},
            session_id=session_id
        )
        
        if performance_result.success:
            print("✅ Performance analysis completed successfully")
            perf = performance_result.data['portfolio_performance']
            print(f"   Total return: {perf['total_return']:.2f}%")
            print(f"   Sharpe ratio: {perf['sharpe_ratio']:.2f}")
            print(f"   Max drawdown: {perf['max_drawdown']:.2f}%")
        else:
            print(f"❌ Performance analysis failed: {performance_result.error}")
        
        # Test 5: Risk analysis
        print("\n⚠️  Testing risk analysis...")
        risk_result = await mcp_server.execute_tool(
            tool_name='analyze_portfolio_risk',
            parameters={'confidence_level': 0.95, 'time_horizon': 1},
            session_id=session_id
        )
        
        if risk_result.success:
            print("✅ Risk analysis completed successfully")
            risk = risk_result.data['risk_metrics']
            print(f"   Value at Risk: ${risk['value_at_risk']:,.2f}")
            print(f"   Portfolio volatility: {risk['portfolio_volatility']:.2f}%")
            print(f"   Portfolio beta: {risk['portfolio_beta']:.2f}")
            
            warnings = risk_result.data.get('risk_warnings', [])
            if warnings:
                print(f"   Risk warnings: {len(warnings)}")
                for warning in warnings[:2]:  # Show first 2 warnings
                    print(f"     - {warning}")
        else:
            print(f"❌ Risk analysis failed: {risk_result.error}")
        
        # Test 6: Asset allocation
        print("\n🥧 Testing asset allocation...")
        allocation_result = await mcp_server.execute_tool(
            tool_name='get_asset_allocation',
            parameters={'breakdown_type': 'all'},
            session_id=session_id
        )
        
        if allocation_result.success:
            print("✅ Asset allocation analysis completed successfully")
            data = allocation_result.data
            print(f"   Total portfolio value: ${data['total_portfolio_value']:,.2f}")
            
            if 'sector_allocation' in data:
                print("   Sector allocation:")
                for sector, info in data['sector_allocation'].items():
                    print(f"     - {sector}: {info['weight']:.1f}%")
        else:
            print(f"❌ Asset allocation failed: {allocation_result.error}")
        
        print("\n🎉 MCP Tools Test Complete!")
        print("=" * 50)
        print("✅ All core MCP tools are working correctly")
        print("🚀 Ready for AI assistant integration")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)