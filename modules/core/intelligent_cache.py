"""
Intelligent Caching System for GovSight
Provides smart caching with automatic invalidation and performance optimization
"""

import time
import threading
import pickle
import hashlib
from typing import Any, Dict, Optional, List, Callable
from functools import wraps
from datetime import datetime, timedelta
import streamlit as st

class SmartCache:
    """Thread-safe intelligent cache with automatic invalidation"""
    
    def __init__(self, default_ttl: int = 300, max_memory_mb: int = 100):
        self.cache = {}
        self.metadata = {}
        self.access_counts = {}
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory = 0
        self.lock = threading.RLock()
        
        # Performance tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
    
    def _calculate_size(self, obj: Any) -> int:
        """Calculate approximate memory size of object"""
        try:
            return len(pickle.dumps(obj))
        except:
            return 1024  # Default estimate
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate unique cache key"""
        key_data = f"{prefix}|{args}|{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.metadata:
            return True
        
        meta = self.metadata[key]
        return time.time() > meta['expires_at']
    
    def _evict_lru(self):
        """Evict least recently used items to free memory"""
        with self.lock:
            if not self.cache:
                return
            
            # Sort by last access time (oldest first)
            sorted_keys = sorted(
                self.metadata.keys(),
                key=lambda k: self.metadata[k]['last_access']
            )
            
            # Remove oldest entries until memory is acceptable
            for key in sorted_keys:
                if self.current_memory < self.max_memory_bytes * 0.8:
                    break
                
                self._remove_entry(key)
                self.stats['evictions'] += 1
    
    def _remove_entry(self, key: str):
        """Remove cache entry and update memory tracking"""
        if key in self.cache:
            self.current_memory -= self.metadata[key]['size']
            del self.cache[key]
            del self.metadata[key]
            if key in self.access_counts:
                del self.access_counts[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            self.stats['total_requests'] += 1
            
            if key not in self.cache or self._is_expired(key):
                self.stats['misses'] += 1
                if key in self.cache:
                    self._remove_entry(key)
                return None
            
            # Update access metadata
            self.metadata[key]['last_access'] = time.time()
            self.access_counts[key] = self.access_counts.get(key, 0) + 1
            
            self.stats['hits'] += 1
            return self.cache[key]
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache"""
        with self.lock:
            # Calculate size and check if it fits
            size = self._calculate_size(value)
            
            # Don't cache extremely large objects
            if size > self.max_memory_bytes * 0.3:
                return False
            
            # Evict old entries if needed
            if self.current_memory + size > self.max_memory_bytes:
                self._evict_lru()
            
            # Remove existing entry if present
            if key in self.cache:
                self._remove_entry(key)
            
            # Store new entry
            expires_at = time.time() + (ttl or self.default_ttl)
            
            self.cache[key] = value
            self.metadata[key] = {
                'created_at': time.time(),
                'last_access': time.time(),
                'expires_at': expires_at,
                'size': size
            }
            self.access_counts[key] = 1
            self.current_memory += size
            
            return True
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries by pattern"""
        with self.lock:
            if pattern is None:
                # Clear all
                self.cache.clear()
                self.metadata.clear()
                self.access_counts.clear()
                self.current_memory = 0
            else:
                # Clear entries matching pattern
                keys_to_remove = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_remove:
                    self._remove_entry(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self.lock:
            hit_rate = 0
            if self.stats['total_requests'] > 0:
                hit_rate = self.stats['hits'] / self.stats['total_requests']
            
            return {
                'hit_rate': hit_rate,
                'total_entries': len(self.cache),
                'memory_usage_mb': self.current_memory / (1024 * 1024),
                'memory_usage_percent': (self.current_memory / self.max_memory_bytes) * 100,
                **self.stats
            }

# Global cache instances
_caches = {}

def get_cache(name: str = 'default', ttl: int = 300, max_memory_mb: int = 50) -> SmartCache:
    """Get or create named cache instance"""
    if name not in _caches:
        _caches[name] = SmartCache(default_ttl=ttl, max_memory_mb=max_memory_mb)
    return _caches[name]

def cache_result(cache_name: str = 'default', ttl: int = 300, key_prefix: str = None):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache(cache_name, ttl)
            
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = cache._generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.put(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def cached_dataframe(ttl: int = 300, cache_name: str = 'dataframes'):
    """Specialized decorator for caching pandas DataFrames"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache(cache_name, ttl, max_memory_mb=200)  # Larger cache for DataFrames
            
            cache_key = cache._generate_key(func.__name__, *args, **kwargs)
            
            cached_df = cache.get(cache_key)
            if cached_df is not None:
                return cached_df.copy()  # Return copy to prevent modification
            
            result = func(*args, **kwargs)
            
            # Only cache if result is a DataFrame and not too large
            if hasattr(result, 'shape') and len(result) < 10000:  # Don't cache huge DataFrames
                cache.put(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_by_operation(operation_type: str):
    """Invalidate relevant caches based on data operation type"""
    patterns_to_invalidate = {
        'financial_data': ['gl_accounts', 'transactions', 'balances'],
        'employee_data': ['payroll', 'employees', 'benefits'],
        'budget_data': ['budgets', 'allocations', 'scenarios'],
        'all': None  # Invalidate everything
    }
    
    patterns = patterns_to_invalidate.get(operation_type, [operation_type])
    
    for cache_name in _caches:
        cache = _caches[cache_name]
        if patterns is None:
            cache.invalidate()
        else:
            for pattern in patterns:
                cache.invalidate(pattern)

# Session state cache for Streamlit
def st_cache_data(ttl: int = 300, max_entries: int = 100):
    """Streamlit-aware caching decorator"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize session cache if not exists
            if 'st_cache' not in st.session_state:
                st.session_state.st_cache = {}
            
            cache = st.session_state.st_cache
            
            # Generate key
            key_data = f"{func.__name__}|{args}|{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    return result
                else:
                    del cache[cache_key]
            
            # Execute and cache
            result = func(*args, **kwargs)
            
            # Maintain cache size
            if len(cache) >= max_entries:
                # Remove oldest entry
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]
            
            cache[cache_key] = (result, time.time())
            return result
        
        return wrapper
    return decorator

def get_cache_performance_report() -> Dict[str, Any]:
    """Get comprehensive cache performance report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'caches': {}
    }
    
    total_memory = 0
    total_entries = 0
    weighted_hit_rate = 0
    total_requests = 0
    
    for name, cache in _caches.items():
        stats = cache.get_stats()
        report['caches'][name] = stats
        
        total_memory += stats['memory_usage_mb']
        total_entries += stats['total_entries']
        total_requests += stats['total_requests']
        weighted_hit_rate += stats['hit_rate'] * stats['total_requests']
    
    if total_requests > 0:
        weighted_hit_rate /= total_requests
    
    report['summary'] = {
        'total_memory_mb': total_memory,
        'total_entries': total_entries,
        'overall_hit_rate': weighted_hit_rate,
        'total_requests': total_requests
    }
    
    return report