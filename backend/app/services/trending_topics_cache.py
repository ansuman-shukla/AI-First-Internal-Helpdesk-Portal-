"""
Trending Topics Cache Service

This service manages caching of trending topics analysis to avoid running
expensive LLM analysis on every dashboard load. Topics are cached for 24 hours
and refreshed via scheduled jobs.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_database
from app.services.ai.trending_topics import extract_trending_topics

logger = logging.getLogger(__name__)


class TrendingTopicsCacheService:
    """Service for managing trending topics cache with 24-hour refresh cycle"""
    
    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.cache_collection = None
        self.tickets_collection = None
        self.cache_duration_hours = 24
        self.cache_key = "trending_topics_cache"
    
    async def _ensure_db_connection(self):
        """Ensure database connection is established"""
        if self.db is None:
            self.db = get_database()
            self.cache_collection = self.db.trending_topics_cache
            self.tickets_collection = self.db.tickets
            logger.info("Trending topics cache service connected to database")
    
    async def get_cached_trending_topics(self, days: int = 30, limit: int = 10) -> Optional[Dict[str, Any]]:
        """
        Get cached trending topics if available and not expired.
        
        Args:
            days: Number of days to analyze (used for cache key)
            limit: Maximum number of topics to return
            
        Returns:
            Cached trending topics data or None if expired/not found
        """
        await self._ensure_db_connection()
        
        try:
            cache_key = f"{self.cache_key}_{days}_{limit}"
            cached_data = await self.cache_collection.find_one({"cache_key": cache_key})
            
            if not cached_data:
                logger.info(f"No cached trending topics found for key: {cache_key}")
                return None
            
            # Check if cache is expired
            cached_at = cached_data.get("cached_at")
            if not cached_at:
                logger.warning("Cached data missing timestamp, treating as expired")
                return None
            
            # Convert to datetime if it's a string
            if isinstance(cached_at, str):
                cached_at = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
            
            expiry_time = cached_at + timedelta(hours=self.cache_duration_hours)
            
            if datetime.utcnow() > expiry_time:
                logger.info(f"Cached trending topics expired (cached at: {cached_at})")
                return None
            
            logger.info(f"Returning cached trending topics (cached at: {cached_at})")
            return cached_data.get("data")
            
        except Exception as e:
            logger.error(f"Error retrieving cached trending topics: {str(e)}")
            return None
    
    async def cache_trending_topics(self, data: Dict[str, Any], days: int = 30, limit: int = 10) -> bool:
        """
        Cache trending topics data with timestamp.
        
        Args:
            data: Trending topics data to cache
            days: Number of days analyzed (for cache key)
            limit: Number of topics (for cache key)
            
        Returns:
            True if cached successfully, False otherwise
        """
        await self._ensure_db_connection()
        
        try:
            cache_key = f"{self.cache_key}_{days}_{limit}"
            cache_document = {
                "cache_key": cache_key,
                "data": data,
                "cached_at": datetime.utcnow(),
                "expires_at": datetime.utcnow() + timedelta(hours=self.cache_duration_hours),
                "parameters": {
                    "days": days,
                    "limit": limit
                }
            }
            
            # Upsert the cache document
            await self.cache_collection.replace_one(
                {"cache_key": cache_key},
                cache_document,
                upsert=True
            )
            
            logger.info(f"Successfully cached trending topics for key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching trending topics: {str(e)}")
            return False
    
    async def refresh_trending_topics_cache(self, days: int = 30, limit: int = 10) -> Dict[str, Any]:
        """
        Refresh trending topics cache by running new analysis.
        
        Args:
            days: Number of days to analyze
            limit: Maximum number of topics to return
            
        Returns:
            Fresh trending topics data
        """
        await self._ensure_db_connection()
        
        try:
            logger.info(f"Refreshing trending topics cache for {days} days, limit {limit}")
            
            # Get date filter for the specified period
            from datetime import datetime, timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            date_filter = {"created_at": {"$gte": start_date}}
            
            # Get recent tickets with title and description
            pipeline = [
                {"$match": date_filter},
                {
                    "$project": {
                        "title": 1,
                        "description": 1,
                        "department": 1,
                        "created_at": 1
                    }
                },
                {"$sort": {"created_at": -1}},
                {"$limit": 1000}  # Limit to prevent overwhelming the LLM
            ]
            
            tickets = await self.tickets_collection.aggregate(pipeline).to_list(1000)
            
            if not tickets:
                logger.warning("No tickets found for trending topics analysis")
                data = {
                    "period": f"Last {days} days",
                    "total_tickets_analyzed": 0,
                    "trending_topics": [],
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_refresh": True
                }
            else:
                # Extract trending topics using LLM
                topics = await extract_trending_topics(tickets, limit)
                
                data = {
                    "period": f"Last {days} days",
                    "total_tickets_analyzed": len(tickets),
                    "trending_topics": topics,
                    "generated_at": datetime.utcnow().isoformat(),
                    "cache_refresh": True
                }
            
            # Cache the fresh data
            await self.cache_trending_topics(data, days, limit)
            
            logger.info(f"Successfully refreshed trending topics cache: {len(data.get('trending_topics', []))} topics from {data.get('total_tickets_analyzed', 0)} tickets")
            return data
            
        except Exception as e:
            logger.error(f"Error refreshing trending topics cache: {str(e)}")
            raise
    
    async def get_trending_topics(self, days: int = 30, limit: int = 10, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get trending topics from cache or refresh if needed.
        
        Args:
            days: Number of days to analyze
            limit: Maximum number of topics to return
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Trending topics data (cached or fresh)
        """
        try:
            if not force_refresh:
                # Try to get from cache first
                cached_data = await self.get_cached_trending_topics(days, limit)
                if cached_data:
                    logger.info("Returning cached trending topics")
                    return cached_data
            
            # Cache miss or force refresh - generate fresh data
            logger.info("Cache miss or force refresh - generating fresh trending topics")
            return await self.refresh_trending_topics_cache(days, limit)
            
        except Exception as e:
            logger.error(f"Error getting trending topics: {str(e)}")
            raise



    async def clear_cache(self) -> bool:
        """
        Clear all trending topics cache entries.

        Returns:
            True if cleared successfully, False otherwise
        """
        await self._ensure_db_connection()

        try:
            result = await self.cache_collection.delete_many({})
            logger.info(f"Cleared {result.deleted_count} trending topics cache entries")
            return True

        except Exception as e:
            logger.error(f"Error clearing trending topics cache: {str(e)}")
            return False

    async def get_cache_status(self) -> Dict[str, Any]:
        """
        Get status of trending topics cache.

        Returns:
            Cache status information
        """
        await self._ensure_db_connection()

        try:
            cache_entries = await self.cache_collection.find({}).to_list(100)

            status = {
                "total_cache_entries": len(cache_entries),
                "cache_duration_hours": self.cache_duration_hours,
                "entries": []
            }

            for entry in cache_entries:
                cached_at = entry.get("cached_at")
                expires_at = entry.get("expires_at")

                # Convert to datetime if needed
                if isinstance(cached_at, str):
                    cached_at = datetime.fromisoformat(cached_at.replace('Z', '+00:00'))
                if isinstance(expires_at, str):
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

                is_expired = datetime.utcnow() > expires_at if expires_at else True

                status["entries"].append({
                    "cache_key": entry.get("cache_key"),
                    "cached_at": cached_at.isoformat() if cached_at else None,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "is_expired": is_expired,
                    "parameters": entry.get("parameters", {}),
                    "topics_count": len(entry.get("data", {}).get("trending_topics", []))
                })

            return status

        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}")
            return {
                "total_cache_entries": 0,
                "cache_duration_hours": self.cache_duration_hours,
                "entries": [],
                "error": str(e)
            }


# Global instance
trending_topics_cache_service = TrendingTopicsCacheService()
