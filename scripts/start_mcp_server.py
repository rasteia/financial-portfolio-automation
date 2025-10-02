#!/usr/bin/env python3
"""
Script to start the Financial Portfolio MCP Server.
"""

import sys
import os
import subprocess

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == '__main__':
    # Run the MCP server module
    subprocess.run([
        sys.executable, '-m', 'financial_portfolio_automation.mcp'
    ], cwd=project_root)