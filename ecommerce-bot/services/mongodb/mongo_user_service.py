#!/usr/bin/env python3
"""
MongoDB Seeder for Clothes Database
Run this to populate your database with sample products
"""

import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.getenv('DB_NAME', 'ecommerce_clothes')

# Sample clothes data
SAMPLE_PRODUCTS = [
    # Formal Shirts
    {
        "_id": "PROD001",
        "name": "Classic White Business Shirt",
        "category": "shirt",
        "sizes": ["S", "M", "L", "XL"],
        "color": "White",
        "style": "formal",
        "price": 2499,
        "description": "Premium cotton formal shirt perfect for office meetings and business events",
        "image_url": "https://example.com/white-shirt.jpg",
        "rating": 4.5,
        "stock": 50,
        "tags": ["office", "business", "classic"]
    },
    {
        "_id": "PROD002",
        "name": "Navy Blue Formal Shirt",
        "category": "shirt",
        "sizes": ["M", "L", "XL", "XXL"],
        "color": "Navy Blue",
        "style": "formal",
        "price": 2799,
        "description": "Elegant navy blue shirt with subtle texture for professional look",
        "image_url": "https://example.com/navy-shirt.jpg",
        "rating": 4.6,
        "stock": 35,
        "tags": ["office", "business", "elegant"]
    },
    
    # Casual Shirts
    {
        "_id": "PROD003",
        "name": "Checked Casual Shirt",
        "category": "shirt",
        "sizes": ["S", "M", "L"],
        "color": "Red and Black",
        "style": "casual",
        "price": 1599,
        "description": "Trendy checked pattern shirt for casual outings and weekend wear",
        "image_url": "https://example.com/checked-shirt.jpg",
        "rating": 4.3,
        "stock": 60,
        "tags": ["weekend", "casual", "trendy"]
    },
    {
        "_id": "PROD004",
        "name": "Linen Summer Shirt",
        "category": "shirt",
        "sizes": ["M", "L", "XL"],
        "color": "Light Blue",
        "style": "casual",
        "price": 1899,
        "description": "Breathable linen shirt perfect for summer days",
        "image_url": "https://example.com/linen-shirt.jpg",
        "rating": 4.4,
        "stock": 40,
        "tags": ["summer", "casual", "comfort"]
    },
    
    # Pants
    {
        "_id": "PROD005",
        "name": "Formal Black Trousers",
        "category": "pants",
        "sizes": ["30", "32", "34", "36"],
        "color": "Black",
        "style": "formal",
        "price": 3299,
        "description": "Classic fit formal trousers for professional attire",
        "image_url": "https://example.com/black-trousers.jpg",
        "rating": 4.5,
        "stock": 45,
        "tags": ["office", "formal", "classic"]
    },
    {
        "_id": "PROD006",
        "name": "Khaki Chinos",
        "category": "pants",
        "sizes": ["30", "32", "34"],
        "color": "Khaki",
        "style": "casual",
        "price": 2499,
        "description": "Versatile chinos that work for both casual and semi-formal occasions",
        "image_url": "https://example.com/khaki-chinos.jpg",
        "rating": 4.4,
        "stock": 55,
        "tags": ["versatile", "casual", "comfortable"]
    },
    {
        "_id": "PROD007",
        "name": "Blue Denim Jeans",
        "category": "pants",
        "sizes": ["28", "30", "32", "34", "36"],
        "color": "Blue",
        "style": "casual",
        "price": 2999,
        "description": "Classic blue jeans with modern slim fit",
        "image_url": "https://example.com/blue-jeans.jpg",
        "rating": 4.6,
        "stock": 70,
        "tags": ["denim", "casual", "everyday"]
    },
    
    # Dresses
    {
        "_id": "PROD008",
        "name": "Floral Summer Dress",
        "category": "dress",
        "sizes": ["S", "M", "L"],
        "color": "Floral Print",
        "style": "casual",
        "price": 2799,
        "description": "Light and breezy summer dress with beautiful floral patterns",
        "image_url": "https://example.com/floral-dress.jpg",
        "rating": 4.7,
        "stock": 30,
        "tags": ["summer", "feminine", "floral"]
    },
    {
        "_id": "PROD009",
        "name": "Little Black Dress",
        "category": "dress",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Black",
        "style": "formal",
        "price": 4499,
        "description": "Elegant black dress perfect for evening events and parties",
        "image_url": "https://example.com/black-dress.jpg",
        "rating": 4.8,
        "stock": 25,
        "tags": ["party", "elegant", "evening"]
    },
    
    # T-Shirts
    {
        "_id": "PROD010",
        "name": "Basic Cotton T-Shirt Pack",
        "category": "tshirt",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Multi (White, Black, Gray)",
        "style": "casual",
        "price": 1299,
        "description": "Pack of 3 essential cotton t-shirts for everyday wear",
        "image_url": "https://example.com/basic-tshirts.jpg",
        "rating": 4.2,
        "stock": 100,
        "tags": ["basic", "everyday", "value"]
    },
    {
        "_id": "PROD011",
        "name": "Graphic Print T-Shirt",
        "category": "tshirt",
        "sizes": ["M", "L", "XL"],
        "color": "Navy Blue",
        "style": "casual",
        "price": 899,
        "description": "Trendy graphic print t-shirt for casual style",
        "image_url": "https://example.com/graphic-tshirt.jpg",
        "rating": 4.1,
        "stock": 80,
        "tags": ["trendy", "casual", "youth"]
    },
    
    # Sportswear
    {
        "_id": "PROD012",
        "name": "Athletic Performance Shorts",
        "category": "shorts",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Black",
        "style": "sporty",
        "price": 1499,
        "description": "Quick-dry athletic shorts for gym and running",
        "image_url": "https://example.com/sports-shorts.jpg",
        "rating": 4.5,
        "stock": 65,
        "tags": ["gym", "sports", "athletic"]
    },
    {
        "_id": "PROD013",
        "name": "Yoga Leggings",
        "category": "pants",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Purple",
        "style": "sporty",
        "price": 1999,
        "description": "High-waist yoga leggings with excellent stretch",
        "image_url": "https://example.com/yoga-leggings.jpg",
        "rating": 4.6,
        "stock": 40,
        "tags": ["yoga", "fitness", "comfort"]
    }
]

def seed_database():
    """Seed the database with sample products"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Clear existing products
    db.products.delete_many({})
    
    # Insert sample products
    db.products.insert_many(SAMPLE_PRODUCTS)
    
    print(f"✅ Successfully seeded {len(SAMPLE_PRODUCTS)} products to {DB_NAME}")
    
    # Create indexes for better performance
    db.products.create_index([("category", 1)])
    db.products.create_index([("style", 1)])
    db.products.create_index([("price", 1)])
    db.products.create_index([("sizes", 1)])
    
    print("✅ Created database indexes")
    
    # Add some sample user interaction data for Personalize
    sample_interactions = [
        {"user_id": "user1", "item_id": "PROD001", "event_type": "view", "timestamp": datetime.now()},
        {"user_id": "user1", "item_id": "PROD002", "event_type": "purchase", "timestamp": datetime.now()},
        {"user_id": "user2", "item_id": "PROD003", "event_type": "view", "timestamp": datetime.now()},
        {"user_id": "user2", "item_id": "PROD004", "event_type": "add_to_cart", "timestamp": datetime.now()},
    ]
    
    db.interactions.insert_many(sample_interactions)
    print("✅ Added sample user interactions")
    
    client.close()

if __name__ == "__main__":
    seed_database()
