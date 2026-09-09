from __future__ import annotations

from typing import Any

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests import factories, helpers

from ckanext.scheming.plugins import SchemingDatasetsPlugin

from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.model import (
    SchemingSchemaPin,
    SchemingSchemaVersion,
    SchemingState,
)
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.schema_migration.model import (
    MigrationRun,
    MigrationRunItem,
    SchemaMigration,
)

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic"),
    pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context"),
]

SCHEMA_TYPE = "test-type"


def definition(*fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "about": "Example schema",
        "dataset_type": SCHEMA_TYPE,
        "dataset_fields": list(fields),
        "resource_fields": [{"field_name": "url"}],
    }


def create_v1(*fields: dict[str, Any]) -> SchemingSchemaVersion:
    row = SchemingSchemaVersion.create("dataset", SCHEMA_TYPE, definition(*fields))
    _publish()
    return row


@pytest.fixture
def v1() -> SchemingSchemaVersion:
    return create_v1({"field_name": "old_name"})


def lock_v2(*fields: dict[str, Any]) -> SchemingSchemaVersion:
    """Lock v2 and publish it, the way a real schema update plus request does."""
    row = SchemingSchemaVersion.lock("dataset", SCHEMA_TYPE, definition(*fields))
    SchemingState.bump("dataset")
    model.Session.commit()
    _publish()
    return row


def _publish() -> None:
    """Make the newest schema live, as the next request would.

    Touching ``_expanded_schemas`` forces the merge now, which is also what
    registers the dataset type with ``lookup_package_plugin``.
    """
    sync.forget_request_check()
    SchemingDatasetsPlugin.instance._expanded_schemas  # noqa: B018


def store_mapping(mapping: dict[str, Any], to_version: int = 2) -> SchemaMigration:
    return SchemaMigration.save(
        "dataset", SCHEMA_TYPE, 1, to_version, mapping, "tester"
    )


def copy_mapping(
    target: str, source: str, dropped: list[str] | None = None
) -> dict[str, Any]:
    mapping = mapping_lib.empty()
    mapping["dataset_fields"][target] = {"action": "copy", "source": source}
    mapping["dropped"]["dataset_fields"] = dropped or []
    return mapping


class TestSingleDatasetMigration:
    def test_a_renamed_field_carries_its_value_over(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )

        migrated = helpers.call_action("package_show", id=dataset["id"])

        assert migrated["new_name"] == "kept"
        assert "old_name" not in migrated

    def test_the_pin_moves_to_the_target_version(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )

        pin = SchemingSchemaPin.get("dataset", dataset["id"])

        assert pin.version == 2

    def test_a_single_apply_returns_a_finished_run(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )

        assert run["status"] == MigrationRun.FINISHED
        assert run["total"] == 1
        assert run["ok_count"] == 1

    def test_the_recorded_changes_hold_the_discarded_value(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="lost")
        lock_v2({"field_name": "new_name"})

        mapping = mapping_lib.empty()
        mapping["dropped"]["dataset_fields"] = ["old_name"]
        mapping["dataset_fields"]["new_name"] = {"action": "drop"}
        store_mapping(mapping)

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )
        item = MigrationRunItem.for_run(run["id"])[0]

        assert item.changes["dataset"]["old_name"]["before"] == "lost"

    def test_migrating_twice_skips_the_second_time(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        for _ in range(2):
            run = helpers.call_action(
                "scheming_migration_apply",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
                id=dataset["id"],
            )

        assert run["skipped_count"] == 1
        assert run["ok_count"] == 0


class TestFailedMigration:
    def test_a_dataset_failing_validation_keeps_its_pin(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "required_field", "validators": "not_empty"})

        mapping = mapping_lib.empty()
        mapping["dropped"]["dataset_fields"] = ["old_name"]
        mapping["dataset_fields"]["required_field"] = {"action": "drop"}
        store_mapping(mapping)

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )

        assert run["failed_count"] == 1
        assert SchemingSchemaPin.get("dataset", dataset["id"]).version == 1

    def test_a_failing_dataset_keeps_its_old_data(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "required_field", "validators": "not_empty"})

        mapping = mapping_lib.empty()
        mapping["dropped"]["dataset_fields"] = ["old_name"]
        mapping["dataset_fields"]["required_field"] = {"action": "drop"}
        store_mapping(mapping)

        helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )

        shown = helpers.call_action("package_show", id=dataset["id"])

        assert shown["old_name"] == "kept"


class TestDryRun:
    def test_a_valid_migration_passes_its_dry_run(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
            dry_run=True,
        )

        assert run["failed_count"] == 0
        assert run["ok_count"] == 1

    def test_a_dry_run_writes_an_item_but_no_dataset_change(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "new_name"})
        store_mapping(copy_mapping("new_name", "old_name", dropped=["old_name"]))

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
            dry_run=True,
        )

        assert run["dry_run"] is True
        assert len(MigrationRunItem.for_run(run["id"])) == 1
        assert SchemingSchemaPin.get("dataset", dataset["id"]).version == 1
        shown = helpers.call_action("package_show", id=dataset["id"])

        assert shown["old_name"] == "kept"


class TestValueMapping:
    @pytest.fixture
    def themed_v1(self) -> SchemingSchemaVersion:
        return create_v1(
            {"field_name": "theme", "choices": [{"value": "a"}, {"value": "b"}]}
        )

    def test_a_value_map_rewrites_a_choice_that_no_longer_exists(self, themed_v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, theme="b")
        lock_v2({"field_name": "theme", "choices": [{"value": "a"}]})

        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["theme"] = {
            "action": "copy",
            "source": "theme",
            "value_map": {"b": "a"},
        }
        store_mapping(mapping)

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
        )
        item = MigrationRunItem.for_run(run["id"])[0]
        shown = helpers.call_action("package_show", id=dataset["id"])

        assert run["ok_count"] == 1, item.errors
        assert shown.get("theme") == "a", item.changes


class TestGuidedValues:
    def test_per_dataset_values_answer_a_manual_field(self, v1):
        dataset = factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2({"field_name": "old_name"}, {"field_name": "quality"})

        mapping = copy_mapping("old_name", "old_name")
        mapping["dataset_fields"]["quality"] = {"action": "manual"}
        store_mapping(mapping)

        run = helpers.call_action(
            "scheming_migration_apply",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            id=dataset["id"],
            values={"dataset_fields": {"quality": "high"}},
        )
        item = MigrationRunItem.for_run(run["id"])[0]
        shown = helpers.call_action("package_show", id=dataset["id"])

        assert run["ok_count"] == 1, item.errors
        assert shown.get("quality") == "high", {
            "changes": item.changes,
            "extras": shown.get("extras"),
        }

    def test_bulk_refuses_while_a_field_is_left_to_the_guided_form(self, v1):
        factories.Dataset(type=SCHEMA_TYPE, old_name="kept")
        lock_v2(
            {"field_name": "old_name"},
            {"field_name": "quality", "validators": "not_empty"},
        )

        mapping = copy_mapping("old_name", "old_name")
        mapping["dataset_fields"]["quality"] = {"action": "manual"}
        store_mapping(mapping)

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_migration_apply",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
            )

        assert "per dataset" in str(err.value.error_dict)
