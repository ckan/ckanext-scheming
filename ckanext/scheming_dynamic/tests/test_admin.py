from __future__ import annotations

import json
from typing import Any

import pytest
from freezegun import freeze_time

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.tests import factories, helpers

from ckanext.scheming_dynamic.model import (
    SchemingPreset,
    SchemingSchemaActivity,
    SchemingSchemaVersion,
)
from ckanext.scheming_dynamic.tests import factories as scheming_factories

STATUS_OK = 200
STATUS_REDIRECT = 302
STATUS_BAD_REQUEST = 400
STATUS_FORBIDDEN = 403
STATUS_NOT_FOUND = 404

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic"),
    pytest.mark.ckan_config(
        "scheming.dataset_schemas", "ckanext.scheming:ckan_dataset.yaml"
    ),
    pytest.mark.ckan_config("scheming.dataset_fallback", "true"),
    pytest.mark.usefixtures("with_plugins", "clean_db"),
]


def _sysadmin_headers() -> dict[str, str]:
    return {"Authorization": factories.SysadminWithToken()["token"]}


class TestAdminAccess:
    def test_anonymous_is_forbidden(self, app):
        app.get(tk.url_for("scheming_dynamic_admin.index"), status=STATUS_FORBIDDEN)
        app.get(tk.url_for("scheming_dynamic_admin.new"), status=STATUS_FORBIDDEN)
        app.get(
            tk.url_for("scheming_dynamic_admin.presets_index"),
            status=STATUS_FORBIDDEN,
        )
        app.get(
            tk.url_for("scheming_dynamic_admin.preset_new"), status=STATUS_FORBIDDEN
        )

    def test_regular_user_is_forbidden(self, app):
        headers = {"Authorization": factories.UserWithToken()["token"]}

        app.get(
            tk.url_for("scheming_dynamic_admin.index"),
            headers=headers,
            status=STATUS_FORBIDDEN,
        )
        app.get(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=headers,
            status=STATUS_FORBIDDEN,
        )
        app.post(
            tk.url_for("scheming_dynamic_admin.preview"),
            headers=headers,
            data={"definition": "{}"},
            status=STATUS_FORBIDDEN,
        )
        app.get(
            tk.url_for("scheming_dynamic_admin.presets_index"),
            headers=headers,
            status=STATUS_FORBIDDEN,
        )
        app.get(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=headers,
            status=STATUS_FORBIDDEN,
        )
        app.post(
            tk.url_for("scheming_dynamic_admin.preset_preview"),
            headers=headers,
            data={"definition": "{}"},
            status=STATUS_FORBIDDEN,
        )

    def test_sysadmin_sees_the_listing(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.index"), headers=_sysadmin_headers()
        )

        assert resp.status_code == STATUS_OK
        assert "Dynamic schemas" in resp.body

    def test_sysadmin_sees_the_presets_listing(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.presets_index"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "Field presets" in resp.body


class TestSchemaList:
    def test_created_schema_is_listed(self, app, dataset_schema: dict[str, Any]):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.index"), headers=_sysadmin_headers()
        )

        assert "test-type" in resp.body

    def test_empty_listing_shows_hint(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.index"), headers=_sysadmin_headers()
        )

        assert "No dynamic schemas" in resp.body

    def test_unpinned_schema_shows_mutable(self, app, dataset_schema: dict[str, Any]):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.index"), headers=_sysadmin_headers()
        )

        assert "fa-lock-open" in resp.body
        assert 'class="fa fa-lock ' not in resp.body

    def test_pinned_schema_shows_locked_version(
        self, app, dataset_schema: dict[str, Any]
    ):
        factories.Dataset(type="test-type")  # locks/pins version 1

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.index"), headers=_sysadmin_headers()
        )

        assert 'class="fa fa-lock ' in resp.body
        assert "fa-lock-open" not in resp.body


class TestSchemaCreate:
    def test_form_renders(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.new"), headers=_sysadmin_headers()
        )

        assert resp.status_code == STATUS_OK
        assert 'name="definition"' in resp.body

    def test_valid_definition_creates_schema(self, app, schema_definition):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={
                "schema_type": "test-type",
                "definition": json.dumps(schema_definition),
            },
            follow_redirects=False,
        )

        assert resp.status_code == STATUS_REDIRECT
        assert SchemingSchemaVersion.head("dataset", "test-type") is not None

    def test_missing_field_name_is_reported(self, app, schema_definition):
        definition = {**schema_definition, "dataset_fields": [{"label": "No name"}]}

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={
                "schema_type": "test-type",
                "definition": json.dumps(definition),
            },
        )

        assert resp.status_code == STATUS_OK
        assert "is a required property" in resp.body
        assert SchemingSchemaVersion.head("dataset", "test-type") is None

    def test_malformed_json_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={"schema_type": "test-type", "definition": "{not json"},
        )

        assert resp.status_code == STATUS_OK
        assert "Could not parse as valid JSON" in resp.body

    def test_unknown_form_snippet_is_reported(self, app, schema_definition):
        definition = {
            **schema_definition,
            "dataset_fields": [
                {"field_name": "custom_title", "form_snippet": "nope.html"}
            ],
        }

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={
                "schema_type": "test-type",
                "definition": json.dumps(definition),
            },
        )

        assert resp.status_code == STATUS_OK
        assert "is not valid under any of the given schemas" in resp.body
        assert SchemingSchemaVersion.head("dataset", "test-type") is None

    def test_known_form_snippet_is_accepted(self, app, schema_definition):
        definition = {
            **schema_definition,
            "dataset_fields": [
                {"field_name": "custom_title", "form_snippet": "markdown.html"}
            ],
        }

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={
                "schema_type": "test-type",
                "definition": json.dumps(definition),
            },
        )

        assert resp.status_code == STATUS_OK
        assert SchemingSchemaVersion.head("dataset", "test-type") is not None

    def test_duplicate_schema_is_reported(
        self, app, dataset_schema: dict[str, Any], schema_definition
    ):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.new"),
            headers=_sysadmin_headers(),
            data={
                "schema_type": "test-type",
                "definition": json.dumps(schema_definition),
            },
        )

        assert resp.status_code == STATUS_OK
        assert "already exists" in resp.body


class TestSchemaEdit:
    def test_form_is_prefilled(self, app, dataset_schema: dict[str, Any]):
        resp = app.get(
            tk.h.url_for("scheming_dynamic_admin.edit", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "temporal_coverage" in resp.body

    def test_unknown_schema_is_not_found(self, app):
        app.get(
            tk.h.url_for("scheming_dynamic_admin.edit", schema_type="no-such-type"),
            headers=_sysadmin_headers(),
            status=STATUS_NOT_FOUND,
        )

    def test_valid_definition_updates_schema(
        self, app, dataset_schema: dict[str, Any], schema_definition
    ):
        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }

        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.edit", schema_type="test-type"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(updated)},
        )

        assert resp.status_code == STATUS_OK
        assert "now at version 1" in resp.body
        schema = SchemingSchemaVersion.head("dataset", "test-type")
        assert schema
        assert schema.definition["dataset_fields"][0]["field_name"] == "renamed_field"

    def test_forked_version_is_reported_in_flash(
        self, app, dataset_schema: dict[str, Any], schema_definition
    ):
        factories.Dataset(type="test-type")  # locks/pins version 1

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }

        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.edit", schema_type="test-type"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(updated)},
        )

        assert resp.status_code == STATUS_OK
        assert "now at version 2" in resp.body
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 2

    def test_invalid_definition_is_reported(
        self, app, dataset_schema: dict[str, Any], schema_definition
    ):
        invalid = {**schema_definition, "dataset_fields": [{"label": "No name"}]}

        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.edit", schema_type="test-type"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(invalid)},
        )

        assert resp.status_code == STATUS_OK
        assert "is a required property" in resp.body
        schema = SchemingSchemaVersion.head("dataset", "test-type")
        assert schema
        assert schema.definition == schema_definition


class TestSchemaDelete:
    def test_schema_is_deleted(self, app, dataset_schema: dict[str, Any]):
        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.delete", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert SchemingSchemaVersion.head("dataset", "test-type") is None

    def test_unknown_schema_is_not_found(self, app):
        schema_type = "no-such-type"
        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.delete", schema_type=schema_type),
            headers=_sysadmin_headers(),
        )

        assert f"Scheming schema dataset:{schema_type} not found" in resp.body
        assert SchemingSchemaVersion.head("dataset", schema_type) is None

    def test_schema_in_use_is_not_deleted(self, app, dataset_schema: dict[str, Any]):
        factories.Dataset(type="test-type")

        resp = app.post(
            tk.h.url_for("scheming_dynamic_admin.delete", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "datasets of this type still exist" in resp.body
        assert SchemingSchemaVersion.head("dataset", "test-type") is not None


class TestSchemaHistory:
    def test_anonymous_is_forbidden(self, app, dataset_schema: dict[str, Any]):
        app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            status=STATUS_FORBIDDEN,
        )

    def test_regular_user_is_forbidden(self, app, dataset_schema: dict[str, Any]):
        app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers={"Authorization": factories.UserWithToken()["token"]},
            status=STATUS_FORBIDDEN,
        )

    def test_shows_create_entry(self, app, schema_definition):
        helpers.call_action(
            "scheming_schema_create",
            context={"user": factories.Sysadmin()["name"]},
            definition=schema_definition,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "create" in resp.body

    def test_unknown_schema_shows_empty_state(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="no-such-type"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "No history recorded" in resp.body

    def test_no_restore_button_for_the_current_state(self, app, schema_definition):
        helpers.call_action(
            "scheming_schema_create",
            context={"user": factories.Sysadmin()["name"]},
            definition=schema_definition,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "Restore this version" not in resp.body

    def test_restore_button_shown_for_older_entries(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        helpers.call_action(
            "scheming_schema_update",
            context={"user": sysadmin},
            definition=updated,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        # only the older (create) entry gets a restore button, not the
        # newest (update) entry, since that one already is the live state
        assert resp.body.count("Restore the schema to this definition") == 1

    def test_restore_button_shown_on_a_newest_delete_entry(
        self, app, schema_definition
    ):
        sysadmin = factories.Sysadmin()["name"]
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        helpers.call_action(
            "scheming_schema_delete",
            context={"user": sysadmin},
            schema_type="test-type",
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        # both entries get a button: the delete (newest, but undo-able) and
        # the create (older)
        assert resp.body.count("Restore the schema to this definition") == 2

    def test_initial_entry_shows_full_definition_not_a_diff(
        self, app, schema_definition
    ):
        helpers.call_action(
            "scheming_schema_create",
            context={"user": factories.Sysadmin()["name"]},
            definition=schema_definition,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "Initial definition:" in resp.body
        assert "Diff from previous version:" not in resp.body
        assert "temporal_coverage" in resp.body

    def test_changed_entry_shows_a_highlighted_diff(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        helpers.call_action(
            "scheming_schema_update",
            context={"user": sysadmin},
            definition=updated,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "Diff from previous version:" in resp.body
        assert "No change to the definition." not in resp.body
        assert 'class="diff-add"' in resp.body
        assert 'class="diff-del"' in resp.body
        assert "renamed_field" in resp.body

    def test_unchanged_update_shows_no_change_message(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        # re-submit the exact same definition -- nothing actually
        # changes, but an activity row is still written
        helpers.call_action(
            "scheming_schema_update",
            context={"user": sysadmin},
            definition=schema_definition,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "No change to the definition." in resp.body
        assert "Diff from previous version:" not in resp.body

    def test_delete_entry_shows_deleted_message_not_a_diff(
        self, app, schema_definition
    ):
        sysadmin = factories.Sysadmin()["name"]
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        helpers.call_action(
            "scheming_schema_delete",
            context={"user": sysadmin},
            schema_type="test-type",
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "Schema deleted." in resp.body
        # the delete activity's definition is identical to the create
        # entry's (nothing changed it in between), which would otherwise
        # hit the "no change" branch -- 'delete' must be checked first
        assert "No change to the definition." not in resp.body
        assert "Diff from previous version:" not in resp.body

    def test_entries_are_ordered_newest_first(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        helpers.call_action(
            "scheming_schema_delete",
            context={"user": sysadmin},
            schema_type="test-type",
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert resp.body.index(">delete<") < resp.body.index(">create<")

    def test_non_ascii_definition_is_not_escaped(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        multilingual = {
            **schema_definition,
            "dataset_fields": [
                {"field_name": "temporal_coverage", "label": {"uk_UA": "Назва"}}
            ],
        }
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=multilingual,
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert "Назва" in resp.body
        assert "\\u041d" not in resp.body

    def test_history_paginates_across_pages(self, app):
        # bypass the create/update actions (and their render checks) --
        # only the raw activity rows matter for this view
        for i in range(12):
            with freeze_time(f"2024-01-01T00:00:{i:02d}Z"):
                SchemingSchemaActivity.record(
                    "dataset",
                    "test-type",
                    (
                        SchemingSchemaActivity.CREATE
                        if i == 0
                        else SchemingSchemaActivity.UPDATE
                    ),
                    "test-actor",
                    {
                        "about": "x",
                        "dataset_type": "test-type",
                        "dataset_fields": [{"field_name": f"field-{i:02d}"}],
                        "resource_fields": [],
                    },
                )
        model.Session.commit()

        page1 = app.get(
            tk.url_for("scheming_dynamic_admin.history", schema_type="test-type"),
            headers=_sysadmin_headers(),
        )

        assert page1.status_code == STATUS_OK
        # newest 10 of 12 entries rendered: field-11 (newest) down to field-02
        assert page1.body.count('class="accordion-item"') == 10
        assert "field-11" in page1.body
        assert "field-02" in page1.body
        # field-01 is only diff *context* fetched to compute field-02's
        # diff (a removed "-" line in it) -- it must not get its own
        # accordion entry, and field-00 (one further back) shouldn't be
        # fetched at all
        assert page1.body.count("field-01") == 1
        assert "diff-del" in page1.body
        assert "field-00" not in page1.body
        assert "Initial definition:" not in page1.body

        page2 = app.get(
            tk.url_for(
                "scheming_dynamic_admin.history", schema_type="test-type", page=2
            ),
            headers=_sysadmin_headers(),
        )

        assert page2.status_code == STATUS_OK
        # the 2 remaining, oldest entries, both rendered as their own
        # entries: field-00 (the real first entry) and field-01 (diffed
        # against it, not fetched again as page1's context row)
        assert page2.body.count('class="accordion-item"') == 2
        assert "field-00" in page2.body
        assert "field-01" in page2.body
        assert page2.body.count("Initial definition:") == 1
        assert "Diff from previous version:" in page2.body


class TestSchemaHistoryIndex:
    def test_anonymous_is_forbidden(self, app):
        app.get(
            tk.url_for("scheming_dynamic_admin.history_index"),
            status=STATUS_FORBIDDEN,
        )

    def test_regular_user_is_forbidden(self, app):
        app.get(
            tk.url_for("scheming_dynamic_admin.history_index"),
            headers={"Authorization": factories.UserWithToken()["token"]},
            status=STATUS_FORBIDDEN,
        )

    def test_shows_live_and_deleted_types(self, app, schema_definition):
        sysadmin = factories.Sysadmin()["name"]
        helpers.call_action(
            "scheming_schema_create",
            context={"user": sysadmin},
            definition=schema_definition,
        )
        deleted = {**schema_definition, "dataset_type": "was-a-type"}
        helpers.call_action(
            "scheming_schema_create", context={"user": sysadmin}, definition=deleted
        )
        helpers.call_action(
            "scheming_schema_delete",
            context={"user": sysadmin},
            schema_type="was-a-type",
        )

        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history_index"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "test-type" in resp.body
        assert "was-a-type" in resp.body

    def test_empty_listing_shows_hint(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.history_index"),
            headers=_sysadmin_headers(),
        )

        assert "No schema activity has been recorded yet." in resp.body


class TestSchemaRestore:
    def _create(self, app, definition: dict) -> SchemingSchemaActivity:
        helpers.call_action(
            "scheming_schema_create",
            context={"user": factories.Sysadmin()["name"]},
            definition=definition,
        )
        history = SchemingSchemaActivity.get_history(
            "dataset", definition["dataset_type"]
        )
        return history[0]

    def test_anonymous_is_forbidden(self, app, schema_definition):
        entry = self._create(app, schema_definition)

        app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id=entry.id,
            ),
            status=STATUS_FORBIDDEN,
        )

    def test_regular_user_is_forbidden(self, app, schema_definition):
        entry = self._create(app, schema_definition)

        app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id=entry.id,
            ),
            headers={"Authorization": factories.UserWithToken()["token"]},
            status=STATUS_FORBIDDEN,
        )

    def test_restore_overwrites_an_unpinned_head(self, app, schema_definition):
        create_entry = self._create(app, schema_definition)

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }
        helpers.call_action(
            "scheming_schema_update",
            context={"user": factories.Sysadmin()["name"]},
            definition=updated,
        )
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id=create_entry.id,
            ),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "restored" in resp.body
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 1
        head = SchemingSchemaVersion.head("dataset", "test-type")
        assert head
        assert head.definition == schema_definition

        history = SchemingSchemaActivity.get_history("dataset", "test-type")
        assert [h.action for h in history] == ["create", "update", "update"]

    def test_restore_forks_a_new_version_when_head_is_pinned(
        self, app, schema_definition
    ):
        create_entry = self._create(app, schema_definition)
        factories.Dataset(type="test-type")  # locks/pins version 1

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }
        helpers.call_action(
            "scheming_schema_update",
            context={"user": factories.Sysadmin()["name"]},
            definition=updated,
        )
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 2

        factories.Dataset(type="test-type")  # locks/pins version 2

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id=create_entry.id,
            ),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert SchemingSchemaVersion.head_version("dataset", "test-type") == 3
        head = SchemingSchemaVersion.head("dataset", "test-type")
        assert head
        assert head.definition == schema_definition

    def test_restore_recreates_a_deleted_schema(self, app, schema_definition):
        create_entry = self._create(app, schema_definition)

        helpers.call_action(
            "scheming_schema_delete",
            context={"user": factories.Sysadmin()["name"]},
            schema_type="test-type",
        )
        assert SchemingSchemaVersion.head("dataset", "test-type") is None

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id=create_entry.id,
            ),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        head = SchemingSchemaVersion.head("dataset", "test-type")
        assert head
        assert head.definition == schema_definition

    def test_unknown_activity_id_is_not_found(self, app, dataset_schema):
        app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="test-type",
                activity_id="does-not-exist",
            ),
            headers=_sysadmin_headers(),
            status=STATUS_NOT_FOUND,
        )

    def test_activity_from_another_schema_type_is_not_found(
        self, app, schema_definition
    ):
        entry = self._create(app, schema_definition)
        self._create(app, {**schema_definition, "dataset_type": "other-type"})

        app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.restore",
                schema_type="other-type",
                activity_id=entry.id,
            ),
            headers=_sysadmin_headers(),
            status=STATUS_NOT_FOUND,
        )


class TestSchemaPreview:
    def test_preview_renders_dataset_and_resource_forms(self, app, schema_definition):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(schema_definition)},
        )

        assert resp.status_code == STATUS_OK
        assert 'name="temporal_coverage"' in resp.body
        assert 'name="url"' in resp.body
        assert "Resource form" in resp.body

    def test_preview_expands_presets(self, app, schema_definition):
        definition = {
            **schema_definition,
            "dataset_fields": [{"field_name": "title", "preset": "title"}],
        }

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(definition)},
        )

        assert resp.status_code == STATUS_OK
        assert 'name="title"' in resp.body

    def test_missing_field_name_is_reported(self, app, schema_definition):
        definition = {**schema_definition, "dataset_fields": [{"label": "No name"}]}

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(definition)},
            status=STATUS_BAD_REQUEST,
        )

        assert "is a required property" in resp.body

    def test_malformed_json_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preview"),
            headers=_sysadmin_headers(),
            data={"definition": "{oops"},
            status=STATUS_BAD_REQUEST,
        )

        assert "Could not parse as valid JSON" in resp.body


class TestPresetList:
    def test_created_preset_is_listed(self, app, preset: SchemingPreset):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.presets_index"),
            headers=_sysadmin_headers(),
        )

        assert "test-preset" in resp.body

    def test_empty_listing_shows_hint(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.presets_index"),
            headers=_sysadmin_headers(),
        )

        assert "No presets have been created yet." in resp.body


class TestPresetCreate:
    def test_form_renders(self, app):
        resp = app.get(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert 'name="definition"' in resp.body

    def test_valid_definition_creates_preset(self, app, preset_definition):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(preset_definition)},
            follow_redirects=False,
        )

        assert resp.status_code == STATUS_REDIRECT
        assert SchemingPreset.get("test-preset") is not None

    def test_missing_preset_name_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps({"values": {}})},
        )

        assert resp.status_code == STATUS_OK
        assert "Missing value" in resp.body

    def test_malformed_json_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=_sysadmin_headers(),
            data={"definition": "{not json"},
        )

        assert resp.status_code == STATUS_OK
        assert "Could not parse as valid JSON" in resp.body

    def test_duplicate_preset_is_reported(
        self, app, preset: SchemingPreset, preset_definition: dict
    ):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_new"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(preset_definition)},
        )

        assert resp.status_code == STATUS_OK
        assert "already exists" in resp.body


class TestPresetEdit:
    def test_form_is_prefilled(
        self, app, preset: SchemingPreset, preset_definition: dict
    ):
        resp = app.get(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_edit", preset_name="test-preset"
            ),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert "not_empty" in resp.body

    def test_unknown_preset_is_not_found(self, app):
        app.get(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_edit", preset_name="no-such-preset"
            ),
            headers=_sysadmin_headers(),
            status=STATUS_NOT_FOUND,
        )

    def test_valid_definition_updates_preset(
        self, app, preset: SchemingPreset, preset_definition: dict
    ):
        updated = {**preset_definition, "values": {"form_snippet": "text.html"}}

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_edit", preset_name="test-preset"
            ),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(updated)},
        )

        assert resp.status_code == STATUS_OK
        row = SchemingPreset.get("test-preset")
        assert row
        assert row.values == {"form_snippet": "text.html"}

    def test_invalid_definition_is_reported(
        self, app, preset: SchemingPreset, preset_definition: dict
    ):
        invalid = {
            **preset_definition,
            "values": {"repeating_subfields": "notalist"},
        }

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_edit", preset_name="test-preset"
            ),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(invalid)},
        )

        assert resp.status_code == STATUS_OK
        assert "is not of type" in resp.body
        row = SchemingPreset.get("test-preset")
        assert row
        assert row.values == preset_definition["values"]


class TestPresetDelete:
    def test_preset_is_deleted(self, app, preset: SchemingPreset):
        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_delete", preset_name="test-preset"
            ),
            headers=_sysadmin_headers(),
        )

        assert resp.status_code == STATUS_OK
        assert SchemingPreset.get("test-preset") is None

    def test_unknown_preset_is_not_found(self, app):
        preset_name = "no-such-preset"
        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_delete", preset_name=preset_name
            ),
            headers=_sysadmin_headers(),
        )

        # the message quotes preset_name (HTML-escaped on render), so only
        # assert on the quote-free portion
        assert "not found" in resp.body
        assert preset_name in resp.body
        assert SchemingPreset.get(preset_name) is None

    def test_preset_in_use_is_not_deleted(
        self, app, preset: SchemingPreset, schema_definition: dict
    ):
        definition = {
            **schema_definition,
            "dataset_fields": [{"field_name": "x", "preset": "test-preset"}],
        }
        SchemingSchemaVersion.create("dataset", "test-type", definition)

        resp = app.post(
            tk.h.url_for(
                "scheming_dynamic_admin.preset_delete", preset_name="test-preset"
            ),
            headers=_sysadmin_headers(),
        )

        assert "still used by" in resp.body
        assert SchemingPreset.get("test-preset") is not None


class TestPresetPreview:
    def test_preview_renders_the_field(self, app, preset_definition: dict):
        definition = {**preset_definition, "values": {"preset": "title"}}

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(definition)},
        )

        assert resp.status_code == STATUS_OK
        assert 'name="preview_field"' in resp.body

    def test_missing_preset_name_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps({"values": {}})},
            status=STATUS_BAD_REQUEST,
        )

        assert "is a required property" in resp.body

    def test_malformed_json_is_reported(self, app):
        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_preview"),
            headers=_sysadmin_headers(),
            data={"definition": "{oops"},
            status=STATUS_BAD_REQUEST,
        )

        assert "Could not parse as valid JSON" in resp.body

    def test_cycle_is_reported(self, app, preset_definition: dict):
        # "test-preset" starts with no base, and "a" bases on it, so both
        # currently resolve fine and "a" is a valid enum choice; previewing
        # "test-preset" based on "a" is what closes the loop
        scheming_factories.Preset(
            preset_name="test-preset", values=preset_definition["values"]
        )
        scheming_factories.Preset(preset_name="a", values={"preset": "test-preset"})

        definition = {**preset_definition, "values": {"preset": "a"}}

        resp = app.post(
            tk.url_for("scheming_dynamic_admin.preset_preview"),
            headers=_sysadmin_headers(),
            data={"definition": json.dumps(definition)},
            status=STATUS_BAD_REQUEST,
        )

        assert "cycle" in resp.body.lower()
