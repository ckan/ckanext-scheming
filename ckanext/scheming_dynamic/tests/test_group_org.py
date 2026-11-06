"""Dynamic group and organization schemas: actions, runtime merge, routes,
admin UI, CLI and migrations."""

from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.lib.plugins import lookup_group_plugin
from ckan.tests import factories, helpers
from ckan.cli.cli import ckan

from ckanext.scheming.plugins import (
    SchemingGroupsPlugin,
    SchemingOrganizationsPlugin,
)
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.const import ENTITY_TYPE_URL_PREFIXES
from ckanext.scheming_dynamic.model import SchemingSchemaPin, SchemingSchemaVersion

STATUS_OK = 200

PLUGINS = "scheming_datasets scheming_groups scheming_organizations scheming_dynamic"


def group_schema(group_type="group", fields=None):
    return {
        "about": "Example group schema",
        "group_type": group_type,
        "fields": fields or [{"field_name": "title"}, {"field_name": "notes"}],
    }


def org_schema(organization_type="organization", fields=None):
    return {
        "about": "Example organization schema",
        "organization_type": organization_type,
        "fields": fields or [{"field_name": "title"}, {"field_name": "notes"}],
    }


@pytest.mark.ckan_config("ckan.plugins", PLUGINS)
@pytest.mark.ckan_config("scheming.group_schemas", "")
@pytest.mark.ckan_config("scheming.organization_schemas", "")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestGroupOrgSchemaSync:
    def test_group_schema_visible_without_restart(self):
        assert not tk.h.scheming_get_group_schema("mytheme")

        helpers.call_action(
            "scheming_schema_create",
            entity_type="group",
            definition=group_schema("mytheme"),
        )
        sync.forget_request_check()  # as a fresh request would

        schema = tk.h.scheming_get_group_schema("mytheme")
        assert schema
        assert [f["field_name"] for f in schema["fields"]] == ["title", "notes"]

    def test_org_schema_visible_without_restart(self):
        helpers.call_action(
            "scheming_schema_create",
            entity_type="organization",
            definition=org_schema("publisher"),
        )
        sync.forget_request_check()

        schema = tk.h.scheming_get_organization_schema("publisher")
        assert schema
        assert [f["field_name"] for f in schema["fields"]] == ["title", "notes"]

    def test_custom_group_type_resolves_to_scheming_plugin(self):
        assert lookup_group_plugin("mytheme") is not SchemingGroupsPlugin.instance

        helpers.call_action(
            "scheming_schema_create",
            entity_type="group",
            definition=group_schema("mytheme"),
        )
        sync.forget_request_check()
        tk.h.scheming_group_schemas()  # trigger the lazy DB sync

        assert lookup_group_plugin("mytheme") is SchemingGroupsPlugin.instance

    def test_custom_org_type_resolves_to_scheming_plugin(self):
        helpers.call_action(
            "scheming_schema_create",
            entity_type="organization",
            definition=org_schema("publisher"),
        )
        sync.forget_request_check()
        tk.h.scheming_organization_schemas()

        assert lookup_group_plugin("publisher") is SchemingOrganizationsPlugin.instance

    def test_deleting_schema_is_blocked_while_a_group_exists(self):
        helpers.call_action(
            "scheming_schema_create",
            entity_type="group",
            definition=group_schema("mytheme"),
        )
        factories.Group(type="mytheme")

        with pytest.raises(tk.ValidationError):
            helpers.call_action(
                "scheming_schema_delete",
                entity_type="group",
                schema_type="mytheme",
            )

    def test_new_group_is_pinned_to_head_version(self):
        helpers.call_action(
            "scheming_schema_create",
            entity_type="group",
            definition=group_schema("mytheme"),
        )
        group = factories.Group(type="mytheme")

        pin = SchemingSchemaPin.get("group", group["id"])
        assert pin is not None
        assert pin.version == 1


@pytest.mark.ckan_config("ckan.plugins", PLUGINS)
@pytest.mark.ckan_config("scheming.group_schemas", "")
@pytest.mark.ckan_config("scheming.organization_schemas", "")
@pytest.mark.ckan_config("scheming.group_fallback", "true")
@pytest.mark.ckan_config("scheming.organization_fallback", "true")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGroupOrgRoutes:
    def test_custom_group_type_new_form_renders(self, app, test_request_context):
        user = factories.SysadminWithToken()
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                entity_type="group",
                definition=group_schema(
                    "mytheme", [{"field_name": "custom_group_field"}]
                ),
            )

        resp = app.get("/mytheme/new", headers={"Authorization": user["token"]})

        assert resp.status_code == STATUS_OK
        assert "custom_group_field" in resp.body

    def test_custom_org_type_new_form_renders(self, app, test_request_context):
        user = factories.SysadminWithToken()
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                entity_type="organization",
                definition=org_schema(
                    "publisher", [{"field_name": "custom_org_field"}]
                ),
            )

        resp = app.get("/publisher/new", headers={"Authorization": user["token"]})

        assert resp.status_code == STATUS_OK
        assert "custom_org_field" in resp.body

    def test_unknown_group_type_is_not_found(self, app):
        app.get("/no-such-group-type/new", status=404)


@pytest.mark.ckan_config("ckan.plugins", PLUGINS)
@pytest.mark.ckan_config("scheming.group_schemas", "")
@pytest.mark.ckan_config("scheming.organization_schemas", "")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGroupOrgAdminUI:
    def _headers(self):
        return {"Authorization": factories.SysadminWithToken()["token"]}

    @pytest.mark.parametrize("entity_type", ["group", "organization"])
    def test_index_and_create_flow(self, app, entity_type):
        headers = self._headers()
        prefix = ENTITY_TYPE_URL_PREFIXES[entity_type]

        # the schemas index lists every entity type together now, so there's
        # no /<entity_type>/ listing route -- just the bare index
        resp = app.get("/ckan-admin/scheming/", headers=headers)
        assert resp.status_code == STATUS_OK

        definition = (
            group_schema("mytheme")
            if entity_type == "group"
            else org_schema("publisher")
        )
        schema_type = definition[f"{entity_type}_type"]

        resp = app.post(
            f"/ckan-admin/scheming/{prefix}/new",
            headers=headers,
            data={"definition": tk.h.dump_json(definition)},
        )
        assert resp.status_code == STATUS_OK
        assert SchemingSchemaVersion.head(entity_type, schema_type)

        resp = app.get(
            f"/ckan-admin/scheming/{prefix}/{schema_type}/edit", headers=headers
        )
        assert resp.status_code == STATUS_OK

        resp = app.post(
            f"/ckan-admin/scheming/{prefix}/{schema_type}/delete",
            headers=headers,
        )
        assert resp.status_code == STATUS_OK
        assert not SchemingSchemaVersion.head(entity_type, schema_type)

    @pytest.mark.parametrize("entity_type", ["group", "organization"])
    def test_preview_renders_fields(self, app, entity_type):
        definition = (
            group_schema("mytheme", [{"field_name": "preview_me"}])
            if entity_type == "group"
            else org_schema("publisher", [{"field_name": "preview_me"}])
        )

        resp = app.post(
            f"/ckan-admin/scheming/{ENTITY_TYPE_URL_PREFIXES[entity_type]}/preview",
            headers=self._headers(),
            data={"definition": tk.h.dump_json(definition)},
        )

        assert resp.status_code == STATUS_OK
        assert "preview_me" in resp.body


@pytest.mark.ckan_config("ckan.plugins", PLUGINS)
@pytest.mark.ckan_config(
    "scheming.group_schemas", "ckanext.scheming:group_with_bookface.json"
)
@pytest.mark.ckan_config("scheming.organization_schemas", "")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_extended_cli")
class TestGroupCliSyncAndPin:
    def test_sync_imports_static_group_schema(self, cli):
        result = cli.invoke(
            ckan, ["scheming-dynamic", "sync", "--type", "group", "group"]
        )

        assert result.exit_code == 0, result.output
        assert SchemingSchemaVersion.head_version("group", "group") == 1

    def test_pin_adopts_existing_groups(self, cli, test_request_context):
        with test_request_context():
            group = factories.Group(type="group")

        cli.invoke(ckan, ["scheming-dynamic", "sync", "--type", "group", "group"])
        assert SchemingSchemaPin.get("group", group["id"]) is None

        result = cli.invoke(
            ckan, ["scheming-dynamic", "pin", "--type", "group", "group"]
        )

        assert result.exit_code == 0, result.output
        pin = SchemingSchemaPin.get("group", group["id"])
        assert pin is not None
        assert pin.version == 1


@pytest.mark.ckan_config("ckan.plugins", PLUGINS)
@pytest.mark.ckan_config("scheming.group_schemas", "")
@pytest.mark.ckan_config("scheming.organization_schemas", "")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_extended_cli")
class TestGroupOrgMigration:
    def test_group_schema_migration_end_to_end(self, cli, test_request_context):
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                entity_type="group",
                definition=group_schema("mytheme", [{"field_name": "title"}]),
            )
            group = factories.Group(type="mytheme")

            helpers.call_action(
                "scheming_schema_update",
                entity_type="group",
                definition=group_schema(
                    "mytheme",
                    [
                        {"field_name": "title"},
                        {
                            "field_name": "category",
                            "validators": "not_empty unicode_safe",
                        },
                    ],
                ),
            )

        pinned_schema = SchemingSchemaPin.get("group", group["id"])

        assert pinned_schema
        assert pinned_schema.version == 1
        assert SchemingSchemaVersion.head_version("group", "mytheme") == 2

        # store the mapping answering the new required field, then migrate
        with test_request_context():
            helpers.call_action(
                "scheming_migration_mapping_update",
                entity_type="group",
                schema_type="mytheme",
                from_version=1,
                to_version=2,
                mapping={
                    "fields": {"category": {"action": "constant", "value": "general"}},
                    "dropped": {"fields": []},
                },
            )

        result = cli.invoke(
            ckan,
            [
                "scheming-dynamic",
                "migration",
                "apply",
                "--type",
                "group",
                "mytheme",
                "1",
                "2",
            ],
        )
        assert result.exit_code == 0, result.output

        pinned_schema = SchemingSchemaPin.get("group", group["id"])

        assert pinned_schema
        assert pinned_schema.version == 2

        with test_request_context():
            shown = helpers.call_action("group_show", id=group["id"])
        assert shown["category"] == "general"
