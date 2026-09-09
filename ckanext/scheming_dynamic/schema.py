from __future__ import annotations

from pathlib import Path
from typing import Any

import ckan.plugins as p
import ckan.plugins.toolkit as tk

import ckanext.scheming
from ckanext.scheming.plugins import _SchemingMixin
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE


class BaseSchema:
    """Base class for dataset, group, and organization schemas.

    Shared root keys (`about`) and all field-level $defs. Subclasses
    add the root keys specific to their schema type.
    """

    schema_id: str
    title: str
    description: str

    I18N_TEXT = {
        "title": tk._("Label"),
        "x-info": {
            "variant": "modal",
            "title": tk._("About"),
            "content": tk._(
                "A label/help\\_text/form\\_placeholder value:\n"
                "- a plain string, translated via gettext\n"
                "- an object mapping language codes to strings "
                "(translations)\n"
                "- `null`/empty, to render no visible text — for `label` "
                "specifically, this falls back to `field_name` instead; "
                "`help_text`/`form_placeholder` just aren't shown\n\n"
            ),
        },
        "oneOf": [
            {"x-switcherTitle": tk._("Text"), "type": "string"},
            {
                "x-switcherTitle": tk._("Translations (language code to text)"),
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            {"x-switcherTitle": tk._("No label"), "type": "null"},
        ],
    }

    CHOICE = {
        "type": "object",
        "required": ["value"],
        "title": tk._("Choice {{i1}}"),
        "properties": {
            "value": {"type": "string", "title": tk._("Value")},
            "label": {"$ref": "#/$defs/i18n_text"},
        },
        "additionalProperties": True,
    }

    FIELD = {
        "type": "object",
        "title": tk._("Field {{i1}}"),
        "required": [],
        "x-deactivateNonRequired": True,
        "x-navWarning": False,
        "properties": {
            "field_name": {
                "type": "string",
                "title": tk._("Field name"),
            },
            "label": {"$ref": "#/$defs/i18n_text", "title": tk._("Label")},
            "required": {
                "type": "boolean",
                "title": tk._("Required"),
                "x-format": "checkbox",
            },
            "default": {"type": "string", "title": tk._("Default")},
            "preset": {"$ref": "#/$defs/preset", "title": tk._("Preset")},
            "form_snippet": {
                "$ref": "#/$defs/form_snippet",
                "title": tk._("Form snippet"),
            },
            "display_snippet": {
                "$ref": "#/$defs/display_snippet",
                "title": tk._("Display snippet"),
            },
            "help_text": {"$ref": "#/$defs/i18n_text", "title": tk._("Help text")},
            "form_placeholder": {
                "$ref": "#/$defs/i18n_text",
                "title": tk._("Form placeholder"),
            },
            "choices": {
                "type": "array",
                "items": {"$ref": "#/$defs/choice"},
                "title": tk._("Choices"),
            },
            "repeating_label": {
                "$ref": "#/$defs/i18n_text",
                "title": tk._("Repeating label"),
            },
            "repeating_subfields": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/field"},
                "title": tk._("Repeating subfields"),
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About repeating subfields"),
                    "content": tk._(
                        "Makes this field the parent of a repeatable group of "
                        "subfields (e.g. a list of contacts, each with their "
                        "own address/phone/etc.), entered the same way as "
                        "normal fields.\n\n"
                        "Needs an `IPackageController` plugin with "
                        "`before_index` to convert repeating subfields into a "
                        "format solr can index — the built-in "
                        "`scheming_nerf_index` plugin does this by encoding "
                        "them as JSON strings."
                    ),
                },
            },
            "start_form_page": {
                "$ref": "#/$defs/start_form_page",
                "title": tk._("Start form page"),
            },
        },
        "additionalProperties": True,
    }

    FIELD_LIST = {
        "type": "array",
        "minItems": 1,
        "items": {"type": "object", "$ref": "#/$defs/field"},
    }

    def build(self) -> dict[str, Any]:
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": self.schema_id,
            "title": self.title,
            "description": self.description,
            "type": "object",
            "required": self.required(),
            "properties": self.properties(),
            "additionalProperties": True,
            "$defs": self.defs(),
            "x-enableCollapseToggle": False,
            "x-navWarning": False,
        }

    def required(self) -> list[str]:
        return ["about"]

    def properties(self) -> dict[str, Any]:
        return {
            "about": {"type": "string", "title": tk._("About"), "minLength": 1},
        }

    def defs(self) -> dict[str, Any]:
        return {
            "i18n_text": self.I18N_TEXT,
            "choice": self.CHOICE,
            "start_form_page": {
                "type": "object",
                "title": tk._("Start form page"),
                "required": ["title", "description"],
                "properties": {
                    "title": {"$ref": "#/$defs/i18n_text", "title": tk._("Title")},
                    "description": {
                        "$ref": "#/$defs/i18n_text",
                        "title": tk._("Description"),
                    },
                },
                "additionalProperties": True,
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About start form page"),
                    "content": tk._(
                        "Marks this field as the start of a new page of the "
                        "dataset creation/editing form, splitting the fields "
                        "before it and the fields from here on into separate "
                        "pages.\n\n"
                        "`title` and `description` are shown for navigation "
                        "between pages.\n\n"
                        "Only applies to top-level dataset fields — not "
                        "resource fields or repeating subfields."
                    ),
                },
            },
            "preset": {
                "type": "string",
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About presets"),
                    "content": tk._(
                        "A preset bundles different field attributes "
                        "(such as `form_snippet`, `display_snippet`, "
                        "`validators`, `output_validators`, etc.) "
                        "so you don't have to wire those up by hand.\n\n"
                        "Must be one of the presets registered at startup via "
                        "the `scheming.presets` config option."
                    ),
                },
                "enum": self._registered_preset_names(),
            },
            "form_snippet": {
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About"),
                    "content": tk._(
                        "Form snippet rendered for the field: one of the "
                        "scheming/form_snippets/*.html templates available in "
                        "the registered template directories, or null to hide "
                        "the field from forms."
                    ),
                },
                "oneOf": [
                    {
                        "x-switcherTitle": tk._("Snippet template"),
                        "type": "string",
                        "enum": self._available_snippets("form_snippets"),
                    },
                    {"x-switcherTitle": tk._("Hide field from forms"), "type": "null"},
                ],
            },
            "display_snippet": {
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About"),
                    "content": tk._(
                        "Display snippet rendered for the field: one of the "
                        "scheming/display_snippets/*.html templates available "
                        "in the registered template directories, or null to "
                        "hide the field from display pages."
                    ),
                },
                "oneOf": [
                    {
                        "x-switcherTitle": tk._("Snippet template"),
                        "type": "string",
                        "enum": self._available_snippets("display_snippets"),
                    },
                    {
                        "x-switcherTitle": tk._("Hide field from display pages"),
                        "type": "null",
                    },
                ],
            },
            "field": {
                **self.FIELD,
                "if": {
                    "required": ["preset"],
                    "properties": {"preset": {"enum": self._presets_with_field_name()}},
                },
                "else": {
                    "required": ["field_name"],
                    "properties": {
                        "field_name": {
                            "minLength": 1,
                            "pattern": "^[A-Za-z0-9_\\-]+$",
                        },
                    },
                },
            },
        }

    @staticmethod
    def _available_snippets(kind: str) -> list[str]:
        """Get the names of snippets available for the given kind.

        Return the names of scheming/<kind>/*.html templates found in
        every registered template directory.

        Falls back to ckanext-scheming's own templates when the app config
        is not available (e.g. building the schema outside a CKAN app).
        Underscore-prefixed templates are partials included by other
        snippets and are not offered.
        """
        template_dirs = list(tk.config.get("computed_template_paths") or [])
        template_dirs.append(str(Path(ckanext.scheming.__file__).parent / "templates"))

        names = {
            path.name
            for directory in template_dirs
            for path in Path(directory, "scheming", kind).glob("*.html")
            if not path.name.startswith("_")
        }
        return sorted(names)

    @staticmethod
    def _registered_preset_names() -> list[str]:
        """Return the names of all presets registered at startup or in the DB."""
        BaseSchema._sync_dynamic_presets()

        return sorted(_SchemingMixin.get_presets(tk.config) or {})

    @staticmethod
    def _presets_with_field_name() -> list[str]:
        """Presets that supply their own `field_name`."""
        BaseSchema._sync_dynamic_presets()
        presets = _SchemingMixin.get_presets(tk.config) or {}

        return sorted(
            name for name, values in presets.items() if "field_name" in values
        )

    @staticmethod
    def _sync_dynamic_presets() -> None:
        if not p.plugin_loaded("scheming_dynamic"):
            return

        sync.ensure_presets_synced()


class DatasetSchema(BaseSchema):
    schema_id = "https://github.com/ckan/ckanext-scheming/scheming_dynamic/dataset_schema.schema.json"
    title = "Dataset schema"
    description = "Structural schema for a ckanext-scheming dataset schema definition"

    def required(self) -> list[str]:
        return super().required() + [
            "dataset_type",
            "dataset_fields",
            "resource_fields",
        ]

    def properties(self) -> dict[str, Any]:
        return {
            **super().properties(),
            "dataset_type": {
                "type": "string",
                "title": tk._("Dataset type"),
                "minLength": 1,
                "pattern": "^[A-Za-z0-9_\\-]+$",
            },
            "dataset_fields": {
                **self.FIELD_LIST,
                "title": tk._("Dataset fields"),
                "x-navWarning": False,
            },
            "resource_fields": {
                **self.FIELD_LIST,
                "title": tk._("Resource fields"),
                "x-navWarning": False,
            },
            "draft_fields_required": {
                "type": "boolean",
                "title": tk._("Draft fields required"),
                "x-format": "checkbox",
                "x-info": {
                    "variant": "modal",
                    "title": tk._("About draft fields required"),
                    "content": tk._(
                        "Whether required fields are enforced while a dataset "
                        "is still in draft state.\n\n"
                        "Keep `false` to allow saving dataset and resource "
                        "metadata even if some required fields are still "
                        "blank, as long as the dataset hasn't been published "
                        "yet — needed for required fields on form pages past "
                        "the first, or to save partially-entered metadata."
                    ),
                },
            },
        }


class _GroupOrgSchema(BaseSchema):
    """Shared shape for group and organization schemas.

    Groups and organizations have a single flat ``fields`` list and no
    resource sub-form, so — unlike datasets — they get no form-page splitting
    (``start_form_page`` is dropped from the field shape here).
    """

    type_field: str
    type_title: str

    def required(self) -> list[str]:
        # ``about`` is optional for group/organization schemas -- existing
        # file-defined schemas (e.g. group_with_bookface.json) don't set it
        return [self.type_field, "fields"]

    def properties(self) -> dict[str, Any]:
        return {
            **super().properties(),
            self.type_field: {
                "type": "string",
                "title": self.type_title,
                "minLength": 1,
                "pattern": "^[A-Za-z0-9_\\-]+$",
            },
            "fields": {**self.FIELD_LIST, "title": tk._("Fields")},
        }

    def defs(self) -> dict[str, Any]:
        built = super().defs()
        field = {**built["field"]}
        field["properties"] = {
            k: v
            for k, v in field.get("properties", {}).items()
            if k != "start_form_page"
        }
        field.pop("start_form_page", None)
        built["field"] = field
        built.pop("start_form_page", None)
        return built


class GroupSchema(_GroupOrgSchema):
    schema_id = "https://github.com/ckan/ckanext-scheming/scheming_dynamic/group_schema.schema.json"
    title = "ckanext-scheming group schema"
    description = "Structural schema for a ckanext-scheming group schema definition"

    type_field = "group_type"
    type_title = tk._("Group type")


class OrganizationSchema(_GroupOrgSchema):
    schema_id = "https://github.com/ckan/ckanext-scheming/scheming_dynamic/organization_schema.schema.json"
    title = "ckanext-scheming organization schema"
    description = (
        "Structural schema for a ckanext-scheming organization schema definition"
    )

    type_field = "organization_type"
    type_title = tk._("Organization type")


class PresetSchema(BaseSchema):
    """Schema for a single field preset.

    A preset's ``values`` accept the same attribute bag as a dataset/
    resource field (validators, form_snippet, display_snippet, classes,
    choices, even its own ``preset`` to base on another registered preset)
    since that's exactly what gets merged into a field using it.
    """

    schema_id = "https://github.com/ckan/ckanext-scheming/scheming_dynamic/preset_schema.schema.json"
    title = "Preset"
    description = "Structural schema for a ckanext-scheming field preset definition"

    def __init__(self, exclude_preset_name: str | None = None) -> None:
        self._exclude_preset_name = exclude_preset_name

    def build(self) -> dict[str, Any]:
        schema = super().build()
        schema["additionalProperties"] = False
        schema["x-enablePropertiesToggle"] = False
        return schema

    def required(self) -> list[str]:
        return ["preset_name", "values"]

    def properties(self) -> dict[str, Any]:
        properties = {
            k: v for k, v in self.FIELD["properties"].items() if k != "start_form_page"
        }

        return {
            "preset_name": {
                "type": "string",
                "title": tk._("Preset name"),
                "minLength": 1,
                "pattern": "^[A-Za-z0-9_\\-]+$",
            },
            "values": {
                "type": "object",
                "title": tk._("Values"),
                "required": [],
                "properties": {**properties, "start_form_page": False},
                "additionalProperties": True,
                "x-deactivateNonRequired": True,
                "x-navWarning": False,
                "x-enableCollapseToggle": False,
            },
        }

    def defs(self) -> dict[str, Any]:
        """Same $defs as a dataset/group/org schema, minus this preset itself.

        Excluding the preset being edited from the `preset` enum only
        blocks the obvious one-hop self-reference in the form; the
        `scheming_preset_values_valid` validator is what actually
        catches longer cycles.
        """
        built = super().defs()
        if self._exclude_preset_name:
            built["preset"] = {
                **built["preset"],
                "enum": [
                    name
                    for name in built["preset"]["enum"]
                    if name != self._exclude_preset_name
                ],
            }
        return built


SCHEMA_CLASSES: dict[str, type[BaseSchema]] = {
    DEFAULT_ENTITY_TYPE: DatasetSchema,
    "group": GroupSchema,
    "organization": OrganizationSchema,
}
