import pytest

from ckanext.scheming.plugins import _load_schema
from ckanext.scheming.errors import SchemingException
import ckanext.scheming.helpers as helpers


class TestLoadSchema(object):
    def test_invalid_module(self):
        with pytest.raises(SchemingException):
            _load_schema("verybad.nogood:schema")

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            _load_schema("ckanext.scheming:__init__.py")

    def test_url_to_schema(self):
        assert (
            _load_schema(
                "https://raw.githubusercontent.com/ckan/ckanext-scheming/"
                "master/ckanext/scheming/camel_photos.yaml"
            )["dataset_type"]
            == "camel-photos"
        )

    @pytest.mark.ckan_config(
        "scheming.dataset_schemas",
        "ckanext.scheming.tests:test_extensions.yaml"
    )
    def test_extend_non_existing(self, make_app):
        with pytest.raises(KeyError, match="unknown schema: dataset"):
            make_app()

    @pytest.mark.ckan_config(
        "scheming.dataset_schemas",
        "ckanext.scheming:ckan_dataset.yaml ckanext.scheming.tests:test_extensions.yaml"
    )
    @pytest.mark.usefixtures("with_plugins")
    def test_extend_existing(self):
        schema = helpers.scheming_get_dataset_schema("test-extensions")
        assert "resource_fields" not in schema
        assert helpers.scheming_field_by_name(schema["dataset_fields"], "title") == {
            "field_name": "title", "label": "Extended title"
        }
