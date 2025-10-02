#!/usr/bin/env python3
"""
Messaging Gateway MCP Server
A standard MCP server for handling messaging operations and gateway functionality.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("MCP library not available, falling back to basic implementation", file=sys.stderr)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("messaging-gateway")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="send_message",
            description="Send a message through the messaging gateway",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "description": "The recipient of the message"
                    },
                    "message": {
                        "type": "string",
                        "description": "The message content"
                    },
                    "channel": {
                        "type": "string",
                        "description": "The channel to send through",
                        "default": "default"
                    }
                },
                "required": ["recipient", "message"]
            }
        ),
        Tool(
            name="get_message_status",
            description="Get the status of a previously sent message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "The ID of the message to check"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="list_channels",
            description="List available messaging channels",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="configure_channel",
            description="Configure a messaging channel",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {
                        "type": "string",
                        "description": "The channel name to configure"
                    },
                    "config": {
                        "type": "string",
                        "description": "JSON configuration string for the channel"
                    }
                },
                "required": ["channel", "config"]
            }
        ),
        Tool(
            name="get_gateway_status",
            description="Get the current status of the messaging gateway",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "send_message":
            return await send_message(arguments)
        elif name == "get_message_status":
            return await get_message_status(arguments)
        elif name == "list_channels":
            return await list_channels(arguments)
        elif name == "configure_channel":
            return await configure_channel(arguments)
        elif name == "get_gateway_status":
            return await get_gateway_status(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "error": str(e),
                "tool": name
            }, indent=2)
        )]

async def send_message(arguments: dict) -> List[TextContent]:
    """Send a message through the messaging gateway."""
    recipient = arguments.get("recipient")
    message = arguments.get("message")
    channel = arguments.get("channel", "default")
    
    # Simulate message sending
    result = {
        "status": "success",
        "message_id": f"msg_{hash(f'{recipient}{message}{channel}') % 10000}",
        "recipient": recipient,
        "channel": channel,
        "timestamp": "2025-09-22T21:54:00Z",
        "message_length": len(message)
    }
    
    logger.info(f"Message sent to {recipient} via {channel}")
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def get_message_status(arguments: dict) -> List[TextContent]:
    """Get the status of a previously sent message."""
    message_id = arguments.get("message_id")
    
    # Simulate status check
    result = {
        "message_id": message_id,
        "status": "delivered",
        "sent_at": "2025-09-22T21:54:00Z",
        "delivered_at": "2025-09-22T21:54:05Z",
        "attempts": 1
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def list_channels(arguments: dict) -> List[TextContent]:
    """List available messaging channels."""
    channels = {
        "default": {"status": "active", "type": "internal"},
        "email": {"status": "active", "type": "smtp"},
        "sms": {"status": "inactive", "type": "twilio"},
        "slack": {"status": "active", "type": "webhook"},
        "discord": {"status": "active", "type": "webhook"}
    }
    
    result = {
        "status": "success",
        "channels": channels,
        "total_channels": len(channels)
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def configure_channel(arguments: dict) -> List[TextContent]:
    """Configure a messaging channel."""
    channel = arguments.get("channel")
    config = arguments.get("config")
    
    try:
        config_data = json.loads(config)
        
        result = {
            "status": "success",
            "channel": channel,
            "configured": True,
            "config_applied": list(config_data.keys())
        }
        
        logger.info(f"Channel {channel} configured successfully")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    except json.JSONDecodeError as e:
        result = {
            "status": "error",
            "error": f"Invalid JSON configuration: {str(e)}",
            "channel": channel
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def get_gateway_status(arguments: dict) -> List[TextContent]:
    """Get the current status of the messaging gateway."""
    result = {
        "status": "operational",
        "uptime": "24h 15m",
        "messages_sent_today": 42,
        "active_channels": 4,
        "queue_size": 0,
        "last_maintenance": "2025-09-21T10:00:00Z"
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    """Main function to run the MCP server."""
    if not MCP_AVAILABLE:
        logger.error("MCP library not available. Please install: pip install mcp")
        sys.exit(1)
        
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Starting Messaging Gateway MCP Server...")
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server initialization error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)