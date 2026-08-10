"""Core data types shared by every consumer of the dictionary."""
from __future__ import annotations

from dataclasses import dataclass, field

WELL_SCOPE = "Well"
PRODUCTION_SCOPE = "Production Interval {id}"
COMPLETION_SCOPE = "Completion Interval {id}"


@dataclass
class ParamRow:
    scope: str
    category: str
    subcategory: str
    parameter: str
    input_type: str
    unit: str
    affected_subcategory: str
    affected_parameter: str
    data_validation: str
    tooltip: str
    user_comment: str


@dataclass
class FieldSpec:
    kind: str  # select | text | number | date | multi_number
    options: list[str] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    required: bool = False
    multi_labels: list[str] = field(default_factory=list)
