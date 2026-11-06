import pytest
from flask import render_template
from bs4 import BeautifulSoup

import ckan.plugins.toolkit as tk


class TestArbitrarySchema:
    def test_arbitrary_schema_structure(self):
        schema = tk.h.scheming_get_arbitrary_schema("ckanext_notifier")

        assert schema["scheming_version"]
        assert schema["schema_id"] == "ckanext_notifier"
        assert schema["about"]
        assert isinstance(schema["fields"], list)

    @pytest.mark.usefixtures("with_request_context")
    def test_render_arbitrary_schema(self, app):
        schema = tk.h.scheming_get_arbitrary_schema("ckanext_notifier")

        result = render_template(
            "scheming/snippets/render_fields.html",
            fields=schema["fields"],
            data={},
            errors={},
        )

        soup = BeautifulSoup(result)

        assert len(soup.select("div.form-group")) == 3


@pytest.mark.usefixtures("with_plugins")
class TestGetArbitrarySchemaHelper:
    def test_get_all_arbitrary_schemas(self):
        assert tk.h.scheming_arbitrary_schemas()

    @pytest.mark.ckan_config("scheming.arbitrary_schemas", "")
    def test_get_all_arbitrary_schemas_if_none(self):
        assert not tk.h.scheming_arbitrary_schemas()

    def test_get_specific_schema(self):
        assert tk.h.scheming_get_arbitrary_schema("ckanext_notifier")

    @pytest.mark.ckan_config("scheming.arbitrary_schemas", "")
    def test_get_specific_schema_if_none(self):
        assert not tk.h.scheming_get_arbitrary_schema("ckanext_notifier")
