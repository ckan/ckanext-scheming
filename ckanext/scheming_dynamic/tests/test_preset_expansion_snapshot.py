"""A pinned/locked schema version must keep validating and rendering the
way it did when it was locked, even after a preset it used gets edited
later. Covers the ``SchemingSchemaVersion.expanded`` snapshot and the two
read paths that rely on it: ``sync.pinned_expanded_schema`` (validation,
forms) and ``schema_migration.apply.expanded_definition`` (migrations).
"""

from __future__ import annotations

from typing import Any

import pytest

from ckan import model
from ckan.tests import factories, helpers

from ckanext.scheming.plugins import SchemingDatasetsPlugin, _SchemingMixin
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.model import SchemingSchemaPin, SchemingSchemaVersion
from ckanext.scheming_dynamic.schema_migration.apply import expanded_definition
from ckanext.scheming_dynamic.tests import factories as dynamic_factories

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


def _publish() -> None:
    """Make the newest schema/preset state live, as the next request would."""
    sync.forget_request_check()
    SchemingDatasetsPlugin.instance._expanded_schemas  # noqa: B018


class TestLockSnapshotsExpansion:
    def test_lock_stores_expanded_alongside_definition(self):
        dynamic_factories.Preset(
            preset_name="snap-preset", values={"validators": "not_empty"}
        )
        row = SchemingSchemaVersion.create(
            "dataset",
            SCHEMA_TYPE,
            definition({"field_name": "notes", "preset": "snap-preset"}),
        )

        assert row.expanded is not None
        [field] = row.expanded["dataset_fields"]
        assert field["validators"] == "not_empty"

    def test_in_place_head_overwrite_refreshes_expanded(self):
        dynamic_factories.Preset(
            preset_name="snap-preset", values={"validators": "not_empty"}
        )
        helpers.call_action(
            "scheming_schema_create",
            definition=definition({"field_name": "notes", "preset": "snap-preset"}),
        )

        updated = definition({"field_name": "renamed", "preset": "snap-preset"})
        row_dict = helpers.call_action(
            "scheming_schema_update", schema_type=SCHEMA_TYPE, definition=updated
        )

        head = SchemingSchemaVersion.get("dataset", SCHEMA_TYPE, row_dict["version"])
        [field] = head.expanded["dataset_fields"]
        assert field["field_name"] == "renamed"
        assert field["validators"] == "not_empty"


class TestPinnedExpandedSchemaImmuneToPresetEdits:
    def test_pinned_version_keeps_its_validators_after_preset_edit(self):
        preset = dynamic_factories.Preset(
            preset_name="drift-preset", values={"validators": "not_empty"}
        )
        helpers.call_action(
            "scheming_schema_create",
            definition=definition({"field_name": "notes", "preset": "drift-preset"}),
        )
        _publish()

        dataset = factories.Dataset(type=SCHEMA_TYPE)
        v1 = SchemingSchemaVersion.head_version("dataset", SCHEMA_TYPE)

        # move the schema to v2 so the dataset's pin (still v1) differs from head
        helpers.call_action(
            "scheming_schema_update",
            schema_type=SCHEMA_TYPE,
            definition=definition(
                {"field_name": "notes", "preset": "drift-preset"},
                {"field_name": "extra"},
            ),
        )
        _publish()

        assert SchemingSchemaPin.get("dataset", dataset["id"]).version == v1

        # edit the preset the pinned version used -- this must not change
        # what the pinned dataset validates against
        preset.update_values({"validators": "ignore_missing"})
        sync.forget_request_check()
        sync.ensure_presets_synced()

        # the live registry did move -- proves the assertion below isn't
        # passing merely because the edit never took effect
        assert _SchemingMixin._presets["drift-preset"] == {
            "validators": "ignore_missing"
        }

        pinned = sync.pinned_expanded_schema("dataset", SCHEMA_TYPE, dataset["id"])
        assert pinned is not None
        [notes_field] = [
            f for f in pinned["dataset_fields"] if f["field_name"] == "notes"
        ]
        assert notes_field["validators"] == "not_empty"

    def test_process_cache_does_not_leak_the_pre_edit_expansion_after_restart(self):
        """Even a fresh process (empty cache) must read the locked snapshot,
        not re-expand against the now-different preset registry."""
        preset = dynamic_factories.Preset(
            preset_name="drift-preset", values={"validators": "not_empty"}
        )
        helpers.call_action(
            "scheming_schema_create",
            definition=definition({"field_name": "notes", "preset": "drift-preset"}),
        )
        _publish()

        dataset = factories.Dataset(type=SCHEMA_TYPE)
        helpers.call_action(
            "scheming_schema_update",
            schema_type=SCHEMA_TYPE,
            definition=definition(
                {"field_name": "notes", "preset": "drift-preset"},
                {"field_name": "extra"},
            ),
        )
        _publish()

        preset.update_values({"validators": "ignore_missing"})
        sync.forget_request_check()
        sync.ensure_presets_synced()
        assert _SchemingMixin._presets["drift-preset"] == {
            "validators": "ignore_missing"
        }

        # simulate a fresh worker: nothing cached yet
        sync._expanded_version_cache.clear()

        pinned = sync.pinned_expanded_schema("dataset", SCHEMA_TYPE, dataset["id"])
        [notes_field] = [
            f for f in pinned["dataset_fields"] if f["field_name"] == "notes"
        ]
        assert notes_field["validators"] == "not_empty"

    def test_row_predating_the_snapshot_still_falls_back_to_live_expansion(self):
        """Rows locked before ``expanded`` existed have it as NULL; the read
        paths must keep working (live re-expansion) for those, unchanged
        from the old behaviour."""
        preset = dynamic_factories.Preset(
            preset_name="drift-preset", values={"validators": "not_empty"}
        )
        row = SchemingSchemaVersion.create(
            "dataset",
            SCHEMA_TYPE,
            definition({"field_name": "notes", "preset": "drift-preset"}),
        )
        row.expanded = None  # simulate a pre-migration row
        model.Session.commit()
        _publish()

        dataset = factories.Dataset(type=SCHEMA_TYPE)
        helpers.call_action(
            "scheming_schema_update",
            schema_type=SCHEMA_TYPE,
            definition=definition(
                {"field_name": "notes", "preset": "drift-preset"},
                {"field_name": "extra"},
            ),
        )
        _publish()

        preset.update_values({"validators": "ignore_missing"})
        # ensure_presets_synced() no-ops once per request; without this, the
        # in-request registry (already read by the _publish() calls above)
        # would still hold the pre-edit value.
        sync.forget_request_check()
        sync.ensure_presets_synced()

        pinned = sync.pinned_expanded_schema("dataset", SCHEMA_TYPE, dataset["id"])
        [notes_field] = [
            f for f in pinned["dataset_fields"] if f["field_name"] == "notes"
        ]
        # unlike the snapshot case, a NULL-expanded row re-expands live
        assert notes_field["validators"] == "ignore_missing"


class TestMigrationApplyExpandedDefinitionUsesSnapshot:
    def test_expanded_definition_reads_the_locked_snapshot(self):
        preset = dynamic_factories.Preset(
            preset_name="drift-preset", values={"validators": "not_empty"}
        )
        row = SchemingSchemaVersion.create(
            "dataset",
            SCHEMA_TYPE,
            definition({"field_name": "notes", "preset": "drift-preset"}),
        )

        preset.update_values({"validators": "ignore_missing"})
        sync.ensure_presets_synced()

        expanded = expanded_definition("dataset", SCHEMA_TYPE, row.version)
        [field] = expanded["dataset_fields"]
        assert field["validators"] == "not_empty"
