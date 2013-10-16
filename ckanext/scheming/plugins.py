from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm

from paste.deploy.converters import asbool

import importlib
import os

class SchemingException(Exception):
    pass


class SchemingPlugin(p.SingletonPlugin, DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)

    _schemas = None

    def update_config(self, config):
        # add our templates
        p.toolkit.add_template_directory(config, 'templates')

    def configure(self, config):
        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.is_fallback', False))
        self._schema_urls = config.get('scheming.schema_urls', ""
            ).split()
        if not self._schema_urls

    def _load_schemas(self):
        if self._schemas:
            return self._schemas

        self._schemas = {}
        for n in self._schemas:
            schema = _load_schema_module_path(n)
            schema = json.loads(schema)
            self._schemas[schema['dataset_type']] = schema

        return self._schemas

def _load_schema_module_path(self, n):
    """
    Given a path like "ckanext.spatialx:spatialx_schema.json"
    find the second part relative to the import path of the first
    """
    module, file_name = n.split(':', 1)
    m = importlib.import_module(module)
    p = m.__path__
    p = os.path.join(p, file_name)
    assert os.path.exists(p)
    data = open(p).read()
    return data

