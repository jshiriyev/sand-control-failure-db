"""Generates db/generated/*_columns.py and field_registry.json from MASTER.xlsx.

Regenerate after editing MASTER.xlsx:

    python -m db.codegen

Never hand-edit anything under db/generated/ -- it's overwritten wholesale
every run, and CI fails the build if the committed output doesn't match what
this script produces right now (the "codegen drift check" -- see
.github/workflows/ci.yml).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from db.naming import derive_column_names  # noqa: E402
from db.type_mapping import sqla_type_for  # noqa: E402
from dictionary import (  # noqa: E402
    COMPLETION_SCOPE,
    SAND_BODY_SCOPE,
    WELL_SCOPE,
    ParamRow,
    classify_field,
    load_dictionary,
)
from dictionary.models import FieldSpec  # noqa: E402

MASTER_XLSX = REPO_ROOT / "MASTER.xlsx"
GENERATED_DIR = Path(__file__).resolve().parent / "generated"

# (registry key prefix, Scope literal, generated module name, table name)
SCOPES = [
    ("well", WELL_SCOPE, "well_columns", "well"),
    ("completion_interval", COMPLETION_SCOPE, "completion_interval_columns", "completion_interval"),
    ("sand_body", SAND_BODY_SCOPE, "sand_body_columns", "sand_body"),
]


class CodegenError(Exception):
    pass


def _column_type_name(row: ParamRow, spec: FieldSpec) -> str:
    return type(sqla_type_for(row.input_type, spec)).__name__


def generate() -> dict[str, list[tuple[str, str, str]]]:
    """Writes db/generated/* and returns {scope_key: [(col_name, type_name, source_parameter), ...]}."""
    rows = load_dictionary(MASTER_XLSX)
    registry: dict[str, dict] = {}
    per_table_columns: dict[str, list[tuple[str, str, str]]] = {}

    for scope_key, scope_literal, module_name, table_name in SCOPES:
        scope_rows = [r for r in rows if r.scope == scope_literal]
        seen: set[str] = set()
        columns: list[tuple[str, str, str]] = []

        for row in scope_rows:
            spec = classify_field(row)
            col_names = derive_column_names(row.parameter, spec.kind, spec.multi_labels)
            for name in col_names:
                if name in seen:
                    raise CodegenError(
                        f"column name collision in table {table_name!r}: {name!r} "
                        f"(from Parameter {row.parameter!r})"
                    )
                seen.add(name)
            type_name = _column_type_name(row, spec)
            columns.extend((name, type_name, row.parameter) for name in col_names)

            registry_key = f"{scope_key}::{row.category}::{row.subcategory}::{row.parameter}"
            registry[registry_key] = {
                "scope": scope_key,
                "table": table_name,
                "category": row.category,
                "subcategory": row.subcategory,
                "parameter": row.parameter,
                "kind": spec.kind,
                "db_type": type_name,
                "db_columns": col_names,
                "options": spec.options,
                "min_value": spec.min_value,
                "max_value": spec.max_value,
                "step": spec.step,
                "required": spec.required,
                "min_length": spec.min_length,
                "max_length": spec.max_length,
                "pattern": spec.pattern,
                "unit": row.unit,
            }

        per_table_columns[scope_key] = columns
        _write_columns_module(module_name, table_name, columns)

    _write_registry(registry)
    return per_table_columns


def _write_columns_module(module_name: str, table_name: str, columns: list[tuple[str, str, str]]) -> None:
    used_types = sorted({t for _, t, _ in columns})
    if used_types:
        import_line = f"from sqlalchemy import Column, {', '.join(used_types)}"
    else:
        import_line = "from sqlalchemy import Column"
    lines = [
        "# GENERATED FILE -- DO NOT EDIT BY HAND.",
        "# Regenerate with: python -m db.codegen   (source: MASTER.xlsx, sheet MasterView)",
        import_line,
        "",
        f"{table_name.upper()}_COLUMNS = [",
    ]
    for name, type_name, comment in columns:
        escaped_comment = comment.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    Column("{name}", {type_name}, nullable=True, comment="{escaped_comment}"),')
    lines.append("]")
    lines.append("")
    (GENERATED_DIR / f"{module_name}.py").write_text("\n".join(lines), encoding="utf-8")


def _write_registry(registry: dict) -> None:
    text = json.dumps(registry, indent=2, sort_keys=True) + "\n"
    (GENERATED_DIR / "field_registry.json").write_text(text, encoding="utf-8")


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    init_file = GENERATED_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")
    per_table = generate()
    counts = ", ".join(f"{k}={len(v)}" for k, v in per_table.items())
    print(f"Wrote db/generated/ ({counts} columns).")


if __name__ == "__main__":
    main()
