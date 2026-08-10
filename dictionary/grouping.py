"""Groups dictionary rows by Category -> Subcategory, preserving source order."""
from __future__ import annotations

from dictionary.models import ParamRow


def group_by_category_subcategory(rows: list[ParamRow]) -> dict[str, dict[str, list[ParamRow]]]:
    grouped: dict[str, dict[str, list[ParamRow]]] = {}
    for r in rows:
        grouped.setdefault(r.category, {}).setdefault(r.subcategory, []).append(r)
    return grouped
