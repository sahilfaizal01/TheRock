import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Simple file-based cache for GitHub data"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """Get the file path for a cache key"""
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str, max_age_hours: int = 24) -> Optional[Any]:
        """Get cached data if it exists and is not expired"""
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            # Check if expired
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=max_age_hours):
                logger.info(f"Cache expired for {key}")
                return None

            logger.info(f"Cache hit for {key}")
            return cached['data']

        except Exception as e:
            logger.error(f"Error reading cache for {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> bool:
        """Cache data with current timestamp"""
        cache_path = self._get_cache_path(key)

        try:
            cached = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }

            with open(cache_path, 'w') as f:
                json.dump(cached, f, indent=2, default=str)

            logger.info(f"Cached data for {key}")
            return True

        except Exception as e:
            logger.error(f"Error caching data for {key}: {e}")
            return False

    def clear(self, key: Optional[str] = None) -> bool:
        """Clear cache for a specific key or all cache"""
        try:
            if key:
                cache_path = self._get_cache_path(key)
                if os.path.exists(cache_path):
                    os.remove(cache_path)
                    logger.info(f"Cleared cache for {key}")
            else:
                # Clear all cache files
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(self.cache_dir, filename))
                logger.info("Cleared all cache")

            return True

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
