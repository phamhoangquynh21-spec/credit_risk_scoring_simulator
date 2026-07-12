"""Cached service-role Supabase client for the src.db access layer.

Matches the pattern in services/ml/persistence.py: `supabase` is imported
lazily inside the factory so importing src.db never hard-requires it.
"""
from __future__ import annotations

import functools
import os


@functools.lru_cache(maxsize=1)
def get_service_client():
    """Return a process-wide Supabase client using the service-role key.

    Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from the environment
    (loading a local .env first if present). Raises RuntimeError naming the
    missing variable when unset.
    """
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set (required by src.db)")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set (required by src.db)")
    from supabase import create_client
    return create_client(url, key)
