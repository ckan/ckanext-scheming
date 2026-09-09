from __future__ import annotations

import json

from ckanext.scheming_dynamic.schema import DatasetSchema
from ckanext.scheming_dynamic.tests.helpers import SCHEMA_DEFINITION
from ckanext.scheming_dynamic.validator import error_location, iter_errors, load_data


def errors_for(data):
    return list(iter_errors(data, DatasetSchema()))


class TestIterErrors:
    def test_minimal_valid_schema_has_no_errors(self):
        assert errors_for(SCHEMA_DEFINITION) == []

    def test_missing_root_keys_are_reported(self):
        errors = errors_for({})
        messages = {e.message for e in errors}
        assert "'about' is a required property" in messages
        assert "'dataset_type' is a required property" in messages
        assert "'dataset_fields' is a required property" in messages
        assert "'resource_fields' is a required property" in messages
        assert all(error_location(e) == "<root>" for e in errors)

    def test_missing_field_name_is_reported(self):
        data = {**SCHEMA_DEFINITION, "dataset_fields": [{"label": "No name here"}]}
        errors = errors_for(data)
        assert any(
            error_location(e) == "dataset_fields/0" and "field_name" in e.message
            for e in errors
        )

    def test_field_name_wrong_type_is_reported(self):
        data = {**SCHEMA_DEFINITION, "dataset_fields": [{"field_name": 123}]}
        errors = errors_for(data)
        assert any(error_location(e) == "dataset_fields/0/field_name" for e in errors)

    def test_required_wrong_type_is_reported(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "required": "yes"}],
        }
        errors = errors_for(data)
        assert any(error_location(e) == "dataset_fields/0/required" for e in errors)

    def test_unknown_preset_is_reported(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "preset": "not_a_real_preset"}],
        }
        errors = errors_for(data)
        assert any(error_location(e) == "dataset_fields/0/preset" for e in errors)

    def test_known_preset_is_accepted(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "preset": "title"}],
        }
        assert errors_for(data) == []

    def test_multilang_label_is_accepted(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [
                {"field_name": "x", "label": {"en": "Title", "fr": "Titre"}}
            ],
        }
        assert errors_for(data) == []

    def test_multilang_label_with_non_string_value_is_rejected(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "label": {"en": "Title", "fr": 5}}],
        }
        errors = errors_for(data)
        assert any(error_location(e) == "dataset_fields/0/label" for e in errors)

    def test_null_label_is_accepted(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "label": None}],
        }
        assert errors_for(data) == []

    def test_boolean_choice_label_is_rejected(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [
                {
                    "field_name": "x",
                    "preset": "select",
                    "choices": [{"value": False, "label": False}],
                }
            ],
        }
        errors = errors_for(data)
        assert any(
            error_location(e) == "dataset_fields/0/choices/0/label" for e in errors
        )

    def test_choices_missing_label_is_accepted(self):
        # scheming_choices_label() falls back to `c.get('label', value)`.
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "choices": [{"value": "a"}]}],
        }
        assert errors_for(data) == []

    def test_choices_missing_value_is_rejected(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "choices": [{"label": "A"}]}],
        }
        errors = errors_for(data)
        assert any(error_location(e) == "dataset_fields/0/choices/0" for e in errors)

    def test_default_accepts_string(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [{"field_name": "x", "default": "abc"}],
        }
        assert errors_for(data) == []

    def test_default_rejects_non_string(self):
        for default in (1, True, None, [], {}):
            data = {
                **SCHEMA_DEFINITION,
                "dataset_fields": [{"field_name": "x", "default": default}],
            }
            assert errors_for(data) != []

    def test_unknown_field_keys_are_ignored(self):
        data = {
            **SCHEMA_DEFINITION,
            "dataset_fields": [
                {
                    "field_name": "x",
                    "form_snippet": "markdown.html",
                    "msf_group": "General info",
                    "validators": "ignore_missing unicode_safe",
                }
            ],
        }
        assert errors_for(data) == []


class TestLoadData:
    def test_load_yaml(self, tmp_path):
        path = tmp_path / "schema.yaml"
        path.write_text("about: Example schema\ndataset_type: foo\n")
        assert load_data(path) == {
            "about": "Example schema",
            "dataset_type": "foo",
        }

    def test_load_yml_extension(self, tmp_path):
        path = tmp_path / "schema.yml"
        path.write_text("about: Example schema\n")
        assert load_data(path) == {"about": "Example schema"}

    def test_load_json(self, tmp_path):
        path = tmp_path / "schema.json"
        path.write_text(json.dumps({"about": "Example schema"}))
        assert load_data(path) == {"about": "Example schema"}


class TestErrorLocation:
    def test_root_error_location(self):
        errors = errors_for({})
        assert errors
        assert all(error_location(e) == "<root>" for e in errors)

    def test_nested_error_location(self):
        data = {
            **SCHEMA_DEFINITION,
            "resource_fields": [{"field_name": "x", "required": "yes"}],
        }
        errors = errors_for(data)
        assert any(error_location(e) == "resource_fields/0/required" for e in errors)
