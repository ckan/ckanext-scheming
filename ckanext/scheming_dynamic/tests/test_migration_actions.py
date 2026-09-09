from __future__ import annotations

from typing import Any

import pytest

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests import factories, helpers

from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.model import SchemingSchemaVersion, SchemingState
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.schema_migration.model import (
    MigrationRun,
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


@pytest.fixture
def v1() -> SchemingSchemaVersion:
    return SchemingSchemaVersion.create(
        "dataset", SCHEMA_TYPE, definition({"field_name": "old_name"})
    )


def lock_v2(*fields: dict[str, Any]) -> SchemingSchemaVersion:
    """Lock v2 and make it live, the way a real schema update does."""
    row = SchemingSchemaVersion.lock("dataset", SCHEMA_TYPE, definition(*fields))
    SchemingState.bump("dataset")
    model.Session.commit()
    sync.forget_request_check()
    return row


@pytest.fixture
def two_versions(v1: SchemingSchemaVersion) -> None:
    """v2 keeps ``old_name`` and adds a required field nothing can fill."""
    lock_v2(
        {"field_name": "old_name"},
        {"field_name": "quality", "validators": "not_empty"},
    )


def complete_mapping() -> dict[str, Any]:
    mapping = mapping_lib.empty()
    mapping["dataset_fields"]["old_name"] = {"action": "copy", "source": "old_name"}
    mapping["dataset_fields"]["quality"] = {"action": "constant", "value": "high"}
    return mapping


class TestVersionPairValidation:
    def test_the_same_version_twice_is_rejected(self, two_versions):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_migration_mapping_show",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=1,
            )

    def test_a_version_that_does_not_exist_is_rejected(self, two_versions):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_migration_mapping_show",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=99,
            )

    def test_an_unknown_schema_type_is_rejected(self, two_versions):
        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_migration_mapping_show",
                schema_type="no-such-type",
                from_version=1,
                to_version=2,
            )


class TestMappingShow:
    def test_it_suggests_a_mapping_when_nothing_is_stored(self, two_versions):
        result = helpers.call_action(
            "scheming_migration_mapping_show",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
        )

        assert result["stored"] is None
        assert result["mapping"] == result["suggested"]

    def test_it_reports_what_still_needs_deciding(self, two_versions):
        result = helpers.call_action(
            "scheming_migration_mapping_show",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
        )

        assert [p["field_name"] for p in result["unresolved"]] == ["quality"]

    def test_a_stored_mapping_wins_over_the_suggestion(self, two_versions):
        mapping = complete_mapping()
        SchemaMigration.save("dataset", SCHEMA_TYPE, 1, 2, mapping, "tester")

        result = helpers.call_action(
            "scheming_migration_mapping_show",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
        )

        assert result["stored"] is not None
        assert result["mapping"] == mapping
        assert result["unresolved"] == []


class TestMappingUpdate:
    def test_a_mapping_naming_an_unknown_target_field_is_rejected(self, two_versions):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["nope"] = {"action": "drop"}

        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_migration_mapping_update",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
                mapping=mapping,
            )

    def test_saving_twice_updates_the_same_row(self, two_versions):
        mapping = mapping_lib.empty()

        for _ in range(2):
            helpers.call_action(
                "scheming_migration_mapping_update",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
                mapping=mapping,
            )

        assert SchemaMigration.get("dataset", SCHEMA_TYPE, 1, 2) is not None


class TestApplyGuards:
    def test_applying_without_a_stored_mapping_is_rejected(self, two_versions):
        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_migration_apply",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
            )

        assert "No mapping stored" in str(err.value.error_dict)

    def test_applying_with_open_questions_is_rejected(self, two_versions):
        SchemaMigration.save(
            "dataset", SCHEMA_TYPE, 1, 2, mapping_lib.empty(), "tester"
        )

        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_migration_apply",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
            )

    def test_a_second_run_on_an_active_pair_is_refused(self, two_versions):
        mapping = complete_mapping()
        SchemaMigration.save("dataset", SCHEMA_TYPE, 1, 2, mapping, "tester")

        MigrationRun.create(
            entity_type="dataset",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            mapping_used=mapping,
            status=MigrationRun.RUNNING,
            dry_run=False,
            total=0,
            actor="tester",
        )

        with pytest.raises(tk.ValidationError) as err:
            helpers.call_action(
                "scheming_migration_apply",
                schema_type=SCHEMA_TYPE,
                from_version=1,
                to_version=2,
            )

        assert "already running" in str(err.value.error_dict)


class TestStatus:
    def test_it_counts_datasets_behind_the_live_version(self, v1):
        factories.Dataset(type=SCHEMA_TYPE, old_name="a")
        lock_v2({"field_name": "old_name"})

        rows = helpers.call_action("scheming_migration_status")
        row = next(r for r in rows if r["schema_type"] == SCHEMA_TYPE)

        assert row["live_version"] == 2
        assert row["behind"] == 1
        assert row["distribution"] == {1: 1}


class TestRunCancel:
    def test_a_finished_run_cannot_be_cancelled(self, v1):
        run = MigrationRun.create(
            entity_type="dataset",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            mapping_used={},
            status=MigrationRun.FINISHED,
            dry_run=False,
            total=0,
            actor="tester",
        )

        with pytest.raises(tk.ValidationError):
            helpers.call_action("scheming_migration_run_cancel", id=run.id)

    def test_cancelling_an_active_run_frees_the_version_pair(self, v1):
        run = MigrationRun.create(
            entity_type="dataset",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            mapping_used={},
            status=MigrationRun.RUNNING,
            dry_run=False,
            total=0,
            actor="tester",
        )

        helpers.call_action("scheming_migration_run_cancel", id=run.id)

        assert MigrationRun.active("dataset", SCHEMA_TYPE, 1, 2) is None

    def test_cancelling_stamps_the_finish_time(self, v1):
        run = MigrationRun.create(
            entity_type="dataset",
            schema_type=SCHEMA_TYPE,
            from_version=1,
            to_version=2,
            mapping_used={},
            status=MigrationRun.RUNNING,
            dry_run=False,
            total=0,
            actor="tester",
        )

        assert run.finished is None

        result = helpers.call_action("scheming_migration_run_cancel", id=run.id)

        assert result["status"] == MigrationRun.CANCELLED
        assert run.status == MigrationRun.CANCELLED
        assert run.finished is not None


class TestAuth:
    @pytest.mark.parametrize(
        "action",
        [
            "scheming_migration_status",
            "scheming_migration_mapping_show",
            "scheming_migration_mapping_update",
            "scheming_migration_mapping_delete",
            "scheming_migration_apply",
            "scheming_migration_run_list",
            "scheming_migration_run_show",
            "scheming_migration_run_cancel",
        ],
    )
    def test_a_normal_user_is_refused(self, action):
        user = factories.User()

        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(action, context={"user": user["name"], "model": None})
