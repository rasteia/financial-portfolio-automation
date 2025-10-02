#!/usr/bin/env python3
"""
MCP Server entry point for financial portfolio automation tools.

This module provides the main entry point for running the MCP server
that exposes financial portfolio management tools to AI assistants.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Any

from .mcp_server import MCPToolServer


def load_config() -> Dict[str, Any]:
    """Load configuration for MCP server."""
    # Default configuration for MCP server
    default_config = {
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
            'enabled': False,  # Disabled for MCP integration
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
    
    # Try to load from config file if available
    try:
        with open('config/config.json', 'r') as f:
            file_config = json.load(f)
            default_config.update(file_config)
    except FileNotFoundError:
        # Use default config if file doesn't exist
        pass
    except Exception as e:
        logging.warning(f"Error loading config file: {e}")
    
    return default_config


async def main():
    """Main entry point for MCP server."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Financial Portfolio MCP Server")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize MCP server
        mcp_server = MCPToolServer(config)
        
        # Create a simple session for MCP integration
        session_id = mcp_server.create_session('mcp_integration_session')
        
        logger.info(f"MCP Server initialized with {len(mcp_server.tools)} tools")
        
        # Print available tools for debugging
        tools = mcp_server.get_tool_definitions()
        logger.info("Available tools:")
        for tool in tools:
            logger.info(f"  - {tool['name']}: {tool['description']}")
        
        # Simple MCP protocol handler
        while True:
            try:
                # Read JSON-RPC message from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                
                try:
                    request = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                
                # Handle MCP requests
                if request.get('method') == 'tools/list':
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': {
                            'tools': [
                                {
                                    'name': tool['name'],
                                    'description': tool['description'],
                                    'inputSchema': tool['parameters']
                                }
                                for tool in tools
                            ]
                        }
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                
                elif request.get('method') == 'tools/call':
                    tool_name = request.get('params', {}).get('name')
                    arguments = request.get('params', {}).get('arguments', {})
                    
                    # Execute tool
                    result = await mcp_server.execute_tool(
                        tool_name=tool_name,
                        parameters=arguments,
                        session_id=session_id
                    )
                    
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': {
                            'content': [
                                {
                                    'type': 'text',
                                    'text': json.dumps(result.to_dict(), indent=2)
                                }
                            ]
                        }
                    }
                    
                    if not result.success:
                        response['error'] = {
                            'code': -1,
                            'message': result.error
                        }
                    
                    print(json.dumps(response))
                    sys.stdout.flush()
                
                elif request.get('method') == 'initialize':
                    response = {
                        'jsonrpc': '2.0',
                        'id': request.get('id'),
                        'result': {
                            'protocolVersion': '2024-11-05',
                            'capabilities': {
                                'tools': {}
                            },
                            'serverInfo': {
                                'name': 'financial-portfolio-automation',
                                'version': '1.0.0'
                            }
                        }
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                error_response = {
                    'jsonrpc': '2.0',
                    'id': request.get('id') if 'request' in locals() else None,
                    'error': {
                        'code': -32603,
                        'message': f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()
    
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())