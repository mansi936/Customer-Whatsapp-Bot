#!/usr/bin/env python3
"""
Main script to run the E-Commerce WhatsApp Bot
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_requirements():
    """Check if all requirements are met"""
    issues = []
    
    # Check for .env file
    if not Path(".env").exists():
        issues.append("⚠️  .env file not found. Run 'python setup.py' first")
    
    # Check for required directories
    required_dirs = ["logs", "data"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            Path(dir_name).mkdir(exist_ok=True)
            logger.info(f"Created directory: {dir_name}")
    
    # Check for Docker (optional)
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        logger.info("✅ Docker is available")
    except:
        issues.append("⚠️  Docker not found. You'll need to run Redis, MongoDB, and PostgreSQL manually")
    
    if issues:
        print("\n".join(issues))
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)

def start_services():
    """Start required services"""
    print("\n🚀 Starting E-Commerce WhatsApp Bot Services")
    print("=" * 50)
    
    # Check if Docker services are needed
    try:
        subprocess.run(["docker", "ps"], capture_output=True, check=True)
        response = input("\nStart Docker services (Redis, MongoDB, PostgreSQL)? (y/n): ")
        if response.lower() == 'y':
            print("Starting Docker services...")
            subprocess.run(["docker-compose", "up", "-d"], check=True)
            print("✅ Docker services started")
            # Wait for services to be ready
            import time
            time.sleep(5)
    except:
        print("⚠️  Docker not available. Ensure services are running manually")
    
    print("\n" + "=" * 50)

def run_webhook_server():
    """Run the FastAPI webhook server"""
    print("\n🌐 Starting Webhook Server...")
    print("=" * 50)
    
    try:
        # Run with uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "webhook.enablex_webhook:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n✋ Webhook server stopped")
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        sys.exit(1)

def run_mcp_server():
    """Run the MCP server in a separate process"""
    print("\n🔧 Starting MCP Server...")
    print("=" * 50)
    
    try:
        subprocess.run([sys.executable, "server/mcp_server.py"])
    except KeyboardInterrupt:
        print("\n\n✋ MCP server stopped")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")

def display_info():
    """Display useful information"""
    print("\n" + "=" * 50)
    print("📍 Service Endpoints:")
    print("  - Webhook API: http://localhost:8000")
    print("  - API Docs: http://localhost:8000/docs")
    print("  - Health Check: http://localhost:8000/health")
    print("\n📱 WhatsApp Integration:")
    print("  - Configure EnableX webhook URL: http://your-domain:8000/webhook/enablex")
    print("\n🛠️  Commands:")
    print("  - View logs: tail -f logs/app.log")
    print("  - Stop services: Ctrl+C")
    print("  - Stop Docker: docker-compose down")
    print("=" * 50 + "\n")

def main():
    """Main entry point"""
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     E-Commerce WhatsApp Bot - MCP Architecture   ║
    ╚══════════════════════════════════════════════════╝
    """)
    
    # Check requirements
    check_requirements()
    
    # Start services
    start_services()
    
    # Display information
    display_info()
    
    # Run webhook server (blocking)
    run_webhook_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)