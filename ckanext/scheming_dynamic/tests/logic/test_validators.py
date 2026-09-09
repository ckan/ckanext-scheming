from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories, helpers

from ckanext.scheming_dynamic.logic.validators import (
    scheming_definition_valid,
    scheming_preset_exists,
    scheming_preset_not_in_use,
    scheming_preset_values_valid,
    scheming_schema_exists,
    scheming_schema_not_in_use,
)
from ckanext.scheming_dynamic.model import SchemingSchemaVersion
from ckanext.scheming_dynamic.tests import factories as scheming_factories


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingSchemaExists:
    def call_validator(self, entity_type: str, schema_type: str) -> None:
        data = {
            ("entity_type",): entity_type,
            ("schema_type",): schema_type,
        }
        return scheming_schema_exists(("schema_type",), data, {}, {})

    def test_existing_schema_passes(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        assert self.call_validator("dataset", "test-type") is None

    def test_missing_schema_raises_invalid(self):
        with pytest.raises(tk.Invalid, match="not found"):
            self.call_validator("dataset", "test-type")

    def test_schema_for_other_entity_type_does_not_count(self, schema_definition):
        SchemingSchemaVersion.create("group", "test-type", schema_definition)

        with pytest.raises(tk.Invalid, match="not found"):
            self.call_validator("dataset", "test-type")


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingSchemaNotInUse:
    def _call_not_in_use_validator(self, entity_type: str, schema_type: str) -> None:
        data = {
            ("entity_type",): entity_type,
            ("schema_type",): schema_type,
        }
        return scheming_schema_not_in_use(("schema_type",), data, {}, {})

    def test_passes_when_no_package_of_type_exists(self):
        assert self._call_not_in_use_validator("dataset", "test-type") is None

    def test_raises_invalid_when_package_of_type_exists(self):
        factories.Dataset(type="test-type")

        with pytest.raises(tk.Invalid, match="still exist"):
            self._call_not_in_use_validator("dataset", "test-type")

    def test_raises_invalid_when_only_a_trashed_package_of_type_exists(self):
        dataset = factories.Dataset(type="test-type")
        helpers.call_action("package_delete", id=dataset["id"])

        with pytest.raises(tk.Invalid, match="still exist"):
            self._call_not_in_use_validator("dataset", "test-type")


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingDefinitionValid:
    def call_definition_validator(self, definition: dict) -> None:
        data = {
            ("entity_type",): "dataset",
            ("definition",): definition,
        }
        return scheming_definition_valid(("definition",), data, {}, {})

    def test_valid_definition_passes(self, schema_definition):
        assert self.call_definition_validator(schema_definition) is None

    def test_valid_repeating_subfields_passes(self, schema_definition):
        schema_definition["dataset_fields"] = [
            {
                "field_name": "citation",
                "repeating_subfields": [{"field_name": "originator"}],
            }
        ]

        assert self.call_definition_validator(schema_definition) is None

    def test_unknown_entity_type_raises_invalid(self):
        with pytest.raises(tk.Invalid, match="not supported"):
            scheming_definition_valid(
                ("definition",),
                {("entity_type",): "bogus", ("definition",): {}},
                {},
                {},
            )

    def test_missing_required_key_raises_invalid(self, schema_definition):
        del schema_definition["dataset_type"]

        with pytest.raises(tk.Invalid, match="dataset_type"):
            self.call_definition_validator(schema_definition)

    def test_unknown_preset_raises_invalid(self, schema_definition):
        schema_definition["dataset_fields"] = [
            {"field_name": "title", "preset": "not_a_real_preset"}
        ]

        with pytest.raises(tk.Invalid, match="is not one of"):
            self.call_definition_validator(schema_definition)

    @pytest.mark.parametrize(
        "bad_repeating_subfields",
        [
            {"field_name": "originator"},
            "notalist",
            ["originator"],
        ],
        ids=["dict-instead-of-list", "plain-string", "list-of-strings"],
    )
    def test_malformed_repeating_subfields_raises_invalid(
        self, schema_definition, bad_repeating_subfields
    ):
        schema_definition["dataset_fields"] = [
            {"field_name": "citation", "repeating_subfields": bad_repeating_subfields}
        ]

        with pytest.raises(tk.Invalid, match="is not of type"):
            self.call_definition_validator(schema_definition)


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingPresetExists:
    def call_validator(self, preset_name: str) -> None:
        data = {("preset_name",): preset_name}
        return scheming_preset_exists(("preset_name",), data, {}, {})

    def test_existing_preset_passes(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        assert self.call_validator("test-preset") is None

    def test_missing_preset_raises_invalid(self):
        with pytest.raises(tk.Invalid, match="not found"):
            self.call_validator("test-preset")


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingPresetNotInUse:
    def _call_not_in_use_validator(self, preset_name: str) -> None:
        data = {("preset_name",): preset_name}
        return scheming_preset_not_in_use(("preset_name",), data, {}, {})

    def test_passes_when_unused(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        assert self._call_not_in_use_validator("test-preset") is None

    def test_raises_invalid_when_another_preset_bases_on_it(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        scheming_factories.Preset(
            preset_name="dependent-preset", values={"preset": "test-preset"}
        )

        with pytest.raises(tk.Invalid, match="dependent-preset"):
            self._call_not_in_use_validator("test-preset")

    def test_raises_invalid_when_used_by_a_schema(
        self, preset_definition, schema_definition
    ):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        definition = {
            **schema_definition,
            "dataset_fields": [{"field_name": "x", "preset": "test-preset"}],
        }
        SchemingSchemaVersion.create("dataset", "test-type", definition)

        with pytest.raises(tk.Invalid, match="test-type"):
            self._call_not_in_use_validator("test-preset")


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingPresetValuesValid:
    def call_values_validator(self, preset_name: str, values: dict) -> None:
        data = {("preset_name",): preset_name, ("values",): values}
        return scheming_preset_values_valid(("values",), data, {}, {})

    def test_valid_values_pass(self, preset_definition):
        assert (
            self.call_values_validator("test-preset", preset_definition["values"])
            is None
        )

    def test_malformed_values_raise_invalid(self):
        with pytest.raises(tk.Invalid, match="is not of type"):
            self.call_values_validator(
                "test-preset", {"repeating_subfields": "notalist"}
            )

    def test_self_reference_on_a_not_yet_created_preset_is_rejected(self):
        # "test-preset" isn't registered yet, so it can't be its own base
        # either way: caught by the preset enum, not the cycle resolver
        with pytest.raises(tk.Invalid, match="is not one of"):
            self.call_values_validator("test-preset", {"preset": "test-preset"})

    def test_unknown_base_raises_invalid(self):
        with pytest.raises(tk.Invalid, match="not-a-real-preset"):
            self.call_values_validator("test-preset", {"preset": "not-a-real-preset"})

    def test_editing_a_preset_into_a_cycle_is_rejected(self, preset_definition):
        # "test-preset" already exists (no base yet) and "a" already bases on
        # it, so both currently resolve fine and "a" is a valid enum choice;
        # editing "test-preset" to base on "a" is what closes the loop, and
        # is the only way to reach the resolve()-based cycle check, since a
        # brand new preset can never be a valid base for anything yet
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        scheming_factories.Preset(preset_name="a", values={"preset": "test-preset"})

        with pytest.raises(tk.Invalid, match="cycle"):
            self.call_values_validator("test-preset", {"preset": "a"})

    def test_base_on_builtin_preset_passes(self):
        assert self.call_values_validator("test-preset", {"preset": "title"}) is None
