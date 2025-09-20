import asyncio
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import logging
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
import sys
from pathlib import Path
import os
# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from image_service import ImageService

logger = logging.getLogger(__name__)

class TryOnService:
    def __init__(self):
        """Initialize the TryOn service with Google Gemini API."""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.enabled = False
        self.model = "gemini-2.5-flash-image-preview"
        
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured - TryOn service will be disabled")
        else:
            try:
                self.client = genai.Client(api_key=self.gemini_api_key)
                self.enabled = True
                logger.info("TryOn service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                logger.warning("TryOn service will be disabled")
        
        # Initialize image service (it handles its own errors)
        try:
            self.image_service = ImageService()
        except Exception as e:
            logger.error(f"Failed to initialize image service: {e}")
            self.image_service = None
    
    async def process_tryon(self, user_image_url: str, product_image_url: str, phone_number: Optional[str] = None) -> Dict[str, Any]:
        """Process virtual try-on with user and product images."""
        job_id = str(uuid.uuid4())
        
        if not self.enabled or not self.client:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": "TryOn service is not enabled",
                "message": "Virtual try-on service is not available. Please configure GEMINI_API_KEY."
            }
        
        if not self.image_service:
            return {
                "job_id": job_id,
                "status": "failed",
                "error": "Image service is not available",
                "message": "Image storage service is not configured."
            }
        
        try:
            # Download both images using image service
            logger.info(f"Downloading images for job {job_id}")
            user_image_bytes = await self.image_service.download_image(user_image_url)
            product_image_bytes = await self.image_service.download_image(product_image_url)
            
            if not user_image_bytes or not product_image_bytes:
                raise Exception("Failed to download one or both images")
            
            # Create the prompt for virtual try-on
            prompt = """
            You are a virtual try-on assistant. I'm providing two images:
            1. First image: A person wearing clothes
            2. Second image: A clothing item (shirt, dress, etc.)
            
            Generate a realistic image showing the person from the first image wearing the clothing item from the second image.
            Make sure:
            - The clothing fits naturally on the person's body
            - The person's face, pose, and background remain the same
            - The clothing's texture, color, and pattern are preserved accurately
            - The lighting and shadows are realistic
            - The overall image looks natural and professional
            """
            
            # Generate virtual try-on using Gemini
            logger.info(f"Generating virtual try-on for job {job_id}")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=user_image_bytes,
                        mime_type="image/jpeg"
                    ),
                    types.Part.from_bytes(
                        data=product_image_bytes,
                        mime_type="image/jpeg"
                    )
                ],
                generation_config=types.GenerationConfig(
                    temperature=0.4,
                    top_p=0.95,
                    top_k=64,
                    max_output_tokens=8192,
                    response_mime_type="image/jpeg"
                )
            )
            
            # Extract generated image
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        # Get the generated image data
                        generated_image_data = part.inline_data.data
                        
                        # Upload the generated image to storage
                        if phone_number:
                            image_url = await self.image_service.upload_tryon_result(
                                phone_number, 
                                generated_image_data
                            )
                        else:
                            # If no phone number provided, use a generic naming
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            key = f"tryon_results/anonymous_{job_id}_{timestamp}.jpg"
                            image_url = await self.image_service.upload_image(
                                generated_image_data,
                                key
                            )
                        
                        # Also include base64 for backward compatibility
                        image_base64 = base64.b64encode(generated_image_data).decode('utf-8')
                        
                        return {
                            "job_id": job_id,
                            "status": "completed",
                            "result": {
                                "image_url": image_url,
                                "image_base64": image_base64,
                                "mime_type": "image/jpeg",
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            "message": "Virtual try-on completed successfully"
                        }
            
            # If no image was generated
            return {
                "job_id": job_id,
                "status": "failed",
                "error": "No image generated",
                "message": "Failed to generate virtual try-on image"
            }
            
        except Exception as e:
            logger.error(f"Error processing try-on for job {job_id}: {str(e)}")
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(e),
                "message": "An error occurred during virtual try-on processing"
            }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a try-on job."""
        # In this implementation, jobs are processed synchronously
        # In a production system, you might want to implement async job processing
        return {
            "job_id": job_id,
            "status": "unknown",
            "message": "Job status tracking not implemented in this version"
        }
