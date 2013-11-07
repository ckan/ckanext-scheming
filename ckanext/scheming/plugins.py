from pylons.i18n import _
from pylons import c
import ckan.plugins as p
from ckan.lib.plugins import DefaultDatasetForm, DefaultGroupForm, DefaultOrganizationForm
from ckan.logic.schema import group_form_schema, default_show_group_schema
from ckan.logic.converters import convert_from_extras
from ckan.lib.navl.validators import ignore_missing

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
            'scheming_language_text',
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
        self._schemas = _load_schemas(self._schema_urls, 'type')

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
        self._schemas = _load_schemas(self._schema_urls, 'type')

    def group_types(self):
        return list(self._schemas)

    def get_helpers(self):
        return _SharedPluginInit.get_helpers()

    def about_template(self):
        return 'scheming/group/about.html'

    def edit_template(self):
        return 'scheming/group/edit.html'

    def setup_template_variables(self, context, data_dict):
        group_type = context.get('group_type')
        if not group_type:
            group_type = c.group_dict['type']
        c.scheming_schema = self._schemas[group_type]
        c.scheming_fields = c.scheming_schema['fields']

    def db_to_form_schema_options(self, options):
        schema = default_show_group_schema()
        group_type = options['context']['group'].type
        scheming_schema = self._schemas[group_type]
        scheming_fields = scheming_schema['fields']
        for f in scheming_fields:
            if f['field_name'] not in schema:
                schema[f['field_name']] = [convert_from_extras, ignore_missing]
        return schema


class SchemingOrganizationsPlugin(p.SingletonPlugin, DefaultOrganizationForm):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(_IScheming)

    def update_config(self, config):
        _SharedPluginInit.add_template_directory(config)

        self._is_fallback = p.toolkit.asbool(
            config.get('scheming.organization_fallback', False))
        self._schema_urls = config.get('scheming.organization_schemas', ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'type')

    def group_types(self):
        return list(self._schemas)

    def get_helpers(self):
        return _SharedPluginInit.get_helpers()

    def about_template(self):
        return 'scheming/organization/about.html'

    def edit_template(self):
        return 'scheming/organization/edit.html'

    def setup_template_variables(self, context, data_dict):
        group_type = context.get('group_type')
        if not group_type:
            group_type = c.group_dict['type']
        c.scheming_schema = self._schemas[group_type]
        c.scheming_fields = c.scheming_schema['fields']

    def db_to_form_schema_options(self, options):
        schema = default_show_group_schema()
        group_type = options['context']['group'].type
        scheming_schema = self._schemas[group_type]
        scheming_fields = scheming_schema['fields']
        for f in scheming_fields:
            if f['field_name'] not in schema:
                schema[f['field_name']] = [convert_from_extras, ignore_missing]
        return schema


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

