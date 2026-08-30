"""Data Validation / Affected-column cell parsing.

Data Validation cells are close to JSON, modeled after Excel's own Data
Validation dialog: a type name plus optional modifiers, e.g.
`{"Decimal": {"min": 0}}`, `{"List": {"options": ["A", "B"], "required":
True}}`, `{"Whole number": {"min": 1, "max": 10, "required": True}}`, or a
bare `{"Decimal"}` / `{"Short Date"}` / `{"Any Value": {}}` when there's
nothing to constrain. `List`/`Boolean` cells nest their option array under
an `"options"` key alongside any other modifiers (`required`, etc.) rather
than being the modifier dict directly; the older flat-list shape
(`{"List": ["A", "B"]}`, no modifiers possible) still parses too, for any
cell that hasn't been migrated. They're parsed with ast.literal_eval
(tolerant of JSON's lowercase true/false/null too, since the cells aren't
strictly JSON) rather than a strict JSON parser.

Multi-number Text cells (sub-values packed into one cell, e.g. "Mud PSD")
nest one such spec per sub-value inside a `{[...]}` wrapper. That wrapper
isn't valid literal syntax on its own -- `_split_top_level` + a per-segment
re-parse recovers it into a list of the same per-spec shape used everywhere
else, so each sub-value can carry its own type/min/max independently.

Affected Subcategory / Affected Parameter cells are a separate, older
trigger -> target DSL that this dictionary revision left unchanged --
see parse_affected_cell.
"""
from __future__ import annotations

import ast
import re

_BOOL_NULL_RE = re.compile(r"\btrue\b|\bfalse\b|\bnull\b")
_BOOL_NULL_TOKENS = {"true": "True", "false": "False", "null": "None"}


def safe_literal(raw: str):
    """ast.literal_eval, tolerant of JSON's lowercase true/false/null."""
    if not raw:
        return None
    text = str(raw).strip()
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        pass
    normalized = _BOOL_NULL_RE.sub(lambda m: _BOOL_NULL_TOKENS[m.group(0)], text)
    try:
        return ast.literal_eval(normalized)
    except (ValueError, SyntaxError):
        return None


def _split_top_level(text: str) -> list[str]:
    """Splits on top-level commas only, respecting {}/[] nesting and quoted
    strings -- used to recover the malformed multi-number wrapper shape."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    for ch in text:
        if ch == '"':
            in_string = not in_string
        if not in_string:
            if ch in "{[":
                depth += 1
            elif ch in "}]":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _single_spec(parsed) -> dict | None:
    """{"Type": {...modifiers}} or bare {"Type"} -> a spec dict, or None if
    `parsed` isn't shaped like either."""
    if isinstance(parsed, dict) and len(parsed) == 1:
        type_name, body = next(iter(parsed.items()))
    elif isinstance(parsed, set) and len(parsed) == 1:
        type_name, body = next(iter(parsed)), {}
    else:
        return None
    spec = {
        "type": str(type_name), "options": None, "min": None, "max": None, "required": False,
        "pattern": None, "length": None,
    }
    if isinstance(body, list):
        # Legacy shape: {"List": ["A", "B"]} -- the body *is* the option list.
        spec["options"] = body
    elif isinstance(body, dict):
        if "options" in body:
            # Current shape: {"List": {"options": ["A", "B"], "required": True}}
            # -- options live alongside other modifiers so a List/Boolean cell
            # can carry "required" (or any future modifier) too.
            spec["options"] = body.get("options")
        spec["min"] = body.get("min")
        spec["max"] = body.get("max")
        spec["required"] = bool(body.get("required"))
        spec["pattern"] = body.get("pattern")
        spec["length"] = body.get("length")
    return spec


_MULTI_WRAPPER_RE = re.compile(r"^\{\s*\[(.*)\]\s*\}$", re.S)


def parse_validation_cell(raw: str) -> dict | list[dict] | None:
    """Parses a Data Validation cell into one spec dict (single-value
    fields) or a list of spec dicts (multi-number Text fields, one per
    sub-value) -- see _single_spec for the dict shape. Returns None if the
    cell is blank or doesn't match any recognized shape.
    """
    text = (raw or "").strip()
    if not text:
        return None
    parsed = safe_literal(text)

    if isinstance(parsed, list) and parsed:
        specs = [_single_spec(item) for item in parsed]
        if all(specs):
            return specs

    if parsed is not None:
        return _single_spec(parsed)

    # Malformed-but-consistent shape used by today's multi-number Text
    # cells, e.g. {["Decimal": {"min": 0}, "Decimal": {"min": 0}]} -- not
    # valid literal syntax as a whole, so recover it segment by segment.
    m = _MULTI_WRAPPER_RE.match(text)
    if m:
        segments = _split_top_level(m.group(1))
        specs = [_single_spec(safe_literal("{" + segment + "}")) for segment in segments]
        if specs and all(specs):
            return specs

    return None


def parse_dropdown_options(raw: str) -> list[str]:
    """Ordered option list from a `{"List": [...]}` cell (or [] if `raw`
    isn't a List-shaped cell). Options come from a Python/JSON list literal,
    so source order is preserved directly -- no separate ordering pass
    needed.
    """
    spec = parse_validation_cell(raw)
    if isinstance(spec, dict) and spec.get("options") is not None:
        return list(spec["options"])
    return []


# Matches a trailing run of slash-separated tokens at the end of a parameter
# name, e.g. "...D10/D25/D40/D50/D75/D90" -> "D10/D25/D40/D50/D75/D90".
MULTI_LABEL_SUFFIX_RE = re.compile(r'([A-Za-z0-9]+(?:/[A-Za-z0-9]+)+)$')


def _derive_multi_labels(unit: str, parameter: str, n: int) -> list[str]:
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


def parse_multi_number(raw: str, unit: str, parameter: str) -> tuple[list[str], list[dict]] | None:
    """(labels, per-sub-value specs) for a multi-number Text cell, or None
    if `raw` isn't a multi-number cell. Labels come from the Unit column if
    it's slash-delimited and the count matches, otherwise from a trailing
    slash-delimited run in the Parameter name, otherwise generic
    "Value 1", "Value 2", ...
    """
    specs = parse_validation_cell(raw)
    if not isinstance(specs, list) or not specs:
        return None
    labels = _derive_multi_labels(unit, parameter, len(specs))
    return labels, specs


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
