from nose.tools import assert_equals, assert_raises

from ckanext.scheming.plugins import _load_schema
from ckanext.scheming.errors import SchemingException

class TestLoadSchema(object):
    def test_invalid_module(self):
        assert_raises(SchemingException, _load_schema, 'verybad.nogood:schema')

    def test_invalid_format(self):
        assert_raises(ValueError, _load_schema, 'ckanext.scheming:__init__.py')

    def test_url_to_schema(self):
        assert_equals(_load_schema(
            'https://raw.githubusercontent.com/ckan/ckanext-scheming/'
            'master/ckanext/scheming/camel_photos.json')['dataset_type'],
            'camel-photos')
