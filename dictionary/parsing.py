"""Data Validation / Affected-column cell parsing.

Cells are written as Python-literal-safe text. Curly-brace *sets* of quoted
strings (e.g. dropdown options) do not preserve source order once parsed by
ast.literal_eval (Python sets are unordered), so option lists are extracted
with an order-preserving regex instead. Dict literals (trigger -> spec, or
constraint-type -> modifiers) DO preserve key order and are safe to parse
directly.
"""
from __future__ import annotations

import ast
import re


def safe_literal(raw: str):
    if not raw:
        return None
    try:
        return ast.literal_eval(str(raw).strip())
    except (ValueError, SyntaxError):
        return None


def parse_dropdown_options(raw: str) -> list[str]:
    """Extract quoted option strings in source order (regex, not literal_eval)."""
    if not raw:
        return []
    return re.findall(r'"([^"]*)"', str(raw))


def parse_number_spec(raw: str) -> dict:
    parsed = safe_literal(raw)
    spec: dict = {}
    if parsed is None:
        return spec
    if isinstance(parsed, set):
        token = next(iter(parsed), "")
        if "positive" in token.lower():
            spec["min_value"] = 0
        return spec
    if isinstance(parsed, dict):
        for constraint_type, modifiers in parsed.items():
            ct = str(constraint_type).lower()
            if "positive" in ct:
                spec["min_value"] = 0
            if "integer" in ct:
                spec["step"] = 1
            if isinstance(modifiers, dict):
                if "min" in modifiers:
                    spec["min_value"] = modifiers["min"]
                if "max" in modifiers:
                    spec["max_value"] = modifiers["max"]
                if modifiers.get("required"):
                    spec["required"] = True
    return spec


# Matches a trailing run of slash-separated tokens at the end of a parameter
# name, e.g. "...D10/D25/D40/D50/D75/D90" -> "D10/D25/D40/D50/D75/D90".
MULTI_LABEL_SUFFIX_RE = re.compile(r'([A-Za-z0-9]+(?:/[A-Za-z0-9]+)+)$')


def parse_multi_number(raw: str, unit: str, parameter: str) -> list[str] | None:
    parsed = safe_literal(raw)
    if not isinstance(parsed, set):
        return None
    token = next(iter(parsed), "")
    tokens = [t.strip() for t in token.split("/")]
    if len(tokens) < 2 or not all(t.lower() == "number" for t in tokens):
        return None
    n = len(tokens)
    if unit:
        unit_tokens = [t.strip() for t in unit.split("/")]
        if len(unit_tokens) == n:
            return unit_tokens
    m = MULTI_LABEL_SUFFIX_RE.search(parameter)
    if m:
        name_tokens = m.group(1).split("/")
        if len(name_tokens) == n:
            return name_tokens
    return [f"Value {i + 1}" for i in range(n)]


def parse_affected_cell(raw: str) -> list[tuple[str, str, bool]]:
    """'{"Trigger": {"Target1", "Target2"}, "Trigger2": {"Target3": False}}'
    -> [(trigger, target, exclude), ...]. exclude=True means "hide on match"
    (the target started visible); exclude=False means "show on match" (the
    target started hidden) -- the original convention.
    """
    parsed = safe_literal(raw)
    if not isinstance(parsed, dict):
        return []
    out = []
    for trigger_value, spec in parsed.items():
        if isinstance(spec, dict):
            for target, flag in spec.items():
                out.append((str(trigger_value), str(target), flag is False))
        elif isinstance(spec, (set, list, tuple)):
            for target in spec:
                out.append((str(trigger_value), str(target), False))
    return out
