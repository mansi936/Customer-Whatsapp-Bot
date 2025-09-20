#!/usr/bin/env python3
"""
Example usage of the Virtual Try-On Service
"""

import asyncio
import os
from dotenv import load_dotenv
import sys
import base64
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.tryon.tryon_service import TryOnService

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get Google API key from environment
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables")
        print("Please add GOOGLE_API_KEY=your_api_key to your .env file")
        return
    
    # Initialize the try-on service
    tryon_service = TryOnService(api_key=google_api_key)
    
    # Example image URLs (replace with actual URLs)
    user_image_url = "https://example.com/user_image.jpg"  # Image of person
    product_image_url = "https://example.com/product_image.jpg"  # Image of clothing item
    phone_number = "+1234567890"  # Optional: provide phone number for better file organization
    
    print("Starting virtual try-on process...")
    print(f"User image: {user_image_url}")
    print(f"Product image: {product_image_url}")
    
    # Process virtual try-on
    result = await tryon_service.process_tryon(user_image_url, product_image_url, phone_number)
    
    print(f"\nJob ID: {result['job_id']}")
    print(f"Status: {result['status']}")
    print(f"Message: {result.get('message', '')}")
    
    if result['status'] == 'completed' and 'result' in result:
        # The generated image is already uploaded to storage
        print(f"\nGenerated image URL: {result['result']['image_url']}")
        
        # Optionally, save a local copy
        image_data = base64.b64decode(result['result']['image_base64'])
        output_path = f"tryon_result_{result['job_id']}.jpg"
        
        with open(output_path, 'wb') as f:
            f.write(image_data)
        
        print(f"Local copy saved to: {output_path}")
    elif result['status'] == 'failed':
        print(f"\nError: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    asyncio.run(main())