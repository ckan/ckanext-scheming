#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import inspect
import logging
import ckan.plugins as p
from paste.reloader import watch_file
from paste.deploy.converters import asbool
from ckan.common import c
from collections import OrderedDict
from ckantoolkit import _
from ckan.lib.plugins import DefaultTranslation
try:
    from ckan.lib.helpers import helper_functions as core_helper_functions
except ImportError:  # CKAN <= 2.5
    core_helper_functions = None
from navl_validate import validate as navl_validate
from ckan.plugins.toolkit import (
    DefaultDatasetForm,
    DefaultGroupForm,
    DefaultOrganizationForm,
    get_validator,
    get_converter,
    add_template_directory,
    add_resource
)
from ckanext.scheming import helpers, validation, logic, loader
from ckanext.scheming.errors import SchemingException

ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')
convert_to_extras = get_converter('convert_to_extras')
convert_from_extras = get_converter('convert_from_extras')

DEFAULT_PRESETS = 'ckanext.scheming:presets.json'

log = logging.getLogger(__name__)


class _SchemingMixin(object):
    """
    Store single plugin instances in class variable 'instance'

    All plugins below need helpers and template directories, but we should
    only do them once when any plugin is loaded.
    """
    instance = None
    _presets = None
    _helpers_loaded = False
    _template_dir_added = False
    _validators_loaded = False
    _is_fallback = False
    _schema_urls = tuple()
    _schemas = dict()
    _expanded_schemas = tuple()

    def get_helpers(self):
        if core_helper_functions is None:
            if _SchemingMixin._helpers_loaded:
                return {}
            _SchemingMixin._helpers_loaded = True
        elif 'scheming_language_text' in core_helper_functions:
            return {}
        _SchemingMixin._helpers_loaded = True

        return dict(helpers.all_helpers)

    def get_validators(self):
        if _SchemingMixin._validators_loaded:
            return {}
        _SchemingMixin._validators_loaded = True

        validators = dict(validation.all_validators)
        return validators

    def _add_template_directory(self, config):
        if _SchemingMixin._template_dir_added:
            return
        _SchemingMixin._template_dir_added = True
        add_template_directory(config, 'templates')
        add_resource('fanstatic', 'scheming')

    @staticmethod
    def _load_presets(config):
        if _SchemingMixin._presets is not None:
            return

        presets = reversed(
            config.get(
                'scheming.presets',
                DEFAULT_PRESETS
            ).split()
        )

        _SchemingMixin._presets = {
            field['preset_name']: field['values']
            for preset_path in presets
            for field in _load_schema(preset_path)['presets']
        }

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

        if config.get(self.SCHEMA_OPTION):
            self._schema_urls = config.get(self.SCHEMA_OPTION, "").split()
            self._schemas = _load_schemas(
                self._schema_urls,
                self.SCHEMA_TYPE_FIELD
            )

        # This loads all the schemas from a given directory
        if config.get(self.SCHEMA_DIRECTORY_OPTION):
            directory_schemas = _load_schemas_directory(
                config.get(self.SCHEMA_DIRECTORY_OPTION),
                self.SCHEMA_TYPE_FIELD,
                self.SCHEMA_DIRECTORY_OPTION
            )

            for k, v in directory_schemas.items():
                if not self._schemas.get(k):
                    self._schemas[k] = v

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
        group_type = data_dict.get('type')
        if not group_type:
            if c.group_dict:
                group_type = c.group_dict['type']
            else:
                group_type = self.UNSPECIFIED_GROUP_TYPE
        c.scheming_schema = self._schemas[group_type]
        c.group_type = group_type
        c.scheming_fields = c.scheming_schema['fields']

    def validate(self, context, data_dict, schema, action):
        thing, action_type = action.split('_')
        t = data_dict.get('type')
        if not t or t not in self._schemas:
            return data_dict, {'type': _("Unsupported {thing} type: {t}").format(
                thing=thing, t=t)}
        scheming_schema = self._expanded_schemas[t]
        scheming_fields = scheming_schema['fields']

        get_validators = (
            _field_output_validators_group
            if action_type == 'show' else _field_validators
        )
        for f in scheming_fields:
            schema[f['field_name']] = get_validators(
                f,
                scheming_schema,
                f['field_name'] not in schema
            )

        return navl_validate(data_dict, schema, context)


class SchemingDatasetsPlugin(p.SingletonPlugin, DefaultDatasetForm,
                             _SchemingMixin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITranslation)

    SCHEMA_DIRECTORY_OPTION = 'scheming.dataset_schemas_directory'
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
                _("Unsupported dataset type: {t}").format(t=t)]}
        scheming_schema = self._expanded_schemas[t]

        if action_type == 'show':
            get_validators = _field_output_validators
        elif action_type == 'create':
            get_validators = _field_create_validators
        else:
            get_validators = _field_validators

        for f in scheming_schema['dataset_fields']:
            schema[f['field_name']] = get_validators(
                f,
                scheming_schema,
                f['field_name'] not in schema
            )

        resource_schema = schema['resources']
        for f in scheming_schema.get('resource_fields', []):
            resource_schema[f['field_name']] = get_validators(
                f, scheming_schema, False)

        # Setting up schemas for resource types
        if "resources" in scheming_schema:
            schema["resource_schemas"] = {}
            for resource_type in scheming_schema["resource_schemas"]:
                schema["resource_schemas"][resource_type] = dict(schema["resources"])
                for f in scheming_schema["resource_schemas"][resource_type]["resource_fields"]:
                    schema["resource_schemas"][resource_type][f['field_name']] = get_validators(
                        f,
                        scheming_schema,
                        f['field_name'] not in schema["resources"]
                    )

        return navl_validate(data_dict, schema, context)

    def get_actions(self):
        """
        publish dataset schemas
        """
        return {
            'scheming_dataset_schema_list': logic.scheming_dataset_schema_list,
            'scheming_dataset_schema_show': logic.scheming_dataset_schema_show,
        }

    def i18n_domain(self):
        '''
        Change the gettext domain handled by this plugin.
        This python module is called "scheming_datasets" meaning that the
        DefaultTranslation object's implementation of this function expects the
        domain to be ckanext-scheming_datasets.  But the domain we're using is
        ckanext-scheming.
        '''
        domain = 'ckanext-scheming'
        log.debug("Domain: {}".format(domain))
        return domain


class SchemingGroupsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
                           DefaultGroupForm, _SchemingMixin, DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)
    p.implements(p.ITranslation)

    SCHEMA_OPTION = 'scheming.group_schemas'
    SCHEMA_DIRECTORY_OPTION = 'scheming.group_schemas_directory'
    FALLBACK_OPTION = 'scheming.group_fallback'
    SCHEMA_TYPE_FIELD = 'group_type'
    UNSPECIFIED_GROUP_TYPE = 'group'

    @classmethod
    def _store_instance(cls, self):
        SchemingGroupsPlugin.instance = self

    def about_template(self):
        return 'scheming/group/about.html'

    def group_form(group_type=None):
        return 'scheming/group/group_form.html'

    def get_actions(self):
        return {
            'scheming_group_schema_list': logic.scheming_group_schema_list,
            'scheming_group_schema_show': logic.scheming_group_schema_show,
        }


class SchemingOrganizationsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
                                  DefaultOrganizationForm, _SchemingMixin,
                                  DefaultTranslation):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)
    p.implements(p.ITranslation)

    SCHEMA_OPTION = 'scheming.organization_schemas'
    SCHEMA_DIRECTORY_OPTION = 'scheming.organization_schemas_directory'
    FALLBACK_OPTION = 'scheming.organization_fallback'
    SCHEMA_TYPE_FIELD = 'organization_type'
    UNSPECIFIED_GROUP_TYPE = 'organization'

    @classmethod
    def _store_instance(cls, self):
        SchemingOrganizationsPlugin.instance = self

    def about_template(self):
        return 'scheming/organization/about.html'

    def group_form(group_type=None):
        return 'scheming/organization/group_form.html'

    # use the correct controller (see ckan/ckan#2771)
    def group_controller(self):
        return 'organization'

    def get_actions(self):
        return {
            'scheming_organization_schema_list':
                logic.scheming_organization_schema_list,
            'scheming_organization_schema_show':
                logic.scheming_organization_schema_show,
        }

    def i18n_domain(self):
        '''
        Change the gettext domain handled by this plugin.
        This python module is called "scheming_datasets" meaning that the
        DefaultTranslation object's implementation of this function expects the
        domain to be ckanext-scheming_datasets.  But the domain we're using is
        ckanext-scheming.
        '''
        domain = 'ckanext-scheming'
        log.debug("Domain: {}".format(domain))
        return domain


def _load_schemas(schemas, type_field):
    out = {}
    for n in schemas:
        schema = _load_schema(n)
        out[schema[type_field]] = schema
    return out


def _load_schemas_directory(schema_directory_path, type_field, config_field):
    if not os.path.isdir(schema_directory_path):
        raise ValueError(
            '{} not a valid path'.format(config_field)
        )
    schema_paths = _files_from_directory(schema_directory_path)
    out = {}
    for file_path in schema_paths:
        with open(file_path) as schema_file:
            schema = loader.load(schema_file)
            out[schema[type_field]] = schema
    return out


def _files_from_directory(path, extension='.json'):
    listed_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if extension in file:
                listed_files.append(os.path.join(root, file))
    return listed_files


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
        watch_file(p)
        with open(p) as schema_file:
            return loader.load(schema_file)


def _load_schema_url(url):
    import urllib2
    try:
        res = urllib2.urlopen(url)
        tables = res.read()
    except urllib2.URLError:
        raise SchemingException("Could not load {url}".format(url=url))

    return loader.loads(tables, url)


def _field_output_validators_group(f, schema, convert_extras):
    """
    Return the output validators for a scheming field f, tailored for groups
    and orgs.
    """
    return _field_output_validators(
        f,
        schema,
        convert_extras,
        convert_from_extras_type=validation.convert_from_extras_group
    )


def _field_output_validators(f, schema, convert_extras,
                             convert_from_extras_type=convert_from_extras):
    """
    Return the output validators for a scheming field f
    """
    if convert_extras:
        validators = [convert_from_extras_type, ignore_missing]
    else:
        validators = [ignore_missing]
    if 'output_validators' in f:
        validators += validation.validators_from_string(
            f['output_validators'], f, schema)
    return validators


def _field_validators(f, schema, convert_extras):
    """
    Return the validators for a scheming field f
    """
    if 'validators' in f:
        validators = validation.validators_from_string(
            f['validators'],
            f,
            schema
        )
    elif helpers.scheming_field_required(f):
        validators = [not_empty]
    else:
        validators = [ignore_missing]

    if convert_extras:
        validators.append(convert_to_extras)

    # If this field contains children, we need a special validator to handle
    # them.
    if 'subfields' in f:
        validators = [validation.composite_form(f, schema)] + validators

    return validators


def _field_create_validators(f, schema, convert_extras):
    """
    Return the validators to use when creating for scheming field f,
    normally the same as the validators used for updating
    """
    if 'create_validators' not in f:
        return _field_validators(f, schema, convert_extras)

    validators = validation.validators_from_string(
        f['create_validators'],
        f,
        schema
    )

    if convert_extras:
        validators.append(convert_to_extras)

    # If this field contains children, we need a special validator to handle
    # them.
    if 'subfields' in f:
        validators = [validation.composite_form(f, schema)] + validators

    return validators


def _expand(schema, field):
    """
    If scheming field f includes a preset value return a new field
    based on the preset with values from f overriding any values in the
    preset. Applies default values to fields that are expected to always exist.

    raises SchemingException if the preset given is not found.
    """
    preset = field.get('preset')
    if preset:
        if preset not in _SchemingMixin._presets:
            raise SchemingException('preset \'{}\' not defined'.format(preset))
        field = dict(_SchemingMixin._presets[preset], **field)

    field.setdefault(u'display_group', schema.get(
        'display_group_default',
        u'General'
    ))

    return field


def _expand_schemas(schemas):
    """
    Return a new dict of schemas with all field presets expanded.
    """
    out = {}
    for name, original in schemas.iteritems():
        schema = dict(original)
        for grouping in ('fields', 'dataset_fields', 'resource_fields'):
            if grouping not in schema:
                continue

            schema[grouping] = [
                _expand(schema, field)
                for field in schema[grouping]
            ]

            for field in schema[grouping]:
                if 'subfields' in field:
                    field['subfields'] = [
                        _expand(schema, subfield)
                        for subfield in field['subfields']
                    ]

        # Expand and combine resource-specific fields
        # with the package's general resource fields.
        # At present resource-specific fields can only be appended
        for resource in schema.get("resources", []):
            expanded_fields = schema.get("resource_fields", []) + [
                _expand(schema, field)
                for field in resource["resource_fields"]
            ]
            # Resource-specific fields with the same name override
            expanded_fields = list(v for v in (OrderedDict(
                (x['field_name'], x)
                for x in expanded_fields
            ).values()))
            resource["resource_fields"] = expanded_fields
            schema.setdefault(
                "resource_schemas", {}
            )[resource["resource_type"]] = resource
        out[name] = schema
    return out
