import functools

_cache = {}

def get_cached(key):
    return _cache.get(key)

def set_cached(key, value):
    _cache[key] = value
