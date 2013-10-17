from pylons.i18n import _
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm, DefaultGroupForm

from paste.deploy.converters import asbool

from ckanext.scheming import helpers

import importlib
import os
import json

class SchemingException(Exception):
    pass

class _IScheming(p.Interface):
    "plugin interface used internally to locate scheming plugin instances"
    pass

class _SharedPluginInit(object):
    """
    Both plugins below need these, but we should only do them once
    when either plugin is loaded.
    """
    _helpers_loaded = False
    _template_dir_added = False

    @classmethod
    def get_helpers(cls):
        if cls._helpers_loaded:
            return {}
        cls._helpers_loaded = True
        return dict((h, getattr(helpers, h)) for h in [
            'language_text',
            ])

    @classmethod
    def add_template_directory(cls, config):
        if cls._template_dir_added:
            return
        cls._template_dir_added = True
        p.toolkit.add_template_directory(config, 'templates')


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(_IScheming)

    def update_config(self, config):
        _SharedPluginInit.add_template_directory(config)

        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.dataset_fallback', False))
        self._schema_urls = config.get('scheming.dataset_schemas', ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'dataset_type')

    def package_types(self):
        return list(self._schemas)

    def get_helpers(self):
        return _SharedPluginInit.get_helpers()


class SchemingGroupsPlugin(p.SingletonPlugin, DefaultGroupForm):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(_IScheming)

    def update_config(self, config):
        _SharedPluginInit.add_template_directory(config)

        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.group_fallback', False))
        self._schema_urls = config.get('scheming.group_schemas', ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'group_type')

    def group_types(self):
        return list(self._schemas)

    def get_helpers(self):
        return _SharedPluginInit.get_helpers()


def _load_schemas(schemas, type_field):
    out = {}
    for n in schemas:
        schema = _load_schema(n)
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

