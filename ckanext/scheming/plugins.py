from pylons.i18n import _
from pylons import c
import ckan.plugins as p
from ckan.lib.plugins import (DefaultDatasetForm, DefaultGroupForm,
    DefaultOrganizationForm)
from ckan.plugins.toolkit import (get_validator, get_converter,
    navl_validate, add_template_directory, asbool)
from ckan.logic.schema import group_form_schema, default_show_group_schema

from paste.deploy.converters import asbool

from ckanext.scheming import helpers
from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import validators_from_string
from ckanext.scheming.logic import (
    scheming_dataset_schema_list, scheming_dataset_schema_show,
    scheming_group_schema_list, scheming_group_schema_show,
    scheming_organization_schema_list, scheming_organization_schema_show,
    )

import os
import json
import inspect

ignore_missing = get_validator('ignore_missing')
convert_to_extras = get_converter('convert_to_extras')
convert_from_extras = get_converter('convert_from_extras')

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
            'scheming_field_required': helpers.scheming_field_required,
            'scheming_dataset_schemas': helpers.scheming_dataset_schemas,
            'scheming_get_dataset_schema': helpers.scheming_get_dataset_schema,
            'scheming_group_schemas': helpers.scheming_group_schemas,
            'scheming_get_group_schema': helpers.scheming_get_group_schema,
            'scheming_organization_schemas':
                helpers.scheming_organization_schemas,
            'scheming_get_organization_schema':
                helpers.scheming_get_organization_schema,
            }

    def _add_template_directory(self, config):
        if _SchemingMixin._template_dir_added:
            return
        _SchemingMixin._template_dir_added = True
        add_template_directory(config, 'templates')

    def update_config(self, config):
        self._store_instance(self)
        self._add_template_directory(config)

        self._is_fallback = asbool(config.get(self.FALLBACK_OPTION, False))
        self._schema_urls = config.get(self.SCHEMA_OPTION, "").split()
        self._schemas = _load_schemas(self._schema_urls, self.SCHEMA_TYPE_FIELD)


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

    def validate(self, context, data_dict, schema, action, group_type):
        thing, action_type = action.split('_')
        t = group_type
        if not t or t not in self._schemas:
            return data_dict, {'type': "Unsupported {thing} type: {t}".format(
                thing=thing, t=t)}
        scheming_schema = self._schemas[t]
        scheming_fields = scheming_schema['fields']
        for f in scheming_fields:
            if action_type == 'show':
                if f['field_name'] not in schema:
                    validators = [convert_from_extras, ignore_missing]
                else:
                    validators = [ignore_missing]
                if 'output_validators' in f:
                    validators += validators_from_string(f['output_validators'])
            else:
                if 'validators' in f:
                    validators = validators_from_string(f['validators'])
                else:
                    validators = [ignore_missing, unicode]
                if f['field_name'] not in schema:
                    validators = validators + [convert_to_extras]
            schema[f['field_name']] = validators

        return navl_validate(data_dict, schema, context)


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm,
        _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions)

    SCHEMA_OPTION = 'scheming.dataset_schemas'
    FALLBACK_OPTION = 'scheming.dataset_fallback'
    SCHEMA_TYPE_FIELD = 'dataset_type'

    def read_template(self):
        return 'scheming/package/read.html'

    def resource_template(self):
        return 'scheming/package/resource_read.html'

    def package_form(self):
        return 'scheming/package/snippets/package_form.html'

    def resource_form(self):
        return 'scheming/package/snippets/resource_form.html'

    def package_types(self):
        return list(self._schemas)

    def validate(self, context, data_dict, schema, action, dataset_type):
        """
        Validate and convert for package_create, package_update and
        package_show actions.
        """
        thing, action_type = action.split('_')
        t = dataset_type
        if not t or t not in self._schemas:
            return data_dict, {'type': [
                "Unsupported dataset type: {t}".format(t=t)]}
        scheming_schema = self._schemas[t]

        for f in scheming_schema['dataset_fields']:
            if action_type == 'show':
                if f['field_name'] not in schema:
                    validators = [convert_from_extras, ignore_missing]
                else:
                    validators = [ignore_missing]
                if 'output_validators' in f:
                    validators += validators_from_string(f['output_validators'])
            else:
                if 'validators' in f:
                    validators = validators_from_string(f['validators'])
                else:
                    validators = [ignore_missing, unicode]
                if f['field_name'] not in schema:
                    validators = validators + [convert_to_extras]
            schema[f['field_name']] = validators

        resource_schema = schema['resources']
        for f in scheming_schema['resource_fields']:
            if action_type == 'show':
                validators = [ignore_missing]
                if 'output_validators' in f:
                    validators += validators_from_string(f['output_validators'])
            else:
                if 'validators' in f:
                    validators = validators_from_string(f['validators'])
                else:
                    validators = [ignore_missing, unicode]
            resource_schema[f['field_name']] = validators

        return navl_validate(data_dict, schema, context)

    def get_actions(self):
        """
        publish dataset schemas
        """
        return {
            'scheming_dataset_schema_list': scheming_dataset_schema_list,
            'scheming_dataset_schema_show': scheming_dataset_schema_show,
        }


class SchemingGroupsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
        DefaultGroupForm, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)

    SCHEMA_OPTION = 'scheming.group_schemas'
    FALLBACK_OPTION = 'scheming.group_fallback'
    SCHEMA_TYPE_FIELD = 'group_type'

    def about_template(self):
        return 'scheming/group/about.html'

    def edit_template(self):
        return 'scheming/group/edit.html'

    def get_actions(self):
        return {
            'scheming_group_schema_list': scheming_group_schema_list,
            'scheming_group_schema_show': scheming_group_schema_show,
        }


class SchemingOrganizationsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
        DefaultOrganizationForm, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)

    SCHEMA_OPTION = 'scheming.organization_schemas'
    FALLBACK_OPTION = 'scheming.organization_fallback'
    SCHEMA_TYPE_FIELD = 'organization_type'

    def about_template(self):
        return 'scheming/organization/about.html'

    def edit_template(self):
        return 'scheming/organization/edit.html'

    def get_actions(self):
        return {
            'scheming_organization_schema_list': scheming_organization_schema_list,
            'scheming_organization_schema_show': scheming_organization_schema_show,
        }


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
        # __import__ has an odd signature
        m = __import__(module, fromlist=[''])
    except ImportError:
        return
    p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
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
