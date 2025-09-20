#!/usr/bin/env python3
"""Diagnose MCP server startup issues"""
import subprocess
import sys
import os
import asyncio
from pathlib import Path

def test_direct_server_run():
    """Test running the MCP server directly"""
    server_path = Path(__file__).parent / "server" / "mcp_server.py"
    
    print(f"Testing MCP server at: {server_path}")
    print(f"Server exists: {server_path.exists()}")
    
    if not server_path.exists():
        print("❌ Server file not found!")
        return
    
    print("\n" + "="*50)
    print("Running server with --help flag:")
    try:
        result = subprocess.run(
            [sys.executable, str(server_path), "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏱️ Server timed out - this might be normal for STDIO mode")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_mcp_imports():
    """Test if MCP modules can be imported"""
    print("\n" + "="*50)
    print("Testing MCP imports:")
    
    modules = [
        "mcp",
        "mcp.server",
        "mcp.server.fastmcp",
        "mcp.client",
        "mcp.client.stdio"
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")

async def test_stdio_connection():
    """Test STDIO connection to MCP server"""
    print("\n" + "="*50)
    print("Testing STDIO connection:")
    
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        
        server_path = Path(__file__).parent / "server" / "mcp_server.py"
        
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[str(server_path)],
            env=None
        )
        
        print(f"Command: {server_params.command}")
        print(f"Args: {server_params.args}")
        
        # Try to establish connection
        try:
            async with stdio_client(server_params) as (read, write):
                print("✅ STDIO connection established")
                
                async with ClientSession(read, write) as session:
                    print("✅ Client session created")
                    
                    # Try to initialize
                    await session.initialize()
                    print("✅ Session initialized")
                    
                    # List tools
                    response = await session.list_tools()
                    print(f"✅ Found {len(response.tools)} tools")
                    
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")

def check_server_syntax():
    """Check server file for syntax errors"""
    print("\n" + "="*50)
    print("Checking server syntax:")
    
    server_path = Path(__file__).parent / "server" / "mcp_server.py"
    
    try:
        with open(server_path, 'r') as f:
            code = f.read()
        
        compile(code, str(server_path), 'exec')
        print("✅ Server syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error in server: {e}")
    except Exception as e:
        print(f"❌ Error checking syntax: {e}")

def test_simple_server():
    """Create and test a minimal MCP server"""
    print("\n" + "="*50)
    print("Testing minimal MCP server:")
    
    minimal_server = '''#!/usr/bin/env python3
import sys
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("test")
    
    @mcp.tool()
    async def test_tool() -> str:
        return "Test successful"
    
    if __name__ == "__main__":
        mcp.run(transport="stdio")
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
'''
    
    # Write minimal server
    test_server_path = Path(__file__).parent / "test_minimal_server.py"
    test_server_path.write_text(minimal_server)
    
    # Test it
    try:
        result = subprocess.run(
            [sys.executable, str(test_server_path), "--help"],
            capture_output=True,
            text=True,
            timeout=2
        )
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⏱️ Minimal server timed out")
    finally:
        # Clean up
        if test_server_path.exists():
            test_server_path.unlink()

if __name__ == "__main__":
    print("MCP Server Diagnostics")
    print("=" * 60)
    
    test_mcp_imports()
    check_server_syntax()
    test_direct_server_run()
    test_simple_server()
    
    print("\nRunning async STDIO test...")
    asyncio.run(test_stdio_connection())