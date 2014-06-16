from pylons.i18n import _
from pylons import c
import ckan.plugins as p
from ckan.lib.plugins import (DefaultDatasetForm, DefaultGroupForm,
    DefaultOrganizationForm)
from ckan.plugins.toolkit import toolkit
from ckan.logic.schema import group_form_schema, default_show_group_schema

from paste.deploy.converters import asbool

from ckanext.scheming import helpers

import os
import json

ignore_missing = toolkit.get_validator('ignore_missing')
convert_to_extras = toolkit.get_converter('convert_to_extras')
convert_from_extras = toolkit.get_converter('convert_from_extras')

class SchemingException(Exception):
    pass

class _SchemingMixin(object):
    """
    Store single plugin instances in class variable 'instance'

    All plugins below need helpers and template directories, but we should
    only do them once when any plugin is loaded.
    """
    instance = None
    _helpers_loaded = False
    _template_dir_added = False

    @classmethod
    def _store_instance(cls, self):
        assert cls.instance is None
        cls.instance = self

    def get_helpers(self):
        if _SchemingMixin._helpers_loaded:
            return {}
        _SchemingMixin._helpers_loaded = True
        return {
            'scheming_language_text': helpers.scheming_language_text,
            }

    def _add_template_directory(self, config):
        if _SchemingMixin._template_dir_added:
            return
        _SchemingMixin._template_dir_added = True
        p.toolkit.add_template_directory(config, 'templates')

    def update_config(self, config):
        self._store_instance(self)
        self._add_template_directory(config)

        self._is_fallback = p.toolkit.asbool(
            config.get(self.FALLBACK_OPTION, False))
        self._schema_urls = config.get(self.SCHEMA_OPTION, ""
            ).split()
        self._schemas = _load_schemas(self._schema_urls, 'type')

    def validate(self, context, data_dict, schema, action):
        thing, action_type = action.split('_')
        t = data_dict.get('type')
        if not t or t not in self._schemas:
            return data_dict, {'type': "Unsupported {thing} type".format(
                thing=thing)}
        scheming_schema = self._schemas[t]
        scheming_fields = scheming_schema['fields']
        for f in scheming_fields:
            if f['field_name'] in schema:
                continue
            if action_type == 'show':
                schema[f['field_name']] = [convert_from_extras, ignore_missing]
            else:
                schema[f['field_name']] = [ignore_missing, convert_to_extras]
        return p.toolkit.navl_validate(data_dict, schema, context)


class _GroupOrganizationMixin(object):
    """
    Common methods for SchemingGroupsPlugin and SchemingOrganizationsPlugin
    """

    def group_types(self):
        return list(self._schemas)

    def setup_template_variables(self, context, data_dict):
        group_type = context.get('group_type')
        if not group_type:
            group_type = c.group_dict['type']
        c.scheming_schema = self._schemas[group_type]
        c.scheming_fields = c.scheming_schema['fields']

    def db_to_form_schema_options(self, options):
        # FIXME: investigate why this is necessary
        return default_show_group_schema()


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm,
        _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)

    SCHEMA_OPTION = 'scheming.dataset_schemas'
    FALLBACK_OPTION = 'scheming.dataset_fallback'

    def package_types(self):
        return list(self._schemas)


class SchemingGroupsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
        DefaultGroupForm, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)

    SCHEMA_OPTION = 'scheming.group_schemas'
    FALLBACK_OPTION = 'scheming.group_fallback'

    def about_template(self):
        return 'scheming/group/about.html'

    def edit_template(self):
        return 'scheming/group/edit.html'


class SchemingOrganizationsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
        DefaultOrganizationForm, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)

    SCHEMA_OPTION = 'scheming.organization_schemas'
    FALLBACK_OPTION = 'scheming.organization_fallback'

    def about_template(self):
        return 'scheming/organization/about.html'

    def edit_template(self):
        return 'scheming/organization/edit.html'


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
    return schema

def _load_schema_module_path(url):
    """
    Given a path like "ckanext.spatialx:spatialx_schema.json"
    find the second part relative to the import path of the first
    """

    module, file_name = url.split(':', 1)
    try:
        m = __import__(module)
    except ImportError:
        return
    p = m.__path__[0]
    p = os.path.join(p, file_name)
    if os.path.exists(p):
        return json.load(open(p))

def _load_schema_url(url):
    import urllib2
    try:
        res = urllib2.urlopen(url)
        tables = res.read()
    except urllib2.URLError:
        raise SchemingException("Could not load %s" % url)

    return json.loads(tables)
