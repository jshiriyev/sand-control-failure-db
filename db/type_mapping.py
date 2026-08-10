"""Maps a dictionary Input Type (+ parsed FieldSpec) to a SQLAlchemy column type.

| Dictionary Input Type      | SQLAlchemy / Postgres type                          |
|-----------------------------|------------------------------------------------------|
| Dropdown Menu                | Text -- allow-list enforced by the API, not the DB   |
| Boolean                      | Boolean -- small, stable Yes/No domain                |
| Text (plain)                  | Text                                                  |
| Text (multi-number)          | Numeric, once per expanded sub-column                |
| Number, no integer step      | Numeric -- unconstrained precision/scale              |
| Number, step == 1            | Integer                                               |
| Short Date                   | Date                                                  |
"""
from __future__ import annotations

from sqlalchemy import Boolean, Date, Integer, Numeric, Text
from sqlalchemy.types import TypeEngine

from dictionary import FieldSpec


def sqla_type_for(input_type: str, spec: FieldSpec) -> TypeEngine:
    if input_type == "Boolean":
        return Boolean()
    if input_type == "Short Date":
        return Date()
    if input_type == "Number":
        return Integer() if spec.step == 1 else Numeric()
    if spec.kind == "multi_number":
        return Numeric()
    # Dropdown Menu, plain Text, and anything unrecognized -> free text.
    return Text()
