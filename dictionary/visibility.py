"""Resolve the workbook's affected-field rules for every consumer.

The workbook stores a rule on its *source* row (for example, Sand failure
shows a set of targets when Yes is selected). Rendering and validation need
the inverse, target -> triggering answer. Keeping that inversion here lets
the HTML generator and the backend registry use the same rule graph.
"""
from __future__ import annotations

from collections import defaultdict

from dictionary.models import ParamRow
from dictionary.parsing import parse_affected_cell

RuleMap = dict[tuple[str, str], list[tuple[str, str]]]


def build_visibility_rules(rows: list[ParamRow]) -> dict[str, RuleMap]:
    maps: dict[str, RuleMap] = {
        "subcat_show": defaultdict(list),
        "subcat_hide": defaultdict(list),
        "param_show": defaultdict(list),
        "param_hide": defaultdict(list),
    }
    for row in rows:
        for value, target, exclude in parse_affected_cell(row.affected_subcategory):
            kind = "subcat_hide" if exclude else "subcat_show"
            maps[kind][(row.category, target)].append((row.parameter, value))
        for value, target, exclude in parse_affected_cell(row.affected_parameter):
            kind = "param_hide" if exclude else "param_show"
            maps[kind][(row.category, target)].append((row.parameter, value))
    return maps


def target_rules(rules: RuleMap, category: str, target: str) -> list[dict[str, str]]:
    """JSON-friendly form of all OR-connected rules for one target."""
    return [
        {"parameter": parameter, "value": value}
        for parameter, value in rules.get((category, target), [])
    ]
