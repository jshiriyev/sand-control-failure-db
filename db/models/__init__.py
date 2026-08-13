"""Importing this package registers all 4 tables on db.base.Base.metadata."""
from db.models.completion_interval import CompletionInterval
from db.models.organization import Organization
from db.models.sand_body import SandBody
from db.models.well import Well

__all__ = ["CompletionInterval", "Organization", "SandBody", "Well"]
