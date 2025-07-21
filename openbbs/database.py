"""Compatibility helpers for database access.

This module previously served as a placeholder while the project was
experimenting with various database backends.  It now simply re-exports
the lightweight helpers from :mod:`db` so existing imports continue to
work.
"""

from db import connect, init_db, record_sync

__all__ = ["connect", "init_db", "record_sync"]

