import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dotenv import load_dotenv
import uuid
import time
import base64
import logging

# Load environment variables
load_dotenv()

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
import uvicorn

# Import from existing project structure
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.client_pool import ClientPool
from client.mcp_client import MCPClient
from services.redis.redis_adapter import RedisAdapter as EnhancedRedisService
from services.mongodb.mongodb_service import MongoUserService
from services.image_service import ImageService
from services.llm.unified_llm_service import get_llm_service
from services.llm.connection_warmer import get_llm_warmer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Dependencies:
    def __init__(self):
        self.client_pool: Optional[ClientPool] = None
        self.redis_service: Optional[EnhancedRedisService] = None
        self.mongo_service: Optional[MongoUserService] = None
        self.image_service: Optional[ImageService] = None
        self.llm_service = None
        self.llm_warmer = None


deps = Dependencies()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    try:
        # Initialize services
        try:
            deps.redis_service = EnhancedRedisService()
            await deps.redis_service.initialize()
            logger.info("Redis service initialized successfully")
        except Exception as e:
            logger.warning(f"Redis service initialization failed: {e}")
            logger.warning("Continuing without Redis - sessions will not persist")
            deps.redis_service = None
        
        # Initialize LLM service
        deps.llm_service = get_llm_service()
        await deps.llm_service.warm_connections()
        logger.info("LLM service initialized")
        
        # Initialize LLM connection warmer
        deps.llm_warmer = await get_llm_warmer()
        await deps.llm_warmer.start()
        logger.info("LLM connection warmer started")
        
        # Initialize client pool with dependencies
        try:
            deps.client_pool = ClientPool(
                pool_size=5,
                session_manager=deps.redis_service,
                server_manager=None  # Server manager will be initialized in ClientPool
            )
            await deps.client_pool.initialize()
            logger.info("Client pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize client pool: {e}")
            deps.client_pool = None
        
        # MongoDB connection
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri:
            deps.mongo_service = MongoUserService()
            # Note: MongoUserService might need initialization
        
        # Initialize image service (optional)
        try:
            deps.image_service = ImageService()
            if not deps.image_service.enabled:
                logger.warning("Image service disabled - image uploads will not be available")
                deps.image_service = None
        except Exception as e:
            logger.error(f"Failed to initialize image service: {e}")
            deps.image_service = None
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error("Startup error", exc_info=e)
        raise
    
    # Yield control to the application
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    
    # Stop LLM warmer
    if deps.llm_warmer:
        await deps.llm_warmer.stop()
    
    # Close client pool
    if deps.client_pool:
        await deps.client_pool.close()
        
    # Close redis connections
    if deps.redis_service:
        # Clean up redis connections if needed
        pass


app = FastAPI(title="E-commerce Bot - EnableX Webhook", lifespan=lifespan)


@app.post("/enablex/whatsapp/webhook")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming WhatsApp messages via EnableX"""
    # Generate unique request ID
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    
    try:
        # Get raw body first for debugging
        raw_body = await request.body()
        
        # Check if body is empty
        if not raw_body:
            logger.warning(f"Received empty webhook body (request_id: {request_id})")
            return JSONResponse({"status": "success", "message": "Empty body received"})
        
        # Try to parse JSON
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except Exception as json_error:
            logger.warning(f"Failed to parse JSON from webhook: {json_error}")
            return JSONResponse({"status": "error", "message": "Invalid JSON payload"})
        
        # Check if this is an incoming message
        if "messages" in body and body["messages"]:
            # Handle incoming messages
            for message in body["messages"]:
                from_number = message.get("from", "")
                message_type = message.get("type", "")
                message_id = message.get("id", "")
                
                # Normalize phone number
                if not from_number.startswith('+'):
                    from_number = '+' + from_number
                
                # Extract message content based on type
                message_body = ""
                media_urls = []
                
                if message_type == "text":
                    message_body = message.get("text", {}).get("body", "")
                elif message_type == "image":
                    image_data = message.get("image", {})
                    media_urls.append(image_data.get("fileLink", ""))
                    message_body = image_data.get("caption", "")
                elif message_type == "document":
                    doc_data = message.get("document", {})
                    media_urls.append(doc_data.get("fileLink", ""))
                    message_body = doc_data.get("caption", "")
                
                logger.info(f"Received WhatsApp message from {from_number}: {message_body}")
                
                # Process message in background
                background_tasks.add_task(
                    process_message,
                    from_number=from_number,
                    message_body=message_body,
                    media_urls=media_urls,
                    message_sid=message_id,
                    request_id=request_id
                )
        
        elif "statuses" in body and body["statuses"]:
            # Handle status updates
            for status in body["statuses"]:
                status_type = status.get("status", "")
                message_id = status.get("id", "")
                logger.info(f"Status update: {status_type} for message {message_id}")
        
        return JSONResponse({"status": "success", "message": "Webhook processed"})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)})


async def process_message(
    from_number: str,
    message_body: str,
    media_urls: list,
    message_sid: str,
    request_id: str
):
    """Process message asynchronously"""
    try:
        # Get or create user session
        session_key = f"session:{from_number}"
        session = {}
        
        if deps.redis_service:
            try:
                session_data = await deps.redis_service.get(session_key)
                if session_data:
                    session = json.loads(session_data)
            except Exception as e:
                logger.error(f"Error getting session: {e}")
        
        # Initialize session if needed
        if not session:
            session = {
                "user_id": from_number,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "conversation_history": []
            }
        
        # Handle media uploads if present
        uploaded_images = []
        if media_urls:
            if deps.image_service and deps.image_service.enabled:
                for url in media_urls:
                    try:
                        # Download media
                        image_data = await download_media(url)
                        if image_data:
                            # Upload to storage
                            image_url = await deps.image_service.upload_user_image(from_number, image_data)
                            uploaded_images.append(image_url)
                            logger.info(f"Uploaded image: {image_url}")
                    except Exception as e:
                        logger.error(f"Error processing media: {e}")
            else:
                logger.warning("Image service not available - media uploads will be skipped")
                # Still note the media was received but not processed
                for url in media_urls:
                    uploaded_images.append(f"[Media received but not processed: {url}]")
        
        # Build the message for processing
        full_message = message_body
        if uploaded_images:
            full_message = f"{message_body} [Images: {', '.join(uploaded_images)}]" if message_body else f"[Images: {', '.join(uploaded_images)}]"
        
        # Process with MCP client from pool
        response_text = "I'll help you with that."
        
        if deps.client_pool:
            try:
                # Get client from pool
                async with deps.client_pool.get_connection(from_number) as mcp_client:
                    # Process the message
                    result = await mcp_client.process_message(full_message)
                    response_text = result.get("reply", "I'll help you with that.")
                    
                    # Log connection stats
                    if hasattr(mcp_client, '_connection_id'):
                        logger.info(f"Used connection {mcp_client._connection_id} (reused: {mcp_client._was_reused})")
                        
            except Exception as e:
                logger.error(f"Error processing with MCP client: {e}")
                response_text = "Sorry, I couldn't process your message. Please try again."
        else:
            # Fallback if pool not available
            logger.warning("Client pool not available, using direct client")
            mcp_client = MCPClient(
                user_id=from_number,
                session_manager=deps.redis_service,
                server_manager=None
            )
            
            try:
                result = await mcp_client.process_message(full_message)
                response_text = result.get("reply", "I'll help you with that.")
            except Exception as e:
                logger.error(f"Error processing with MCP client: {e}")
                response_text = "Sorry, I couldn't process your message. Please try again."
        
        # Update session
        session["conversation_history"].append({
            "role": "user",
            "content": full_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        session["conversation_history"].append({
            "role": "assistant", 
            "content": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 20 messages
        session["conversation_history"] = session["conversation_history"][-20:]
        
        # Save session
        if deps.redis_service:
            try:
                await deps.redis_service.set(
                    session_key,
                    json.dumps(session),
                    ttl=86400  # 24 hours
                )
            except Exception as e:
                logger.error(f"Error saving session: {e}")
        
        # Send response via WhatsApp
        await send_whatsapp_message(from_number, response_text)
        
    except Exception as e:
        logger.error(f"Message processing error: {e}", exc_info=True)
        await send_whatsapp_message(
            from_number,
            "Sorry, I couldn't process your message. Please try again."
        )


async def download_media(url: str) -> Optional[bytes]:
    """Download media from EnableX URL"""
    try:
        # Get app credentials for Basic Auth
        app_id = os.getenv("ENABLEX_APP_ID")
        app_key = os.getenv("ENABLEX_APP_KEY")
        
        if not app_id or not app_key:
            logger.error("EnableX credentials not configured")
            return None
        
        # Create Basic auth header
        auth_string = f"{app_id}:{app_key}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call EnableX get-media API
            response = await client.request(
                method="GET",
                url="https://api.enablex.io/whatsapp/v1/get-media",
                json={"fileLink": url},
                headers={
                    "Authorization": f"Basic {auth_b64}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Failed to download media: {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Media download error: {e}")
        return None


async def send_whatsapp_message(to_number: str, message: str, media_url: Optional[str] = None):
    """Send WhatsApp message via EnableX"""
    try:
        app_id = os.getenv("ENABLEX_APP_ID")
        app_key = os.getenv("ENABLEX_APP_KEY")
        from_number = os.getenv("ENABLEX_WHATSAPP_NUMBER")
        
        if not all([app_id, app_key, from_number]):
            logger.error("EnableX configuration incomplete")
            return
        
        url = "https://api.enablex.io/whatsapp/v1/messages"
        
        # Create auth header
        auth_string = f"{app_id}:{app_key}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        
        # Build payload
        payload = {
            "to": to_number,
            "from": from_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        # Add media if provided
        if media_url:
            payload["type"] = "image"
            del payload["text"]
            payload["image"] = {
                "link": media_url,
                "caption": message
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to send WhatsApp message: {response.text}")
            else:
                logger.info(f"WhatsApp message sent to {to_number}")
                
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_data = {
        "status": "healthy",
        "services": {
            "client_pool": deps.client_pool is not None,
            "redis": deps.redis_service is not None,
            "mongodb": deps.mongo_service is not None,
            "image_service": deps.image_service is not None
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Add pool statistics if available
    if deps.client_pool:
        health_data["pool_stats"] = deps.client_pool.get_stats()
        
    # Add LLM service statistics
    if deps.llm_service:
        health_data["llm_stats"] = deps.llm_service.get_stats()
    
    # Add LLM warmer statistics
    if deps.llm_warmer:
        health_data["llm_warmer_stats"] = deps.llm_warmer.get_stats()
        health_data["llm_provider_health"] = deps.llm_warmer.get_provider_health()
    
    return health_data


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
