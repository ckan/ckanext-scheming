import pytest

from ckanext.scheming.plugins import _load_schema
from ckanext.scheming.errors import SchemingException


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
