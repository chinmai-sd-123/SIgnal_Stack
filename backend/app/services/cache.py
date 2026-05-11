"""
Redis Cache Service.

Provides caching for:
- Snapshot metadata (avoid re-fetching from disk)
- GitHub API responses (rate limit protection)
- Signal extraction results (for repeated evaluations)
- LLM responses (for identical prompts)
"""

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import timedelta
import os

# Try to import redis, fall back to in-memory cache if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheService:
    """
    Cache service with Redis backend and in-memory fallback.
    
    All cache operations are safe - they never raise exceptions,
    falling back to no-cache behavior if Redis is unavailable.
    """
    
    def __init__(self):
        self.redis_client = None
        self._memory_cache: Dict[str, Any] = {}
        self._connect()
    
    def _connect(self):
        """Attempt to connect to Redis."""
        if not REDIS_AVAILABLE:
            print("Redis not installed, using in-memory cache")
            return
        
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        try:
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            print(f"Connected to Redis at {redis_url}")
        except Exception as e:
            print(f"Redis connection failed: {e}, using in-memory cache")
            self.redis_client = None
    
    def _make_key(self, prefix: str, *args) -> str:
        """Create a cache key from prefix and args."""
        key_parts = [prefix] + [str(a) for a in args]
        return ":".join(key_parts)
    
    def _hash_key(self, data: str) -> str:
        """Create a hash for large keys."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            print(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set a value in cache with TTL."""
        try:
            serialized = json.dumps(value)
            if self.redis_client:
                self.redis_client.setex(key, ttl_seconds, serialized)
            else:
                self._memory_cache[key] = value
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with a given prefix."""
        count = 0
        try:
            if self.redis_client:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(cursor, match=f"{prefix}:*")
                    if keys:
                        self.redis_client.delete(*keys)
                        count += len(keys)
                    if cursor == 0:
                        break
            else:
                keys_to_delete = [k for k in self._memory_cache if k.startswith(prefix)]
                for k in keys_to_delete:
                    del self._memory_cache[k]
                    count += 1
        except Exception as e:
            print(f"Cache clear error: {e}")
        return count

    # Convenience methods for specific cache types
    
    def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Get cached snapshot metadata."""
        return self.get(self._make_key("snapshot", snapshot_id))
    
    def set_snapshot(self, snapshot_id: str, metadata: Dict, ttl: int = 86400) -> bool:
        """Cache snapshot metadata (24h default)."""
        return self.set(self._make_key("snapshot", snapshot_id), metadata, ttl)
    
    def get_github_response(self, url: str) -> Optional[Dict]:
        """Get cached GitHub API response."""
        return self.get(self._make_key("github", self._hash_key(url)))
    
    def set_github_response(self, url: str, response: Dict, ttl: int = 300) -> bool:
        """Cache GitHub API response (5min default)."""
        return self.set(self._make_key("github", self._hash_key(url)), response, ttl)
    
    def get_signals(self, repo_url: str, commit_hash: str) -> Optional[Dict]:
        """Get cached signal extraction results."""
        key = self._make_key("signals", self._hash_key(f"{repo_url}:{commit_hash}"))
        return self.get(key)
    
    def set_signals(self, repo_url: str, commit_hash: str, signals: Dict, ttl: int = 3600) -> bool:
        """Cache signal extraction results (1h default)."""
        key = self._make_key("signals", self._hash_key(f"{repo_url}:{commit_hash}"))
        return self.set(key, signals, ttl)
    
    def get_llm_response(self, prompt_hash: str) -> Optional[Dict]:
        """Get cached LLM response."""
        return self.get(self._make_key("llm", prompt_hash))
    
    def set_llm_response(self, prompt: str, response: Dict, ttl: int = 3600) -> bool:
        """Cache LLM response (1h default)."""
        prompt_hash = self._hash_key(prompt)
        return self.set(self._make_key("llm", prompt_hash), response, ttl)


# Global cache instance
cache = CacheService()


def cached(prefix: str, ttl_seconds: int = 3600, key_args: list = None):
    """
    Decorator to cache function results.
    
    Usage:
        @cached("github_repos", ttl_seconds=300, key_args=["repo_url"])
        def fetch_repo(repo_url: str) -> dict:
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Build cache key from specified args
            if key_args:
                key_parts = []
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                
                for i, arg in enumerate(args):
                    if i < len(params) and params[i] in key_args:
                        key_parts.append(str(arg))
                
                for key_arg in key_args:
                    if key_arg in kwargs:
                        key_parts.append(str(kwargs[key_arg]))
                
                cache_key = cache._make_key(prefix, *key_parts)
            else:
                cache_key = cache._make_key(prefix, cache._hash_key(str(args) + str(kwargs)))
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator
