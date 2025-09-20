#!/usr/bin/env python3
"""
Start the MCP Server
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path

def start_mcp_server():
    """Start the MCP server"""
    server_path = Path(__file__).parent / "server" / "mcp_server.py"
    
    if not server_path.exists():
        print(f"❌ MCP server not found at: {server_path}")
        return False
    
    print("🚀 Starting MCP Server...")
    print(f"📁 Server path: {server_path}")
    
    try:
        # Run the MCP server directly
        result = subprocess.run([
            sys.executable, str(server_path)
        ], check=True, capture_output=False)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start MCP server: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 MCP server stopped by user")
        return True

if __name__ == "__main__":
    start_mcp_server()