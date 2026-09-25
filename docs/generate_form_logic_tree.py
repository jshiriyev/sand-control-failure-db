#!/usr/bin/env python3
"""Build the standalone, read-only form logic explorer from MASTER.xlsx.

The explorer deliberately imports build_model() from the real form generator.
That way its rule edges follow the same parsed Affected Subcategory and
Affected Parameter cells as the production form, rather than maintaining a
second interpretation of the workbook.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dictionary import classify_field, load_dictionary  # noqa: E402
from form.generate_form import build_model  # noqa: E402

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "form_logic_tree_template.html"
OUTPUT = HERE / "form_logic_tree.html"
SCOPE_GROUPS = (
    ("well", "Well", "well"),
    ("completion_interval", "Completion Interval", "completion"),
    ("sand_body", "Sand Body", "sand_body"),
)


def rules(table: dict, category: str, target: str) -> list[dict[str, str]]:
    return [
        {"parameter": parameter, "value": value}
        for parameter, value in table.get((category, target), [])
    ]


def build_tree() -> dict:
    rows = load_dictionary(ROOT / "MASTER.xlsx")
    model = build_model(rows)
    scopes = []
    controls = []

    for key, label, model_key in SCOPE_GROUPS:
        categories = []
        for category, subcategories in model[model_key].items():
            rendered_subcategories = []
            for subcategory, fields in subcategories.items():
                rendered_fields = []
                for row in fields:
                    spec = classify_field(row)
                    rendered_fields.append({
                        "number": row.row_number,
                        "parameter": row.parameter,
                        "unit": row.unit,
                        "required": spec.required,
                        "show": rules(model["param_show"], category, row.parameter),
                        "hide": rules(model["param_hide"], category, row.parameter),
                    })
                    if row.affected_subcategory or row.affected_parameter:
                        controls.append({
                            "scope": key,
                            "number": row.row_number,
                            "parameter": row.parameter,
                            "kind": spec.kind,
                            "options": spec.options,
                        })
                rendered_subcategories.append({
                    "name": subcategory,
                    "show": rules(model["subcat_show"], category, subcategory),
                    "hide": rules(model["subcat_hide"], category, subcategory),
                    "fields": rendered_fields,
                })
            categories.append({"name": category, "subcategories": rendered_subcategories})
        scopes.append({"key": key, "label": label, "categories": categories})

    return {"source": "MASTER.xlsx / MasterView", "scopes": scopes, "controls": controls}


def main() -> None:
    payload = json.dumps(build_tree(), ensure_ascii=False, separators=(",", ":"))
    # JSON is embedded in a script element. Prevent a workbook label from
    # terminating that element, while keeping the file usable without a server.
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    source = TEMPLATE.read_text(encoding="utf-8")
    if source.count("__TREE_DATA__") != 1:
        raise ValueError("Explorer template must have exactly one data placeholder")
    OUTPUT.write_text(source.replace("__TREE_DATA__", payload), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
