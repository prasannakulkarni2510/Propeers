"""Shared singletons for the API."""
from __future__ import annotations

from functools import lru_cache

from .service import Service


@lru_cache(maxsize=1)
def get_service() -> Service:
    return Service()
