"""
Declarative base that all ORM models inherit from.

Import Base here so Alembic's env.py can reference a single location.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
