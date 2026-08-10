"""The shared SQLAlchemy declarative base every model attaches to."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
