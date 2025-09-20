#!/usr/bin/env python3
"""
E-commerce MCP Server using FastMCP
This standalone server can be run directly with FastMCP
"""
from typing import Any, Dict, List, Optional
import logging
import uuid
import sys
import json
import os
import asyncio
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Import the TryOn service
from services.tryon.tryon_service import TryOnService

# Import AWS services
from services.aws_services.recommendation_service import (
    get_recommendations,
    get_recommendations_with_metadata,
    get_item_recommendations
)
from services.aws_services.put_events_service import put_event, put_events_batch

# Initialize FastMCP server
mcp = FastMCP("ecommerce",stateless_http=True, host="localhost", port=8002)

# Configure logging to stderr to avoid interfering with MCP communication
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # This defaults to stderr
)

logger = logging.getLogger(__name__)

# Initialize services
try_on_service = TryOnService()

# Get tracking ID from environment or use placeholder
TRACKING_ID = os.getenv("PERSONALIZE_TRACKING_ID", "demo-tracker-id")


# Product Tools

@mcp.tool()
async def search_products(query: str, category: Optional[str] = None, 
                         min_price: Optional[float] = None, max_price: Optional[float] = None, 
                         limit: int = 10) -> str:
    """Search for products in the catalog.
    
    Args:
        query: Search query string
        category: Optional category filter
        min_price: Optional minimum price filter
        max_price: Optional maximum price filter
        limit: Maximum number of results to return
    """
    logger.info(f"Searching products: query='{query}', category={category}, "
               f"price_range={min_price}-{max_price}, limit={limit}")
    
    # TODO: Implement actual product search from PostgreSQL / product catalog
    # This is a mock implementation
    mock_products = [
        {
            "id": "PROD001",
            "name": "Sample Laptop",
            "description": "High-performance laptop for work and gaming",
            "price": 999.99,
            "category": "Electronics",
            "in_stock": True
        },
        {
            "id": "PROD002",
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with long battery life",
            "price": 29.99,
            "category": "Electronics",
            "in_stock": True
        },
        {
            "id": "PROD003",
            "name": "Office Chair",
            "description": "Comfortable ergonomic office chair",
            "price": 299.99,
            "category": "Furniture",
            "in_stock": True
        }
    ]
    
    # Filter by query (simple contains check for demo)
    filtered_products = [
        p for p in mock_products 
        if query.lower() in p["name"].lower() or query.lower() in p["description"].lower()
    ]
    
    # Apply filters
    if category:
        filtered_products = [p for p in filtered_products if p["category"].lower() == category.lower()]
    if min_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] >= min_price]
    if max_price is not None:
        filtered_products = [p for p in filtered_products if p["price"] <= max_price]
    
    # Limit results
    filtered_products = filtered_products[:limit]
    
    if not filtered_products:
        return f"No products found matching '{query}'"
    
    # Format results as string for MCP
    output = f"Found {len(filtered_products)} products:\n\n"
    for product in filtered_products:
        output += f"• {product['name']} (ID: {product['id']})\n"
        output += f"  Price: ${product['price']:.2f}\n"
        output += f"  Category: {product['category']}\n"
        output += f"  In Stock: {'Yes' if product['in_stock'] else 'No'}\n\n"
    
    return output


@mcp.tool()
async def get_product_details(product_id: str, user_id: Optional[str] = None) -> str:
    """Get detailed information about a specific product.
    
    Args:
        product_id: The unique identifier of the product
        user_id: Optional user ID for tracking view events
    """
    logger.info(f"Getting details for product: {product_id}")
    
    # TODO: Implement actual product lookup from database
    # This is a mock implementation
    mock_product_db = {
        "PROD001": {
            "id": "PROD001",
            "name": "Dell XPS 13 Laptop",
            "description": "High-performance laptop for work and gaming",
            "price": 89999,
            "category": "Electronics",
            "in_stock": True,
            "specifications": {
                "processor": "Intel i7 12th Gen",
                "ram": "16GB DDR5",
                "storage": "512GB NVMe SSD",
                "display": "13.4\" FHD+ Touch"
            },
            "images": ["laptop1.jpg", "laptop2.jpg"]
        },
        "PROD002": {
            "id": "PROD002",
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with long battery life",
            "price": 2999,
            "category": "Electronics",
            "in_stock": True,
            "specifications": {
                "connectivity": "Bluetooth 5.0",
                "battery": "AA x 2",
                "dpi": "1600",
                "warranty": "1 year"
            }
        },
        "PROD006": {
            "id": "PROD006",
            "name": "Blue Formal Shirt",
            "description": "Premium cotton formal shirt for office wear",
            "price": 1999,
            "category": "Clothing",
            "in_stock": True,
            "specifications": {
                "material": "100% Cotton",
                "fit": "Slim Fit",
                "sizes": "S, M, L, XL, XXL",
                "care": "Machine washable"
            }
        }
    }
    
    product = mock_product_db.get(product_id)
    if not product:
        return f"Product with ID '{product_id}' not found"
    
    # Track product view event if user_id provided
    if user_id:
        try:
            await asyncio.to_thread(
                put_event,
                tracking_id=TRACKING_ID,
                user_id=user_id,
                session_id=f"session_{user_id}_{int(time.time())}",
                item_id=product_id,
                event_type="view",
                properties={
                    "category": product['category'],
                    "price": str(product['price'])
                }
            )
        except Exception as e:
            logger.warning(f"Failed to track product view event: {e}")
    
    # Format product details as string
    output = f"📦 **{product['name']}**\n\n"
    output += f"💰 Price: ₹{product['price']:,}\n"
    output += f"📋 ID: {product['id']}\n"
    output += f"📝 {product['description']}\n"
    output += f"🏷️ Category: {product['category']}\n"
    output += f"✅ In Stock: {'Yes' if product['in_stock'] else 'No'}\n\n"
    
    if product.get('specifications'):
        output += "**Specifications:**\n"
        for spec, value in product['specifications'].items():
            output += f"  • {spec.title()}: {value}\n"
    
    # Get similar products
    try:
        similar_items = get_item_recommendations(
            item_id=product_id,
            num_results=3
        )
        if similar_items:
            output += f"\n**You might also like:**\n"
            for similar_id in similar_items[:3]:
                if similar_id in mock_product_db:
                    similar_product = mock_product_db[similar_id]
                    output += f"  • {similar_product['name']} - ₹{similar_product['price']:,}\n"
    except:
        pass
    
    return output


@mcp.tool()
async def get_personalized_recommendations(user_id: str, limit: int = 5) -> str:
    """Get personalized product recommendations for a user using AWS Personalize.
    
    Args:
        user_id: The unique identifier of the user
        limit: Maximum number of recommendations to return
    """
    logger.info(f"Getting personalized recommendations for user: {user_id}, limit={limit}")
    
    try:
        # Get recommendations from AWS Personalize
        recommended_item_ids = get_recommendations(
            user_id=user_id,
            num_results=limit
        )
        
        if not recommended_item_ids:
            return f"No personalized recommendations available for user {user_id} at this time.\n\nYou might want to browse our popular products or search for something specific!"
        
        # In production, you would fetch actual product details from database
        # For demo, we'll create a mapping of some product IDs
        product_catalog = {
            "PROD001": {"name": "Dell XPS 13 Laptop", "price": 89999, "category": "Electronics"},
            "PROD002": {"name": "Wireless Mouse", "price": 2999, "category": "Electronics"},
            "PROD003": {"name": "USB-C Hub", "price": 4999, "category": "Electronics"},
            "PROD004": {"name": "Laptop Stand", "price": 3999, "category": "Accessories"},
            "PROD005": {"name": "Wireless Keyboard", "price": 7999, "category": "Electronics"},
            "PROD006": {"name": "Blue Formal Shirt", "price": 1999, "category": "Clothing"},
            "PROD007": {"name": "Denim Jeans", "price": 2999, "category": "Clothing"},
            "PROD008": {"name": "Sports Shoes", "price": 4999, "category": "Footwear"}
        }
        
        output = f"🎯 Personalized recommendations for you:\n\n"
        
        for i, item_id in enumerate(recommended_item_ids, 1):
            if item_id in product_catalog:
                product = product_catalog[item_id]
                output += f"{i}. **{product['name']}**\n"
                output += f"   Price: ₹{product['price']:,}\n"
                output += f"   Category: {product['category']}\n\n"
            else:
                # If product not in mock catalog, show the ID
                output += f"{i}. Product ID: {item_id}\n"
                output += f"   (Details coming soon)\n\n"
        
        output += "💡 These recommendations are personalized based on your preferences and browsing history."
        
        # Track that recommendations were shown
        try:
            await asyncio.to_thread(
                put_event,
                tracking_id=TRACKING_ID,
                user_id=user_id,
                session_id=f"session_{user_id}_{int(time.time())}",
                item_id="recommendation_page",
                event_type="view",
                properties={"recommendation_count": len(recommended_item_ids)},
                impression=recommended_item_ids[:10]  # Track impressions
            )
        except Exception as e:
            logger.warning(f"Failed to track recommendation event: {e}")
        
        return output
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {e}")
        
        # Fallback to static recommendations
        return f"""Recommendations for you:

1. **Dell XPS 13 Laptop** - ₹89,999
   Perfect for work and entertainment
   
2. **Wireless Mouse** - ₹2,999
   Ergonomic design for comfort
   
3. **USB-C Hub** - ₹4,999
   Expand your connectivity

Unable to fetch personalized recommendations at the moment. These are our popular items!"""


# Cart Tools

@mcp.tool()
async def add_to_cart(user_id: str, product_id: str, quantity: int = 1) -> str:
    """Add a product to the user's cart.
    
    Args:
        user_id: The unique identifier of the user
        product_id: The product to add
        quantity: Number of items to add
    """
    logger.info(f"Adding to cart: user={user_id}, product={product_id}, quantity={quantity}")
    
    # Track add to cart event
    try:
        await asyncio.to_thread(
            put_event,
            tracking_id=TRACKING_ID,
            user_id=user_id,
            session_id=f"session_{user_id}_{int(time.time())}",
            item_id=product_id,
            event_type="add_to_cart",
            event_value=float(quantity),
            properties={
                "quantity": str(quantity)
            }
        )
    except Exception as e:
        logger.warning(f"Failed to track add to cart event: {e}")
    
    # TODO: Implement actual cart management with Redis/database
    # This is a mock implementation
    return f"""✅ Added to cart successfully!

    Product ID: {product_id}
    Quantity: {quantity}
    User: {user_id}

    Your cart now has {quantity} item(s).
    Use 'view_cart' to see all items."""


@mcp.tool()
async def view_cart(user_id: str) -> str:
    """View the contents of a user's cart.
    
    Args:
        user_id: The unique identifier of the user
    """
    logger.info(f"Viewing cart for user: {user_id}")
    
    # TODO: Implement actual cart retrieval from Redis/database
    # This is a mock implementation
    cart_items = [
        {
            "product_id": "PROD001",
            "name": "Sample Laptop",
            "price": 999.99,
            "quantity": 1,
            "subtotal": 999.99
        },
        {
            "product_id": "PROD002",
            "name": "Wireless Mouse", 
            "price": 29.99,
            "quantity": 2,
            "subtotal": 59.98
        }
    ]
    
    if not cart_items:
        return f"Your cart is empty. Start shopping!"
    
    output = f"🛒 Shopping Cart for {user_id}:\n\n"
    total = 0
    
    for item in cart_items:
        subtotal = item['subtotal']
        total += subtotal
        output += f"• {item['name']} (ID: {item['product_id']})\n"
        output += f"  ${item['price']:.2f} x {item['quantity']} = ${subtotal:.2f}\n\n"
    
    output += f"─────────────────────\n"
    output += f"Total: ${total:.2f}\n"
    output += f"\nReady to checkout? Use 'process_order' command."
    
    return output


@mcp.tool()
async def remove_from_cart(user_id: str, product_id: str) -> str:
    """Remove a product from the user's cart.
    
    Args:
        user_id: The unique identifier of the user
        product_id: The product to remove
    """
    logger.info(f"Removing from cart: user={user_id}, product={product_id}")
    
    # TODO: Implement actual cart item removal
    return f"""✅ Removed from cart successfully!

        Product ID: {product_id}
        User: {user_id}

        Use 'view_cart' to see updated cart contents."""


# Order Tools

@mcp.tool()
async def process_order(user_id: str, payment_method: str, 
                       shipping_street: str, shipping_city: str,
                       shipping_state: str, shipping_zip: str) -> str:
    """Process an order from the user's cart.
    
    Args:
        user_id: The unique identifier of the user
        payment_method: Payment method (credit_card, paypal, etc.)
        shipping_street: Street address
        shipping_city: City
        shipping_state: State/Province
        shipping_zip: ZIP/Postal code
    """
    logger.info(f"Processing order for user: {user_id}")
    
    # TODO: Implement actual order processing
    # This would involve:
    # 1. Validating cart contents
    # 2. Processing payment
    # 3. Creating order record
    # 4. Clearing cart
    # 5. Triggering fulfillment
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    
    return f"""✅ Order Placed Successfully!

        Order ID: {order_id}
        Date: 2024-01-20

        Shipping Address:
        {shipping_street}
        {shipping_city}, {shipping_state} {shipping_zip}

        Payment Method: {payment_method}

        Order Total: $1,059.97

        Estimated Delivery: 3-5 business days

        You will receive an email confirmation shortly.
        Track your order using the order ID."""


@mcp.tool()
async def get_order_status(order_id: str, user_id: Optional[str] = None) -> str:
    """Get the status of an order.
    
    Args:
        order_id: The order identifier
        user_id: Optional user ID for verification
    """
    logger.info(f"Getting order status: order_id={order_id}, user_id={user_id}")
    
    # TODO: Implement actual order status lookup
    # This is a mock implementation
    return f"""📦 Order Status

        Order ID: {order_id}
        Status: In Transit
        Last Updated: 2024-01-21 14:30

        Tracking Timeline:
        ✅ Order Placed - Jan 20, 10:30 AM
        ✅ Payment Confirmed - Jan 20, 10:31 AM  
        ✅ Order Processed - Jan 20, 2:00 PM
        ✅ Shipped - Jan 21, 9:00 AM
        🚚 In Transit - Jan 21, 2:30 PM
        ⏳ Out for Delivery - Pending
        ⏳ Delivered - Pending

        Tracking Number: 1Z999AA1234567890
        Carrier: UPS

        Estimated Delivery: Jan 23, 2024"""


# Try-On Tools

@mcp.tool()
async def virtual_tryon(user_id: str, user_image_url: str, product_id: str, 
                       product_image_url: Optional[str] = None) -> str:
    """Process a virtual try-on with user's photo and product image.
    
    Args:
        user_id: The unique identifier of the user
        user_image_url: URL of the user's photo (full body or upper body preferred)
        product_id: The product ID to try on
        product_image_url: Optional direct URL of the product image. If not provided, will look up product.
    """
    logger.info(f"Processing virtual try-on: user={user_id}, product={product_id}")
    
    # Check if try-on service is available
    if not try_on_service.enabled:
        return """❌ Virtual Try-On Service Unavailable

                The virtual try-on feature is currently not available.
                This service requires a Gemini API key to be configured.

                Please contact support or try again later."""
    
    try:
        # If product image URL not provided, look up the product
        if not product_image_url:
            # In a real implementation, this would look up the product from database
            # For now, we'll use mock data
            mock_product_images = {
                "PROD001": "https://example.com/laptop.jpg",  # Obviously not clothing
                "PROD002": "https://example.com/white-shirt.jpg",
                "PROD003": "https://example.com/blue-dress.jpg",
                "PROD004": "https://example.com/denim-jacket.jpg",
                "PROD005": "https://example.com/black-tshirt.jpg"
            }
            
            product_image_url = mock_product_images.get(product_id)
            if not product_image_url:
                return f"""❌ Product Not Found

                Product ID '{product_id}' not found in our catalog.
                Please provide a valid product ID or the product image URL directly.

                Available clothing items:
                - PROD002: White Formal Shirt
                - PROD003: Blue Summer Dress
                - PROD004: Denim Jacket
                - PROD005: Black T-Shirt"""
        
        # Process the virtual try-on
        result = await try_on_service.process_tryon(
            user_image_url=user_image_url,
            product_image_url=product_image_url,
            phone_number=user_id  # Using user_id as phone number for storage
        )
        
        if result["status"] == "completed":
            return f"""✨ Virtual Try-On Complete!

                Product: {product_id}
                Status: Ready to view
                Result: {result['result']['image_url']}

                Your virtual try-on has been generated successfully!
                The image shows how {product_id} would look on you.

                Next steps:
                - Save this image for reference
                - Share with friends for feedback
                - Add to cart if you like the fit!

                Would you like to:
                1. Try another product
                2. Add this item to cart
                3. View similar products"""
        
        elif result["status"] == "failed":
            return f"""❌ Virtual Try-On Failed

                We couldn't generate the virtual try-on image.
                Error: {result.get('error', 'Unknown error')}

                Please ensure:
                - Your photo shows your full body or upper body clearly
                - The image URLs are accessible
                - The product is a clothing item

                Try again with a different photo or contact support if the issue persists."""
            
        else:
            return f"""⏳ Processing Virtual Try-On

                Job ID: {result.get('job_id', 'unknown')}
                Status: {result.get('status', 'processing')}

                Your virtual try-on is being processed. This usually takes 10-30 seconds.
                Please check back in a moment."""
            
    except Exception as e:
        logger.error(f"Error in virtual try-on: {str(e)}")
        return f"""❌ Virtual Try-On Error

                An error occurred while processing your request:
                {str(e)}

                Please try again or contact support if the issue continues."""


@mcp.tool()
async def get_tryon_tips() -> str:
    """Get tips for best virtual try-on results."""
    
    return """📸 Virtual Try-On Tips for Best Results:

                **Photo Requirements:**
                ✅ Full body or upper body shot
                ✅ Good lighting (natural light preferred)
                ✅ Plain or simple background
                ✅ Standing straight, facing camera
                ✅ Fitted clothes to show body shape

                **What to Avoid:**
                ❌ Blurry or low-quality photos
                ❌ Heavy shadows or backlighting
                ❌ Sitting or unusual poses
                ❌ Multiple people in photo
                ❌ Very loose or baggy clothing

                **Supported Products:**
                👔 Shirts & Blouses
                👗 Dresses & Skirts
                🧥 Jackets & Coats
                👕 T-Shirts & Tops
                👖 Pants & Jeans (coming soon)

                **Pro Tips:**
                1. Use a recent photo for accurate sizing
                2. Try multiple angles for different views
                3. Save results to compare different items
                4. Share with friends for second opinions

                Ready to try? Send your photo and choose a product!"""


# Main entry point
if __name__ == "__main__":
    # Run the server with stdio transport
    mcp.run(transport='streamable-http')