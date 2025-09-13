import os
from typing import Dict, List, Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "E-Commerce WhatsApp Bot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server Settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    
    # EnableX Configuration
    ENABLEX_APP_ID: str = Field(..., env="ENABLEX_APP_ID")
    ENABLEX_APP_KEY: str = Field(..., env="ENABLEX_APP_KEY")
    ENABLEX_API_URL: str = Field(default="https://api.enablex.io", env="ENABLEX_API_URL")
    ENABLEX_WEBHOOK_SECRET: str = Field(..., env="ENABLEX_WEBHOOK_SECRET")
    ENABLEX_WHATSAPP_NUMBER: str = Field(..., env="ENABLEX_WHATSAPP_NUMBER")
    
    # Redis Configuration
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_SESSION_TTL: int = Field(default=86400, env="REDIS_SESSION_TTL")  # 24 hours
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # MongoDB Configuration
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    MONGODB_DATABASE: str = Field(default="ecommerce_bot", env="MONGODB_DATABASE")
    MONGODB_MAX_POOL_SIZE: int = Field(default=50, env="MONGODB_MAX_POOL_SIZE")
    
    # PostgreSQL Configuration
    POSTGRES_URL: str = Field(..., env="DATABASE_URL")
    POSTGRES_POOL_SIZE: int = Field(default=20, env="POSTGRES_POOL_SIZE")
    
    # LLM Configuration
    LLM_PROVIDERS: List[str] = Field(default=["azure", "groq", "openai"], env="LLM_PROVIDERS")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = Field(default=None, env="AZURE_OPENAI_DEPLOYMENT")
    GROQ_API_KEY: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4", env="LLM_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=2000, env="LLM_MAX_TOKENS")
    
    # MCP Configuration
    MCP_SERVER_HOST: str = Field(default="localhost", env="MCP_SERVER_HOST")
    MCP_SERVER_PORT: int = Field(default=5555, env="MCP_SERVER_PORT")
    MCP_CLIENT_POOL_SIZE: int = Field(default=5, env="MCP_CLIENT_POOL_SIZE")
    MCP_CONNECTION_TIMEOUT: int = Field(default=30, env="MCP_CONNECTION_TIMEOUT")
    MCP_MAX_IDLE_TIME: int = Field(default=300, env="MCP_MAX_IDLE_TIME")
    
    # Amazon Personalize Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    PERSONALIZE_CAMPAIGN_ARN: Optional[str] = Field(default=None, env="PERSONALIZE_CAMPAIGN_ARN")
    
    # Azure Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = Field(default=None, env="AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER: str = Field(default="product-images", env="AZURE_STORAGE_CONTAINER")
    AZURE_CDN_ENDPOINT: Optional[str] = Field(default=None, env="AZURE_CDN_ENDPOINT")
    
    # Try-On Service Configuration
    TRYON_PROVIDER: str = Field(default="google", env="TRYON_PROVIDER")  # google, neo, banana
    GOOGLE_TRYON_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_TRYON_API_KEY")
    NEO_TRYON_API_KEY: Optional[str] = Field(default=None, env="NEO_TRYON_API_KEY")
    BANANA_TRYON_API_KEY: Optional[str] = Field(default=None, env="BANANA_TRYON_API_KEY")
    
    # Payment Gateway Configuration
    RAZORPAY_KEY_ID: Optional[str] = Field(default=None, env="RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: Optional[str] = Field(default=None, env="RAZORPAY_KEY_SECRET")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE: str = Field(default="logs/app.log", env="LOG_FILE")
    
    # Performance Configuration
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    CONNECTION_WARMER_ENABLED: bool = Field(default=True, env="CONNECTION_WARMER_ENABLED")
    CONNECTION_WARMER_INTERVAL: int = Field(default=60, env="CONNECTION_WARMER_INTERVAL")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Redis Session Schema
REDIS_SESSION_SCHEMA = {
    "version": "1.0",
    "structure": {
        "user_id": "string",
        "phone_number": "string",
        "created_at": "timestamp",
        "updated_at": "timestamp",
        "expires_at": "timestamp",
        "user_data": {
            "profile": {
                "name": "string",
                "email": "string",
                "preferences": {
                    "categories": ["string"],
                    "brands": ["string"],
                    "price_range": {
                        "min": "number",
                        "max": "number"
                    }
                }
            },
            "metrics": {
                "total_orders": "number",
                "total_spent": "number",
                "last_order_date": "timestamp"
            }
        },
        "cart": {
            "items": [
                {
                    "product_id": "string",
                    "product_name": "string",
                    "quantity": "number",
                    "price": "number",
                    "image_url": "string",
                    "attributes": "object"
                }
            ],
            "total_items": "number",
            "total_amount": "number",
            "discount": "number",
            "tax": "number",
            "final_amount": "number"
        },
        "conversation_context": {
            "history": [
                {
                    "timestamp": "timestamp",
                    "message": "string",
                    "response": "string",
                    "intent": "string"
                }
            ],
            "current_flow": "string",  # browsing|cart|checkout|support
            "last_activity": "timestamp",
            "ai_context": {
                "last_search": "string",
                "viewed_products": ["string"],
                "interested_categories": ["string"]
            }
        },
        "recommendations": {
            "personalized": ["string"],
            "viewed": ["string"],
            "cart_based": ["string"],
            "trending": ["string"]
        },
        "order_context": {
            "pending_order": {
                "order_id": "string",
                "status": "string",
                "payment_method": "string",
                "delivery_address": "object"
            },
            "last_order": "object"
        },
        "try_on_context": {
            "user_image_url": "string",
            "tried_products": ["string"],
            "saved_results": ["object"]
        }
    }
}