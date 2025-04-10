"""
Cache utility functions for the financial tracker.
This module provides simple caching mechanisms to reduce API calls.
"""
import time

# Global cache dictionary
_cache = {}

def get_cached(key, ttl=60, fetch_func=None):
    """
    Get a value from the cache, or fetch it if not available.
    
    Args:
        key (str): The cache key
        ttl (int): Time-to-live in seconds
        fetch_func (callable): Function to call to fetch data if not in cache
    
    Returns:
        The cached value or newly fetched value
    """
    global _cache
    
    # Check if key exists and is not expired
    if key in _cache and time.time() - _cache[key]['timestamp'] < ttl:
        return _cache[key]['data']
    
    # If fetch function provided, use it to get fresh data
    if fetch_func:
        data = fetch_func()
        _cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        return data
    
    return None

def set_cached(key, data):
    """
    Store a value in the cache.
    
    Args:
        key (str): The cache key
        data: The data to cache
        
    Returns:
        The cached data
    """
    global _cache
    
    _cache[key] = {
        'data': data,
        'timestamp': time.time()
    }
    
    return data

def invalidate_cache(key=None):
    """
    Invalidate a specific cache key or the entire cache.
    
    Args:
        key (str, optional): The cache key to invalidate. If None, invalidates all.
    """
    global _cache
    
    if key:
        if key in _cache:
            del _cache[key]
    else:
        _cache = {}