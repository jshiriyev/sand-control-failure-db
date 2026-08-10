#!/usr/bin/env python3
"""Generate a standalone HTML intake form from the Sand Control Failure Data Dictionary.

Usage:
    python form/generate_form.py [input.xlsx] [output.html]

Input is the "MasterView" sheet of MASTER.xlsx, 11 columns in this order:
    Scope, Category, Subcategory, Parameter, Input Type, Unit,
    Affected Subcategory, Affected Parameter, Data Validation, Tooltip, User comment

The dictionary-parsing layer (ParamRow, FieldSpec, load_dictionary,
classify_field, and the cell-DSL parsers) lives in the top-level `dictionary`
package and is shared with `db/codegen.py`, so the form and the database
schema are always derived from the exact same interpretation of MASTER.xlsx.
See CLAUDE.md for the full data model. Key points this generator relies on:

- `Scope` is one of "Well", "Production Interval {id}", "Completion Interval {id}" --
  a well has one or more Production Intervals, each of which has one or more
  Completion Intervals (sand bodies). The form renders two independently
  repeatable, nested block levels for these.
- `Data Validation`, `Affected Subcategory` and `Affected Parameter` cells are
  written as Python-literal-safe text (parsed with ast.literal_eval), e.g.
  `{"Positive Number"}`, `{"Positive Integer": {"min": 1, "max": 10}}`, or
  `{"Onshore": {"Water depth": False, "Tree type": False}}`. In the Affected
  columns, a target listed as a plain set member means "start hidden, SHOW when
  this trigger value is selected" (the original convention); a target mapped to
  `False` means "start visible, HIDE when this trigger value is selected" (the
  newer exclude convention). Both can apply to the same target.

Requires: openpyxl (pip install openpyxl)
"""
from __future__ import annotations

import argparse
import html
import sys
from collections import defaultdict
from pathlib import Path

# Allow `python form/generate_form.py` to find the top-level `dictionary`
# package regardless of the current working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dictionary import (  # noqa: E402
    COMPLETION_SCOPE,
    PRODUCTION_SCOPE,
    WELL_SCOPE,
    FieldSpec,
    ParamRow,
    classify_field,
    group_by_category_subcategory,
    load_dictionary,
    parse_affected_cell,
)

DEFAULT_INPUT = REPO_ROOT / "MASTER.xlsx"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "sand_control_form.html"
DEFAULT_MAX_PRODUCTION = 10
DEFAULT_MAX_COMPLETION = 10

WELL_ZONE_CLASS = {
    "General Information": "zone-general",
    "Well Specific": "zone-well",
}

# These two counter Parameters get an "Apply" button next to their input so
# typing a number can actually grow the corresponding repeater. Matched by
# exact Parameter name -- if the dictionary renames either field, it just
# reverts to a plain Number input (no crash, no special handling lost).
COUNTER_ROLES = {
    "Number of production intervals": "apply-production",
    "Number of Completion Intervals": "apply-completion",
}


# --------------------------------------------------------------------------
# Conditional-visibility model (rendering-only concern -- the DB layer stores
# every field regardless of the form's show/hide rules, so this stays local
# rather than moving into the shared dictionary package).
# --------------------------------------------------------------------------

def build_model(rows: list[ParamRow]) -> dict:
    well_rows = [r for r in rows if r.scope == WELL_SCOPE]
    production_rows = [r for r in rows if r.scope == PRODUCTION_SCOPE]
    completion_rows = [r for r in rows if r.scope == COMPLETION_SCOPE]

    subcat_show: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    subcat_hide: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    param_show: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    param_hide: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)

    for r in rows:
        for trigger_value, target, exclude in parse_affected_cell(r.affected_subcategory):
            bucket = subcat_hide if exclude else subcat_show
            bucket[(r.category, target)].append((r.parameter, trigger_value))
        for trigger_value, target, exclude in parse_affected_cell(r.affected_parameter):
            bucket = param_hide if exclude else param_show
            bucket[(r.category, target)].append((r.parameter, trigger_value))

    return {
        "well": group_by_category_subcategory(well_rows),
        "production": group_by_category_subcategory(production_rows),
        "completion": group_by_category_subcategory(completion_rows),
        "subcat_show": subcat_show,
        "subcat_hide": subcat_hide,
        "param_show": param_show,
        "param_hide": param_hide,
    }


# --------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------

def esc(value) -> str:
    return html.escape(str(value), quote=True)


def build_show_hide_attr(category: str, name: str, show_rules: dict, hide_rules: dict) -> str:
    show = show_rules.get((category, name))
    hide = hide_rules.get((category, name))
    attrs = ""
    if show:
        expr = "||".join(f"{p}={v}" for p, v in show)
        attrs += f' data-show-if="{esc(expr)}"'
    if hide:
        expr = "||".join(f"{p}={v}" for p, v in hide)
        attrs += f' data-hide-if="{esc(expr)}"'
    if show:
        attrs += ' style="display:none"'
    return attrs


def render_control(row: ParamRow, spec: FieldSpec) -> str:
    dp = esc(row.parameter)
    req_attr = " required" if spec.required else ""
    if spec.kind == "select":
        options = ['<option value="" selected disabled>Select...</option>']
        options += [f'<option value="{esc(o)}">{esc(o)}</option>' for o in spec.options]
        return f'<select data-param="{dp}" data-kind="select"{req_attr}>{"".join(options)}</select>'
    if spec.kind == "number":
        attrs = ""
        if spec.min_value is not None:
            attrs += f' min="{spec.min_value}"'
        if spec.max_value is not None:
            attrs += f' max="{spec.max_value}"'
        attrs += f' step="{spec.step or "any"}"'
        return (f'<input type="number"{attrs}{req_attr} data-param="{dp}" '
                f'data-kind="number" placeholder="Enter value">')
    if spec.kind == "date":
        return f'<input type="date"{req_attr} data-param="{dp}" data-kind="date">'
    if spec.kind == "multi_number":
        items = "".join(
            f'<span class="mn-item"><span class="mn-label">{esc(lbl)}</span>'
            f'<input type="number" step="any" class="mn-input"></span>'
            for lbl in spec.multi_labels
        )
        return f'<div class="multi-number" data-param="{dp}" data-kind="multi_number">{items}</div>'
    return f'<textarea rows="2"{req_attr} data-param="{dp}" data-kind="text" placeholder="Enter text"></textarea>'


def render_field_row(row: ParamRow, param_show: dict, param_hide: dict) -> str:
    spec = classify_field(row)
    control = render_control(row, spec)
    show_unit = row.unit and spec.kind != "multi_number"
    unit_html = f'<span class="field-unit">{esc(row.unit)}</span>' if show_unit else '<span class="field-unit"></span>'
    attrs = build_show_hide_attr(row.category, row.parameter, param_show, param_hide)
    req_mark = '<span class="required-mark">*</span>' if spec.required else ""
    tip_html = f'<span class="tt" tabindex="0" data-tip="{esc(row.tooltip)}">?</span>' if row.tooltip else ""
    role = COUNTER_ROLES.get(row.parameter)
    action_html = (f'<span class="field-action"><button type="button" class="apply-count-btn" '
                    f'data-role="{role}">Apply</button></span>' if role else '<span class="field-action"></span>')
    return (f'<label class="field-row"{attrs}>'
            f'<span class="field-name">{esc(row.parameter)}{req_mark}{tip_html}</span>'
            f'{control}{unit_html}{action_html}</label>')


def render_subcategory(category: str, subcategory: str, rows: list[ParamRow], model: dict) -> str:
    field_rows = "".join(render_field_row(r, model["param_show"], model["param_hide"]) for r in rows)
    attrs = build_show_hide_attr(category, subcategory, model["subcat_show"], model["subcat_hide"])
    return (f'<section class="subcategory" data-category="{esc(category)}" '
            f'data-subcategory="{esc(subcategory)}"{attrs}>'
            f'<h3 class="subcat-title">{esc(subcategory)}</h3>'
            f'<div class="field-grid">{field_rows}</div></section>')


def render_flat_groups(grouped: dict[str, dict[str, list[ParamRow]]], model: dict) -> str:
    """Render subcategory sections with no category heading, in source order."""
    parts = []
    for category, subcats in grouped.items():
        for subcategory, rows in subcats.items():
            parts.append(render_subcategory(category, subcategory, rows, model))
    return "".join(parts)


def render_well_section(model: dict) -> str:
    zones = []
    for category, subcats in model["well"].items():
        css_class = WELL_ZONE_CLASS.get(category, "zone-well")
        groups = "".join(render_subcategory(category, sc, rows, model) for sc, rows in subcats.items())
        zones.append(f'<section class="zone {css_class}"><h2 class="zone-title">{esc(category)}</h2>{groups}</section>')
    return f'<div id="well-section">{"".join(zones)}</div>'


def render_completion_template(model: dict) -> str:
    groups = render_flat_groups(model["completion"], model)
    return (
        '<template class="completion-interval-template">'
        '<section class="interval-instance completion-instance">'
        '<div class="interval-banner">'
        '<h3 class="zone-title">COMPLETION INTERVAL <span class="interval-index"></span></h3>'
        '<button type="button" class="remove-interval-btn">Remove</button>'
        '</div>'
        f'{groups}'
        '</section>'
        '</template>'
    )


def render_production_template(model: dict) -> str:
    own_groups = render_flat_groups(model["production"], model)
    completion_tpl = render_completion_template(model)
    return (
        '<template id="production-interval-template">'
        '<section class="interval-instance production-instance">'
        '<div class="interval-banner">'
        '<h2 class="zone-title">PRODUCTION INTERVAL <span class="interval-index"></span></h2>'
        '<button type="button" class="remove-interval-btn">Remove</button>'
        '</div>'
        f'<div class="own-fields">{own_groups}</div>'
        '<div class="completion-nest">'
        '<div class="completion-intervals-toolbar">'
        '<h3>Completion Intervals</h3>'
        '<button type="button" class="add-completion-btn">+ Add Completion Interval</button>'
        '</div>'
        '<div class="completion-intervals-container"></div>'
        '</div>'
        f'{completion_tpl}'
        '</section>'
        '</template>'
    )


CSS = """
:root {
  --header-bg: #203864; --header-text: #ffffff;
  --general-header: #ffd966; --general-row: #fff2cc;
  --well-header: #9dc3e6; --well-row: #deebf7;
  --odd-header: #a9d18e; --odd-row: #e2f0d9;
  --even-header: #f4b183; --even-row: #fbe5d6;
  --ci-odd-header: #b4a7d6; --ci-odd-row: #ede7f6;
  --ci-even-header: #ea9999; --ci-even-row: #fbe4e4;
  --banner-text: #002060;
  --ink: #1f2328; --border: #c9c9c9;
}
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0 0 4rem; background: #f4f4f4; color: var(--ink); }
header.page-header { background: var(--header-bg); color: var(--header-text); padding: 1.25rem 1.5rem; }
header.page-header h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
header.page-header p { margin: 0; opacity: .85; font-size: .9rem; }
main { max-width: 980px; margin: 1.5rem auto; padding: 0 1rem; }
.zone { margin-bottom: 1.25rem; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; }
.zone-title { margin: 0; padding: .6rem 1rem; font-size: 1.05rem; font-weight: bold; color: var(--banner-text); }
.zone-general > .zone-title { background: var(--general-header); }
.zone-well > .zone-title { background: var(--well-header); }
.subcategory { border-top: 1px solid var(--border); }
.subcat-title { margin: 0; padding: .45rem 1rem; font-size: .95rem; font-weight: bold; }
.zone-general .subcat-title { background: var(--general-header); }
.zone-well .subcat-title { background: var(--well-header); }

.production-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1.25rem; }
.production-instance.interval-odd > .interval-banner .zone-title { background: var(--odd-header); }
.production-instance.interval-even > .interval-banner .zone-title { background: var(--even-header); }
.production-instance.interval-odd > .own-fields .subcat-title { background: var(--odd-header); }
.production-instance.interval-even > .own-fields .subcat-title { background: var(--even-header); }
.production-instance.interval-odd > .own-fields .field-row { background: var(--odd-row); }
.production-instance.interval-even > .own-fields .field-row { background: var(--even-row); }

.completion-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1rem; }
.completion-instance.interval-odd > .interval-banner .zone-title { background: var(--ci-odd-header); }
.completion-instance.interval-even > .interval-banner .zone-title { background: var(--ci-even-header); }
.completion-instance.interval-odd .subcat-title { background: var(--ci-odd-header); }
.completion-instance.interval-even .subcat-title { background: var(--ci-even-header); }
.completion-instance.interval-odd .field-row { background: var(--ci-odd-row); }
.completion-instance.interval-even .field-row { background: var(--ci-even-row); }

.field-grid { display: flex; flex-direction: column; }
.field-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.4fr) 90px 74px; gap: .75rem; align-items: center; padding: .4rem 1rem; border-top: 1px solid #eee; }
.zone-general .field-row { background: var(--general-row); }
.zone-well .field-row { background: var(--well-row); }
.field-name { font-size: .88rem; display: flex; align-items: center; gap: .3rem; }
.field-unit { font-size: .8rem; color: #555; }
.field-action { display: flex; }
.apply-count-btn { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .3rem .6rem; cursor: pointer; font-size: .78rem; }
.apply-count-btn:hover { opacity: .9; }
.required-mark { color: #b23; font-weight: bold; }
.tt {
  display: inline-flex; align-items: center; justify-content: center;
  width: 15px; height: 15px; border-radius: 50%; background: #8896a6; color: #fff;
  font-size: .68rem; font-weight: bold; cursor: help; position: relative; flex: 0 0 auto;
}
.tt:hover::after, .tt:focus::after {
  content: attr(data-tip); position: absolute; left: 0; bottom: 130%;
  background: #1f2328; color: #fff; padding: .4rem .6rem; border-radius: 4px; font-size: .75rem;
  font-weight: normal; white-space: normal; width: 220px; line-height: 1.35; z-index: 30;
  box-shadow: 0 2px 8px rgba(0,0,0,.3);
}
.tt:hover::before, .tt:focus::before {
  content: ''; position: absolute; left: 3px; bottom: 115%;
  border: 5px solid transparent; border-top-color: #1f2328; z-index: 30;
}
select, input[type=text], input[type=number], input[type=date], textarea {
  width: 100%; padding: .35rem .5rem; border: 1px solid #aaa; border-radius: 4px; font: inherit; background: #fff;
}
textarea { resize: vertical; }
.multi-number { display: flex; gap: .5rem; flex-wrap: wrap; }
.mn-item { display: flex; flex-direction: column; flex: 1 1 80px; }
.mn-label { font-size: .72rem; color: #555; }
.interval-banner { display: flex; align-items: center; justify-content: space-between; }
.interval-banner .zone-title { flex: 1; }
.remove-interval-btn { margin-right: 1rem; background: #b23; color: #fff; border: none; border-radius: 4px; padding: .3rem .7rem; cursor: pointer; font-size: .8rem; }
.remove-interval-btn:hover { background: #8f1c1c; }
#production-intervals-toolbar { display: flex; justify-content: space-between; align-items: center; margin: 1.5rem 0 .75rem; }
#production-intervals-toolbar h2 { margin: 0; font-size: 1.1rem; }
#add-production-btn { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .5rem 1rem; cursor: pointer; font-size: .9rem; }
#add-production-btn:disabled { background: #9aa; cursor: not-allowed; }
.completion-nest { margin: .75rem 0 0; padding: .5rem 0 .75rem 1rem; border-left: 3px solid var(--border); }
.completion-intervals-toolbar { display: flex; justify-content: space-between; align-items: center; margin: 0 1rem .6rem 0; }
.completion-intervals-toolbar h3 { margin: 0; font-size: .95rem; }
.add-completion-btn { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .4rem .8rem; cursor: pointer; font-size: .82rem; }
.add-completion-btn:disabled { background: #9aa; cursor: not-allowed; }
.completion-intervals-container { display: flex; flex-direction: column; gap: .75rem; }
.export-bar { position: sticky; bottom: 0; background: #fff; border-top: 2px solid var(--header-bg); padding: .75rem 1rem; display: flex; gap: .75rem; justify-content: flex-end; max-width: 980px; margin: 0 auto; }
.export-bar button { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .55rem 1.1rem; cursor: pointer; font-size: .9rem; }
.export-bar button:hover { opacity: .9; }
"""

JS = """
(function () {
  const MAX_PRODUCTION = __MAX_PRODUCTION__;
  const MAX_COMPLETION = __MAX_COMPLETION__;
  const wellSection = document.getElementById('well-section');

  function findParamField(root, paramName) {
    return root.querySelector(`[data-param="${CSS.escape(paramName)}"]`);
  }
  function getControlValue(el) {
    return (el.tagName === 'SELECT' || el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') ? el.value : '';
  }
  function exprMatches(root, expr) {
    return expr.split('||').some((rule) => {
      const i = rule.indexOf('=');
      const param = rule.slice(0, i);
      const value = rule.slice(i + 1);
      const trigger = findParamField(root, param);
      return trigger && getControlValue(trigger) === value;
    });
  }
  function evaluateVisibility(root) {
    root.querySelectorAll('[data-show-if], [data-hide-if]').forEach((el) => {
      let visible = true;
      const showExpr = el.getAttribute('data-show-if');
      if (showExpr) visible = exprMatches(root, showExpr);
      const hideExpr = el.getAttribute('data-hide-if');
      if (visible && hideExpr && exprMatches(root, hideExpr)) visible = false;
      el.style.display = visible ? '' : 'none';
    });
  }

  function setupRepeater({ container, template, addBtn, maxCount, labelSingular, onAdd }) {
    let count = 0;

    function renumber() {
      let i = 0;
      Array.from(container.children).forEach((section) => {
        i += 1;
        section.classList.remove('interval-odd', 'interval-even');
        section.classList.add(i % 2 === 1 ? 'interval-odd' : 'interval-even');
        const idxEl = section.querySelector(':scope > .interval-banner .interval-index');
        if (idxEl) idxEl.textContent = i;
        section.dataset.intervalIndex = i;
      });
      count = i;
      addBtn.disabled = count >= maxCount;
      addBtn.textContent = count >= maxCount ? `Maximum ${maxCount} reached` : `+ Add ${labelSingular}`;
    }

    function add() {
      if (count >= maxCount) return null;
      const node = template.content.cloneNode(true);
      const section = node.querySelector('.interval-instance');
      const removeBtn = section.querySelector(':scope > .interval-banner .remove-interval-btn');
      removeBtn.addEventListener('click', () => {
        if (count <= 1) {
          alert(`At least one ${labelSingular} is required and cannot be removed.`);
          return;
        }
        section.remove();
        renumber();
      });
      section.addEventListener('change', () => evaluateVisibility(section));
      container.appendChild(node);
      renumber();
      evaluateVisibility(section);
      if (onAdd) onAdd(section);
      return section;
    }

    addBtn.addEventListener('click', add);
    renumber();
    return { add, get count() { return count; } };
  }

  function wireApplyButton(root, ensureCount) {
    const btn = root.querySelector('.apply-count-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const input = btn.closest('.field-row').querySelector('[data-kind="number"]');
      const n = input ? parseInt(input.value, 10) : NaN;
      if (!Number.isFinite(n) || n < 1) return;
      ensureCount(n);
    });
  }

  function wireCompletionRepeater(productionSection) {
    const repeater = setupRepeater({
      container: productionSection.querySelector('.completion-intervals-container'),
      template: productionSection.querySelector('.completion-interval-template'),
      addBtn: productionSection.querySelector('.add-completion-btn'),
      maxCount: MAX_COMPLETION,
      labelSingular: 'Completion Interval',
    });
    repeater.add();
    wireApplyButton(productionSection.querySelector('.own-fields'), (n) => {
      const target = Math.min(n, MAX_COMPLETION);
      while (repeater.count < target) repeater.add();
    });
  }

  const productionRepeater = setupRepeater({
    container: document.getElementById('production-intervals-container'),
    template: document.getElementById('production-interval-template'),
    addBtn: document.getElementById('add-production-btn'),
    maxCount: MAX_PRODUCTION,
    labelSingular: 'Production Interval',
    onAdd: wireCompletionRepeater,
  });

  wellSection.addEventListener('change', () => evaluateVisibility(wellSection));
  evaluateVisibility(wellSection);
  productionRepeater.add();
  wireApplyButton(wellSection, (n) => {
    const target = Math.min(n, MAX_PRODUCTION);
    while (productionRepeater.count < target) productionRepeater.add();
  });

  // ---- export ----
  function readFieldValue(fieldRow) {
    const control = fieldRow.querySelector('[data-kind]');
    if (!control) return null;
    const kind = control.dataset.kind;
    if (kind === 'multi_number') {
      const vals = Array.from(control.querySelectorAll('input')).map((i) => i.value);
      return vals.every((v) => v === '') ? null : vals;
    }
    return control.value === '' ? null : control.value;
  }

  function fieldParam(fieldRow) {
    const control = fieldRow.querySelector('[data-param]');
    return control ? control.getAttribute('data-param') : '';
  }

  function walkVisibleFields(root, cb) {
    if (!root) return;
    root.querySelectorAll('.subcategory').forEach((sub) => {
      if (sub.style.display === 'none') return;
      sub.querySelectorAll('.field-row').forEach((fr) => {
        if (fr.style.display === 'none') return;
        cb(sub, fr);
      });
    });
  }

  function collectBucket(root) {
    const bucket = {};
    walkVisibleFields(root, (sub, fr) => {
      const cat = sub.dataset.category, subc = sub.dataset.subcategory;
      const param = fieldParam(fr);
      const val = readFieldValue(fr);
      if (val === null) return;
      bucket[cat] = bucket[cat] || {};
      bucket[cat][subc] = bucket[cat][subc] || {};
      bucket[cat][subc][param] = val;
    });
    return bucket;
  }

  function collectData() {
    const well = collectBucket(wellSection);
    const production_intervals = [];
    document.getElementById('production-intervals-container').querySelectorAll(':scope > .production-instance').forEach((prodSection) => {
      const fields = collectBucket(prodSection.querySelector('.own-fields'));
      const completion_intervals = [];
      prodSection.querySelectorAll(':scope > .completion-nest > .completion-intervals-container > .completion-instance').forEach((compSection) => {
        completion_intervals.push(collectBucket(compSection));
      });
      production_intervals.push({ fields, completion_intervals });
    });
    return { generated_at: new Date().toISOString(), well, production_intervals };
  }

  function collectCsvRows() {
    const rows = [];
    const pushRows = (root, prodIdx, compIdx) => {
      walkVisibleFields(root, (sub, fr) => {
        const val = readFieldValue(fr);
        if (val === null) return;
        rows.push([sub.dataset.category, sub.dataset.subcategory, fieldParam(fr),
          prodIdx, compIdx, Array.isArray(val) ? val.join(' / ') : val, fr.querySelector('.field-unit').textContent]);
      });
    };
    pushRows(wellSection, '', '');
    document.getElementById('production-intervals-container').querySelectorAll(':scope > .production-instance').forEach((prodSection) => {
      const prodIdx = prodSection.dataset.intervalIndex;
      pushRows(prodSection.querySelector('.own-fields'), prodIdx, '');
      prodSection.querySelectorAll(':scope > .completion-nest > .completion-intervals-container > .completion-instance').forEach((compSection) => {
        pushRows(compSection, prodIdx, compSection.dataset.intervalIndex);
      });
    });
    return rows;
  }

  function toCsv(rows) {
    const header = ['Category', 'Subcategory', 'Parameter', 'Production Interval', 'Completion Interval', 'Value', 'Unit'];
    const escCell = (v) => '"' + String(v).replace(/"/g, '""') + '"';
    return [header, ...rows].map((r) => r.map(escCell).join(',')).join('\\r\\n');
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  document.getElementById('export-json-btn').addEventListener('click', () => {
    download('sand_control_record.json', JSON.stringify(collectData(), null, 2), 'application/json');
  });
  document.getElementById('export-csv-btn').addEventListener('click', () => {
    download('sand_control_record.csv', toCsv(collectCsvRows()), 'text/csv');
  });
})();
"""


def render_html(model: dict, max_production: int = DEFAULT_MAX_PRODUCTION,
                 max_completion: int = DEFAULT_MAX_COMPLETION) -> str:
    well_html = render_well_section(model)
    production_template_html = render_production_template(model)
    js = JS.replace("__MAX_PRODUCTION__", str(max_production)).replace("__MAX_COMPLETION__", str(max_completion))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sand Control Failure Record Form (Producer Wells)</title>
<style>{CSS}</style>
</head>
<body>
<header class="page-header">
  <h1>Sand Control Failure Record Form &mdash; Producer Wells</h1>
  <p>Fill in the fields below, then use Export JSON / Export CSV to save your record. Hover the <strong>?</strong> icon next to a field for guidance.</p>
</header>
<main>
  <form id="sand-form" onsubmit="return false;">
    {well_html}
    <div id="production-intervals-toolbar">
      <h2>Production Intervals</h2>
      <button type="button" id="add-production-btn">+ Add Production Interval</button>
    </div>
    <div id="production-intervals-container"></div>
    {production_template_html}
  </form>
</main>
<div class="export-bar">
  <button type="button" id="export-json-btn">Export as JSON</button>
  <button type="button" id="export-csv-btn">Export as CSV</button>
</div>
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="Path to the dictionary xlsx file")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT, help="Path to write the generated HTML form")
    parser.add_argument("--max-production-intervals", type=int, default=DEFAULT_MAX_PRODUCTION,
                         help="Maximum number of Production Interval blocks a user can add")
    parser.add_argument("--max-completion-intervals", type=int, default=DEFAULT_MAX_COMPLETION,
                         help="Maximum number of Completion Interval blocks per Production Interval")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    rows = load_dictionary(input_path)
    if not rows:
        raise SystemExit("No rows found in the dictionary sheet.")
    model = build_model(rows)
    html_out = render_html(model, max_production=args.max_production_intervals,
                            max_completion=args.max_completion_intervals)

    output_path = Path(args.output)
    output_path.write_text(html_out, encoding="utf-8")
    well_subcats = sum(len(v) for v in model["well"].values())
    production_subcats = sum(len(v) for v in model["production"].values())
    completion_subcats = sum(len(v) for v in model["completion"].values())
    print(f"Wrote {output_path} ({len(rows)} parameters: "
          f"{well_subcats} well-scope, {production_subcats} production-interval-scope, "
          f"{completion_subcats} completion-interval-scope subcategories).")


if __name__ == "__main__":
    main()
