from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories, helpers

from ckanext.scheming_dynamic.model import (
    SchemingPreset,
    SchemingSchemaActivity,
    SchemingSchemaPin,
    SchemingSchemaVersion,
)
from ckanext.scheming_dynamic.tests import factories as scheming_factories


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestSchemingSchemaCreate:
    def test_create_returns_schema_dict(self, schema_definition):
        result = helpers.call_action(
            "scheming_schema_create",
            definition=schema_definition,
        )

        assert result["entity_type"] == "dataset"
        assert result["schema_type"] == "test-type"
        assert result["definition"] == schema_definition
        assert result["version"] == 1
        assert result["created"]

    def test_created_schema_is_persisted(self, schema_definition):
        helpers.call_action(
            "scheming_schema_create",
            definition=schema_definition,
        )

        row = SchemingSchemaVersion.head("dataset", "test-type")
        assert row
        assert row.definition == schema_definition

    def test_duplicate_schema_is_rejected(self, schema_definition):
        helpers.call_action(
            "scheming_schema_create",
            definition=schema_definition,
        )

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_schema_create",
                definition=schema_definition,
            )

        assert "already exists" in str(err.value.error_dict["schema_type"])

    def test_missing_definition_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_schema_create")

    def test_invalid_entity_type_is_rejected(self, schema_definition):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_schema_create",
                entity_type="user",
                definition=schema_definition,
            )

    @pytest.mark.parametrize(
        ("entity_type", "type_field"),
        [("group", "group_type"), ("organization", "organization_type")],
    )
    def test_group_and_organization_schemas_can_be_created(
        self, entity_type, type_field
    ):
        result = helpers.call_action(
            "scheming_schema_create",
            entity_type=entity_type,
            definition={
                "about": "Example schema",
                type_field: entity_type,
                "fields": [{"field_name": "title"}],
            },
        )

        assert result["entity_type"] == entity_type
        assert result["schema_type"] == entity_type
        assert result["version"] == 1
        assert SchemingSchemaVersion.head(entity_type, entity_type)

    @pytest.mark.parametrize(
        ("entity_type", "type_field", "schema_type"),
        [
            ("group", "group_type", "dataset"),
            ("group", "group_type", "organization"),
            ("organization", "organization_type", "dataset"),
            ("organization", "organization_type", "group"),
        ],
    )
    def test_reserved_type_name_for_wrong_entity_type_is_rejected(
        self, entity_type, type_field, schema_type
    ):
        # "dataset"/"group"/"organization" are always served by CKAN's own
        # built-in blueprint for the matching entity type, ahead of the
        # dynamic catch-alls -- using one for a different entity_type would
        # create a schema no URL could ever reach
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_schema_create",
                entity_type=entity_type,
                definition={
                    "about": "Example schema",
                    type_field: schema_type,
                    "fields": [{"field_name": "title"}],
                },
            )

        assert "reserved for entity_type" in str(err.value.error_dict["schema_type"])

    def test_reserved_type_name_for_dataset_entity_type_is_rejected(
        self, schema_definition
    ):
        definition = {**schema_definition, "dataset_type": "group"}

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_create", definition=definition)

        assert "reserved for entity_type" in str(err.value.error_dict["schema_type"])

    def test_schema_type_claimed_by_another_entity_type_is_rejected(
        self, schema_definition
    ):
        # the dataset and group/organization catch-all routes match on the
        # same URL shape, so a live schema_type under one entity_type
        # shadows -- and makes unreachable -- the same name under another
        helpers.call_action("scheming_schema_create", definition=schema_definition)

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_schema_create",
                entity_type="group",
                definition={
                    "about": "Example schema",
                    "group_type": schema_definition["dataset_type"],
                    "fields": [{"field_name": "title"}],
                },
            )

        assert "already used by entity_type 'dataset'" in str(
            err.value.error_dict["schema_type"]
        )

    @pytest.mark.parametrize(
        ("entity_type", "type_field"),
        [("group", "group_type"), ("organization", "organization_type")],
    )
    def test_group_type_colliding_with_core_blueprint_is_rejected(
        self, entity_type, type_field
    ):
        # CKAN registers a Flask blueprint named after each dynamic type at
        # startup; "user" is already taken by core, so
        # register_group_blueprints would raise ValueError and abort the
        # next restart. Reject it at save time instead.
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_schema_create",
                entity_type=entity_type,
                definition={
                    "about": "Example schema",
                    type_field: "user",
                    "fields": [{"field_name": "title"}],
                },
            )

        assert "collides with an existing route" in str(
            err.value.error_dict["schema_type"]
        )

    def test_dataset_type_colliding_with_core_blueprint_is_rejected(
        self, schema_definition
    ):
        definition = {**schema_definition, "dataset_type": "user"}

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_create", definition=definition)

        assert "collides with an existing route" in str(
            err.value.error_dict["schema_type"]
        )

    def test_dataset_schema_can_override_the_builtin_dataset_type(
        self, schema_definition
    ):
        # a schema named after the built-in type it customises must still be
        # allowed even though "dataset"/"dataset_resource" blueprints exist
        # at runtime -- CKAN routes those through its own blueprint, it never
        # registers a per-type one for them
        definition = {**schema_definition, "dataset_type": "dataset"}

        result = helpers.call_action("scheming_schema_create", definition=definition)

        assert result["schema_type"] == "dataset"

    def test_dataset_type_ending_in_resource_is_rejected(self, schema_definition):
        # "_resource" is the suffix CKAN appends to build a type-specific
        # resource blueprint name; a real type named that way collides with
        # it (see build_dynamic_type_url) and can misroute URLs for either
        # type, or crash schema rendering outright
        definition = {**schema_definition, "dataset_type": "test-type_resource"}

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_create", definition=definition)

        assert "must not end with '_resource'" in str(
            err.value.error_dict["definition"]
        )

    def test_empty_definition_is_rejected(self):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_create", definition={})

        assert "<root>" in str(err.value.error_dict["definition"])

    def test_definition_with_invalid_field_is_rejected(self, schema_definition):
        definition = {
            **schema_definition,
            "dataset_fields": [{"label": "No field_name here"}],
        }

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_schema_create",
                definition=definition,
            )

        assert "dataset_fields/0" in str(err.value.error_dict["definition"])

    def test_schema_that_fails_to_render_is_rejected(self, schema_definition):
        # select.html needs choices/choices_helper to iterate over; without
        # one it blows up mid-render instead of failing validation
        definition = {
            **schema_definition,
            "dataset_fields": [
                *schema_definition["dataset_fields"],
                {"field_name": "broken", "form_snippet": "select.html"},
            ],
        }

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_create", definition=definition)

        assert "cannot be rendered" in str(err.value.error_dict["definition"]).lower()
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 0


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestSchemingSchemaUpdate:
    def test_update_changes_definition(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "title"}, {"field_name": "notes"}],
        }
        result = helpers.call_action(
            "scheming_schema_update",
            definition=updated,
        )

        assert result["definition"] == updated

        row = SchemingSchemaVersion.head("dataset", "test-type")
        assert row
        assert row.definition == updated

    def test_update_with_unchanged_definition_is_a_noop(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        result = helpers.call_action(
            "scheming_schema_update",
            definition=schema_definition,
        )

        assert result["version"] == 1
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1

    def test_update_with_unchanged_definition_still_logs_activity(
        self, schema_definition
    ):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        before = SchemingSchemaActivity.count_history("dataset", "test-type")

        helpers.call_action(
            "scheming_schema_update",
            definition=schema_definition,
        )

        after = SchemingSchemaActivity.count_history("dataset", "test-type")
        assert after == before + 1

    def test_update_with_unchanged_definition_does_not_fork_pinned_version(
        self, schema_definition
    ):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        factories.Dataset(type="test-type")  # locks/pins version 1

        result = helpers.call_action(
            "scheming_schema_update",
            definition=schema_definition,
        )

        assert result["version"] == 1
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1

    def test_update_missing_schema_is_rejected(self, schema_definition):
        with pytest.raises(tk.ObjectNotFound):
            helpers.call_action(
                "scheming_schema_update",
                definition=schema_definition,
            )

    def test_update_with_invalid_definition_is_rejected(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_schema_update", definition={})
        assert "<root>" in str(err.value.error_dict["definition"])

    def test_update_missing_definition_is_rejected(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_schema_update")


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingSchemaDelete:
    def test_delete_removes_schema(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        result = helpers.call_action("scheming_schema_delete", schema_type="test-type")

        assert result is True
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 0

    def test_delete_only_removes_requested_schema_type(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        SchemingSchemaVersion.create("dataset", "other-type", schema_definition)

        helpers.call_action("scheming_schema_delete", schema_type="other-type")

        assert SchemingSchemaVersion.head_version("dataset", "other-type") == 0
        assert SchemingSchemaVersion.head("dataset", "test-type")

    def test_delete_missing_schema_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_schema_delete", schema_type="test-type")

    def test_delete_missing_schema_type_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_schema_delete")

    def test_delete_is_rejected_when_packages_of_type_exist(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        factories.Dataset(type="test-type")

        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_schema_delete", schema_type="test-type")

        assert SchemingSchemaVersion.head("dataset", "test-type")

    def test_delete_clears_stale_pins_from_purged_datasets(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        dataset = factories.Dataset(type="test-type")
        assert SchemingSchemaPin.get("dataset", dataset["id"])

        helpers.call_action("dataset_purge", id=dataset["id"])
        # nothing removes the pin when its dataset is purged
        assert SchemingSchemaPin.get("dataset", dataset["id"])

        result = helpers.call_action("scheming_schema_delete", schema_type="test-type")

        assert result is True
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 0
        assert SchemingSchemaPin.get("dataset", dataset["id"]) is None

    def test_delete_unsupported_entity_type(self):
        with pytest.raises(tk.ValidationError, match="Value must be one of"):
            helpers.call_action(
                "scheming_schema_delete", schema_type="test-type", entity_type="study"
            )


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestSchemingPresetCreate:
    def test_create_returns_preset_dict(self, preset_definition):
        result = helpers.call_action(
            "scheming_preset_create",
            preset_name=preset_definition["preset_name"],
            values=preset_definition["values"],
        )

        assert result["preset_name"] == "test-preset"
        assert result["values"] == preset_definition["values"]
        assert result["updated"]

    def test_created_preset_is_persisted(self, preset_definition):
        helpers.call_action(
            "scheming_preset_create",
            preset_name=preset_definition["preset_name"],
            values=preset_definition["values"],
        )

        row = SchemingPreset.get("test-preset")
        assert row
        assert row.values == preset_definition["values"]

    def test_duplicate_preset_is_rejected(self, preset_definition):
        helpers.call_action(
            "scheming_preset_create",
            preset_name="test-preset",
            values=preset_definition["values"],
        )

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create",
                preset_name="test-preset",
                values=preset_definition["values"],
            )

        assert "already exists" in str(err.value.error_dict["preset_name"])

    def test_missing_args_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_preset_create")

    def test_missing_preset_name_is_rejected(self, preset_definition):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create", values=preset_definition["values"]
            )

        assert "preset_name" in err.value.error_dict

    def test_missing_values_is_rejected(self):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_preset_create", preset_name="test-preset")

        assert "values" in err.value.error_dict

    def test_invalid_values_is_rejected(self):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create",
                preset_name="test-preset",
                values={"repeating_subfields": "notalist"},
            )

        assert "values" in str(err.value.error_dict["values"])

    def test_self_reference_on_a_not_yet_created_preset_is_rejected(self):
        # "test-preset" isn't registered yet, so it can't be its own base
        # either way: caught by the preset enum, not the cycle resolver
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create",
                preset_name="test-preset",
                values={"preset": "test-preset"},
            )

        assert "is not one of" in str(err.value.error_dict["values"])

    def test_unknown_base_preset_is_rejected(self):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create",
                preset_name="test-preset",
                values={"preset": "not-a-real-preset"},
            )

        assert "not-a-real-preset" in str(err.value.error_dict["values"])

    def test_base_on_builtin_preset_is_accepted(self):
        result = helpers.call_action(
            "scheming_preset_create",
            preset_name="test-preset",
            values={"preset": "title"},
        )

        assert result["values"] == {"preset": "title"}

    def test_preset_that_fails_to_render_is_rejected(self):
        # select.html needs choices/choices_helper to iterate over; without
        # one it blows up mid-render instead of failing validation
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_create",
                preset_name="test-preset",
                values={"form_snippet": "select.html"},
            )

        assert "failed to render" in str(err.value.error_dict["values"]).lower()
        assert SchemingPreset.get("test-preset") is None

    def test_name_shadowing_a_builtin_preset_is_accepted(self):
        # deliberate override, same as a DB schema overriding a file schema
        # of the same type: no uniqueness check against static presets
        result = helpers.call_action(
            "scheming_preset_create",
            preset_name="title",
            values={"validators": "not_empty unicode_safe"},
        )

        assert result["preset_name"] == "title"
        assert result["values"] == {"validators": "not_empty unicode_safe"}


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestSchemingPresetUpdate:
    def test_update_changes_values(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        result = helpers.call_action(
            "scheming_preset_update",
            preset_name="test-preset",
            values={"form_snippet": "text.html"},
        )

        assert result["values"] == {"form_snippet": "text.html"}

        row = SchemingPreset.get("test-preset")
        assert row
        assert row.values == {"form_snippet": "text.html"}

    def test_update_missing_preset_is_rejected(self, preset_definition):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_preset_update",
                preset_name="test-preset",
                values=preset_definition["values"],
            )

    def test_update_with_invalid_values_is_rejected(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_update",
                preset_name="test-preset",
                values={"repeating_subfields": "notalist"},
            )

        assert "values" in str(err.value.error_dict["values"])

    def test_update_missing_values_is_rejected(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_preset_update", preset_name="test-preset")

    def test_update_creating_a_cycle_is_rejected(self, preset_definition):
        # "test-preset" starts with no base, and "a" bases on it, so both
        # currently resolve fine; editing "test-preset" to base on "a" is
        # what closes the loop
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        scheming_factories.Preset(preset_name="a", values={"preset": "test-preset"})

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_preset_update",
                preset_name="test-preset",
                values={"preset": "a"},
            )

        assert "cycle" in str(err.value.error_dict["values"]).lower()
        row = SchemingPreset.get("test-preset")
        assert row
        assert row.values == preset_definition["values"]


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingPresetDelete:
    def test_delete_removes_preset(self, preset_definition):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )

        result = helpers.call_action(
            "scheming_preset_delete", preset_name="test-preset"
        )

        assert result is True
        assert SchemingPreset.get("test-preset") is None

    def test_delete_missing_preset_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_preset_delete", preset_name="test-preset")

    def test_delete_missing_preset_name_is_rejected(self):
        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_preset_delete")

    def test_delete_is_rejected_when_another_preset_bases_on_it(
        self, preset_definition
    ):
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        scheming_factories.Preset(
            preset_name="dependent-preset", values={"preset": "test-preset"}
        )

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_preset_delete", preset_name="test-preset")

        assert "dependent-preset" in str(err.value.error_dict["preset_name"])
        assert SchemingPreset.get("test-preset")

    def test_delete_is_rejected_when_used_by_a_schema(
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

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action("scheming_preset_delete", preset_name="test-preset")

        assert "test-type" in str(err.value.error_dict["preset_name"])
        assert SchemingPreset.get("test-preset")
