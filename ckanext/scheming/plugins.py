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
from ckanext.scheming import loader
from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import (
    validators_from_string, scheming_choices, scheming_required,
    scheming_multiple_choice, scheming_multiple_choice_output)
from ckanext.scheming.logic import (
    scheming_dataset_schema_list, scheming_dataset_schema_show,
    scheming_group_schema_list, scheming_group_schema_show,
    scheming_organization_schema_list, scheming_organization_schema_show,
    )

import os
import inspect

ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')
convert_to_extras = get_converter('convert_to_extras')
convert_from_extras = get_converter('convert_from_extras')

DEFAULT_PRESETS = 'ckanext.scheming:presets.json'


class _SchemingMixin(object):
    """
    Store single plugin instances in class variable 'instance'

    All plugins below need helpers and template directories, but we should
    only do them once when any plugin is loaded.
    """
    instance = None
    _helpers_loaded = False
    _presets = None
    _template_dir_added = False
    _validators_loaded = False

    def get_helpers(self):
        if _SchemingMixin._helpers_loaded:
            return {}
        _SchemingMixin._helpers_loaded = True
        return {
            'scheming_language_text': helpers.scheming_language_text,
            'scheming_choices_label': helpers.scheming_choices_label,
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

    def get_validators(self):
        if _SchemingMixin._validators_loaded:
            return {}
        _SchemingMixin._validators_loaded = True
        return {
            'scheming_choices': scheming_choices,
            'scheming_required': scheming_required,
            'scheming_multiple_choice': scheming_multiple_choice,
            'scheming_multiple_choice_output': scheming_multiple_choice_output,
            }

    def _add_template_directory(self, config):
        if _SchemingMixin._template_dir_added:
            return
        _SchemingMixin._template_dir_added = True
        add_template_directory(config, 'templates')

    def _load_presets(self, config):
        if _SchemingMixin._presets is not None:
            return
        presets = config.get('scheming.presets', DEFAULT_PRESETS).split()
        _SchemingMixin._presets = {}
        for f in reversed(presets):
            for p in _load_schema(f)['presets']:
                _SchemingMixin._presets[p['preset_name']] = p['values']

    def update_config(self, config):
        if self.instance:
            # reloading plugins, probably in WebTest
            _SchemingMixin._helpers_loaded = False
            _SchemingMixin._validators_loaded = False
        # record our plugin instance in a place where our helpers
        # can find it:
        self._store_instance(self)
        self._add_template_directory(config)
        self._load_presets(config)

        self._is_fallback = asbool(config.get(self.FALLBACK_OPTION, False))

        self._schema_urls = config.get(self.SCHEMA_OPTION, "").split()
        self._schemas = _load_schemas(self._schema_urls, self.SCHEMA_TYPE_FIELD)
        self._expanded_schemas = _expand_schemas(self._schemas)

    def is_fallback(self):
        return self._is_fallback


class _GroupOrganizationMixin(object):
    """
    Common methods for SchemingGroupsPlugin and SchemingOrganizationsPlugin
    """

    def group_types(self):
        return list(self._schemas)

    def setup_template_variables(self, context, data_dict):
        group_type = context.get('group_type')
        if not group_type:
            if c.group_dict:
                group_type = c.group_dict['type']
            else:
                group_type = self.UNSPECIFIED_GROUP_TYPE
        c.scheming_schema = self._schemas[group_type]
        c.scheming_fields = c.scheming_schema['fields']

    def db_to_form_schema_options(self, options):
        # FIXME: investigate why this is necessary
        return default_show_group_schema()

    def validate(self, context, data_dict, schema, action):
        thing, action_type = action.split('_')
        t = data_dict.get('type')
        if not t or t not in self._schemas:
            return data_dict, {'type': "Unsupported {thing} type: {t}".format(
                thing=thing, t=t)}
        scheming_schema = self._expanded_schemas[t]
        scheming_fields = scheming_schema['fields']

        get_validators = (_field_output_validators
            if action_type == 'show' else _field_validators)

        for f in scheming_fields:
            schema[f['field_name']] = get_validators(f, scheming_schema,
                f['field_name'] not in schema)

        return navl_validate(data_dict, schema, context)


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm,
        _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.dataset_schemas'
    FALLBACK_OPTION = 'scheming.dataset_fallback'
    SCHEMA_TYPE_FIELD = 'dataset_type'

    @classmethod
    def _store_instance(cls, self):
        SchemingDatasetsPlugin.instance = self

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

    def validate(self, context, data_dict, schema, action):
        """
        Validate and convert for package_create, package_update and
        package_show actions.
        """
        thing, action_type = action.split('_')
        t = data_dict.get('type')
        if not t or t not in self._schemas:
            return data_dict, {'type': [
                "Unsupported dataset type: {t}".format(t=t)]}
        scheming_schema = self._expanded_schemas[t]

        if action_type == 'show':
            get_validators = _field_output_validators
        elif action_type == 'create':
            get_validators = _field_create_validators
        else:
            get_validators = _field_validators

        for f in scheming_schema['dataset_fields']:
            schema[f['field_name']] = get_validators(f, scheming_schema,
                f['field_name'] not in schema)

        resource_schema = schema['resources']
        for f in scheming_schema['resource_fields']:
            resource_schema[f['field_name']] = get_validators(
                f, scheming_schema, False)

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
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.group_schemas'
    FALLBACK_OPTION = 'scheming.group_fallback'
    SCHEMA_TYPE_FIELD = 'group_type'

    @classmethod
    def _store_instance(cls, self):
        SchemingGroupsPlugin.instance = self

    def about_template(self):
        return 'scheming/group/about.html'

# FIXME: implement this template
#    def edit_template(self):
#        return 'scheming/group/edit.html'

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
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.organization_schemas'
    FALLBACK_OPTION = 'scheming.organization_fallback'
    SCHEMA_TYPE_FIELD = 'organization_type'
    UNSPECIFIED_GROUP_TYPE = 'organization'

    @classmethod
    def _store_instance(cls, self):
        SchemingOrganizationsPlugin.instance = self

    def about_template(self):
        return 'scheming/organization/about.html'

# FIXME: implement this template
#    def edit_template(self):
#        return 'scheming/organization/edit.html'

    def get_actions(self):
        return {
            'scheming_organization_schema_list':
                scheming_organization_schema_list,
            'scheming_organization_schema_show':
                scheming_organization_schema_show,
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
        return loader.load(open(p))

def _load_schema_url(url):
    import urllib2
    try:
        res = urllib2.urlopen(url)
        tables = res.read()
    except urllib2.URLError:
        raise SchemingException("Could not load %s" % url)

    return loader.loads(tables, url)


def _field_output_validators(f, schema, convert_extras):
    """
    Return the output validators for a scheming field f
    """
    if convert_extras:
        validators = [convert_from_extras, ignore_missing]
    else:
        validators = [ignore_missing]
    if 'output_validators' in f:
        validators += validators_from_string(
            f['output_validators'], f, schema)
    return validators

def _field_validators(f, schema, convert_extras):
    """
    Return the validators for a scheming field f
    """
    validators = []
    if 'validators' in f:
        validators = validators_from_string(f['validators'], f, schema)
    elif helpers.scheming_field_required(f):
        validators = [not_empty, unicode]
    else:
        validators = [ignore_missing, unicode]

    if convert_extras:
        validators = validators + [convert_to_extras]
    return validators

def _field_create_validators(f, schema, convert_extras):
    """
    Return the validators to use when creating for scheming field f,
    normally the same as the validators used for updating
    """
    if 'create_validators' not in f:
        return _field_validators(f, schema, convert_extras)
    validators = validators_from_string(f['create_validators'], f, schema)

    if convert_extras:
        validators = validators + [convert_to_extras]
    return validators

def _expand_preset(f):
    """
    If scheming field f includes a preset value return a new field
    based on the preset with values from f overriding any values in the
    preset.

    raises SchemingException if the preset given is not found.
    """
    if 'preset' not in f:
        return f
    if f['preset'] not in _SchemingMixin._presets:
        raise SchemingException("preset '%s' not defined" % f['preset'])
    return dict(_SchemingMixin._presets[f['preset']], **f)

def _expand_schemas(schemas):
    """
    Return a new dict of schemas with all field presets expanded.
    """
    out = {}
    for name, original in schemas.iteritems():
        s = dict(original)
        for fname in ('fields', 'dataset_fields', 'resource_fields'):
            if fname not in s:
                continue
            s[fname] = [_expand_preset(f) for f in s[fname]]
        out[name] = s
    return out
