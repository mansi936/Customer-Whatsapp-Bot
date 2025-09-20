import os
import io
import base64
from typing import Optional, Dict, Any, Tuple
from azure.storage.blob import BlobServiceClient, ContentSettings, PublicAccess
from PIL import Image
import logging
from datetime import datetime
import aiohttp
import asyncio

logger = logging.getLogger(__name__)


class ImageService:
    """Service for handling image storage and processing with Azure Blob Storage"""
    
    def __init__(self):
        # Azure configuration
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_service_client = None
        self.enabled = False
        
        if not self.connection_string:
            logger.warning("AZURE_STORAGE_CONNECTION_STRING not configured - image service will be disabled")
            return
        
        try:
            # Initialize BlobServiceClient
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            
            # Container names
            self.user_images_container = os.getenv("AZURE_USER_IMAGES_CONTAINER", "user-images")
            self.clothes_container = os.getenv("AZURE_CLOTHES_CONTAINER", "clothing-images")
            self.tryon_results_container = os.getenv("AZURE_TRYON_RESULTS_CONTAINER", "tryon-results")
            
            # Ensure containers exist with public access
            self._ensure_containers()
            self.enabled = True
            
            logger.info(f"ImageService initialized successfully - user_container: {self.user_images_container}, "
                       f"clothes_container: {self.clothes_container}, "
                       f"tryon_container: {self.tryon_results_container}")
        except Exception as e:
            logger.error(f"Failed to initialize ImageService: {e}")
            logger.warning("ImageService will be disabled - image uploads will not be available")
            self.blob_service_client = None
            self.enabled = False
    
    def _ensure_containers(self):
        """Ensure all containers exist with public blob access"""
        containers = [
            self.user_images_container,
            self.clothes_container,
            self.tryon_results_container
        ]
        
        for container_name in containers:
            try:
                container_client = self.blob_service_client.get_container_client(container_name)
                # Check if container exists
                try:
                    container_client.get_container_properties()
                    logger.info(f"Container exists: {container_name}")
                except:
                    # Create container with public access
                    container_client = self.blob_service_client.create_container(
                        container_name,
                        public_access=PublicAccess.Blob
                    )
                    logger.info(f"Created container with public access: {container_name}")
            except Exception as e:
                logger.error(f"Error ensuring container {container_name}: {e}")
    
    async def upload_image(self, image_data: bytes, key: str, container_type: str = "user") -> str:
        """Upload image to Azure Blob Storage with public access and return URL"""
        if not self.enabled or not self.blob_service_client:
            raise ValueError("ImageService is not enabled - Azure storage not configured")
        
        try:
            # Determine container based on image type
            if container_type == "user":
                container_name = self.user_images_container
            elif container_type == "clothes":
                container_name = self.clothes_container
            elif container_type == "tryon_result":
                container_name = self.tryon_results_container
            else:
                container_name = self.user_images_container
            
            # Get container client
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(key)
            
            # Determine content type
            content_type = "image/jpeg"
            if key.lower().endswith('.png'):
                content_type = "image/png"
            elif key.lower().endswith('.webp'):
                content_type = "image/webp"
            
            # Upload with content settings for proper MIME type
            blob_client.upload_blob(
                image_data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            
            # Get the public URL
            url = blob_client.url
            
            logger.info("Image uploaded to Azure with public access", 
                       key=key, 
                       container=container_name,
                       url=url)
            return url
            
        except Exception as e:
            logger.error("Azure image upload failed", 
                        key=key, 
                        container=container_name,
                        error=str(e))
            raise
    
    async def upload_user_image(self, phone_number: str, image_data: bytes) -> str:
        """Upload user image with standardized naming"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_phone = phone_number.replace("+", "").replace(" ", "")
        key = f"user_images/{safe_phone}_try_on_{timestamp}.jpg"
        return await self.upload_image(image_data, key, container_type="user")
    
    async def upload_clothes_image(self, sku: str, image_data: bytes) -> str:
        """Upload clothing image with SKU-based naming"""
        key = f"clothes/{sku}.jpg"
        return await self.upload_image(image_data, key, container_type="clothes")
    
    async def upload_tryon_result(self, phone_number: str, image_data: bytes) -> str:
        """Upload try-on result image"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_phone = phone_number.replace("+", "").replace(" ", "")
        key = f"tryon_results/{safe_phone}_result_{timestamp}.jpg"
        return await self.upload_image(image_data, key, container_type="tryon_result")
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download image: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error("Image download failed", url=url, error=str(e))
            return None
    
    async def download_from_blob(self, key: str, container_type: str = "user") -> Optional[bytes]:
        """Download image from Azure Blob Storage"""
        try:
            # Determine container
            if container_type == "user":
                container_name = self.user_images_container
            elif container_type == "clothes":
                container_name = self.clothes_container
            elif container_type == "tryon_result":
                container_name = self.tryon_results_container
            else:
                container_name = self.user_images_container
            
            # Get blob client
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(key)
            
            # Download blob
            download_stream = blob_client.download_blob()
            data = download_stream.readall()
            return data
            
        except Exception as e:
            logger.error("Azure blob download failed", key=key, container=container_name, error=str(e))
            return None
    
    async def validate_image(self, image_data: bytes) -> Dict[str, Any]:
        """Validate image for try-on processing"""
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Check image properties
            width, height = img.size
            format = img.format
            
            # Validation rules
            min_size = 256
            max_size = 4096
            valid_formats = ['JPEG', 'PNG', 'WEBP']
            
            is_valid = (
                width >= min_size and height >= min_size and
                width <= max_size and height <= max_size and
                format in valid_formats
            )
            
            return {
                "valid": is_valid,
                "width": width,
                "height": height,
                "format": format,
                "message": "Valid image" if is_valid else f"Image must be {min_size}x{min_size} to {max_size}x{max_size} pixels in JPEG/PNG format"
            }
            
        except Exception as e:
            logger.error("Image validation failed", error=str(e))
            return {
                "valid": False,
                "message": f"Invalid image: {str(e)}"
            }
    
    async def resize_image(self, image_data: bytes, max_size: int = 1024, quality: int = 85) -> bytes:
        """Resize and optimize image for processing"""
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ['RGBA', 'LA'] else None)
                img = rgb_img
            
            # Calculate new size while maintaining aspect ratio
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save to bytes with optimization
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            optimized_data = output.read()
            logger.info("Image optimized", 
                       original_size=len(image_data),
                       optimized_size=len(optimized_data),
                       dimensions=f"{img.width}x{img.height}")
            
            return optimized_data
            
        except Exception as e:
            logger.error("Image resize failed", error=str(e))
            raise
    
    async def prepare_image_for_gemini(self, image_data: bytes) -> Tuple[bytes, str]:
        """Prepare image for Gemini API (resize if needed and determine MIME type)"""
        try:
            # Validate image
            validation = await self.validate_image(image_data)
            if not validation["valid"]:
                raise ValueError(validation["message"])
            
            # Resize if too large (Gemini has size limits)
            img = Image.open(io.BytesIO(image_data))
            if img.width > 2048 or img.height > 2048:
                image_data = await self.resize_image(image_data, max_size=2048)
            
            # Determine MIME type
            format_to_mime = {
                'JPEG': 'image/jpeg',
                'PNG': 'image/png',
                'WEBP': 'image/webp'
            }
            mime_type = format_to_mime.get(validation["format"], 'image/jpeg')
            
            return image_data, mime_type
            
        except Exception as e:
            logger.error("Failed to prepare image for Gemini", error=str(e))
            raise
    
    def image_to_base64(self, image_data: bytes) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def base64_to_image(self, base64_string: str) -> bytes:
        """Convert base64 string to image bytes"""
        return base64.b64decode(base64_string)
    
    async def verify_public_access(self, url: str) -> bool:
        """Verify if the URL is publicly accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Public access check failed: {e}")
            return False
    
    async def delete_image(self, key: str, container_type: str = "user") -> bool:
        """Delete image from Azure Blob Storage"""
        try:
            # Determine container
            if container_type == "user":
                container_name = self.user_images_container
            elif container_type == "clothes":
                container_name = self.clothes_container
            elif container_type == "tryon_result":
                container_name = self.tryon_results_container
            else:
                container_name = self.user_images_container
            
            # Get blob client
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(key)
            
            blob_client.delete_blob()
            logger.info(f"Deleted image: {key} from container: {container_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False
    
    def get_blob_url(self, key: str, container_type: str = "user") -> str:
        """Get public URL for a blob"""
        # Determine container
        if container_type == "user":
            container_name = self.user_images_container
        elif container_type == "clothes":
            container_name = self.clothes_container
        elif container_type == "tryon_result":
            container_name = self.tryon_results_container
        else:
            container_name = self.user_images_container
        
        container_client = self.blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(key)
        return blob_client.url