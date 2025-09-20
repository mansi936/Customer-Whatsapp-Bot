#!/usr/bin/env python3
"""
Environment Setup Helper
Helps create and validate .env files for the e-commerce bot
"""
import os
import sys
from pathlib import Path
import shutil
from typing import Dict, List, Optional


class EnvSetup:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.env_file = self.root_dir / ".env"
        self.env_example = self.root_dir / ".env.example"
        self.env_dev = self.root_dir / ".env.development"
        self.env_prod = self.root_dir / ".env.production"
        
    def create_env_from_example(self):
        """Create .env from .env.example if it doesn't exist"""
        if self.env_file.exists():
            response = input(".env file already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Keeping existing .env file")
                return False
                
        if self.env_example.exists():
            shutil.copy(self.env_example, self.env_file)
            print(f"Created {self.env_file} from {self.env_example}")
            print("Please edit .env and fill in your actual values")
            return True
        else:
            print(f"Error: {self.env_example} not found!")
            return False
            
    def validate_env_file(self):
        """Validate that required environment variables are set"""
        if not self.env_file.exists():
            print("Error: .env file not found!")
            return False
            
        required_vars = [
            # EnableX
            "ENABLEX_APP_ID",
            "ENABLEX_APP_KEY",
            "ENABLEX_WHATSAPP_NUMBER",
            
            # At least one LLM provider
            ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"],
            
            # Storage (at least one)
            ["AZURE_STORAGE_CONNECTION_STRING", "E2E_ACCESS_KEY_ID"],
            
            # Database
            "MONGODB_URI",
            "REDIS_HOST",
        ]
        
        # Read current .env
        env_vars = {}
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        missing = []
        warnings = []
        
        for var in required_vars:
            if isinstance(var, list):
                # At least one of these should be set
                if not any(v in env_vars and env_vars[v] and not env_vars[v].startswith('your_') for v in var):
                    missing.append(f"At least one of: {', '.join(var)}")
            else:
                if var not in env_vars or not env_vars[var] or env_vars[var].startswith('your_'):
                    missing.append(var)
                    
        # Check for placeholder values
        for key, value in env_vars.items():
            if value.startswith('your_') or value == 'REPLACE_ME':
                warnings.append(f"{key} still has placeholder value: {value}")
                
        if missing:
            print("\n❌ Missing required environment variables:")
            for var in missing:
                print(f"  - {var}")
                
        if warnings:
            print("\n⚠️  Environment variables with placeholder values:")
            for warning in warnings:
                print(f"  - {warning}")
                
        if not missing and not warnings:
            print("\n✅ All required environment variables are set!")
            return True
        else:
            print("\n📝 Please update your .env file with actual values")
            return False
            
    def setup_development(self):
        """Set up development environment"""
        print("\n🔧 Setting up development environment...")
        
        # Create .env if needed
        if not self.env_file.exists():
            self.create_env_from_example()
            
        # Merge development settings
        if self.env_dev.exists():
            response = input("Apply development settings? (Y/n): ")
            if response.lower() != 'n':
                print("Development settings will override values in .env when running in dev mode")
                print(f"See {self.env_dev} for development-specific settings")
        else:
            print(f"Development settings file not found: {self.env_dev}")
            
    def check_services(self):
        """Check if required services are running"""
        print("\n🔍 Checking local services...")
        
        services = {
            "MongoDB": ("localhost", 27017),
            "Redis": ("localhost", 6379),
        }
        
        import socket
        
        for service, (host, port) in services.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ {service} is running on {host}:{port}")
            else:
                print(f"❌ {service} is not running on {host}:{port}")
                
    def generate_secrets(self):
        """Generate secure random secrets"""
        import secrets
        
        print("\n🔐 Generating secure secrets...")
        
        webhook_secret = secrets.token_urlsafe(32)
        print(f"WEBHOOK_SIGNATURE_SECRET={webhook_secret}")
        
        print("\nAdd these to your .env file for enhanced security")
        
    def main(self):
        """Main setup process"""
        print("🚀 E-Commerce Bot Environment Setup")
        print("=" * 50)
        
        # Create .env from example
        if not self.env_file.exists():
            print("\n📄 Creating .env file...")
            self.create_env_from_example()
        else:
            print(f"\n📄 Found existing .env file at {self.env_file}")
            
        # Validate environment
        print("\n🔍 Validating environment variables...")
        self.validate_env_file()
        
        # Check services
        self.check_services()
        
        # Development setup
        response = input("\n📦 Set up for development? (y/N): ")
        if response.lower() == 'y':
            self.setup_development()
            
        # Generate secrets
        response = input("\n🔐 Generate secure secrets? (y/N): ")
        if response.lower() == 'y':
            self.generate_secrets()
            
        print("\n✨ Setup complete!")
        print("\nNext steps:")
        print("1. Edit .env and fill in your actual API keys and configuration")
        print("2. Start MongoDB and Redis if not running")
        print("3. Install Python dependencies: pip install -r requirements.txt")
        print("4. Run the webhook: python webhook/enablex_webhook.py")
        

if __name__ == "__main__":
    setup = EnvSetup()
    setup.main()