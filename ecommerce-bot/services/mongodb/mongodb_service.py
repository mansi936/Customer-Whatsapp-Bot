import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import asyncio

logger = logging.getLogger(__name__)

class MongoUserService:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.users_collection = None
        self.orders_collection = None
        self.products_collection = None
        
    async def initialize(self, mongodb_url="mongodb://localhost:27017", database_name="ecommerce_bot", max_pool_size=50):
        """Initialize MongoDB connection"""
        try:
            self.client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=max_pool_size,
                serverSelectionTimeoutMS=5000
            )
            self.db = self.client[database_name]
            
            # Initialize collections
            self.users_collection = self.db.users
            self.orders_collection = self.db.orders
            self.products_collection = self.db.products
            
            # Create indexes
            await self._create_indexes()
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("MongoDB connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # User indexes
            await self.users_collection.create_index("phone_number", unique=True)
            await self.users_collection.create_index("user_id", unique=True)
            await self.users_collection.create_index("email")
            
            # Order indexes
            await self.orders_collection.create_index("user_id")
            await self.orders_collection.create_index("order_id", unique=True)
            await self.orders_collection.create_index("status")
            await self.orders_collection.create_index("created_at")
            
            # Product indexes
            await self.products_collection.create_index("product_id", unique=True)
            await self.products_collection.create_index("category")
            await self.products_collection.create_index("brand")
            await self.products_collection.create_index([("name", "text"), ("description", "text")])
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
    
    # User Management Methods
    
    async def create_user(self, user_data: Dict) -> Dict:
        """Create new user profile"""
        try:
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()
            user_data["total_orders"] = 0
            user_data["total_spent"] = 0
            
            # Default preferences
            if "preferences" not in user_data:
                user_data["preferences"] = {
                    "categories": [],
                    "brands": [],
                    "price_range": {"min": 0, "max": 100000},
                    "notifications": True,
                    "language": "en"
                }
            
            result = await self.users_collection.insert_one(user_data)
            user_data["_id"] = str(result.inserted_id)
            
            logger.info(f"User created: {user_data.get('user_id')}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get user profile by user_id"""
        try:
            user = await self.users_collection.find_one({"user_id": user_id})
            if user:
                user["_id"] = str(user["_id"])
            return user
            
        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}")
            return None
    
    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get user profile by phone number"""
        try:
            user = await self.users_collection.find_one({"phone_number": phone_number})
            if user:
                user["_id"] = str(user["_id"])
            return user
            
        except Exception as e:
            logger.error(f"Error getting user by phone {phone_number}: {e}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict) -> Dict:
        """Update user profile"""
        try:
            updates["updated_at"] = datetime.utcnow()
            
            result = await self.users_collection.update_one(
                {"user_id": user_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                logger.info(f"User profile updated: {user_id}")
                return await self.get_user_profile(user_id)
            else:
                raise ValueError(f"User not found: {user_id}")
                
        except Exception as e:
            logger.error(f"Error updating user profile for {user_id}: {e}")
            raise
    
    async def update_user_preferences(self, user_id: str, preferences: Dict) -> Dict:
        """Update user preferences"""
        try:
            return await self.update_user_profile(
                user_id,
                {"preferences": preferences}
            )
            
        except Exception as e:
            logger.error(f"Error updating preferences for {user_id}: {e}")
            raise
    
    async def update_user_metrics(self, user_id: str, order_amount: float):
        """Update user metrics after order"""
        try:
            await self.users_collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "total_orders": 1,
                        "total_spent": order_amount
                    },
                    "$set": {
                        "last_order_date": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"User metrics updated for {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user metrics for {user_id}: {e}")
    
    # Order Management Methods
    
    async def create_order(self, order_data: Dict) -> Dict:
        """Create new order"""
        try:
            # Generate order ID
            order_data["order_id"] = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{ObjectId()}"
            order_data["created_at"] = datetime.utcnow()
            order_data["updated_at"] = datetime.utcnow()
            order_data["status"] = "pending"
            
            result = await self.orders_collection.insert_one(order_data)
            order_data["_id"] = str(result.inserted_id)
            
            # Update user metrics
            await self.update_user_metrics(
                order_data["user_id"],
                order_data.get("final_amount", 0)
            )
            
            logger.info(f"Order created: {order_data['order_id']}")
            return order_data
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            raise
    
    async def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by order_id"""
        try:
            order = await self.orders_collection.find_one({"order_id": order_id})
            if order:
                order["_id"] = str(order["_id"])
            return order
            
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
    
    async def get_order_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's order history"""
        try:
            cursor = self.orders_collection.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(limit)
            
            orders = []
            async for order in cursor:
                order["_id"] = str(order["_id"])
                orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"Error getting order history for {user_id}: {e}")
            return []
    
    async def update_order_status(self, order_id: str, status: str, additional_data: Dict = None) -> Dict:
        """Update order status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if additional_data:
                update_data.update(additional_data)
            
            result = await self.orders_collection.update_one(
                {"order_id": order_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Order status updated: {order_id} -> {status}")
                return await self.get_order(order_id)
            else:
                raise ValueError(f"Order not found: {order_id}")
                
        except Exception as e:
            logger.error(f"Error updating order status for {order_id}: {e}")
            raise
    
    async def cancel_order(self, order_id: str, reason: str = None) -> Dict:
        """Cancel an order"""
        try:
            additional_data = {
                "cancelled_at": datetime.utcnow(),
                "cancellation_reason": reason
            }
            return await self.update_order_status(order_id, "cancelled", additional_data)
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise
    
    # Product Management Methods
    
    async def add_product(self, product_data: Dict) -> Dict:
        """Add new product to catalog"""
        try:
            product_data["created_at"] = datetime.utcnow()
            product_data["updated_at"] = datetime.utcnow()
            product_data["is_available"] = product_data.get("is_available", True)
            
            result = await self.products_collection.insert_one(product_data)
            product_data["_id"] = str(result.inserted_id)
            
            logger.info(f"Product added: {product_data.get('product_id')}")
            return product_data
            
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            raise
    
    async def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product by product_id"""
        try:
            product = await self.products_collection.find_one({"product_id": product_id})
            if product:
                product["_id"] = str(product["_id"])
            return product
            
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {e}")
            return None
    
    async def search_products(self, query: str = None, filters: Dict = None, limit: int = 20) -> List[Dict]:
        """Search products with text search and filters"""
        try:
            search_filter = {}
            
            # Text search
            if query:
                search_filter["$text"] = {"$search": query}
            
            # Apply filters
            if filters:
                if "category" in filters:
                    search_filter["category"] = filters["category"]
                if "brand" in filters:
                    search_filter["brand"] = filters["brand"]
                if "price_min" in filters or "price_max" in filters:
                    price_filter = {}
                    if "price_min" in filters:
                        price_filter["$gte"] = filters["price_min"]
                    if "price_max" in filters:
                        price_filter["$lte"] = filters["price_max"]
                    search_filter["price"] = price_filter
            
            # Always filter for available products
            search_filter["is_available"] = True
            
            cursor = self.products_collection.find(search_filter).limit(limit)
            
            products = []
            async for product in cursor:
                product["_id"] = str(product["_id"])
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    async def get_products_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get products by category"""
        return await self.search_products(filters={"category": category}, limit=limit)
    
    async def get_products_by_ids(self, product_ids: List[str]) -> List[Dict]:
        """Get multiple products by their IDs"""
        try:
            cursor = self.products_collection.find(
                {"product_id": {"$in": product_ids}}
            )
            
            products = []
            async for product in cursor:
                product["_id"] = str(product["_id"])
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products by IDs: {e}")
            return []
    
    async def update_product_inventory(self, product_id: str, quantity_change: int):
        """Update product inventory after order"""
        try:
            await self.products_collection.update_one(
                {"product_id": product_id},
                {
                    "$inc": {"inventory": -quantity_change},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            logger.info(f"Product inventory updated: {product_id}")
            
        except Exception as e:
            logger.error(f"Error updating product inventory for {product_id}: {e}")
    
    # Analytics Methods
    
    async def get_user_analytics(self, user_id: str) -> Dict:
        """Get user analytics data"""
        try:
            user = await self.get_user_profile(user_id)
            orders = await self.get_order_history(user_id, limit=100)
            
            # Calculate analytics
            total_orders = len(orders)
            total_spent = sum(order.get("final_amount", 0) for order in orders)
            
            # Get favorite categories
            category_counts = {}
            for order in orders:
                for item in order.get("items", []):
                    category = item.get("category")
                    if category:
                        category_counts[category] = category_counts.get(category, 0) + 1
            
            favorite_categories = sorted(
                category_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            return {
                "user_id": user_id,
                "total_orders": total_orders,
                "total_spent": total_spent,
                "average_order_value": total_spent / total_orders if total_orders > 0 else 0,
                "favorite_categories": [cat[0] for cat in favorite_categories],
                "member_since": user.get("created_at") if user else None
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics for {user_id}: {e}")
            return {}

# Singleton instance
mongo_service = MongoUserService()