#!/usr/bin/env python3
"""Check MCP installation and dependencies"""
import sys
import os
import pkg_resources

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Virtual environment: {sys.prefix}")
print("\n" + "="*50 + "\n")

# Check for MCP package
try:
    import mcp
    print(f"✅ MCP module found: {mcp.__file__}")
    print(f"   Version: {pkg_resources.get_distribution('mcp').version}")
except ImportError as e:
    print(f"❌ MCP module not found: {e}")

# Check for other key dependencies
packages = ['fastmcp', 'mcp', 'openai', 'redis', 'azure.storage.blob']
print("\nPackage Status:")
for package in packages:
    try:
        if package == 'azure.storage.blob':
            from azure.storage import blob
            print(f"✅ {package}: Installed")
        else:
            dist = pkg_resources.get_distribution(package)
            print(f"✅ {package}: {dist.version}")
    except:
        print(f"❌ {package}: Not installed")

print("\n" + "="*50 + "\n")

# Try to run MCP server with proper Python
server_path = os.path.join(os.path.dirname(__file__), "server", "mcp_server.py")
print(f"Attempting to check MCP server at: {server_path}")

# Check if we can import the required MCP components
try:
    from mcp.server.fastmcp import FastMCP
    print("✅ FastMCP import successful")
except ImportError as e:
    print(f"❌ FastMCP import failed: {e}")