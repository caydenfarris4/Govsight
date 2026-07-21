"""
Data Caching System
In-memory and persistent caching for external data with TTL support

Features:
- In-memory caching with TTL
- SQLite persistence for long-term storage
- Automatic cache warming on startup
- Manual refresh capabilities
"""

import json
import time
import sqlite3
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from threading import Lock
import os


class DataCache:
    """Single cache entry with TTL support"""
    
    def __init__(self, key: str, value: Any, ttl: int = 3600):
        """
        Initialize cache entry
        
        Args:
            key: Cache key
            value: Cached value
            ttl: Time to live in seconds
        """
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() > self.expires_at
    
    def access(self) -> Any:
        """Access the cached value and update stats"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def refresh(self, value: Any, ttl: int = None):
        """Refresh cache entry with new value"""
        self.value = value
        self.created_at = time.time()
        if ttl:
            self.ttl = ttl
        self.expires_at = self.created_at + self.ttl


class CacheManager:
    """Manages in-memory and persistent caching"""
    
    def __init__(self, db_path: str = None, default_ttl: int = 3600,
                 max_memory_items: int = 1000):
        """
        Initialize cache manager
        
        Args:
            db_path: Path to SQLite database for persistence
            default_ttl: Default time to live in seconds
            max_memory_items: Maximum items to keep in memory
        """
        self.db_path = db_path or "databases/core/cache.db"
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        
        # In-memory cache
        self.memory_cache: Dict[str, DataCache] = {}
        self.cache_lock = Lock()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'refreshes': 0
        }
        
        # Initialize persistence
        self._init_database()
        
        # Warm cache on startup
        self._warm_cache()
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value BLOB,
                created_at REAL,
                expires_at REAL,
                ttl INTEGER,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                data_type TEXT,
                metadata TEXT
            )
        """)
        
        # Create index for expiration
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON cache(expires_at)
        """)
        
        # Create statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                timestamp REAL,
                stat_type TEXT,
                value INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _warm_cache(self):
        """Load frequently accessed items from database to memory"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get non-expired, frequently accessed items
            cursor.execute("""
                SELECT key, value, ttl, created_at, expires_at, access_count
                FROM cache
                WHERE expires_at > ?
                ORDER BY access_count DESC
                LIMIT ?
            """, (time.time(), self.max_memory_items // 2))
            
            rows = cursor.fetchall()
            
            with self.cache_lock:
                for row in rows:
                    key, value_blob, ttl, created_at, expires_at, access_count = row
                    
                    try:
                        # Deserialize value
                        value = pickle.loads(value_blob)
                        
                        # Create cache entry
                        cache_entry = DataCache(key, value, ttl)
                        cache_entry.created_at = created_at
                        cache_entry.expires_at = expires_at
                        cache_entry.access_count = access_count
                        
                        self.memory_cache[key] = cache_entry
                    except Exception as e:
                        print(f"Failed to warm cache for key {key}: {e}")
            
            conn.close()
            
            if rows:
                print(f"Warmed cache with {len(rows)} entries")
        
        except Exception as e:
            print(f"Cache warming failed: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if not found or expired
        
        Returns:
            Cached value or default
        """
        with self.cache_lock:
            # Check memory cache first
            if key in self.memory_cache:
                cache_entry = self.memory_cache[key]
                
                if not cache_entry.is_expired():
                    self.stats['hits'] += 1
                    return cache_entry.access()
                else:
                    # Remove expired entry
                    del self.memory_cache[key]
        
        # Check persistent cache
        value = self._get_from_database(key)
        
        if value is not None:
            self.stats['hits'] += 1
            
            # Add to memory cache if space available
            with self.cache_lock:
                if len(self.memory_cache) < self.max_memory_items:
                    self.memory_cache[key] = DataCache(key, value, self.default_ttl)
            
            return value
        
        self.stats['misses'] += 1
        return default
    
    def _get_from_database(self, key: str) -> Any:
        """Get value from database cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value, expires_at
                FROM cache
                WHERE key = ? AND expires_at > ?
            """, (key, time.time()))
            
            row = cursor.fetchone()
            
            if row:
                value_blob, expires_at = row
                
                # Update access statistics
                cursor.execute("""
                    UPDATE cache
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE key = ?
                """, (time.time(), key))
                
                conn.commit()
                conn.close()
                
                # Deserialize value
                return pickle.loads(value_blob)
            
            conn.close()
        
        except Exception as e:
            print(f"Database cache read failed for {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        
        Returns:
            Success status
        """
        ttl = ttl or self.default_ttl
        
        # Add to memory cache
        with self.cache_lock:
            # Evict if at capacity
            if len(self.memory_cache) >= self.max_memory_items:
                self._evict_lru()
            
            # Update or create entry
            if key in self.memory_cache:
                self.memory_cache[key].refresh(value, ttl)
                self.stats['refreshes'] += 1
            else:
                self.memory_cache[key] = DataCache(key, value, ttl)
        
        # Persist to database
        return self._save_to_database(key, value, ttl)
    
    def _save_to_database(self, key: str, value: Any, ttl: int) -> bool:
        """Save value to database cache"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Serialize value
            value_blob = pickle.dumps(value)
            
            # Determine data type for metadata
            data_type = type(value).__name__
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO cache
                (key, value, created_at, expires_at, ttl, data_type, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                value_blob,
                time.time(),
                time.time() + ttl,
                ttl,
                data_type,
                time.time()
            ))
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Database cache write failed for {key}: {e}")
            return False
    
    def _evict_lru(self):
        """Evict least recently used item from memory cache"""
        if not self.memory_cache:
            return
        
        # Find LRU item
        lru_key = min(self.memory_cache.keys(), 
                     key=lambda k: self.memory_cache[k].last_accessed)
        
        del self.memory_cache[lru_key]
        self.stats['evictions'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete item from cache"""
        # Remove from memory
        with self.cache_lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
        
        # Remove from database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to delete {key} from cache: {e}")
            return False
    
    def clear(self):
        """Clear all cache entries"""
        # Clear memory cache
        with self.cache_lock:
            self.memory_cache.clear()
        
        # Clear database cache
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to clear cache: {e}")
    
    def cleanup_expired(self):
        """Remove expired entries from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM cache
                WHERE expires_at < ?
            """, (time.time(),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                print(f"Cleaned up {deleted} expired cache entries")
        
        except Exception as e:
            print(f"Cache cleanup failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.cache_lock:
            memory_items = len(self.memory_cache)
            memory_expired = sum(1 for entry in self.memory_cache.values() 
                               if entry.is_expired())
        
        # Get database stats
        db_stats = self._get_database_stats()
        
        return {
            'memory': {
                'items': memory_items,
                'expired': memory_expired,
                'capacity': self.max_memory_items,
                'utilization': f"{(memory_items / self.max_memory_items) * 100:.1f}%"
            },
            'database': db_stats,
            'performance': {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{(self.stats['hits'] / max(1, self.stats['hits'] + self.stats['misses'])) * 100:.1f}%",
                'evictions': self.stats['evictions'],
                'refreshes': self.stats['refreshes']
            }
        }
    
    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database cache statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM cache")
            total = cursor.fetchone()[0]
            
            # Expired entries
            cursor.execute("SELECT COUNT(*) FROM cache WHERE expires_at < ?", (time.time(),))
            expired = cursor.fetchone()[0]
            
            # Most accessed
            cursor.execute("""
                SELECT key, access_count
                FROM cache
                ORDER BY access_count DESC
                LIMIT 5
            """)
            most_accessed = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_entries': total,
                'expired_entries': expired,
                'active_entries': total - expired,
                'most_accessed': [{'key': k, 'count': c} for k, c in most_accessed]
            }
        
        except Exception as e:
            print(f"Failed to get database stats: {e}")
            return {}
    
    def refresh_all_external_data(self):
        """Refresh all external data sources"""
        refresh_patterns = [
            'fred_',  # FRED economic data
            'bea_',   # BEA regional data
            'grant_'  # Grant opportunities
        ]
        
        refreshed = 0
        
        with self.cache_lock:
            keys_to_refresh = []
            
            for key in self.memory_cache.keys():
                for pattern in refresh_patterns:
                    if key.startswith(pattern):
                        keys_to_refresh.append(key)
                        break
        
        # Clear the identified keys
        for key in keys_to_refresh:
            self.delete(key)
            refreshed += 1
        
        print(f"Refreshed {refreshed} external data cache entries")
        return refreshed
    
    def get_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate consistent cache key from prefix and parameters"""
        # Sort parameters for consistency
        param_str = json.dumps(params, sort_keys=True)
        
        # Create hash for long parameter strings
        if len(param_str) > 50:
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{prefix}_{param_hash}"
        
        # Use readable key for short parameters
        param_key = '_'.join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{prefix}_{param_key}"