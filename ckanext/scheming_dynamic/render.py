from __future__ import annotations

from typing import Any

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.scheming.plugins import _expand_schemas
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.model import SchemingPreset
from ckanext.scheming_dynamic.preset_resolve import resolve_preset_values


def render_preset_field(preset_name: str, values: dict[str, Any]) -> str:
    """Resolve and render a preset's field snippet, to confirm it renders.

    Raises PresetCycleError or PresetBaseNotFoundError (from
    preset_resolve) if the preset's base chain is broken, or whatever
    exception the form snippet itself raises if rendering fails.
    """
    raw_presets = {row.preset_name: row.values for row in SchemingPreset.get_all()}
    raw_presets[preset_name] = values

    resolved = resolve_preset_values(
        preset_name, raw_presets, sync.get_static_presets()
    )

    field = {"field_name": "preview_field", **resolved}

    return tk.render(
        "scheming_dynamic/snippets/preset_preview.html",
        {"field": field, "licenses": model.Package.get_license_options()},
    )


def render_schema_form(
    entity_type: str, schema_type: str, definition: dict[str, Any]
) -> str:
    """Expand and render a schema's preview form, to confirm it renders.

    Works for dataset, group and organization schemas. Raises whatever
    exception schema expansion or the form snippet render raises if the
    schema can't be expanded/rendered.
    """
    sync.ensure_presets_synced()

    expanded = _expand_schemas({schema_type: definition})[schema_type]

    # Lets build_dynamic_type_url() resolve this type's URLs (e.g. the slug
    # preview) even though it has no database row yet.
    tk.g.scheming_dynamic_preview_type = schema_type

    return tk.render(
        "scheming_dynamic/snippets/schema_preview.html",
        {
            "schema": expanded,
            "entity_type": entity_type,
            "licenses": model.Package.get_license_options(),
        },
    )
