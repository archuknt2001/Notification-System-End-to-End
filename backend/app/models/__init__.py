"""
Models package.

All ORM models are imported here so that:
1. Alembic's env.py only needs to import this one module to register
   every table on Base.metadata for autogenerate.
2. Any module that needs the model classes can import from `app.models`
   rather than from the concrete file path.
"""

from app.models.notification import Notification  # noqa: F401

__all__ = ["Notification"]
