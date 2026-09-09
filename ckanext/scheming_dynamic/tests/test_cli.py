from __future__ import annotations

import json

import pytest

from ckan.cli.cli import ckan
from ckan.tests import factories, helpers

from ckanext.scheming.plugins import SchemingDatasetsPlugin
from ckanext.scheming_dynamic.model import (
    SchemingSchemaPin,
    SchemingSchemaVersion,
)

STATIC_DATASET_SCHEMA_TYPE = "dataset"


def write_schema(tmp_path, data, name="schema.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def static_schema(with_plugins):
    return dict(
        SchemingDatasetsPlugin.instance._static_schemas[STATIC_DATASET_SCHEMA_TYPE]
    )


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "with_extended_cli")
class TestSchemaCommand:
    def test_default_type_is_dataset(self, cli):
        result = cli.invoke(ckan, ["scheming-dynamic", "validation-schema"])
        assert not result.exit_code, result.output
        built = json.loads(result.output)
        assert built["required"] == [
            "about",
            "dataset_type",
            "dataset_fields",
            "resource_fields",
        ]

    @pytest.mark.parametrize(
        ("schema_type", "required_key"),
        [("group", "group_type"), ("organization", "organization_type")],
    )
    def test_type_option(self, cli, schema_type, required_key):
        result = cli.invoke(
            ckan, ["scheming-dynamic", "validation-schema", "--type", schema_type]
        )
        assert not result.exit_code, result.output
        built = json.loads(result.output)
        assert required_key in built["required"]

    def test_invalid_type_option_is_rejected(self, cli):
        result = cli.invoke(
            ckan, ["scheming-dynamic", "validation-schema", "--type", "not-a-type"]
        )
        assert result.exit_code != 0


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "with_extended_cli")
class TestValidateCommand:
    def test_valid_schema_exits_zero(self, cli, tmp_path, schema_definition):
        path = write_schema(tmp_path, schema_definition)
        result = cli.invoke(ckan, ["scheming-dynamic", "validate", str(path)])
        assert result.exit_code == 0, result.output
        assert "OK - no schema violations" in result.output

    def test_invalid_schema_exits_nonzero(self, cli, tmp_path, schema_definition):
        data = {
            **schema_definition,
            "dataset_fields": [{"field_name": "x", "preset": "not_a_real_preset"}],
        }
        path = write_schema(tmp_path, data)
        result = cli.invoke(ckan, ["scheming-dynamic", "validate", str(path)])
        assert result.exit_code == 1
        assert "not_a_real_preset" in result.output

    def test_multiple_files_are_all_reported(self, cli, tmp_path, schema_definition):
        valid = write_schema(tmp_path, schema_definition, "valid.json")
        invalid = write_schema(tmp_path, {"about": "Example schema"}, "invalid.json")

        result = cli.invoke(
            ckan, ["scheming-dynamic", "validate", str(valid), str(invalid)]
        )

        assert result.exit_code == 1
        assert "OK - no schema violations" in result.output
        assert "is a required property" in result.output

    def test_missing_file_argument_is_rejected(self, cli):
        result = cli.invoke(ckan, ["scheming-dynamic", "validate"])
        assert result.exit_code != 0

    def test_nonexistent_file_is_rejected(self, cli):
        result = cli.invoke(
            ckan, ["scheming-dynamic", "validate", "/no/such/file.yaml"]
        )
        assert result.exit_code != 0


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_extended_cli")
class TestSyncCommand:
    def test_creates_schema_and_locks_version_one(self, cli, static_schema):
        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Created dynamic schema" in result.output
        assert "version 1" in result.output

        head = SchemingSchemaVersion.head("dataset", STATIC_DATASET_SCHEMA_TYPE)
        assert head
        assert head.definition == static_schema

        assert (
            SchemingSchemaVersion.head_version("dataset", STATIC_DATASET_SCHEMA_TYPE)
            == 1
        )
        version = SchemingSchemaVersion.get("dataset", STATIC_DATASET_SCHEMA_TYPE, 1)
        assert version
        assert version.definition == static_schema

    def test_rerun_with_unchanged_static_does_nothing(self, cli):
        first = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert first.exit_code == 0, first.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "already matches the static schema" in result.output
        assert (
            SchemingSchemaVersion.head_version("dataset", STATIC_DATASET_SCHEMA_TYPE)
            == 1
        )

    def test_rerun_with_changed_static_locks_new_version(
        self, cli, static_schema, tmp_path, ckan_config
    ):
        schema_path = tmp_path / "dataset.json"
        schema_path.write_text(json.dumps(static_schema))
        ckan_config["scheming.dataset_schemas"] = f"file://{schema_path}"

        first = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert first.exit_code == 0, first.output

        factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)

        updated = {
            **static_schema,
            "dataset_fields": [
                *static_schema["dataset_fields"],
                {"field_name": "extra_field"},
            ],
        }
        schema_path.write_text(json.dumps(updated))

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "now at version 2" in result.output
        assert (
            SchemingSchemaVersion.head_version("dataset", STATIC_DATASET_SCHEMA_TYPE)
            == 2
        )
        v2 = SchemingSchemaVersion.get("dataset", STATIC_DATASET_SCHEMA_TYPE, 2)
        assert v2
        assert v2.definition == updated
        head = SchemingSchemaVersion.head("dataset", STATIC_DATASET_SCHEMA_TYPE)
        assert head
        assert head.definition == updated

    def test_existing_unpinned_schema_is_overwritten_in_place(self, cli, static_schema):
        draft = {**static_schema, "dataset_fields": [{"field_name": "other"}]}
        SchemingSchemaVersion.create("dataset", STATIC_DATASET_SCHEMA_TYPE, draft)

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "now at version 1" in result.output
        assert (
            SchemingSchemaVersion.head_version("dataset", STATIC_DATASET_SCHEMA_TYPE)
            == 1
        )
        version = SchemingSchemaVersion.get("dataset", STATIC_DATASET_SCHEMA_TYPE, 1)
        assert version
        assert version.definition == static_schema

    def test_missing_static_schema_reports_error(self, cli):
        result = cli.invoke(
            ckan,
            ["scheming-dynamic", "sync", "--type", "dataset", "does-not-exist"],
        )

        assert result.exit_code == 1
        assert "No static dataset schema found" in result.output

    def test_sync_unknown_group_schema_type_reports_error(self, cli):
        result = cli.invoke(
            ckan,
            ["scheming-dynamic", "sync", "--type", "group", "test-group"],
        )

        assert result.exit_code != 0
        assert (
            "No static group schema found" in result.output
            or "No scheming plugin for 'group'" in result.output
        )


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_extended_cli")
class TestPinCommand:
    def test_no_locked_version_reports_error(self, cli):
        # STATIC_DATASET_SCHEMA_TYPE was never synced/created, so it has no
        # scheming_schema_version rows at all yet
        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 1
        assert "No locked version" in result.output

    def test_version_does_not_exist_reports_error(self, cli):
        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
                "-v",
                "99",
            ],
        )

        assert result.exit_code == 1
        assert "Version 99 does not exist" in result.output

    def test_pins_legacy_unpinned_dataset_to_head(self, cli):
        # created before the dynamic schema row exists: `create()`'s
        # ensure_pinned hook bails out, leaving it genuinely unpinned --
        # exactly the "existing packages" scenario `sync`/`pin` are for.
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        assert SchemingSchemaPin.get("dataset", legacy["id"]) is None

        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Pinned 1 dataset(s) to version 1" in result.output
        pin = SchemingSchemaPin.get("dataset", legacy["id"])
        assert pin
        assert pin.version == 1

    def test_dry_run_reports_without_pinning(self, cli):
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)

        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Would pin 1 dataset(s) to version 1" in result.output
        assert SchemingSchemaPin.get("dataset", legacy["id"]) is None

    def test_rerun_pins_nothing_already_pinned(self, cli):
        factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        sync_result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert sync_result.exit_code == 0, sync_result.output
        pin_result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert pin_result.exit_code == 0, pin_result.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Pinned 0 dataset(s)" in result.output

    def test_pin_to_explicit_older_version(self, cli):
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
                "-v",
                "1",
            ],
        )

        assert result.exit_code == 0, result.output
        pin = SchemingSchemaPin.get("dataset", legacy["id"])
        assert pin
        assert pin.version == 1

    def test_validation_failure_is_reported_and_left_unpinned(self, cli, static_schema):
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        # pins to v1, which locks it -- so the edit below forks v2 instead
        # of overwriting v1 in place
        factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)

        updated = {
            **static_schema,
            "dataset_fields": [
                *static_schema["dataset_fields"],
                {"field_name": "brand_new_required", "required": True},
            ],
        }
        site_user = helpers.call_action("get_site_user")
        helpers.call_action(
            "scheming_schema_update",
            context={"user": site_user["name"], "ignore_auth": True},
            definition=updated,
        )
        assert (
            SchemingSchemaVersion.head_version("dataset", STATIC_DATASET_SCHEMA_TYPE)
            == 2
        )

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )

        assert result.exit_code == 1
        assert f"[{legacy['id']}] validation failed" in result.output
        assert "brand_new_required" in result.output
        assert SchemingSchemaPin.get("dataset", legacy["id"]) is None

    def test_dry_run_still_reports_validation_failures(self, cli, static_schema):
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output

        factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)

        updated = {
            **static_schema,
            "dataset_fields": [
                *static_schema["dataset_fields"],
                {"field_name": "brand_new_required", "required": True},
            ],
        }
        site_user = helpers.call_action("get_site_user")
        helpers.call_action(
            "scheming_schema_update",
            context={"user": site_user["name"], "ignore_auth": True},
            definition=updated,
        )

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
                "--dry-run",
            ],
        )

        assert result.exit_code == 1
        assert "1 would fail validation and were left unpinned" in result.output
        assert SchemingSchemaPin.get("dataset", legacy["id"]) is None

    def test_no_validate_pins_despite_failure(self, cli, static_schema):
        legacy = factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)
        setup = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "sync",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
            ],
        )
        assert setup.exit_code == 0, setup.output
        factories.Dataset(type=STATIC_DATASET_SCHEMA_TYPE)

        updated = {
            **static_schema,
            "dataset_fields": [
                *static_schema["dataset_fields"],
                {"field_name": "brand_new_required", "required": True},
            ],
        }
        site_user = helpers.call_action("get_site_user")
        helpers.call_action(
            "scheming_schema_update",
            context={"user": site_user["name"], "ignore_auth": True},
            definition=updated,
        )

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "pin",
                "--type",
                "dataset",
                STATIC_DATASET_SCHEMA_TYPE,
                "--no-validate",
            ],
        )

        assert result.exit_code == 0, result.output
        pin = SchemingSchemaPin.get("dataset", legacy["id"])
        assert pin
        assert pin.version == 2
