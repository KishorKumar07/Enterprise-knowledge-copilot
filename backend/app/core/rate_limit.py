"""Per-IP rate limiting (in-memory — fine for a single-instance MVP; swap the
storage_uri for Redis if this ever runs as multiple processes).

Applied to: auth endpoints (brute-force / signup-spam protection) and the
chat message endpoint (protects against one client running up the LLM bill).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
