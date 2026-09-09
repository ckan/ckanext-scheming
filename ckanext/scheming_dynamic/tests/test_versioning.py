from __future__ import annotations

import pytest

from ckan.tests import factories, helpers

from ckanext.scheming_dynamic.model import (
    SchemingSchemaActivity,
    SchemingSchemaPin,
    SchemingSchemaVersion,
)

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic"),
    pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context"),
]


class TestSchemaActivityLog:
    def test_create_writes_activity_row(self, schema_definition):
        helpers.call_action("scheming_schema_create", definition=schema_definition)

        history = SchemingSchemaActivity.get_history("dataset", "test-type")

        assert len(history) == 1
        assert history[0].action == SchemingSchemaActivity.CREATE
        assert history[0].definition == schema_definition
        assert history[0].version == 1

    def test_edit_before_any_pin_overwrites_version_one(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        updated = {**schema_definition, "dataset_fields": [{"field_name": "notes"}]}
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )

        history = SchemingSchemaActivity.get_history("dataset", "test-type")

        assert len(history) == 1
        assert history[0].action == SchemingSchemaActivity.UPDATE
        assert history[0].version == 1
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1

    def test_delete_writes_activity_row(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        helpers.call_action("scheming_schema_delete", schema_type="test-type")

        history = SchemingSchemaActivity.get_history("dataset", "test-type")

        assert [h.action for h in history] == [SchemingSchemaActivity.DELETE]


class TestSchemaVersioning:
    def test_first_package_locks_version_one(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        dataset = factories.Dataset(type="test-type")

        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1
        pin = SchemingSchemaPin.get("dataset", dataset["id"])
        assert pin
        assert pin.version == 1
        version = SchemingSchemaVersion.get("dataset", "test-type", 1)
        assert version
        assert version.definition == schema_definition

    def test_editing_unpinned_schema_does_not_fork_a_version(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)

        updated = {**schema_definition, "dataset_fields": [{"field_name": "notes"}]}
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )

        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1
        version = SchemingSchemaVersion.get("dataset", "test-type", 1)
        assert version
        assert version.definition == updated

    def test_editing_locked_schema_creates_new_version(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        factories.Dataset(type="test-type")

        updated = {**schema_definition, "dataset_fields": [{"field_name": "notes"}]}
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )

        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 2
        v1 = SchemingSchemaVersion.get("dataset", "test-type", 1)
        v2 = SchemingSchemaVersion.get("dataset", "test-type", 2)
        assert v1
        assert v1.definition == schema_definition
        assert v2
        assert v2.definition == updated

    def test_new_package_after_edit_pins_to_new_version(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        old_dataset = factories.Dataset(type="test-type")

        updated = {**schema_definition, "dataset_fields": [{"field_name": "notes"}]}
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )
        new_dataset = factories.Dataset(type="test-type")

        old_pin = SchemingSchemaPin.get("dataset", old_dataset["id"])
        new_pin = SchemingSchemaPin.get("dataset", new_dataset["id"])
        assert old_pin
        assert old_pin.version == 1
        assert new_pin
        assert new_pin.version == 2

    def test_second_edit_before_any_new_pin_overwrites_the_unlocked_version(
        self, schema_definition
    ):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        factories.Dataset(type="test-type")  # locks version 1

        first_edit = {**schema_definition, "dataset_fields": [{"field_name": "a"}]}
        helpers.call_action(
            "scheming_schema_update", definition=first_edit
        )
        second_edit = {**schema_definition, "dataset_fields": [{"field_name": "b"}]}
        helpers.call_action(
            "scheming_schema_update", definition=second_edit
        )

        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 2
        v2 = SchemingSchemaVersion.get("dataset", "test-type", 2)
        assert v2
        assert v2.definition == second_edit

    def test_old_package_keeps_validating_against_its_pinned_version(
        self, schema_definition
    ):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        old_dataset = factories.Dataset(type="test-type")

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "brand_new_field"}],
        }
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )

        shown = helpers.call_action("package_show", id=old_dataset["id"])

        assert shown["type"] == "test-type"
        assert "brand_new_field" not in shown
        assert shown.get("temporal_coverage", "") == ""


class TestSchemaPinLifecycle:
    def test_deleting_a_package_removes_its_pin(self, schema_definition):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        dataset = factories.Dataset(type="test-type")
        assert SchemingSchemaPin.get("dataset", dataset["id"])

        helpers.call_action("package_delete", id=dataset["id"])

        assert SchemingSchemaPin.get("dataset", dataset["id"]) is None

    def test_schema_can_be_deleted_once_its_packages_are_purged(
        self, schema_definition
    ):
        SchemingSchemaVersion.create("dataset", "test-type", schema_definition)
        dataset = factories.Dataset(type="test-type")

        helpers.call_action("dataset_purge", id=dataset["id"])
        helpers.call_action("scheming_schema_delete", schema_type="test-type")

        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 0
        assert SchemingSchemaPin.get("dataset", dataset["id"]) is None


class TestSchemingSchemaActivityList:
    def test_returns_history_oldest_first(self, schema_definition):
        helpers.call_action("scheming_schema_create", definition=schema_definition)
        updated = {**schema_definition, "dataset_fields": [{"field_name": "notes"}]}
        helpers.call_action(
            "scheming_schema_update", definition=updated
        )

        result = helpers.call_action(
            "scheming_schema_activity_list", schema_type="test-type"
        )

        assert [r["action"] for r in result] == ["create", "update"]

    def test_unknown_schema_type_returns_empty_list(self):
        result = helpers.call_action(
            "scheming_schema_activity_list", schema_type="never-created"
        )

        assert result == []
