"""
Caching service with Redis integration and Streamlit cache optimization
"""

import redis
import json
import pickle
import hashlib
from typing import Any, Optional, Dict, List, Callable
from datetime import datetime, timedelta
import streamlit as st
from functools import wraps
import pandas as pd
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Centralized caching service with Redis backend and fallback to memory"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize cache service with Redis connection"""
        self.redis_client = None
        self.memory_cache = {}
        self.cache_stats = {"hits": 0, "misses": 0}
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed, using memory cache: {e}")
    
    def _serialize_key(self, key: str, params: Dict[str, Any] = None) -> str:
        """Create a serialized cache key from parameters"""
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            param_str = json.dumps(sorted_params, default=str, sort_keys=True)
            key_data = f"{key}:{param_str}"
        else:
            key_data = key
        
        # Hash long keys to avoid Redis key length limits
        if len(key_data) > 200:
            return f"hash:{hashlib.md5(key_data.encode()).hexdigest()}"
        return key_data
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        if isinstance(value, pd.DataFrame):
            return json.dumps({
                "type": "dataframe",
                "data": value.to_json(orient="records", date_format="iso"),
                "columns": list(value.columns),
                "index": list(value.index)
            })
        elif isinstance(value, Decimal):
            return json.dumps({"type": "decimal", "value": str(value)})
        elif isinstance(value, (datetime, pd.Timestamp)):
            return json.dumps({"type": "datetime", "value": value.isoformat()})
        else:
            try:
                return json.dumps({"type": "json", "value": value})
            except (TypeError, ValueError):
                # Fallback to pickle for complex objects
                return json.dumps({
                    "type": "pickle",
                    "value": pickle.dumps(value).hex()
                })
    
    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize value from storage"""
        try:
            data = json.loads(serialized)
            value_type = data.get("type")
            
            if value_type == "dataframe":
                df_data = json.loads(data["data"])
                return pd.DataFrame(df_data)
            elif value_type == "decimal":
                return Decimal(data["value"])
            elif value_type == "datetime":
                return datetime.fromisoformat(data["value"])
            elif value_type == "json":
                return data["value"]
            elif value_type == "pickle":
                return pickle.loads(bytes.fromhex(data["value"]))
            else:
                return data["value"]
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to deserialize cache value: {e}")
            return None
    
    def get(self, key: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._serialize_key(key, params)
        
        # Try Redis first
        if self.redis_client:
            try:
                serialized = self.redis_client.get(cache_key)
                if serialized:
                    self.cache_stats["hits"] += 1
                    return self._deserialize_value(serialized)
            except redis.RedisError as e:
                logger.warning(f"Redis get failed: {e}")
        
        # Fallback to memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if entry["expires_at"] > datetime.now():
                self.cache_stats["hits"] += 1
                return entry["value"]
            else:
                del self.memory_cache[cache_key]
        
        self.cache_stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600, params: Dict[str, Any] = None) -> bool:
        """Set value in cache with TTL in seconds"""
        cache_key = self._serialize_key(key, params)
        serialized = self._serialize_value(value)
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, ttl, serialized)
                return True
            except redis.RedisError as e:
                logger.warning(f"Redis set failed: {e}")
        
        # Fallback to memory cache
        self.memory_cache[cache_key] = {
            "value": value,
            "expires_at": datetime.now() + timedelta(seconds=ttl)
        }
        return True
    
    def delete(self, key: str, params: Dict[str, Any] = None) -> bool:
        """Delete value from cache"""
        cache_key = self._serialize_key(key, params)
        
        deleted = False
        
        # Delete from Redis
        if self.redis_client:
            try:
                deleted = bool(self.redis_client.delete(cache_key))
            except redis.RedisError as e:
                logger.warning(f"Redis delete failed: {e}")
        
        # Delete from memory cache
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
            deleted = True
        
        return deleted
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        deleted_count = 0
        
        # Clear from Redis
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted_count += self.redis_client.delete(*keys)
            except redis.RedisError as e:
                logger.warning(f"Redis pattern clear failed: {e}")
        
        # Clear from memory cache
        keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.memory_cache[key]
            deleted_count += 1
        
        return deleted_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.cache_stats.copy()
        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"])
            if (stats["hits"] + stats["misses"]) > 0 else 0
        )
        stats["memory_cache_size"] = len(self.memory_cache)
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_memory_usage"] = info.get("used_memory_human", "N/A")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except redis.RedisError:
                stats["redis_status"] = "disconnected"
        else:
            stats["redis_status"] = "not_configured"
        
        return stats

# Global cache instance
cache_service = CacheService()

def cached_data(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results with Streamlit integration"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and parameters
            func_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            
            # Convert args and kwargs to hashable format
            cache_params = {
                "args": str(args),
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            
            # Try to get from cache first
            cached_result = cache_service.get(func_name, cache_params)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_service.set(func_name, result, ttl, cache_params)
            
            return result
        
        return wrapper
    return decorator

@st.cache_data(ttl=300)  # 5 minutes TTL
def get_cached_costs(date_filter: str = None) -> pd.DataFrame:
    """Get costs with Streamlit caching"""
    from services.storage import get_costs
    return get_costs()

@st.cache_data(ttl=300)
def get_cached_sales_orders(date_filter: str = None) -> pd.DataFrame:
    """Get sales orders with Streamlit caching"""
    from services.storage import get_sales_orders
    return get_sales_orders()

@st.cache_data(ttl=600)  # 10 minutes TTL
def get_cached_fx_rates() -> pd.DataFrame:
    """Get FX rates with Streamlit caching"""
    from services.storage import get_fx_rates
    return get_fx_rates()

@cached_data(ttl=1800, key_prefix="metrics_")  # 30 minutes TTL
def calculate_cached_metrics(costs_df: pd.DataFrame, sales_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate financial metrics with caching"""
    from utils.data_manager import calculate_metrics
    return calculate_metrics(costs_df, sales_df)

@cached_data(ttl=3600, key_prefix="reports_")  # 1 hour TTL
def generate_cached_report(report_type: str, date_range: tuple, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Generate reports with caching"""
    # This would contain actual report generation logic
    return {
        "report_type": report_type,
        "date_range": date_range,
        "filters": filters,
        "generated_at": datetime.now().isoformat(),
        "data": {}  # Report data would go here
    }

def warm_cache():
    """Warm up cache with frequently accessed data"""
    logger.info("Starting cache warming...")
    
    try:
        # Warm up basic data
        get_cached_costs()
        get_cached_sales_orders()
        get_cached_fx_rates()
        
        # Warm up calculated metrics
        costs_df = get_cached_costs()
        sales_df = get_cached_sales_orders()
        if not costs_df.empty and not sales_df.empty:
            calculate_cached_metrics(costs_df, sales_df)
        
        logger.info("Cache warming completed successfully")
    except Exception as e:
        logger.error(f"Cache warming failed: {e}")

def invalidate_financial_cache():
    """Invalidate all financial data caches"""
    patterns = [
        "get_cached_costs*",
        "get_cached_sales_orders*",
        "metrics_*",
        "reports_*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        deleted = cache_service.clear_pattern(pattern)
        total_deleted += deleted
    
    # Also clear Streamlit cache
    st.cache_data.clear()
    
    logger.info(f"Invalidated {total_deleted} cache entries")
    return total_deleted

def get_cache_health() -> Dict[str, Any]:
    """Get cache health metrics"""
    stats = cache_service.get_stats()
    
    health = {
        "status": "healthy" if stats["hit_rate"] > 0.5 else "degraded",
        "hit_rate": stats["hit_rate"],
        "total_requests": stats["hits"] + stats["misses"],
        "memory_cache_size": stats["memory_cache_size"],
        "redis_status": stats.get("redis_status", "unknown")
    }
    
    return health
