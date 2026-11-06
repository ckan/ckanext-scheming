from __future__ import annotations

import pytest

from ckan.tests import factories, helpers

STATUS_OK = 200


@pytest.fixture
def schema_definition(schema_definition):
    return {
        **schema_definition,
        "dataset_fields": [{"field_name": "custom_title", "label": "Custom title"}],
    }


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.ckan_config(
    "scheming.dataset_schemas", "ckanext.scheming:ckan_dataset.yaml"
)
@pytest.mark.ckan_config("scheming.dataset_fallback", "true")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestDynamicTypeRoutes:
    def test_unknown_type_is_not_found(self, app):
        app.get("/no-such-type/new", status=404)

    def test_dynamic_type_new_form_renders(
        self, app, schema_definition, test_request_context
    ):
        user = factories.SysadminWithToken()
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                schema_type="test-type",
                definition=schema_definition,
            )

        resp = app.get("/test-type/new", headers={"Authorization": user["token"]})

        assert resp.status_code == STATUS_OK
        assert "custom_title" in resp.body

    def test_updated_schema_is_rendered_without_restart(
        self, app, schema_definition, test_request_context
    ):
        user = factories.SysadminWithToken()
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                schema_type="test-type",
                definition=schema_definition,
            )
        app.get("/test-type/new", headers={"Authorization": user["token"]})

        updated = {
            **schema_definition,
            "dataset_fields": [{"field_name": "renamed_field"}],
        }
        with test_request_context():
            helpers.call_action(
                "scheming_schema_update",
                definition=updated,
            )

        resp = app.get("/test-type/new", headers={"Authorization": user["token"]})

        assert resp.status_code == STATUS_OK
        assert "renamed_field" in resp.body

    def test_deleted_type_stops_being_served(
        self, app, schema_definition, test_request_context
    ):
        user = factories.SysadminWithToken()
        with test_request_context():
            helpers.call_action(
                "scheming_schema_create",
                schema_type="test-type",
                definition=schema_definition,
            )
        helpers.call_action("scheming_schema_delete", schema_type="test-type")

        app.get(
            "/test-type/new",
            headers={"Authorization": user["token"]},
            status=404,
        )
