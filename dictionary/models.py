"""Core data types shared by every consumer of the dictionary."""
from __future__ import annotations

from dataclasses import dataclass, field

WELL_SCOPE = "Well"
COMPLETION_SCOPE = "Completion Interval {id}"
SAND_BODY_SCOPE = "Sand Body {id}"


@dataclass
class ParamRow:
    row_number: int
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
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None  # HTML5-compatible regex, e.g. r"^[A-Za-z0-9]+$"
    multi_labels: list[str] = field(default_factory=list)
    # Parallel to multi_labels -- per-sub-value min/max pulled from that
    # sub-value's own spec (each sub-value in a multi-number cell carries its
    # own independent Data Validation spec, not just a shared "Number" type).
    multi_min_values: list[float | None] = field(default_factory=list)
    multi_max_values: list[float | None] = field(default_factory=list)
