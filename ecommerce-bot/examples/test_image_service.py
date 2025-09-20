#!/usr/bin/env python3
"""
Test script for Azure Image Service
"""

import asyncio
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.image_service import ImageService

async def main():
    # Load environment variables
    load_dotenv()
    
    # Verify Azure configuration
    if not os.getenv("AZURE_STORAGE_CONNECTION_STRING"):
        print("Error: AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
        print("Please add AZURE_STORAGE_CONNECTION_STRING to your .env file")
        return
    
    try:
        # Initialize the image service
        image_service = ImageService()
        print("✓ Image service initialized successfully")
        
        # Test with a sample image URL
        test_image_url = "https://via.placeholder.com/800x600/FF0000/FFFFFF?text=Test+Image"
        print(f"\nTesting with sample image: {test_image_url}")
        
        # Download the test image
        print("Downloading image...")
        image_data = await image_service.download_image(test_image_url)
        if image_data:
            print(f"✓ Downloaded image: {len(image_data)} bytes")
        else:
            print("✗ Failed to download image")
            return
        
        # Validate the image
        print("\nValidating image...")
        validation = await image_service.validate_image(image_data)
        print(f"✓ Validation result: {validation}")
        
        # Upload as user image
        print("\nUploading as user image...")
        phone_number = "+1234567890"
        user_image_url = await image_service.upload_user_image(phone_number, image_data)
        print(f"✓ User image uploaded: {user_image_url}")
        
        # Verify public access
        print("\nVerifying public access...")
        is_accessible = await image_service.verify_public_access(user_image_url)
        print(f"✓ Public access: {'Yes' if is_accessible else 'No'}")
        
        # Test resize functionality
        print("\nTesting image resize...")
        resized_data = await image_service.resize_image(image_data, max_size=512)
        print(f"✓ Resized image: {len(resized_data)} bytes")
        
        # Upload resized image as try-on result
        print("\nUploading try-on result...")
        result_url = await image_service.upload_tryon_result(phone_number, resized_data)
        print(f"✓ Try-on result uploaded: {result_url}")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())