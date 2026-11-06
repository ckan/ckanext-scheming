from __future__ import annotations

import difflib
import json
from typing import Any

from flask import Blueprint
from flask.views import MethodView
from markupsafe import Markup

import ckan.plugins.toolkit as tk
from ckan.lib.pagination import Page
from ckan.views.admin import before_request

from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, TYPE_FIELDS
from ckanext.scheming_dynamic.model import (
    SchemingPreset,
    SchemingSchemaActivity,
    SchemingSchemaPin,
    SchemingSchemaVersion,
)
from ckanext.scheming_dynamic.preset_resolve import (
    PresetBaseNotFoundError,
    PresetCycleError,
)
from ckanext.scheming_dynamic.render import render_preset_field, render_schema_form
from ckanext.scheming_dynamic.schema import SCHEMA_CLASSES, PresetSchema
from ckanext.scheming_dynamic.validator import error_location, iter_errors
from ckanext.scheming_dynamic.views.routing import entity_route

ADMIN_BP = "scheming_dynamic_admin"
HISTORY_PAGE_SIZE = 10
SCHEMA_TYPES_PAGE_SIZE = 20

bp = Blueprint(ADMIN_BP, __name__, url_prefix="/ckan-admin/scheming")


def _check_entity_type(entity_type: str) -> None:
    if entity_type not in SCHEMA_CLASSES:
        tk.abort(404, tk._("Unknown entity type"))


def _meta_schema(entity_type: str) -> dict[str, Any]:
    return SCHEMA_CLASSES[entity_type]().build()


def _preset_meta_schema(exclude_preset_name: str | None = None) -> dict[str, Any]:
    return PresetSchema(exclude_preset_name=exclude_preset_name).build()


def _preset_action_args(raw: str, preset_name: str | None = None) -> dict[str, Any]:
    """Turn the form's JSON ``definition`` textarea into flat
    ``scheming_preset_{create,update}`` action params.

    The admin form edits a ``{"preset_name": ..., "values": {...}}`` document
    (schema-editor driven); the actions take ``preset_name`` and ``values``
    apart. On edit ``preset_name`` is fixed by the URL, so the document's own
    is ignored.
    """
    try:
        doc = json.loads(raw) if raw.strip() else {}
    except ValueError as e:
        raise tk.ValidationError(
            {"definition": [tk._("Could not parse as valid JSON")]}
        ) from e
    if not isinstance(doc, dict):
        raise tk.ValidationError(
            {"definition": [tk._("Definition must be a JSON object")]}
        )

    args: dict[str, Any] = {"values": doc.get("values")}
    if preset_name is not None:
        args["preset_name"] = preset_name
    elif "preset_name" in doc:
        args["preset_name"] = doc["preset_name"]
    return args


def _flatten_errors(error_dict: dict[str, Any]) -> dict[str, list[str]]:
    """Collapse a preset action's per-field errors under ``definition`` so the
    single JSON textarea can surface them inline."""
    messages: list[str] = []
    for value in error_dict.values():
        messages.extend(value if isinstance(value, list) else [value])
    return {"definition": messages}


def index() -> str:
    """List the head version of every schema, across all entity types."""
    schemas = [
        {
            "schema_type": row.schema_type,
            "entity_type": row.entity_type,
            "created": row.created,
            "version": row.version,
            "is_locked": SchemingSchemaPin.is_version_locked(
                row.entity_type, row.schema_type, row.version
            ),
        }
        for entity_type in SCHEMA_CLASSES
        for row in SchemingSchemaVersion.get_heads_of_type(entity_type)
    ]
    schemas.sort(key=lambda s: (s["entity_type"], s["schema_type"]))

    return tk.render(
        "scheming_dynamic/index.html",
        {"schemas": schemas, "active_tab": "schemas"},
    )


class CreateView(MethodView):
    def get(
        self,
        entity_type: str = DEFAULT_ENTITY_TYPE,
        data: dict[str, Any] | None = None,
        errors: dict[str, Any] | None = None,
        error_summary: dict[str, Any] | None = None,
    ) -> str:
        _check_entity_type(entity_type)
        return tk.render(
            "scheming_dynamic/schema_form.html",
            {
                "data": data or {},
                "errors": errors or {},
                "error_summary": error_summary or {},
                "meta_schema": _meta_schema(entity_type),
                "presets": tk.h.scheming_get_presets() or {},
                "is_new": True,
                "entity_type": entity_type,
            },
        )

    def post(self, entity_type: str = DEFAULT_ENTITY_TYPE) -> str | Any:
        _check_entity_type(entity_type)
        data = {
            "entity_type": entity_type,
            "definition": tk.request.form.get("definition", ""),
        }

        try:
            row = tk.get_action("scheming_schema_create")({}, dict(data))
        except tk.ValidationError as e:
            return self.get(entity_type, data, e.error_dict, e.error_summary)

        tk.h.flash_success(tk._("Schema '{}' created.").format(row["schema_type"]))
        return tk.redirect_to(f"{ADMIN_BP}.index")


class EditView(MethodView):
    def get(
        self,
        schema_type: str,
        entity_type: str = DEFAULT_ENTITY_TYPE,
        data: dict[str, Any] | None = None,
        errors: dict[str, Any] | None = None,
        error_summary: dict[str, Any] | None = None,
    ) -> str:
        _check_entity_type(entity_type)
        schema = SchemingSchemaVersion.head(entity_type, schema_type)
        if not schema:
            return tk.abort(404, tk._("Schema not found"))

        if data is None:
            data = {
                "schema_type": schema_type,
                "definition": json.dumps(
                    schema.definition, indent=2, ensure_ascii=False
                ),
            }

        return tk.render(
            "scheming_dynamic/schema_form.html",
            {
                "data": data,
                "errors": errors or {},
                "error_summary": error_summary or {},
                "meta_schema": _meta_schema(entity_type),
                "presets": tk.h.scheming_get_presets() or {},
                "is_new": False,
                "schema_type": schema_type,
                "entity_type": entity_type,
            },
        )

    def post(
        self, schema_type: str, entity_type: str = DEFAULT_ENTITY_TYPE
    ) -> str | Any:
        _check_entity_type(entity_type)
        raw = tk.request.form.get("definition", "")

        try:
            row = tk.get_action("scheming_schema_update")(
                {}, {"entity_type": entity_type, "definition": raw}
            )
        except tk.ObjectNotFound:
            return tk.abort(404, tk._("Schema not found"))
        except tk.ValidationError as e:
            return self.get(
                schema_type,
                entity_type,
                {"schema_type": schema_type, "definition": raw},
                e.error_dict,
                e.error_summary,
            )

        tk.h.flash_success(
            tk._("Schema '{}' updated; now at version {}.").format(
                schema_type, row["version"]
            )
        )
        return tk.redirect_to(f"{ADMIN_BP}.index")


def history(schema_type: str, entity_type: str = DEFAULT_ENTITY_TYPE) -> str:
    _check_entity_type(entity_type)
    page_number = tk.h.get_page_number(tk.request.args)

    total = SchemingSchemaActivity.count_history(entity_type, schema_type)
    offset = max(total - page_number * HISTORY_PAGE_SIZE, 0)
    end = max(total - (page_number - 1) * HISTORY_PAGE_SIZE, 0)
    page_size = max(end - offset, 0)

    rows = (
        SchemingSchemaActivity.get_history(
            entity_type, schema_type, limit=page_size, offset=offset
        )
        if page_size
        else []
    )

    previous_text = None
    if offset > 0 and rows:
        context_row = rows[0]
        previous_text = json.dumps(
            context_row.definition, indent=2, sort_keys=True, ensure_ascii=False
        )
        rows = rows[1:]

    entries = []
    for row in rows:
        row_dict = row.as_dict()
        text = json.dumps(
            row_dict["definition"], indent=2, sort_keys=True, ensure_ascii=False
        )
        has_previous = previous_text is not None
        diff = (
            "\n".join(
                difflib.unified_diff(
                    previous_text.splitlines(),  # type: ignore
                    text.splitlines(),
                    lineterm="",
                )
            )
            if has_previous
            else None
        )
        entries.append(
            {
                **row_dict,
                "has_previous": has_previous,
                "diff": _highlight_diff(diff) if diff else diff,
                "definition_text": text,
            }
        )
        previous_text = text

    entries.reverse()

    return tk.render(
        "scheming_dynamic/schema_history.html",
        {
            "schema_type": schema_type,
            "entity_type": entity_type,
            "page": Page(
                entries,
                page=page_number,
                items_per_page=HISTORY_PAGE_SIZE,
                item_count=total,
                presliced_list=True,
            ),
            "active_tab": "history",
        },
    )


def _highlight_diff(diff_text: str) -> Markup:
    """Wrap unified-diff lines in classed spans for light CSS highlighting."""
    css_class = "diff-hunk"
    lines = []

    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            css_class = "diff-meta"
        elif line.startswith("@@"):
            css_class = "diff-hunk"
        elif line.startswith("+"):
            css_class = "diff-add"
        elif line.startswith("-"):
            css_class = "diff-del"
        else:
            css_class = "diff-ctx"
        lines.append(Markup('<span class="{}">{}</span>').format(css_class, line))

    return Markup("\n").join(lines)


def history_index() -> str:
    """List every schema_type with recorded activity, live or deleted,
    across all entity types."""
    page_number = tk.h.get_page_number(tk.request.args)

    total = SchemingSchemaActivity.count_schema_types()
    offset = (page_number - 1) * SCHEMA_TYPES_PAGE_SIZE
    schema_types = SchemingSchemaActivity.get_schema_types(
        limit=SCHEMA_TYPES_PAGE_SIZE, offset=offset
    )

    live = {
        (entity_type, row.schema_type)
        for entity_type in SCHEMA_CLASSES
        for row in SchemingSchemaVersion.get_heads_of_type(entity_type)
    }

    rows = [
        {
            "schema_type": schema_type,
            "entity_type": entity_type,
            "is_live": (entity_type, schema_type) in live,
        }
        for schema_type, entity_type in schema_types
    ]

    return tk.render(
        "scheming_dynamic/history_index.html",
        {
            "page": Page(
                rows,
                page=page_number,
                items_per_page=SCHEMA_TYPES_PAGE_SIZE,
                item_count=total,
                presliced_list=True,
            ),
            "active_tab": "history",
        },
    )


def preview(entity_type: str = DEFAULT_ENTITY_TYPE) -> Any:
    """Render unsaved schema definition as a preview.

    Returns an HTML fragment: either the rendered form fields or the list
    of validation errors (with a 400 status) when the definition cannot be
    rendered.
    """
    _check_entity_type(entity_type)
    raw = tk.request.form.get("definition", "")

    try:
        definition = json.loads(raw)
    except ValueError:
        return _preview_errors([tk._("Could not parse as valid JSON")])

    errors = [
        f"{error_location(e)}: {e.message}"
        for e in iter_errors(definition, SCHEMA_CLASSES[entity_type]())
    ]
    if errors:
        return _preview_errors(errors)

    schema_type = definition[TYPE_FIELDS[entity_type]]

    try:
        body = render_schema_form(entity_type, schema_type, definition)
    except Exception as e:  # noqa: BLE001
        return _preview_errors([tk._("Schema cannot be rendered: {}").format(e)])

    return _with_queued_assets(body)


def _preview_errors(messages: list[str]) -> Any:
    body = tk.render(
        "scheming_dynamic/snippets/schema_preview.html",
        {"preview_errors": messages},
    )
    return body, 400


def _with_queued_assets(body: str) -> str:
    """Append the <link>/<script> tags for assets the just-rendered form."""
    return "".join(
        [
            str(body),
            str(tk.h.render_assets("style")),
            str(tk.h.render_assets("script")),
        ]
    )


def restore(
    schema_type: str, activity_id: str, entity_type: str = DEFAULT_ENTITY_TYPE
) -> Any:
    """Re-apply a historical activity entry's definition to the schema."""
    _check_entity_type(entity_type)
    entry = SchemingSchemaActivity.get(activity_id)

    if (
        not entry
        or entry.schema_type != schema_type
        or entry.entity_type != entity_type
    ):
        return tk.abort(404, tk._("Activity entry not found"))

    if SchemingSchemaVersion.head(entity_type, schema_type):
        action = "scheming_schema_update"
    else:
        action = "scheming_schema_create"
    data = {"entity_type": entity_type, "definition": entry.definition}

    try:
        tk.get_action(action)({}, data)
    except tk.ObjectNotFound:
        return tk.abort(404, tk._("Schema not found"))
    except tk.ValidationError as e:
        tk.h.flash_error("; ".join(e.error_summary.values()))
    else:
        tk.h.flash_success(tk._("Schema '{}' restored.").format(schema_type))

    return tk.redirect_to(
        f"{ADMIN_BP}.history", schema_type=schema_type, **_route_args(entity_type)
    )


def delete(schema_type: str, entity_type: str = DEFAULT_ENTITY_TYPE) -> Any:
    _check_entity_type(entity_type)
    try:
        tk.get_action("scheming_schema_delete")(
            {}, {"entity_type": entity_type, "schema_type": schema_type}
        )
    except tk.ValidationError as e:
        tk.h.flash_error("; ".join(e.error_summary.values()))
    else:
        tk.h.flash_success(tk._("Schema '{}' has been deleted.").format(schema_type))

    return tk.redirect_to(f"{ADMIN_BP}.index")


def _route_args(entity_type: str) -> dict[str, str]:
    """url_for kwargs so the non-dataset routes carry their entity_type."""
    return {} if entity_type == DEFAULT_ENTITY_TYPE else {"entity_type": entity_type}


def presets_index() -> str:
    return tk.render(
        "scheming_dynamic/presets_index.html",
        {"presets": SchemingPreset.get_all(), "active_tab": "presets"},
    )


class PresetCreateView(MethodView):
    def get(
        self,
        data: dict[str, Any] | None = None,
        errors: dict[str, Any] | None = None,
        error_summary: dict[str, Any] | None = None,
    ) -> str:
        return tk.render(
            "scheming_dynamic/preset_form.html",
            {
                "data": data or {},
                "errors": errors or {},
                "error_summary": error_summary or {},
                "meta_schema": _preset_meta_schema(),
                "presets": tk.h.scheming_get_presets() or {},
                "is_new": True,
            },
        )

    def post(self) -> str | Any:
        raw = tk.request.form.get("definition", "")

        try:
            args = _preset_action_args(raw)
            row = tk.get_action("scheming_preset_create")({}, args)
        except tk.ValidationError as e:
            return self.get(
                {"definition": raw}, _flatten_errors(e.error_dict), e.error_summary
            )

        tk.h.flash_success(tk._("Preset '{}' created.").format(row["preset_name"]))
        return tk.redirect_to(f"{ADMIN_BP}.presets_index")


class PresetEditView(MethodView):
    def get(
        self,
        preset_name: str,
        data: dict[str, Any] | None = None,
        errors: dict[str, Any] | None = None,
        error_summary: dict[str, Any] | None = None,
    ) -> str:
        preset = SchemingPreset.get(preset_name)
        if not preset:
            return tk.abort(404, tk._("Preset not found"))

        if data is None:
            data = {
                "preset_name": preset_name,
                "definition": json.dumps(
                    {"preset_name": preset.preset_name, "values": preset.values},
                    indent=2,
                    ensure_ascii=False,
                ),
            }

        return tk.render(
            "scheming_dynamic/preset_form.html",
            {
                "data": data,
                "errors": errors or {},
                "error_summary": error_summary or {},
                "meta_schema": _preset_meta_schema(exclude_preset_name=preset_name),
                "presets": {
                    name: values
                    for name, values in (tk.h.scheming_get_presets() or {}).items()
                    if name != preset_name
                },
                "is_new": False,
                "preset_name": preset_name,
            },
        )

    def post(self, preset_name: str) -> str | Any:
        raw = tk.request.form.get("definition", "")

        try:
            args = _preset_action_args(raw, preset_name)
            tk.get_action("scheming_preset_update")({}, args)
        except tk.ObjectNotFound:
            return tk.abort(404, tk._("Preset not found"))
        except tk.ValidationError as e:
            return self.get(
                preset_name,
                {"preset_name": preset_name, "definition": raw},
                _flatten_errors(e.error_dict),
                e.error_summary,
            )

        tk.h.flash_success(tk._("Preset '{}' updated.").format(preset_name))
        return tk.redirect_to(f"{ADMIN_BP}.presets_index")


def preset_preview() -> Any:
    """Render an unsaved preset definition as a preview.

    Treats the preset's ``values`` as a single field (synthesizing a
    ``field_name`` when the preset doesn't supply its own), resolving any
    base preset chain, then renders it with the same form snippet a real
    dataset/resource field using this preset would get.

    Returns an HTML fragment: either the rendered field or the list of
    validation errors (with a 400 status) when the definition cannot be
    rendered.
    """
    raw = tk.request.form.get("definition", "")

    try:
        definition = json.loads(raw)
    except ValueError:
        return _preset_preview_errors([tk._("Could not parse as valid JSON")])

    errors = [
        f"{error_location(e)}: {e.message}"
        for e in iter_errors(definition, PresetSchema())
    ]
    if errors:
        return _preset_preview_errors(errors)

    preset_name = definition["preset_name"]

    try:
        body = render_preset_field(preset_name, definition["values"])
    except PresetCycleError as e:
        return _preset_preview_errors(
            [
                tk._("Preset cycle detected: {}").format(
                    " -> ".join([*e.chain, e.chain[0]])
                )
            ]
        )
    except PresetBaseNotFoundError as e:
        return _preset_preview_errors(
            [tk._(f"Base preset '{e.base}' is not a registered or existing preset")]
        )
    except Exception as e:  # noqa: BLE001
        return _preset_preview_errors(
            [tk._("Form snippet failed to render: {}").format(e)]
        )

    return _with_queued_assets(body)


def _preset_preview_errors(messages: list[str]) -> Any:
    body = tk.render(
        "scheming_dynamic/snippets/preset_preview.html",
        {"preview_errors": messages},
    )
    return body, 400


def preset_delete(preset_name: str) -> Any:
    try:
        tk.get_action("scheming_preset_delete")({}, {"preset_name": preset_name})
    except tk.ValidationError as e:
        tk.h.flash_error("; ".join(e.error_summary.values()))
    else:
        tk.h.flash_success(tk._("Preset '{}' has been deleted.").format(preset_name))

    return tk.redirect_to(f"{ADMIN_BP}.presets_index")


bp.before_request(before_request)


bp.add_url_rule("/", endpoint="index", view_func=index)
entity_route(
    bp, "/new", "/{prefix}/new", endpoint="new", view_func=CreateView.as_view("new")
)
entity_route(
    bp,
    "/<schema_type>/edit",
    "/{prefix}/<schema_type>/edit",
    endpoint="edit",
    view_func=EditView.as_view("edit"),
)
bp.add_url_rule("/history", endpoint="history_index", view_func=history_index)
entity_route(
    bp,
    "/<schema_type>/history",
    "/{prefix}/<schema_type>/history",
    endpoint="history",
    view_func=history,
)
entity_route(
    bp,
    "/<schema_type>/history/<activity_id>/restore",
    "/{prefix}/<schema_type>/history/<activity_id>/restore",
    endpoint="restore",
    view_func=restore,
    methods=["POST"],
)
entity_route(
    bp,
    "/<schema_type>/delete",
    "/{prefix}/<schema_type>/delete",
    endpoint="delete",
    view_func=delete,
    methods=["POST"],
)
entity_route(
    bp,
    "/preview",
    "/{prefix}/preview",
    endpoint="preview",
    view_func=preview,
    methods=["POST"],
)
bp.add_url_rule("/presets/", view_func=presets_index)
bp.add_url_rule("/presets/new", view_func=PresetCreateView.as_view("preset_new"))
bp.add_url_rule(
    "/presets/<preset_name>/edit", view_func=PresetEditView.as_view("preset_edit")
)
bp.add_url_rule(
    "/presets/<preset_name>/delete", view_func=preset_delete, methods=["POST"]
)
bp.add_url_rule("/presets/preview", view_func=preset_preview, methods=["POST"])
