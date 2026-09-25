#!/usr/bin/env python3
"""Generate a standalone HTML intake form from the Sand Control Failure Data Dictionary.

Usage:
    python form/generate_form.py [input.xlsx] [output.html]

Input is the "MasterView" sheet of MASTER.xlsx, 12 columns in this order:
    Row Number, Scope, Category, Subcategory, Parameter, Input Type, Unit,
    Affected Subcategory, Affected Parameter, Data Validation, Tooltip, User comment

The dictionary-parsing layer (ParamRow, FieldSpec, load_dictionary,
classify_field, and the cell-DSL parsers) lives in the top-level `dictionary`
package and is shared with `db/codegen.py`, so the form and the database
schema are always derived from the exact same interpretation of MASTER.xlsx.
See CLAUDE.md for the full data model. Key points this generator relies on:

- `Row Number` is each row's 1-based position in MasterView. It is rendered
  next to every field, zero-padded to 3 digits (e.g. "001", "025", "114"),
  so a submitted/rendered field can be cross-referenced back to its exact
  spreadsheet row.
- `Scope` is one of "Well", "Completion Interval {id}", "Sand Body {id}" --
  a well has one or more Completion Intervals, each of which has one or more
  Sand Bodies. The form renders two independently repeatable, nested block
  levels for these.
- `Data Validation`, `Affected Subcategory` and `Affected Parameter` cells are
  written as Python-literal-safe text (parsed with ast.literal_eval, tolerant
  of JSON's lowercase true/false/null). Data Validation cells are a type name
  plus optional modifiers, e.g. `{"Decimal": {"min": 0}}`, `{"List":
  {"options": ["A", "B"], "required": True}}`, `{"Text Length": {"min": 7,
  "pattern": "alphanumeric"}}`, or a bare `{"Short Date"}` when there's
  nothing to constrain. In the Affected columns, a target listed as a plain
  set member means "start hidden, SHOW when this trigger value is selected"
  (the original convention); a target mapped to `False` means "start
  visible, HIDE when this trigger value is selected" (the newer exclude
  convention). Both can apply to the same target.

Requires: openpyxl (pip install openpyxl)
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

# Allow `python form/generate_form.py` to find the top-level `dictionary`
# package regardless of the current working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dictionary import (  # noqa: E402
    COMPLETION_SCOPE,
    CURRENT_SCHEMA_VERSION,
    SAND_BODY_SCOPE,
    WELL_SCOPE,
    FieldSpec,
    ParamRow,
    build_visibility_rules,
    classify_field,
    group_by_category_subcategory,
    load_dictionary,
)

DEFAULT_INPUT = REPO_ROOT / "MASTER.xlsx"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "sand_control_form.html"
DEFAULT_MAX_COMPLETION = 10
DEFAULT_MAX_SAND_BODY = 10
# Form is emailed out as a standalone file with no backend to check against, so
# expiration is enforced client-side: baked in at generation time and re-checked
# by the browser on every load. Not tamper-proof, but sufficient for the actual
# threat model (a partner company holding onto an old file), and needs no new
# infrastructure. Bump this (or pass --expires-on) each time the form is reissued.
DEFAULT_EXPIRES_ON = "2026-11-01"

WELL_ZONE_CLASS = {
    "General Information": "zone-general",
    "Well Specific": "zone-well",
}

# These two counter Parameters get an "Apply" button next to their input so
# typing a number can actually grow the corresponding repeater. Matched by
# exact Parameter name -- if the dictionary renames either field, it just
# reverts to a plain Number input (no crash, no special handling lost).
COUNTER_ROLES = {
    "Number of Completion Intervals": "apply-completion",
    "Number of sand bodies": "apply-sand-body",
}

# The Well-scope Parameters whose values, joined in this order, name the
# exported files, so a reviewer can tell one record from another without
# opening it. The identification number is carried alongside the name because
# it is the constrained one (7+ alphanumeric), which keeps the filename
# distinct even when two submissions choose the same free-text label.
#
# Matched by exact Parameter name, same convention as COUNTER_ROLES. A missing
# or unusable name becomes "Unnamed"; the anonymized ID is included when
# available, which also gives partially filled drafts a recognizable filename.
EXPORT_NAME_PARAMS = (
    "Well name (anonymized)",
    "Well identification number (anonymized)",
)


# --------------------------------------------------------------------------
# Conditional-visibility model (rendering-only concern -- the DB layer stores
# every field regardless of the form's show/hide rules, so this stays local
# rather than moving into the shared dictionary package).
# --------------------------------------------------------------------------

def build_model(rows: list[ParamRow]) -> dict:
    well_rows = [r for r in rows if r.scope == WELL_SCOPE]
    completion_rows = [r for r in rows if r.scope == COMPLETION_SCOPE]
    sand_body_rows = [r for r in rows if r.scope == SAND_BODY_SCOPE]

    return {
        "well": group_by_category_subcategory(well_rows),
        "completion": group_by_category_subcategory(completion_rows),
        "sand_body": group_by_category_subcategory(sand_body_rows),
        **build_visibility_rules(rows),
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
        # The placeholder is deliberately NOT `disabled`. A disabled option can be
        # the initial selection but can never be chosen again, so a user who picks
        # a value by mistake has no way back to "no answer" -- and that also strands
        # the optional selects that drive show/hide rules (Completion Type, the two
        # Sand Control Selected Method fields, Placement Method, Pack Efficiency
        # Source) in whichever branch was chosen first, with no neutral state to
        # return to. `required` is what enforces required-ness, so a blanked
        # required select is still invalid and still blocks export; making the
        # placeholder reachable weakens nothing.
        #
        # Optional fields label it "(Blank)" rather than "Select...", so the
        # placeholder also says that leaving the field blank is a real answer here.
        blank_label = "Select..." if spec.required else "(Blank)"
        options = [f'<option value="" selected>{blank_label}</option>']
        if spec.options_by:
            # The workbook holds the choices for each Well type. JavaScript
            # supplies the relevant list after the controlling answer changes.
            conditional = f' data-options-by="{esc(json.dumps(spec.options_by))}"'
        else:
            conditional = ""
            options += [f'<option value="{esc(o)}">{esc(o)}</option>' for o in spec.options]
        return f'<select data-param="{dp}" data-kind="select"{conditional}{req_attr}>{"".join(options)}</select>'
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
        items = []
        for i, lbl in enumerate(spec.multi_labels):
            min_v = spec.multi_min_values[i] if i < len(spec.multi_min_values) else None
            max_v = spec.multi_max_values[i] if i < len(spec.multi_max_values) else None
            item_attrs = ""
            if min_v is not None:
                item_attrs += f' min="{min_v}"'
            if max_v is not None:
                item_attrs += f' max="{max_v}"'
            items.append(f'<span class="mn-item"><span class="mn-label">{esc(lbl)}</span>'
                         f'<input type="number" step="any"{item_attrs} class="mn-input"></span>')
        return f'<div class="multi-number" data-param="{dp}" data-kind="multi_number">{"".join(items)}</div>'
    if spec.kind == "text" and (spec.min_length is not None or spec.max_length is not None or spec.pattern):
        attrs = ""
        if spec.min_length is not None:
            attrs += f' minlength="{spec.min_length}"'
        if spec.max_length is not None:
            attrs += f' maxlength="{spec.max_length}"'
        if spec.pattern:
            attrs += f' pattern="{esc(spec.pattern)}"'
        return (f'<input type="text"{attrs}{req_attr} data-param="{dp}" '
                f'data-kind="text" placeholder="Enter text">')
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
    comment_html = f'<input type="text" class="field-comment" data-comment-for="{esc(row.parameter)}" placeholder="Comment">'
    rownum_html = f'<span class="field-rownum">{row.row_number:03d}</span>'
    return (f'<label class="field-row"{attrs}>'
            f'<span class="field-name">{rownum_html}{esc(row.parameter)}{req_mark}{tip_html}</span>'
            f'{control}{unit_html}{action_html}{comment_html}</label>')


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


def render_sand_body_template(model: dict) -> str:
    groups = render_flat_groups(model["sand_body"], model)
    return (
        '<template class="sand-body-template">'
        '<section class="interval-instance sand-body-instance">'
        '<div class="interval-banner">'
        '<h3 class="zone-title">COMPLETION INTERVAL <span class="completion-index"></span>'
        ' - SAND BODY <span class="interval-index"></span></h3>'
        '<button type="button" class="remove-interval-btn">Remove</button>'
        '</div>'
        f'{groups}'
        '</section>'
        '</template>'
    )


def render_completion_template(model: dict) -> str:
    own_groups = render_flat_groups(model["completion"], model)
    sand_body_tpl = render_sand_body_template(model)
    return (
        '<template id="completion-interval-template">'
        '<section class="interval-instance completion-instance">'
        '<div class="interval-banner">'
        '<h2 class="zone-title">COMPLETION INTERVAL <span class="interval-index"></span></h2>'
        '<button type="button" class="remove-interval-btn">Remove</button>'
        '</div>'
        f'<div class="own-fields">{own_groups}</div>'
        '<div class="sand-body-nest">'
        '<div class="sand-bodies-toolbar">'
        '<h3>Sand Bodies</h3>'
        '<button type="button" class="add-sand-body-btn">+ Add Sand Body</button>'
        '</div>'
        '<div class="sand-bodies-container"></div>'
        '</div>'
        f'{sand_body_tpl}'
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
  --sb-odd-header: #b4a7d6; --sb-odd-row: #ede7f6;
  --sb-even-header: #ea9999; --sb-even-row: #fbe4e4;
  --banner-text: #002060;
  --ink: #1f2328; --border: #c9c9c9;
}
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; margin: 0; padding: 0 0 4rem; background: #f4f4f4; color: var(--ink); }
header.page-header { background: var(--header-bg); color: var(--header-text); padding: 1.25rem 1.5rem; }
header.page-header h1 { margin: 0 0 .25rem; font-size: 1.4rem; }
header.page-header p { margin: 0; opacity: .85; font-size: .9rem; }
header.page-header .validity-notice { margin-top: .4rem; font-weight: 600; }
header.page-header .expired-banner { margin-top: .6rem; background: #b00020; color: #fff; padding: .6rem .9rem; border-radius: 4px; font-weight: 600; opacity: 1; }
main { max-width: 1280px; margin: 1.5rem auto; padding: 0 1rem; }
.zone { margin-bottom: 1.25rem; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; }
.zone-title { margin: 0; padding: .6rem 1rem; font-size: 1.05rem; font-weight: bold; color: var(--banner-text); }
.zone-general > .zone-title { background: var(--general-header); }
.zone-well > .zone-title { background: var(--well-header); }
.subcategory { border-top: 1px solid var(--border); }
.subcat-title { margin: 0; padding: .45rem 1rem; font-size: .95rem; font-weight: bold; }
.zone-general .subcat-title { background: var(--general-header); }
.zone-well .subcat-title { background: var(--well-header); }

.completion-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1.25rem; }
.completion-instance.interval-odd > .interval-banner .zone-title { background: var(--odd-header); }
.completion-instance.interval-even > .interval-banner .zone-title { background: var(--even-header); }
.completion-instance.interval-odd > .own-fields .subcat-title { background: var(--odd-header); }
.completion-instance.interval-even > .own-fields .subcat-title { background: var(--even-header); }
.completion-instance.interval-odd > .own-fields .field-row { background: var(--odd-row); }
.completion-instance.interval-even > .own-fields .field-row { background: var(--even-row); }

.sand-body-instance { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: #fff; margin-bottom: 1rem; }
.sand-body-instance.interval-odd > .interval-banner .zone-title { background: var(--sb-odd-header); }
.sand-body-instance.interval-even > .interval-banner .zone-title { background: var(--sb-even-header); }
.sand-body-instance.interval-odd .subcat-title { background: var(--sb-odd-header); }
.sand-body-instance.interval-even .subcat-title { background: var(--sb-even-header); }
.sand-body-instance.interval-odd .field-row { background: var(--sb-odd-row); }
.sand-body-instance.interval-even .field-row { background: var(--sb-even-row); }

.field-grid { display: flex; flex-direction: column; }
.field-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.4fr) 90px 74px minmax(160px, 1fr); gap: .75rem; align-items: center; padding: .4rem 1rem; border-top: 1px solid #eee; }
.zone-general .field-row { background: var(--general-row); }
.zone-well .field-row { background: var(--well-row); }
.field-name { font-size: .88rem; display: flex; align-items: center; gap: .3rem; }
.field-rownum { font-family: "Consolas", monospace; font-size: .72rem; color: #888; flex: 0 0 auto; }
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
.multi-number { display: flex; gap: .25rem; flex-wrap: nowrap; }
.mn-item { display: flex; flex-direction: column; flex: 1 1 0; min-width: 0; }
.mn-label { font-size: .68rem; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
input.mn-input { padding: .35rem .25rem; text-align: center; }
.interval-banner { display: flex; align-items: center; justify-content: space-between; }
.interval-banner .zone-title { flex: 1; }
.remove-interval-btn { margin-right: 1rem; background: #b23; color: #fff; border: none; border-radius: 4px; padding: .3rem .7rem; cursor: pointer; font-size: .8rem; }
.remove-interval-btn:hover { background: #8f1c1c; }
#completion-intervals-toolbar { display: flex; justify-content: space-between; align-items: center; margin: 1.5rem 0 .75rem; }
#completion-intervals-toolbar h2 { margin: 0; font-size: 1.1rem; }
#add-completion-btn { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .5rem 1rem; cursor: pointer; font-size: .9rem; }
#add-completion-btn:disabled { background: #9aa; cursor: not-allowed; }
.sand-body-nest { margin: .75rem 0 0; padding: .5rem 0 .75rem 1rem; border-left: 3px solid var(--border); }
.sand-bodies-toolbar { display: flex; justify-content: space-between; align-items: center; margin: 0 1rem .6rem 0; }
.sand-bodies-toolbar h3 { margin: 0; font-size: .95rem; }
.add-sand-body-btn { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .4rem .8rem; cursor: pointer; font-size: .82rem; }
.add-sand-body-btn:disabled { background: #9aa; cursor: not-allowed; }
.sand-bodies-container { display: flex; flex-direction: column; gap: .75rem; }
.export-bar { position: sticky; z-index: 20; bottom: 0; background: #fff; border-top: 2px solid var(--header-bg); padding: .75rem 1rem; display: flex; flex-wrap: wrap; gap: .75rem; justify-content: flex-end; max-width: 1280px; margin: 0 auto; }
#import-status { flex-basis: 100%; margin: 0; font-size: .85rem; text-align: right; }
#import-status:empty { display: none; }
.export-bar button, .file-action-menu summary { background: var(--header-bg); color: #fff; border: none; border-radius: 4px; padding: .55rem 1.1rem; cursor: pointer; font-size: .9rem; }
.export-bar button:hover, .file-action-menu summary:hover { opacity: .9; }
.file-action-menu { position: relative; }
.file-action-menu summary { display: block; list-style: none; }
.file-action-menu summary::-webkit-details-marker { display: none; }
.file-action-options { position: absolute; right: 0; bottom: calc(100% + .35rem); min-width: 100%; padding: .35rem; display: flex; flex-direction: column; gap: .3rem; background: #fff; border: 1px solid var(--border); border-radius: 4px; box-shadow: 0 3px 8px #0002; }
.file-action-menu:not([open]) .file-action-options { display: none; }
.file-action-options button { white-space: nowrap; text-align: left; }
"""

JS = """
(function () {
  const SCHEMA_VERSION = __SCHEMA_VERSION__;
  const MAX_COMPLETION = __MAX_COMPLETION__;
  const MAX_SAND_BODY = __MAX_SAND_BODY__;
  const EXPIRES_ON = __EXPIRES_ON__;
  const EXPORT_NAME_PARAMS = __EXPORT_NAME_PARAMS__;
  const wellSection = document.getElementById('well-section');
  const sandForm = document.getElementById('sand-form');

  // Cutoff is inclusive of the whole EXPIRES_ON day in the viewer's local time --
  // the form stays usable through that date and locks starting the next day.
  if (EXPIRES_ON && new Date() > new Date(EXPIRES_ON + 'T23:59:59')) {
    document.getElementById('expired-banner').style.display = '';
    document.querySelectorAll('#sand-form input, #sand-form select, #sand-form textarea, #sand-form button')
      .forEach((el) => { el.disabled = true; });
    document.getElementById('import-btn').disabled = true;
    document.querySelectorAll('.file-action-menu').forEach((menu) => {
      menu.open = false;
      menu.inert = true;
      menu.setAttribute('aria-disabled', 'true');
      menu.querySelectorAll('button').forEach((button) => { button.disabled = true; });
    });
    return;
  }

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
  function refreshConditionalOptions(root) {
    root.querySelectorAll('select[data-options-by]').forEach((control) => {
      const config = JSON.parse(control.dataset.optionsBy);
      const [triggerName, byValue] = Object.entries(config)[0];
      const trigger = findParamField(root, triggerName);
      const choices = byValue[trigger ? getControlValue(trigger) : ''] || [];
      const current = control.value;
      const existing = Array.from(control.options).slice(1).map((option) => option.value);
      if (JSON.stringify(existing) === JSON.stringify(choices)) return;
      const blank = new Option(control.required ? 'Select...' : '(Blank)', '');
      control.replaceChildren(blank, ...choices.map((choice) => new Option(choice, choice)));
      control.value = choices.includes(current) ? current : '';
    });
  }
  function clearControl(control) {
    if (control.dataset.kind === 'multi_number') {
      control.querySelectorAll('input').forEach((i) => { i.value = ''; });
      return;
    }
    control.value = '';
  }
  // A hidden field/subcategory must not leave a stale value behind -- otherwise
  // a trigger no longer shown (e.g. the "OH ..." selector after switching
  // Completion Type to Cased Hole) keeps counting toward some other field's
  // show/hide decision even though the user can no longer see or change it.
  function resetHiddenControls(el) {
    el.querySelectorAll('[data-param]').forEach(clearControl);
  }
  // Hiding a control with CSS does NOT exempt it from constraint validation --
  // only `disabled` does. Without this, a required field the user can't even see
  // (for example, the required offshore Water depth field on an Onshore
  // record) keeps failing reportValidity() forever. Because the browser can't
  // focus an unrendered control to show its message, exports die silently.
  // So the same
  // pass that hides a field also disables its controls, and re-enables them
  // when the field comes back.
  //
  // Hidden-ness must be read from the whole ancestor chain rather than the
  // element's own style: a field row can have its own satisfied show-if rule
  // while the parent section is hidden by an unrelated answer. In that case
  // the row still has display:'' but remains unreachable.
  function isRuleHidden(el) {
    for (let node = el; node; node = node.parentElement) {
      if (node.style && node.style.display === 'none') return true;
    }
    return false;
  }
  // Buttons are deliberately excluded: they're barred from constraint
  // validation anyway, and the repeaters own their disabled state (an
  // "+ Add ..." button disabled at max count must stay disabled).
  function syncValidationExemptions(root) {
    root.querySelectorAll('input, select, textarea').forEach((control) => {
      control.disabled = isRuleHidden(control);
    });
  }
  function evaluateVisibility(root) {
    refreshConditionalOptions(root);
    root.querySelectorAll('[data-show-if], [data-hide-if]').forEach((el) => {
      let visible = true;
      const showExpr = el.getAttribute('data-show-if');
      if (showExpr) visible = exprMatches(root, showExpr);
      const hideExpr = el.getAttribute('data-hide-if');
      if (visible && hideExpr && exprMatches(root, hideExpr)) visible = false;
      el.style.display = visible ? '' : 'none';
      if (!visible) resetHiddenControls(el);
    });
    // Only correct once every display above has settled, since an exemption
    // depends on the element's ancestors, not just on the element itself.
    syncValidationExemptions(root);
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
        const completionIdxEl = section.querySelector(':scope > .interval-banner .completion-index');
        if (completionIdxEl) completionIdxEl.textContent = section.closest('.completion-instance').dataset.intervalIndex;
        section.querySelectorAll('.sand-body-instance > .interval-banner .completion-index')
          .forEach((el) => { el.textContent = i; });
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

    function removeLast() {
      if (count <= 1) return;
      const last = container.lastElementChild;
      if (!last) return;
      last.remove();
      renumber();
    }

    addBtn.addEventListener('click', add);
    renumber();
    return { add, removeLast, get count() { return count; } };
  }

  function wireApplyButton(root, repeater, maxCount) {
    const btn = root.querySelector('.apply-count-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const input = btn.closest('.field-row').querySelector('[data-kind="number"]');
      const n = input ? parseInt(input.value, 10) : NaN;
      if (!Number.isFinite(n) || n < 1) return;
      const target = Math.min(n, maxCount);
      while (repeater.count < target) repeater.add();
      while (repeater.count > target && repeater.count > 1) repeater.removeLast();
    });
  }

  function wireSandBodyRepeater(completionSection) {
    const repeater = setupRepeater({
      container: completionSection.querySelector('.sand-bodies-container'),
      template: completionSection.querySelector('.sand-body-template'),
      addBtn: completionSection.querySelector('.add-sand-body-btn'),
      maxCount: MAX_SAND_BODY,
      labelSingular: 'Sand Body',
    });
    completionSection.sandBodyRepeater = repeater;
    repeater.add();
    wireApplyButton(completionSection.querySelector('.own-fields'), repeater, MAX_SAND_BODY);
  }

  const completionRepeater = setupRepeater({
    container: document.getElementById('completion-intervals-container'),
    template: document.getElementById('completion-interval-template'),
    addBtn: document.getElementById('add-completion-btn'),
    maxCount: MAX_COMPLETION,
    labelSingular: 'Completion Interval',
    onAdd: wireSandBodyRepeater,
  });

  wellSection.addEventListener('change', () => evaluateVisibility(wellSection));
  evaluateVisibility(wellSection);
  completionRepeater.add();
  wireApplyButton(wellSection, completionRepeater, MAX_COMPLETION);

  // ---- collect a shared record for both file formats ----
  function readFieldValue(fieldRow) {
    const control = fieldRow.querySelector('[data-kind]');
    if (!control) return null;
    if (control.dataset.kind === 'multi_number') {
      const vals = Array.from(control.querySelectorAll('input')).map((i) => i.value);
      return vals.every((v) => v === '') ? null : vals;
    }
    return control.value === '' ? null : control.value;
  }

  function fieldParam(fieldRow) {
    const control = fieldRow.querySelector('[data-param]');
    return control ? control.getAttribute('data-param') : '';
  }

  function walkFields(root, visibleOnly, cb) {
    if (!root) return;
    root.querySelectorAll('.subcategory').forEach((sub) => {
      if (visibleOnly && sub.style.display === 'none') return;
      sub.querySelectorAll('.field-row').forEach((fr) => {
        if (visibleOnly && fr.style.display === 'none') return;
        cb(sub, fr);
      });
    });
  }

  function putBucketValue(bucket, category, subcategory, parameter, value) {
    bucket[category] = bucket[category] || {};
    bucket[category][subcategory] = bucket[category][subcategory] || {};
    bucket[category][subcategory][parameter] = value;
  }

  function bucketValue(bucket, category, subcategory, parameter) {
    return bucket?.[category]?.[subcategory]?.[parameter] ?? null;
  }

  function findBucketParamValue(bucket, parameter) {
    for (const subcategories of Object.values(bucket || {})) {
      for (const parameters of Object.values(subcategories)) {
        if (Object.hasOwn(parameters, parameter)) return parameters[parameter];
      }
    }
    return null;
  }

  function collectBucket(root) {
    const bucket = {};
    walkFields(root, true, (sub, fr) => {
      const value = readFieldValue(fr);
      if (value !== null) putBucketValue(bucket, sub.dataset.category, sub.dataset.subcategory, fieldParam(fr), value);
    });
    return bucket;
  }

  function collectComments(root) {
    const bucket = {};
    // A comment remains in the form if its conditional field is hidden, so
    // save it even though hidden field values are cleared by visibility rules.
    walkFields(root, false, (sub, fr) => {
      const comment = fr.querySelector('.field-comment').value;
      if (comment !== '') putBucketValue(bucket, sub.dataset.category, sub.dataset.subcategory, fieldParam(fr), comment);
    });
    return bucket;
  }

  function collectData() {
    const well = collectBucket(wellSection);
    const comments = { well: collectComments(wellSection), completion_intervals: [] };
    const completion_intervals = [];
    document.querySelectorAll('#completion-intervals-container > .completion-instance').forEach((comp) => {
      const fields = collectBucket(comp.querySelector('.own-fields'));
      const fieldComments = collectComments(comp.querySelector('.own-fields'));
      const sand_bodies = [], sandComments = [];
      comp.querySelectorAll(':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance').forEach((sb) => {
        sand_bodies.push(collectBucket(sb));
        sandComments.push(collectComments(sb));
      });
      completion_intervals.push({ fields, sand_bodies });
      comments.completion_intervals.push({ fields: fieldComments, sand_bodies: sandComments });
    });
    return { schema_version: SCHEMA_VERSION, generated_at: new Date().toISOString(),
      well, completion_intervals, comments };
  }

  // Keep the familiar long CSV layout. The final Row Type column adds
  // structural rows so blank interval/body blocks and the timestamp survive.
  const CSV_HEADER = ['Category', 'Subcategory', 'Parameter', 'Completion Interval', 'Sand Body',
    'Value', 'Unit', 'Comment', 'Row Type'];

  function collectCsvRows(record) {
    const rows = [
      ['', '', 'schema_version', '', '', record.schema_version, '', '', 'metadata'],
      ['', '', 'generated_at', '', '', record.generated_at, '', '', 'metadata'],
      ['', '', 'record_status', '', '', record.record_status, '', '', 'metadata'],
    ];
    function pushFields(root, values, comments, compIndex, sandIndex) {
      walkFields(root, false, (sub, fr) => {
        const category = sub.dataset.category, subcategory = sub.dataset.subcategory, parameter = fieldParam(fr);
        const value = bucketValue(values, category, subcategory, parameter);
        const comment = bucketValue(comments, category, subcategory, parameter);
        if (value === null && comment === null) return;
        rows.push([category, subcategory, parameter, compIndex, sandIndex,
          Array.isArray(value) ? JSON.stringify(value) : (value ?? ''),
          fr.querySelector('.field-unit').textContent, comment ?? '', 'field']);
      });
    }
    pushFields(wellSection, record.well, record.comments.well, '', '');
    document.querySelectorAll('#completion-intervals-container > .completion-instance').forEach((comp, i) => {
      const index = String(i + 1), data = record.completion_intervals[i];
      const commentData = record.comments.completion_intervals[i];
      rows.push(['', '', '', index, '', '', '', '', 'completion_interval']);
      pushFields(comp.querySelector('.own-fields'), data.fields, commentData.fields, index, '');
      comp.querySelectorAll(':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance').forEach((sb, j) => {
        const sandIndex = String(j + 1);
        rows.push(['', '', '', index, sandIndex, '', '', '', 'sand_body']);
        pushFields(sb, data.sand_bodies[j], commentData.sand_bodies[j], index, sandIndex);
      });
    });
    return rows;
  }

  function toCsv(rows) {
    const quote = (value) => '"' + String(value).replace(/"/g, '""') + '"';
    return [CSV_HEADER, ...rows].map((row) => row.map(quote).join(',')).join('\\r\\n');
  }

  function parseCsv(text) {
    const source = text.replace(/^\\uFEFF/, '');
    const rows = [], row = [];
    let cell = '', quoted = false;
    for (let i = 0; i < source.length; i += 1) {
      const ch = source[i];
      if (quoted) {
        if (ch === '"' && source[i + 1] === '"') { cell += '"'; i += 1; }
        else if (ch === '"') quoted = false;
        else cell += ch;
      } else if (ch === '"') {
        if (cell !== '') throw new Error('Malformed CSV quoting.');
        quoted = true;
      } else if (ch === ',') {
        row.push(cell); cell = '';
      } else if (ch === '\\r' || ch === '\\n') {
        row.push(cell); cell = '';
        rows.push(row.splice(0));
        if (ch === '\\r' && source[i + 1] === '\\n') i += 1;
      } else {
        cell += ch;
      }
    }
    if (quoted) throw new Error('Unclosed quoted CSV cell.');
    if (row.length || cell !== '') { row.push(cell); rows.push(row); }
    return rows;
  }

  function csvToData(text) {
    const rows = parseCsv(text);
    if (!rows.length || rows[0].join('\\0') !== CSV_HEADER.join('\\0')) {
      throw new Error('CSV columns do not match this form.');
    }
    const record = { schema_version: null, generated_at: null, record_status: null,
      well: {}, completion_intervals: [],
      comments: { well: {}, completion_intervals: [] } };

    function requiredIndex(value, maximum, label) {
      const n = Number(value);
      if (!/^[1-9]\\d*$/.test(value) || n > maximum) throw new Error('Invalid ' + label + ' index: ' + value);
      return n;
    }
    function completionAt(raw) {
      const index = requiredIndex(raw, MAX_COMPLETION, 'Completion Interval');
      while (record.completion_intervals.length < index) {
        record.completion_intervals.push({ fields: {}, sand_bodies: [] });
        record.comments.completion_intervals.push({ fields: {}, sand_bodies: [] });
      }
      return index - 1;
    }
    function sandBodyAt(comp, raw) {
      const index = requiredIndex(raw, MAX_SAND_BODY, 'Sand Body');
      while (record.completion_intervals[comp].sand_bodies.length < index) {
        record.completion_intervals[comp].sand_bodies.push({});
        record.comments.completion_intervals[comp].sand_bodies.push({});
      }
      return index - 1;
    }

    for (const row of rows.slice(1)) {
      if (row.length !== CSV_HEADER.length) throw new Error('CSV row has the wrong number of columns.');
      const [category, subcategory, parameter, compRaw, sandRaw, value, unit, comment, type] = row;
      if (type === 'metadata') {
        if (parameter === 'schema_version') {
          if (!/^(0|[1-9]\\d*)$/.test(value)) throw new Error('Invalid schema version in CSV.');
          record.schema_version = Number(value);
        }
        else if (parameter === 'generated_at') record.generated_at = value;
        else if (parameter === 'record_status') record.record_status = value;
        else throw new Error('Unknown CSV metadata: ' + parameter);
        continue;
      }
      if (type === 'completion_interval') { completionAt(compRaw); continue; }
      if (type === 'sand_body') { sandBodyAt(completionAt(compRaw), sandRaw); continue; }
      if (type !== 'field') throw new Error('Unknown CSV row type: ' + type);
      let values = record.well, comments = record.comments.well, root = wellSection;
      if (compRaw !== '') {
        const comp = completionAt(compRaw);
        const compSection = document.querySelector('#completion-intervals-container > .completion-instance');
        if (sandRaw !== '') {
          const sand = sandBodyAt(comp, sandRaw);
          values = record.completion_intervals[comp].sand_bodies[sand];
          comments = record.comments.completion_intervals[comp].sand_bodies[sand];
          root = compSection.querySelector('.sand-body-instance');
        } else {
          values = record.completion_intervals[comp].fields;
          comments = record.comments.completion_intervals[comp].fields;
          root = compSection.querySelector('.own-fields');
        }
      } else if (sandRaw !== '') {
        throw new Error('Sand Body index requires a Completion Interval index.');
      }
      const fieldRow = findFieldRow(root, category, subcategory, parameter);
      if (!fieldRow) throw new Error('Unknown CSV field: ' + parameter);
      if (unit !== fieldRow.querySelector('.field-unit').textContent) {
        throw new Error('Unit does not match this form for ' + parameter + '.');
      }
      if (value !== '') {
        const control = fieldRow.querySelector('[data-kind]');
        const parsed = control.dataset.kind === 'multi_number' ? JSON.parse(value) : value;
        if (bucketValue(values, category, subcategory, parameter) !== null) throw new Error('Duplicate CSV field: ' + parameter);
        putBucketValue(values, category, subcategory, parameter, parsed);
      }
      if (comment !== '') putBucketValue(comments, category, subcategory, parameter, comment);
    }
    return record;
  }

  function findFieldRow(root, category, subcategory, parameter) {
    for (const sub of root.querySelectorAll('.subcategory')) {
      if (sub.dataset.category !== category || sub.dataset.subcategory !== subcategory) continue;
      for (const fieldRow of sub.querySelectorAll('.field-row')) {
        if (fieldParam(fieldRow) === parameter) return fieldRow;
      }
    }
    return null;
  }

  function isObject(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function validateBucket(bucket, root, commentsOnly) {
    if (!isObject(bucket)) throw new Error('A field group is not an object.');
    for (const [category, subcategories] of Object.entries(bucket)) {
      if (!isObject(subcategories)) throw new Error('Invalid subcategory in ' + category + '.');
      for (const [subcategory, parameters] of Object.entries(subcategories)) {
        if (!isObject(parameters)) throw new Error('Invalid fields in ' + subcategory + '.');
        for (const [parameter, value] of Object.entries(parameters)) {
          const row = findFieldRow(root, category, subcategory, parameter);
          if (!row) throw new Error('Field is not in this form: ' + parameter);
          if (commentsOnly) {
            if (typeof value !== 'string') throw new Error('Comment must be text: ' + parameter);
            continue;
          }
          const control = row.querySelector('[data-kind]');
          if (control.dataset.kind === 'multi_number') {
            if (!Array.isArray(value) || value.length !== control.querySelectorAll('input').length ||
                value.some((v) => typeof v !== 'string' && typeof v !== 'number')) {
              throw new Error('Invalid multi-value field: ' + parameter);
            }
          } else if (typeof value !== 'string' && typeof value !== 'number') {
            throw new Error('Invalid field value: ' + parameter);
          } else if (control.tagName === 'SELECT') {
            let options = Array.from(control.options).map((option) => option.value);
            if (control.dataset.optionsBy) {
              const config = JSON.parse(control.dataset.optionsBy);
              const [triggerName, byValue] = Object.entries(config)[0];
              options = byValue[findBucketParamValue(bucket, triggerName)] || [];
            }
            if (!options.includes(String(value))) throw new Error('Unknown option for ' + parameter + '.');
          }
        }
      }
    }
  }

  function validateImport(record) {
    if (!isObject(record) || record.schema_version !== SCHEMA_VERSION) {
      throw new Error('Unsupported or missing schema version. Expected ' + SCHEMA_VERSION + '.');
    }
    if (record.record_status != null &&
        record.record_status !== 'draft' && record.record_status !== 'complete') {
      throw new Error('Unknown file status.');
    }
    if (!Array.isArray(record.completion_intervals) ||
        record.completion_intervals.length < 1 || record.completion_intervals.length > MAX_COMPLETION) {
      throw new Error('File must contain 1 to ' + MAX_COMPLETION + ' Completion Intervals.');
    }
    const firstComp = document.querySelector('#completion-intervals-container > .completion-instance');
    const completionRoot = firstComp.querySelector('.own-fields');
    const sandRoot = firstComp.querySelector('.sand-body-instance');
    validateBucket(record.well, wellSection, false);
    const comments = record.comments ?? { well: {}, completion_intervals: record.completion_intervals.map(
      (comp) => ({ fields: {}, sand_bodies: comp.sand_bodies.map(() => ({})) })) };
    if (!isObject(comments) || !Array.isArray(comments.completion_intervals) ||
        comments.completion_intervals.length !== record.completion_intervals.length) {
      throw new Error('Comment groups do not match Completion Intervals.');
    }
    validateBucket(comments.well, wellSection, true);
    record.completion_intervals.forEach((comp, i) => {
      if (!isObject(comp) || !Array.isArray(comp.sand_bodies) ||
          comp.sand_bodies.length < 1 || comp.sand_bodies.length > MAX_SAND_BODY) {
        throw new Error('Each Completion Interval needs 1 to ' + MAX_SAND_BODY + ' Sand Bodies.');
      }
      const note = comments.completion_intervals[i];
      if (!isObject(note) || !Array.isArray(note.sand_bodies) ||
          note.sand_bodies.length !== comp.sand_bodies.length) {
        throw new Error('Comment groups do not match Sand Bodies.');
      }
      validateBucket(comp.fields, completionRoot, false);
      validateBucket(note.fields, completionRoot, true);
      comp.sand_bodies.forEach((sand, j) => {
        validateBucket(sand, sandRoot, false);
        validateBucket(note.sand_bodies[j], sandRoot, true);
      });
    });
    return comments;
  }

  function fillBucket(root, bucket, commentsOnly) {
    if (!commentsOnly) {
      // Populate controlling answers before setting a dependent dropdown.
      // Otherwise its saved option does not exist yet and the browser drops it.
      root.querySelectorAll('select[data-options-by]').forEach((control) => {
        const [triggerName] = Object.keys(JSON.parse(control.dataset.optionsBy));
        const trigger = findParamField(root, triggerName);
        const value = findBucketParamValue(bucket, triggerName);
        if (trigger && value != null) trigger.value = value;
      });
      refreshConditionalOptions(root);
    }
    for (const [category, subcategories] of Object.entries(bucket)) {
      for (const [subcategory, parameters] of Object.entries(subcategories)) {
        for (const [parameter, value] of Object.entries(parameters)) {
          const row = findFieldRow(root, category, subcategory, parameter);
          if (commentsOnly) {
            row.querySelector('.field-comment').value = value;
          } else {
            const control = row.querySelector('[data-kind]');
            if (control.dataset.kind === 'multi_number') {
              control.querySelectorAll('input').forEach((input, i) => { input.value = value[i]; });
            } else {
              control.value = value;
            }
          }
        }
      }
    }
  }

  function restoreData(record) {
    const comments = validateImport(record); // Check before replacing anything the user has typed.
    while (completionRepeater.count > record.completion_intervals.length) completionRepeater.removeLast();
    while (completionRepeater.count < record.completion_intervals.length) completionRepeater.add();
    sandForm.querySelectorAll('[data-param]').forEach(clearControl);
    sandForm.querySelectorAll('.field-comment').forEach((input) => { input.value = ''; });
    fillBucket(wellSection, record.well, false);
    fillBucket(wellSection, comments.well, true);
    evaluateVisibility(wellSection);
    document.querySelectorAll('#completion-intervals-container > .completion-instance').forEach((comp, i) => {
      const data = record.completion_intervals[i], note = comments.completion_intervals[i];
      const repeater = comp.sandBodyRepeater;
      while (repeater.count > data.sand_bodies.length) repeater.removeLast();
      while (repeater.count < data.sand_bodies.length) repeater.add();
      fillBucket(comp.querySelector('.own-fields'), data.fields, false);
      fillBucket(comp.querySelector('.own-fields'), note.fields, true);
      evaluateVisibility(comp.querySelector('.own-fields'));
      comp.querySelectorAll(':scope > .sand-body-nest > .sand-bodies-container > .sand-body-instance').forEach((sb, j) => {
        fillBucket(sb, data.sand_bodies[j], false);
        fillBucket(sb, note.sand_bodies[j], true);
        evaluateVisibility(sb);
      });
    });
  }

  // Exports are named from the well's anonymized label and identification
  // number, so a reviewer collecting submissions can tell records apart in a
  // download folder without opening them.
  //
  // Repeat exports are deliberately NOT numbered here. A page cannot see the
  // download folder, so an in-page counter would count exports in this session
  // rather than actual filename collisions -- it would stamp "(2)" on the first
  // export after a reload, and miss a real clash with a file saved yesterday.
  // Browsers already uniquify a colliding download themselves, which is both
  // correct and what users expect from every other download they make.
  const ILLEGAL_FILENAME_CHARS = /[<>:"/\\\\|?*\\u0000-\\u001f]/g;
  // Windows rejects these as a base name whatever extension follows them.
  const RESERVED_FILENAMES = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;

  // Each part is capped well short of the whole, so one long free-text label
  // can never crowd the identification number out of the joined filename.
  function safeFilenamePart(value) {
    return (value || '')
      .trim()
      .replace(ILLEGAL_FILENAME_CHARS, '_')
      .replace(/\\s+/g, '_')
      .replace(/_{2,}/g, '_')
      .slice(0, 50)
      .replace(/^[._]+/, '')    // a leading dot hides the file on macOS/Linux
      .replace(/[._]+$/, '');   // Windows silently strips trailing dots
  }

  function exportBaseName() {
    const nameField = findParamField(wellSection, EXPORT_NAME_PARAMS[0]);
    const idField = findParamField(wellSection, EXPORT_NAME_PARAMS[1]);
    // Drafts can be saved before the required well name is entered. Keep the
    // same anonymized-name + ID pattern used by completed exports, but make
    // the missing name explicit instead of producing an ID-only filename.
    const name = safeFilenamePart(nameField ? nameField.value : '') || 'Unnamed';
    const identifier = safeFilenamePart(idField ? idField.value : '');
    const base = [name, identifier].filter((part) => part !== '').join('_');
    return RESERVED_FILENAMES.test(base) ? 'well_' + base : base;
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  }

  function saveFile(format, draft) {
    if (!draft && !sandForm.reportValidity()) return;
    const record = collectData();
    // The filename helps people distinguish files in a folder; this marker
    // survives a rename and lets the JSON/CSV importers identify the status.
    record.record_status = draft ? 'draft' : 'complete';
    const suffix = draft ? '_draft' : '_complete';
    if (format === 'json') {
      download(exportBaseName() + suffix + '.json', JSON.stringify(record, null, 2), 'application/json');
    } else {
      download(exportBaseName() + suffix + '.csv', toCsv(collectCsvRows(record)), 'text/csv');
    }
  }

  // Only three actions are shown in the footer. JSON and CSV are choices
  // within the draft and completed-export menus, so users first choose the
  // operation and then its file format. Both choices call the same serializer.
  document.querySelectorAll('.file-action-menu button[data-format]').forEach((button) => {
    button.addEventListener('click', () => {
      const menu = button.closest('.file-action-menu');
      saveFile(button.dataset.format, menu.dataset.mode === 'draft');
      menu.open = false;
    });
  });

  const importInput = document.getElementById('import-file');
  const importStatus = document.getElementById('import-status');
  document.getElementById('import-btn').addEventListener('click', () => importInput.click());
  importInput.addEventListener('change', async () => {
    const file = importInput.files[0];
    if (!file) return;
    try {
      const content = await file.text();
      const record = file.name.toLowerCase().endsWith('.csv') ? csvToData(content) : JSON.parse(content);
      validateImport(record);
      if (!window.confirm('Importing will replace the current form entries. Continue?')) return;
      restoreData(record);
      importStatus.textContent = 'Loaded ' + file.name +
        (record.record_status ? ' (' + record.record_status + ')' : '') + '.';
    } catch (error) {
      importStatus.textContent = 'Could not load ' + file.name + ': ' + error.message;
      window.alert(importStatus.textContent);
    } finally {
      importInput.value = '';
    }
  });
})();
"""


def render_html(model: dict, max_completion: int = DEFAULT_MAX_COMPLETION,
                 max_sand_bodies: int = DEFAULT_MAX_SAND_BODY,
                 expires_on: str = DEFAULT_EXPIRES_ON) -> str:
    well_html = render_well_section(model)
    completion_template_html = render_completion_template(model)
    js = (JS.replace("__SCHEMA_VERSION__", str(CURRENT_SCHEMA_VERSION))
            .replace("__MAX_COMPLETION__", str(max_completion))
            .replace("__MAX_SAND_BODY__", str(max_sand_bodies))
            .replace("__EXPIRES_ON__", json.dumps(expires_on) if expires_on else "null")
            .replace("__EXPORT_NAME_PARAMS__", json.dumps(list(EXPORT_NAME_PARAMS))))

    if expires_on:
        cutoff = date.fromisoformat(expires_on)
        display_date = f"{cutoff:%B} {cutoff.day}, {cutoff.year}"
        validity_notice = f"<p class=\"validity-notice\">This form accepts submissions through {display_date}.</p>"
    else:
        validity_notice = ""

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
  <p>Import a saved file, save an unfinished draft, or export a completed record. JSON and CSV are available for both saves. Hover the <strong>?</strong> icon next to a field for guidance.</p>
  {validity_notice}
  <p id="expired-banner" class="expired-banner" style="display:none;">
    This form has expired and is no longer accepting submissions. Please contact your Sand Control Failure DB
    program contact for a current version of the form.
  </p>
</header>
<main>
  <form id="sand-form" onsubmit="return false;">
    {well_html}
    <div id="completion-intervals-toolbar">
      <h2>Completion Intervals</h2>
      <button type="button" id="add-completion-btn">+ Add Completion Interval</button>
    </div>
    <div id="completion-intervals-container"></div>
    {completion_template_html}
  </form>
</main>
<div class="export-bar">
  <input type="file" id="import-file" accept=".json,.csv,application/json,text/csv" hidden>
  <button type="button" id="import-btn">Import file</button>
  <details class="file-action-menu" data-mode="draft">
    <summary>Save draft &#9662;</summary>
    <div class="file-action-options">
      <button type="button" data-format="json">Save JSON draft</button>
      <button type="button" data-format="csv">Save CSV draft</button>
    </div>
  </details>
  <details class="file-action-menu" data-mode="complete">
    <summary>Export completed record &#9662;</summary>
    <div class="file-action-options">
      <button type="button" data-format="json">Export JSON</button>
      <button type="button" data-format="csv">Export CSV</button>
    </div>
  </details>
  <p id="import-status" role="status" aria-live="polite"></p>
</div>
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="Path to the dictionary xlsx file")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT, help="Path to write the generated HTML form")
    parser.add_argument("--max-completion-intervals", type=int, default=DEFAULT_MAX_COMPLETION,
                         help="Maximum number of Completion Interval blocks a user can add")
    parser.add_argument("--max-sand-bodies", type=int, default=DEFAULT_MAX_SAND_BODY,
                         help="Maximum number of Sand Body blocks per Completion Interval")
    parser.add_argument("--expires-on", default=DEFAULT_EXPIRES_ON,
                         help="ISO date (YYYY-MM-DD) after which the generated form locks itself "
                              "(client-side check baked in at generation time). Pass \"\" for no expiration.")
    args = parser.parse_args()

    if args.expires_on:
        date.fromisoformat(args.expires_on)  # fail fast on a malformed --expires-on value

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    rows = load_dictionary(input_path)
    if not rows:
        raise SystemExit("No rows found in the dictionary sheet.")
    model = build_model(rows)
    html_out = render_html(model, max_completion=args.max_completion_intervals,
                            max_sand_bodies=args.max_sand_bodies, expires_on=args.expires_on)

    output_path = Path(args.output)
    output_path.write_text(html_out, encoding="utf-8")
    well_subcats = sum(len(v) for v in model["well"].values())
    completion_subcats = sum(len(v) for v in model["completion"].values())
    sand_body_subcats = sum(len(v) for v in model["sand_body"].values())
    print(f"Wrote {output_path} ({len(rows)} parameters: "
          f"{well_subcats} well-scope, {completion_subcats} completion-interval-scope, "
          f"{sand_body_subcats} sand-body-scope subcategories).")


if __name__ == "__main__":
    main()
