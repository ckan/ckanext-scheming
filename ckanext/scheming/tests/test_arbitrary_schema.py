import pytest
from flask import render_template
from bs4 import BeautifulSoup

from ckanext.scheming.helpers import scheming_get_arbitrary_schema


class TestArbitrarySchema:
    def test_arbitrary_schema_structure(self):
        schema = scheming_get_arbitrary_schema("ckanext_notifier")

        assert schema["scheming_version"]
        assert schema["schema_id"] == "ckanext_notifier"
        assert schema["about"]
        assert isinstance(schema["fields"], list)

    @pytest.mark.usefixtures("with_request_context")
    def test_render_arbitrary_schema(self, app):
        schema = scheming_get_arbitrary_schema("ckanext_notifier")

        result = render_template(
            "scheming/snippets/render_fields.html",
            fields=schema["fields"],
            data={},
            errors={},
        )

        soup = BeautifulSoup(result)

        assert len(soup.select("div.form-group")) == 3
