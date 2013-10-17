from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm, DefaultGroupForm

from paste.deploy.converters import asbool

import importlib
import os

class SchemingException(Exception):
    pass

class _IScheming(p.Interface):
    "plugin interface used internally to locate scheming plugin instances"
    pass


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(_IScheming)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'dataset_templates')

        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.dataset_fallback', False))
        self._schema_urls = config.get('scheming.dataset_schemas', ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'dataset_type')

    def package_types(self):
        return [t['dataset_type'] for t in self._schemas]



class SchemingGroupsPlugin(p.SingletonPlugin, DefaultGroupForm):
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(_IScheming)

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'group_templates')

        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.group_fallback', False))
        self._schema_urls = config.get('scheming.group_schemas', ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'group_type')

    def group_types(self):
        return [t['group_type'] for t in self._schemas]


def _load_schemas(schemas, type_field):
    out = {}
    for n in schemas:
        schema = _load_schema(n)
        schema = json.loads(schema)
        out[schema[type_field]] = schema
    return out


def _load_schema(url):
    schema = _load_schema_module_path(url)
    if not schema:
        schema = _load_schema_url(url)
    return json.load(schema)    

def _load_schema_module_path(url):
    """
    Given a path like "ckanext.spatialx:spatialx_schema.json"
    find the second part relative to the import path of the first
    """

    module, file_name = url.split(':', 1)
    try:
        m = importlib.import_module(module)
    except ImportError:
        return
    p = m.__path__[0]
    p = os.path.join(p, file_name)
    if os.path.exists(p):
        return open(p)

