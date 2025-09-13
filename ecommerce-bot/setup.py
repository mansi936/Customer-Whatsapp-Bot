#!/usr/bin/env python3
"""
E-Commerce WhatsApp Bot Setup Script
Initializes the project structure and dependencies
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def create_env_file():
    """Create .env file with required configurations"""
    env_template = """# E-Commerce WhatsApp Bot Configuration

# Application Settings
DEBUG=True
HOST=0.0.0.0
PORT=8000
WORKERS=4

# EnableX Configuration
ENABLEX_APP_ID=688704c91808ff90f000ec85
ENABLEX_APP_KEY=quUyXyeyvyqyuuveMypaZeLanyVaHeJujy3y
ENABLEX_API_URL=https://api.enablex.io
ENABLEX_WEBHOOK_SECRET=your_webhook_secret
ENABLEX_WHATSAPP_NUMBER=919599425455

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
REDIS_SESSION_TTL=86400
REDIS_MAX_CONNECTIONS=50

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=ecommerce_bot
MONGODB_MAX_POOL_SIZE=50

# PostgreSQL Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ecommerce_bot
POSTGRES_POOL_SIZE=20

# LLM Configuration
LLM_PROVIDERS=["azure", "groq", "openai"]
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# MCP Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=5555
MCP_CLIENT_POOL_SIZE=5
MCP_CONNECTION_TIMEOUT=30
MCP_MAX_IDLE_TIME=300

# Amazon Personalize Configuration (Optional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
PERSONALIZE_CAMPAIGN_ARN=your_campaign_arn

# Azure Storage Configuration
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
AZURE_STORAGE_CONTAINER=product-images
AZURE_CDN_ENDPOINT=your_cdn_endpoint

# Try-On Service Configuration
TRYON_PROVIDER=google
GOOGLE_TRYON_API_KEY=your_google_api_key
NEO_TRYON_API_KEY=your_neo_api_key
BANANA_TRYON_API_KEY=your_banana_api_key

# Payment Gateway Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log

# Performance Configuration
ENABLE_METRICS=True
METRICS_PORT=9090
CONNECTION_WARMER_ENABLED=True
CONNECTION_WARMER_INTERVAL=60

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
"""
    
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, "w") as f:
            f.write(env_template)
        print("✅ Created .env file - Please update with your credentials")
    else:
        print("⚠️  .env file already exists")

def create_directories():
    """Create required directories"""
    directories = [
        "logs",
        "data",
        "tests",
        "scripts",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Created project directories")

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Update requirements.txt with comprehensive list
    requirements = """# Core Dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# MCP SDK (install from git if not on PyPI)
# mcp @ git+https://github.com/modelcontextprotocol/python-sdk.git

# Redis
redis==5.0.1
hiredis==2.2.3

# MongoDB
motor==3.3.2
pymongo==4.6.0

# PostgreSQL
asyncpg==0.29.0
sqlalchemy==2.0.23

# WhatsApp/EnableX
httpx==0.25.1
aiohttp==3.9.1

# LLM Providers
openai==1.3.7
anthropic==0.7.7
groq==0.2.0
azure-identity==1.15.0

# AWS Services
boto3==1.33.7
aiobotocore==2.9.0

# Azure Services
azure-storage-blob==12.19.0
azure-core==1.29.5

# Image Processing
Pillow==10.1.0
python-multipart==0.0.6

# Logging & Monitoring
structlog==23.2.0
prometheus-client==0.19.0

# Utils
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pendulum==3.0.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Development
black==23.11.0
flake8==6.1.0
mypy==1.7.1
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install some dependencies. Please check requirements.txt")

def create_docker_compose():
    """Create docker-compose.yml for local development"""
    docker_compose = """version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: ecommerce_bot
    volumes:
      - mongo_data:/data/db

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: ecommerce_bot
      POSTGRES_USER: ecommerce_user
      POSTGRES_PASSWORD: ecommerce_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  mongo_data:
  postgres_data:
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    print("✅ Created docker-compose.yml")

def create_makefile():
    """Create Makefile for common commands"""
    makefile = """# E-Commerce WhatsApp Bot Makefile

.PHONY: help install run test clean docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make run        - Run the application"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean cache files"
	@echo "  make docker-up  - Start Docker services"
	@echo "  make docker-down - Stop Docker services"

install:
	pip install -r requirements.txt

run-webhook:
	python -m uvicorn webhook.enablex_webhook:app --reload --port 8000

run-server:
	python server/mcp_server.py

run-all:
	make docker-up
	make run-webhook

test:
	pytest tests/ -v --cov=.

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

logs:
	tail -f logs/app.log
"""
    
    with open("Makefile", "w") as f:
        f.write(makefile)
    
    print("✅ Created Makefile")

def create_readme():
    """Create README.md with setup instructions"""
    readme = """# E-Commerce WhatsApp Bot

A comprehensive MCP-based WhatsApp bot for e-commerce with AI-powered features.

## Features
- 🔍 Product search with AI recommendations
- 🛒 Cart management
- 📦 Order processing
- 👔 Virtual try-on
- 💳 Payment integration
- 🤖 AI-powered conversation

## Quick Start

### Prerequisites
- Python 3.11+
- Redis
- MongoDB
- PostgreSQL
- Docker (optional)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ecommerce-bot
```

2. Run setup script:
```bash
python setup.py
```

3. Update `.env` file with your credentials

4. Start Docker services:
```bash
make docker-up
```

5. Run the application:
```bash
make run-webhook
```

## Architecture

The system consists of:
- **Webhook Layer**: Handles WhatsApp messages via EnableX
- **Client Layer**: MCP client with LLM integration
- **Server Layer**: MCP server providing e-commerce tools
- **Services Layer**: Redis, MongoDB, LLM, and other services

## Configuration

Edit `.env` file to configure:
- EnableX credentials
- Database connections
- LLM API keys
- Payment gateway credentials

## Development

### Running Tests
```bash
make test
```

### Code Formatting
```bash
black .
flake8 .
```

## API Documentation

Once running, visit:
- Webhook API: http://localhost:8000/docs
- Metrics: http://localhost:9090/metrics

## Support

For issues and questions, please create an issue in the repository.
"""
    
    with open("README.md", "w") as f:
        f.write(readme)
    
    print("✅ Created README.md")

def main():
    """Main setup function"""
    print("🚀 E-Commerce WhatsApp Bot Setup")
    print("=" * 50)
    
    # Create project structure
    create_directories()
    create_env_file()
    create_docker_compose()
    create_makefile()
    create_readme()
    
    # Install dependencies
    response = input("\n📦 Install Python dependencies? (y/n): ")
    if response.lower() == 'y':
        install_dependencies()
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("\nNext steps:")
    print("1. Update .env file with your credentials")
    print("2. Start Docker services: make docker-up")
    print("3. Run the application: make run-webhook")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()