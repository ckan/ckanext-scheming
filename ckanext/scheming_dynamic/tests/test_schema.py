from __future__ import annotations

import pytest

from ckanext.scheming.plugins import DEFAULT_PRESETS
from ckanext.scheming_dynamic.schema import (
    SCHEMA_CLASSES,
    DatasetSchema,
    GroupSchema,
    OrganizationSchema,
)


class TestSchemaTypes:
    @pytest.mark.parametrize(
        ("schema_cls", "expected_required"),
        [
            (
                DatasetSchema,
                ["about", "dataset_type", "dataset_fields", "resource_fields"],
            ),
            (GroupSchema, ["group_type", "fields"]),
            (OrganizationSchema, ["organization_type", "fields"]),
        ],
    )
    def test_required_keys(self, schema_cls, expected_required):
        built = schema_cls().build()
        assert built["required"] == expected_required

    @pytest.mark.parametrize(
        ("schema_cls", "field_list_keys"),
        [
            (DatasetSchema, ["dataset_fields", "resource_fields"]),
            (GroupSchema, ["fields"]),
            (OrganizationSchema, ["fields"]),
        ],
    )
    def test_field_list_properties_reference_shared_field_def(
        self, schema_cls, field_list_keys
    ):
        built = schema_cls().build()
        for key in field_list_keys:
            assert built["properties"][key]["items"] == {
                "type": "object",
                "$ref": "#/$defs/field",
            }

    def test_field_def_has_start_form_page_property(self):
        field_def = DatasetSchema().build()["$defs"]["field"]
        assert field_def["properties"]["start_form_page"] == {
            "$ref": "#/$defs/start_form_page",
            "title": "Start form page",
        }

    def test_start_form_page_requires_title_and_description(self):
        start_form_page = DatasetSchema().build()["$defs"]["start_form_page"]
        assert start_form_page["required"] == ["title", "description"]

    def test_start_form_page_validates_on_dataset_field(self):
        jsonschema = pytest.importorskip("jsonschema")
        built = DatasetSchema().build()
        instance = {
            "about": "https://example.com/schema",
            "dataset_type": "dataset",
            "dataset_fields": [
                {
                    "field_name": "notes",
                    "start_form_page": {
                        "title": "Detailed Metadata",
                        "description": "Improves search and gives useful links",
                    },
                },
            ],
            "resource_fields": [{"field_name": "url"}],
        }
        jsonschema.Draft202012Validator(built).validate(instance)

    def test_start_form_page_missing_description_is_invalid(self):
        jsonschema = pytest.importorskip("jsonschema")
        built = DatasetSchema().build()
        instance = {
            "about": "https://example.com/schema",
            "dataset_type": "dataset",
            "dataset_fields": [
                {"field_name": "notes", "start_form_page": {"title": "Missing desc"}},
            ],
            "resource_fields": [{"field_name": "url"}],
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(built).validate(instance)

    def test_registry_matches_classes(self):
        assert SCHEMA_CLASSES["dataset"] is DatasetSchema
        assert SCHEMA_CLASSES["group"] is GroupSchema
        assert SCHEMA_CLASSES["organization"] is OrganizationSchema

    def test_common_root_properties_are_shared(self):
        for schema_cls in SCHEMA_CLASSES.values():
            props = schema_cls().build()["properties"]
            assert props["about"] == {
                "type": "string",
                "title": "About",
                "minLength": 1,
            }

    def test_group_and_org_field_def_is_shared(self):
        group = GroupSchema().build()["$defs"]["field"]
        org = OrganizationSchema().build()["$defs"]["field"]
        assert group == org

    def test_group_and_org_schemas_have_no_form_pages(self):
        for schema_cls in (GroupSchema, OrganizationSchema):
            built = schema_cls().build()
            assert "start_form_page" not in built["$defs"]
            assert "start_form_page" not in built["$defs"]["field"]["properties"]

    def test_dataset_schema_keeps_form_pages(self):
        built = DatasetSchema().build()
        assert "start_form_page" in built["$defs"]["field"]["properties"]

    def test_builtin_preset_names_include_known_presets(self):
        enum = DatasetSchema().build()["$defs"]["preset"]["enum"]
        assert "title" in enum
        assert "select" in enum
        assert "not_a_real_preset" not in enum

    def test_form_snippet_names_come_from_existing_templates(self):
        template, hidden = DatasetSchema().build()["$defs"]["form_snippet"]["oneOf"]
        assert hidden["type"] == "null"
        assert "large_text.html" in template["enum"]
        assert "markdown.html" in template["enum"]
        assert "_organization_select.html" not in template["enum"]
        assert "not_a_real_snippet.html" not in template["enum"]

    def test_display_snippet_names_come_from_existing_templates(self):
        template, hidden = DatasetSchema().build()["$defs"]["display_snippet"]["oneOf"]
        assert hidden["type"] == "null"
        assert "link.html" in template["enum"]
        assert "not_a_real_snippet.html" not in template["enum"]

    def test_schema_is_valid_jsonschema(self):
        jsonschema = pytest.importorskip("jsonschema")
        for schema_cls in SCHEMA_CLASSES.values():
            jsonschema.Draft202012Validator.check_schema(schema_cls().build())

    def test_draft_fields_required_is_optional_boolean(self):
        props = DatasetSchema().build()["properties"]
        assert props["draft_fields_required"]["type"] == "boolean"
        assert "draft_fields_required" not in DatasetSchema().required()

    def test_repeating_subfields_reference_shared_field_def(self):
        field_def = DatasetSchema().build()["$defs"]["field"]
        assert field_def["properties"]["repeating_subfields"]["items"] == {
            "$ref": "#/$defs/field"
        }

    def test_field_name_unconstrained_by_default(self):
        field_def = DatasetSchema().build()["$defs"]["field"]
        assert field_def["required"] == []
        assert field_def["properties"]["field_name"] == {
            "type": "string",
            "title": "Field name",
        }

    def test_field_name_relaxed_only_for_presets_with_field_name(self):
        field_def = DatasetSchema().build()["$defs"]["field"]
        assert field_def["if"] == {
            "properties": {
                "preset": {"enum": DatasetSchema()._presets_with_field_name()}
            },
            "required": ["preset"],
        }
        assert field_def["else"] == {
            "required": ["field_name"],
            "properties": {
                "field_name": {
                    "minLength": 1,
                    "pattern": "^[A-Za-z0-9_\\-]+$",
                },
            },
        }

    @pytest.mark.ckan_config(
        "scheming.presets",
        f"{DEFAULT_PRESETS} ckanext.scheming_dynamic:tests/presets.yml",
    )
    @pytest.mark.usefixtures("reload_scheming_presets")
    def test_field_name_required_unless_covering_preset(self):
        jsonschema = pytest.importorskip("jsonschema")
        built = DatasetSchema().build()
        schema = DatasetSchema()
        covering_presets = schema._presets_with_field_name()
        assert "preset_with_field_name" in covering_presets
        covering_preset = "preset_with_field_name"
        non_covering_preset = next(
            name
            for name in schema._registered_preset_names()
            if name not in covering_presets
        )

        def is_valid(dataset_field):
            instance = {
                "about": "https://example.com/schema",
                "dataset_type": "dataset",
                "dataset_fields": [dataset_field],
                "resource_fields": [{"field_name": "url"}],
            }
            errors = list(jsonschema.Draft202012Validator(built).iter_errors(instance))
            return len(errors) == 0

        assert is_valid({"preset": covering_preset})
        assert is_valid({"preset": covering_preset, "field_name": ""})
        assert not is_valid({"label": "no preset, no field_name"})
        assert not is_valid({"field_name": ""})
        assert not is_valid({"field_name": "bad name!"})
        assert is_valid({"field_name": "notes"})
        assert not is_valid({"preset": non_covering_preset})

    @pytest.mark.ckan_config("scheming.presets", DEFAULT_PRESETS)
    @pytest.mark.usefixtures("reload_scheming_presets")
    def test_field_name_required_when_no_preset_supplies_it(self):
        jsonschema = pytest.importorskip("jsonschema")
        schema = DatasetSchema()
        assert schema._presets_with_field_name() == []

        built = schema.build()
        assert built["$defs"]["field"]["if"]["properties"]["preset"]["enum"] == []

        def is_valid(dataset_field):
            instance = {
                "about": "https://example.com/schema",
                "dataset_type": "dataset",
                "dataset_fields": [dataset_field],
                "resource_fields": [{"field_name": "url"}],
            }
            errors = list(jsonschema.Draft202012Validator(built).iter_errors(instance))
            return len(errors) == 0

        assert not is_valid({"label": "no preset, no field_name"})
        assert not is_valid({"field_name": ""})
        assert not is_valid({"preset": "title"})
        assert is_valid({"field_name": "notes"})

    def test_repeating_subfields_validate(self):
        jsonschema = pytest.importorskip("jsonschema")
        built = DatasetSchema().build()
        instance = {
            "about": "https://example.com/schema",
            "dataset_type": "dataset",
            "dataset_fields": [
                {
                    "field_name": "contacts",
                    "label": "Contacts",
                    "repeating_label": "Contact",
                    "repeating_subfields": [
                        {"field_name": "address", "label": "Address", "required": True},
                        {"field_name": "phone", "label": "Phone Number"},
                    ],
                },
            ],
            "resource_fields": [{"field_name": "url"}],
        }
        jsonschema.Draft202012Validator(built).validate(instance)
