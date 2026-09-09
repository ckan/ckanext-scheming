import inspect
import logging
import os
from functools import wraps
from typing import Any

import ckan.plugins as p
from ckan import model
from ckan.common import c, json
from ckan.lib import plugins as lib_plugins
from ckan.lib.navl.dictization_functions import unflatten
from ckan.plugins.toolkit import (
    DefaultDatasetForm,
    DefaultGroupForm,
    DefaultOrganizationForm,
    add_resource,
    add_template_directory,
    check_ckan_version,
    get_converter,
    get_validator,
    missing,
    navl_validate,
)

from ckanext.scheming import helpers, loader, logic, validation, views
from ckanext.scheming.errors import SchemingException

ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')
convert_to_extras = get_converter('convert_to_extras')
convert_from_extras = get_converter('convert_from_extras')

DEFAULT_PRESETS = 'ckanext.scheming:presets.json'

log = logging.getLogger(__name__)

def run_once_for_caller(var_name, rval_fn):
    """
    return passed value if this method has been called more than once
    from the same function, e.g. load_plugin_helpers, get_validator

    This lets us have multiple scheming plugins active without repeating
    helpers, validators, template dirs and to be compatible with versions
    of ckan that don't support overwriting helpers/validators
    """
    import inspect

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            caller = inspect.currentframe().f_back
            if var_name in caller.f_locals:
                return rval_fn()
            # inject local varible into caller to track separate calls (reloading)
            caller.f_locals[var_name] = None
            return fn(*args, **kwargs)
        return wrapper
    return decorator


class _SchemingMixin(object):
    """
    Store single plugin instances in class variable 'instance'

    All plugins below need helpers and template directories, but we should
    only do them once when any plugin is loaded.
    """
    instance = None
    _presets = None
    _is_fallback = False
    _schema_urls = tuple()
    _schemas = tuple()
    _expanded_schemas = tuple()

    dynamic_scheming: dict[str, Any] = {
        "schema": {
            "dataset": {"fingerprint": None, "pending_fingerprint": None},
            "group": {"fingerprint": None, "pending_fingerprint": None},
            "organization": {"fingerprint": None, "pending_fingerprint": None},
        },
        "preset": {"fingerprint": None, "static": None},
    }

    @run_once_for_caller('_scheming_get_helpers', dict)
    def get_helpers(self):
        return dict(helpers.all_helpers)

    @run_once_for_caller('_scheming_get_validators', dict)
    def get_validators(self):
        return dict(validation.all_validators)

    @run_once_for_caller('_scheming_add_template_directory', lambda: None)
    def _add_template_directory(self, config):
        if not check_ckan_version('2.9'):
            add_template_directory(config, '2.8_templates')
        add_template_directory(config, 'templates')
        add_resource('assets', 'ckanext-scheming')

    @staticmethod
    def _load_presets(config):

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

    @classmethod
    def get_presets(cls, config):
        """Return the presets registered at startup, loading them if needed."""
        if cls._presets is None:
            cls._load_presets(config)
        return cls._presets

    def update_config(self, config):
        if self.instance:
            # reloading plugins, probably in WebTest
            _SchemingMixin._helpers_loaded = False
            _SchemingMixin._validators_loaded = False
        # record our plugin instance in a place where our helpers
        # can find it:
        self._store_instance(self)
        self._add_template_directory(config)

        # FIXME: need to read configuration in update_config
        # because self._schemas need to be defined early for
        # IDatasetForm
        self._load_presets(config)
        self._is_fallback = p.toolkit.asbool(
            config.get(self.FALLBACK_OPTION, False)
        )

        self._schema_urls = config.get(self.SCHEMA_OPTION, "").split()
        self._schemas = _load_schemas(
            self._schema_urls,
            self.SCHEMA_TYPE_FIELD
        )

        self._expanded_schemas = _expand_schemas(self._schemas)

    def is_fallback(self):
        return self._is_fallback


class _DynamicSchemaSyncMixin:
    """
    Overlay database-stored (ckanext-scheming-dynamic) schemas onto the
    file-defined ones at runtime, without a server restart.

    Shared by the dataset, group and organization plugins. Subclasses set
    ``SCHEMA_ENTITY_TYPE`` and may override ``_after_dynamic_sync`` to run
    entity-type-specific bookkeeping (form pages, blueprint/plugin
    registration) whenever the merged schemas change.
    """
    SCHEMA_ENTITY_TYPE = "dataset"

    _static_schemas = {}
    _schemas_value = {}
    _expanded_value = {}

    @property
    def _schemas(self):
        self._sync_dynamic_schemas()
        return self._schemas_value

    @_schemas.setter
    def _schemas(self, value):
        # keep the file-defined schemas around: they are the base the
        # dynamic database schemas get merged over
        self._static_schemas = value
        self._schemas_value = value

    @property
    def _expanded_schemas(self):
        self._sync_dynamic_schemas()
        return self._expanded_value

    @_expanded_schemas.setter
    def _expanded_schemas(self, value):
        self._expanded_value = value

    def _sync_dynamic_schemas(self):
        """Reload schemas when the scheming_dynamic database changed.

        A no-op unless the ``scheming_dynamic`` plugin is loaded.
        """
        if not p.plugin_loaded("scheming_dynamic"):
            return

        from ckanext.scheming_dynamic import sync  # noqa

        merged = sync.schemas_if_changed(
            self.SCHEMA_ENTITY_TYPE, self._static_schemas)
        if merged is None:
            return

        try:
            expanded = _expand_schemas(merged)
        except Exception:
            log.exception(
                "unable to expand dynamic %s schemas, keeping the previous ones",
                self.SCHEMA_ENTITY_TYPE)
            return

        sync.confirm_applied(self.SCHEMA_ENTITY_TYPE)
        self._schemas_value = merged
        self._expanded_value = expanded
        self._after_dynamic_sync(merged, expanded)

    def _after_dynamic_sync(self, merged, expanded):
        """Hook: run whenever the merged schemas change. Overridden below."""


class _GroupOrganizationMixin(object):
    """
    Common methods for SchemingGroupsPlugin and SchemingOrganizationsPlugin
    """

    is_organization = False

    def group_types(self):
        return list(self._schemas)

    def _after_dynamic_sync(self, merged, expanded):
        self._register_dynamic_group_types(merged)

    def _register_dynamic_group_types(self, schemas):
        """Keep runtime-created group/organization types resolvable.

        ``ckan.lib.plugins.lookup_group_plugin`` reads a dict populated once
        at startup from every ``IGroupForm.group_types()``. A type added to
        the database afterwards is missing from it, so lookups for it fall
        back to the default group/organization form instead of us. Fill in
        the missing entries here and drop the ones for types later deleted
        from the database (mirrors ``_register_dynamic_package_types``).
        """
        controller = "organization" if self.is_organization else "group"
        current_types = set(schemas)

        for group_type in current_types:
            lib_plugins._group_plugins.setdefault(group_type, self)  # type: ignore
            lib_plugins._group_controllers.setdefault(group_type, controller)  # type: ignore

        stale = [
            group_type
            for group_type, plugin in lib_plugins._group_plugins.items()
            if plugin is self and group_type not in current_types
        ]
        for group_type in stale:
            del lib_plugins._group_plugins[group_type]
            lib_plugins._group_controllers.pop(group_type, None)

    def setup_template_variables(self, context, data_dict):
        group_type = data_dict.get('type')
        if not group_type:
            if c.group_dict:
                group_type = c.group_dict['type']
            else:
                group_type = self.UNSPECIFIED_GROUP_TYPE
        c.scheming_schema = self._expanded_schemas[group_type]
        c.group_type = group_type
        c.scheming_fields = c.scheming_schema['fields']

    def validate(self, context, data_dict, schema, action):
        thing, action_type = action.split('_')
        t = data_dict.get('type', self.UNSPECIFIED_GROUP_TYPE)
        if not t or t not in self._schemas:
            return data_dict, {'type': "Unsupported {thing} type: {t}".format(
                thing=thing, t=t)}
        scheming_schema = self._expanded_schemas[t]

        if action_type in ('update', 'show') and p.plugin_loaded(
                'scheming_dynamic'):
            from ckanext.scheming_dynamic import sync  # noqa
            entity_type = (
                'organization' if self.is_organization else 'group')
            pinned = sync.pinned_expanded_schema(
                entity_type, t, data_dict.get('id'))
            if pinned:
                scheming_schema = pinned

        scheming_fields = scheming_schema['fields']

        before = scheming_schema.get('before_validators')
        after = scheming_schema.get('after_validators')

        if before:
            schema['__before'] = validation.validators_from_string(
                before, None, scheming_schema)
        if after:
            schema['__after'] = validation.validators_from_string(
                after, None, scheming_schema)

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
                             _DynamicSchemaSyncMixin, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.IConfigurable)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.dataset_schemas'
    FALLBACK_OPTION = 'scheming.dataset_fallback'
    SCHEMA_TYPE_FIELD = 'dataset_type'
    SCHEMA_ENTITY_TYPE = 'dataset'

    @classmethod
    def _store_instance(cls, self):
        SchemingDatasetsPlugin.instance = self

    def _after_dynamic_sync(self, merged, expanded):
        self._dataset_form_pages = _build_dataset_form_pages(expanded)
        self._register_dynamic_package_types(merged)

    def _register_dynamic_package_types(self, schemas: dict[str, Any]) -> None:
        """Register dynamic dataset types.

        Keep newly-created/removed dynamic dataset types in sync with
        ``ckan.lib.plugins.lookup_package_plugin``.

        That function (used throughout ``ckan.views.dataset`` for templates
        and validation) resolves a package type from a dict populated once,
        at app startup, from every ``IDatasetForm.package_types()``.

        A dataset type added to the database afterwards is missing from
        that dict, so lookups for it silently fall back to the default
        IDatasetForm instead of us. Fill in only the missing entries here;
        never overwrite a type some other plugin already claimed at startup.

        Conversely, if a dynamic type we previously claimed here is later
        deleted from the database, drop it again: otherwise lookups for it
        would keep resolving to us even though ``self._schemas`` no longer
        has a definition for it, and our templates unconditionally call
        ``h.scheming_get_dataset_schema(dataset_type)`` expecting one to
        exist.
        """
        current_types = set(schemas)

        for package_type in current_types:
            lib_plugins._package_plugins.setdefault(package_type, self)  # type: ignore

        stale = [
            package_type
            for package_type, plugin in lib_plugins._package_plugins.items()
            if plugin is self and package_type not in current_types
        ]

        for package_type in stale:
            del lib_plugins._package_plugins[package_type]

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

    def resource_validation_dependencies(self, package_type):
        # Compatibility with https://github.com/ckan/ckan/pull/8421
        schema = self._schemas.get(package_type, {})
        dfr = schema.get('draft_fields_required', True)
        return [] if dfr else ['state']

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
        if action_type in ('update', 'show') and p.plugin_loaded('scheming_dynamic'):
            from ckanext.scheming_dynamic import sync  # noqa
            if pinned := sync.pinned_expanded_schema('dataset', t, data_dict.get('id')):
                scheming_schema = pinned

        before = scheming_schema.get('before_validators')
        after = scheming_schema.get('after_validators')
        if action_type == 'show':
            get_validators = _field_output_validators
            before = after = None
        elif action_type == 'create':
            get_validators = _field_create_validators
        else:
            get_validators = _field_validators

        if before:
            schema['__before'] = validation.validators_from_string(
                before, None, scheming_schema)
        if after:
            schema['__after'] = validation.validators_from_string(
                after, None, scheming_schema)
        fg = (
            (scheming_schema['dataset_fields'], schema, True),
            (scheming_schema['resource_fields'], schema['resources'], False)
        )

        composite_convert_fields = []
        for field_list, destination, is_dataset in fg:
            for f in field_list:
                convert_this = is_dataset and f['field_name'] not in schema
                destination[f['field_name']] = get_validators(
                    f,
                    scheming_schema,
                    convert_this
                )
                if convert_this and 'repeating_subfields' in f:
                    composite_convert_fields.append(f['field_name'])

        def composite_convert_to(key, data, errors, context):
            unflat = unflatten(data)
            for f in composite_convert_fields:
                if f not in unflat:
                    continue
                data[(f,)] = json.dumps(unflat[f], default=lambda x:None if x == missing else x)
                convert_to_extras((f,), data, errors, context)
                del data[(f,)]

        if action_type == 'show':
            if composite_convert_fields and data_dict.get("extras"):
                for ex in data_dict['extras']:
                    if ex['key'] in composite_convert_fields:
                        data_dict[ex['key']] = json.loads(ex['value'])
                data_dict['extras'] = [
                    ex for ex in data_dict['extras']
                    if ex['key'] not in composite_convert_fields
                ]
        else:
            expand_form_composite(data_dict, scheming_schema['dataset_fields'])
            if 'resources' in data_dict:
                for res in data_dict['resources']:
                    expand_form_composite(res, scheming_schema['resource_fields'])
            # convert composite package fields to extras so they are stored
            if composite_convert_fields:
                schema = dict(
                    schema,
                    __after=schema.get('__after', []) + [composite_convert_to])

        return navl_validate(data_dict, schema, context)

    def get_actions(self):
        """
        publish dataset schemas
        """
        return {
            'scheming_dataset_schema_list': logic.scheming_dataset_schema_list,
            'scheming_dataset_schema_show': logic.scheming_dataset_schema_show,
        }

    def setup_template_variables(self, context, data_dict):
        super(SchemingDatasetsPlugin, self).setup_template_variables(
            context, data_dict)
        # do not override licenses if they were already added by some
        # other extension. We just want to make sure, that licenses
        # are not empty.
        if not hasattr(c, 'licenses'):
            c.licenses = [('', '')] + model.Package.get_license_options()

    def configure(self, config):
        # A runtime `plugins_update()` reset the cached schemas; force
        # `scheming_dynamic` to re-merge the DB schemas instead of trusting its
        # stale change-detection fingerprint and dropping them until restart.
        if p.plugin_loaded("scheming_dynamic"):
            from ckanext.scheming_dynamic import sync # noqa
            sync.reset()

        self._dataset_form_pages = _build_dataset_form_pages(
            self._expanded_schemas)

    def prepare_dataset_blueprint(self, package_type, bp):
        views.add_paged_form_rules(bp)
        return bp


def _build_dataset_form_pages(expanded_schemas):
    form_pages = {}

    for t, schema in expanded_schemas.items():
        pages = []
        form_pages[t] = pages

        for f in schema['dataset_fields']:
            if not pages or 'start_form_page' in f:
                fp = f.get('start_form_page', {})
                pages.append({
                    'title': fp.get('title', ''),
                    'description': fp.get('description', ''),
                    'fields': [],
                })
            pages[-1]['fields'].append(f)

        if len(pages) == 1 and not pages[0]['title']:
            # no pages defined
            pages[:] = []

    return form_pages


def expand_form_composite(data, schema):
    """
    when submitting dataset/resource form composite fields look like
    "field-0-subfield..." convert these to lists of dicts
    """
    fields = {(): set()}

    def recur_repeating_subfields(path, field):
        if 'repeating_subfields' in field:
            fields.setdefault(path, set()).add(field['field_name'])
            for subfield in field['repeating_subfields']:
                recur_repeating_subfields((*path, field['field_name']), subfield)

    for field in schema:
        recur_repeating_subfields((), field)

    # if "field" exists, don't look for "field-0-subfield"
    fields[()] -= set(data)
    if not fields[()]:
        return
    indexes = {}
    for key in sorted(data):
        if '-' not in key:
            continue
        parts = key.split('-')
        path = ()
        fieldpath = ()
        parent_data = data
        while len(parts) > 2:
            field, index, *parts = parts
            if field not in fields[fieldpath]:
                parts = (field, index, *parts)
                break
            fieldpath = (*fieldpath, field)
            path = (*path, field)
            if index not in indexes.setdefault(path, {}):
                indexes[path][index] = len(indexes[path])
            comp = parent_data.setdefault(field, [])
            index = indexes[path][index]

            try:
                parent_data = comp[index]
            except IndexError:
                comp.append({})
                parent_data = comp[index]

            path = (*path, index)

        if parent_data is not data:
            parent_data['-'.join(parts)] = data[key]
            del data[key]


class SchemingGroupsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
                           DefaultGroupForm, _DynamicSchemaSyncMixin,
                           _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.group_schemas'
    FALLBACK_OPTION = 'scheming.group_fallback'
    SCHEMA_TYPE_FIELD = 'group_type'
    SCHEMA_ENTITY_TYPE = 'group'
    UNSPECIFIED_GROUP_TYPE = 'group'

    @classmethod
    def _store_instance(cls, self):
        SchemingGroupsPlugin.instance = self

    def about_template(self):
        return 'scheming/group/about.html'

    def group_form(self, group_type=None):
        return 'scheming/group/group_form.html'

    def get_actions(self):
        return {
            'scheming_group_schema_list': logic.scheming_group_schema_list,
            'scheming_group_schema_show': logic.scheming_group_schema_show,
        }


class SchemingOrganizationsPlugin(p.SingletonPlugin, _GroupOrganizationMixin,
                                  DefaultOrganizationForm,
                                  _DynamicSchemaSyncMixin, _SchemingMixin):
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IValidators)

    SCHEMA_OPTION = 'scheming.organization_schemas'
    FALLBACK_OPTION = 'scheming.organization_fallback'
    SCHEMA_TYPE_FIELD = 'organization_type'
    SCHEMA_ENTITY_TYPE = 'organization'
    UNSPECIFIED_GROUP_TYPE = 'organization'

    is_organization = True

    @classmethod
    def _store_instance(cls, self):
        SchemingOrganizationsPlugin.instance = self

    def about_template(self):
        return 'scheming/organization/about.html'

    def group_form(self, group_type=None):
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


class SchemingNerfIndexPlugin(p.SingletonPlugin):
    """
    json.dump repeating dataset fields in before_index to prevent failures
    on unmodified solr schema. It's better to customize your solr schema
    and before_index processing than to use this plugin.
    """
    p.implements(p.IPackageController, inherit=True)

    def before_dataset_index(self, data_dict):
        return self.before_index(data_dict)

    def before_index(self, data_dict):
        schemas = SchemingDatasetsPlugin.instance._expanded_schemas
        if data_dict['type'] not in schemas:
            return data_dict

        for d in schemas[data_dict['type']]['dataset_fields']:
            if d['field_name'] not in data_dict:
                continue
            if 'repeating_subfields' in d:
                data_dict[d['field_name']] = json.dumps(data_dict[d['field_name']])

        return data_dict


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


def _load_schema_module_path(url: str):
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
        with open(p) as schema_file:
            return loader.load(schema_file)


def _load_schema_url(url):
    from six.moves import urllib
    try:
        res = urllib.request.urlopen(url)
        tables = res.read()
    except urllib.error.URLError:
        raise SchemingException("Could not load %s" % url)

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
    if 'repeating_subfields' in f:
        validators = {
            sf['field_name']: _field_output_validators(sf, schema, False)
            for sf in f['repeating_subfields']
        }
    elif convert_extras:
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
    if 'repeating_subfields' in f:
        validators = {
            sf['field_name']: _field_validators(sf, schema, False)
            for sf in f['repeating_subfields']
        }

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
    if 'repeating_subfields' in f:
        validators = {
            sf['field_name']: _field_create_validators(sf, schema, False)
            for sf in f['repeating_subfields']
        }

    return validators


def _check_preset_restrictions(preset, preset_values, field, entity_type):
    """
    Some core presets only make sense on a specific field, or require
    other keys (like choices) to be set on the field. Enforce the
    restrictions declared on the preset in presets.json.

    raises SchemingException if field violates a restriction.
    """
    restrict_to_field = preset_values.get("restrict_to_field")
    if restrict_to_field:
        allowed_entity_types = restrict_to_field.get("entity_type") or []
        if isinstance(allowed_entity_types, str):
            allowed_entity_types = [allowed_entity_types]

        if (
            entity_type not in allowed_entity_types
            or field.get("field_name") != restrict_to_field.get("field_name")
        ):
            raise SchemingException(
                "preset '{}' may only be used for the {} field '{}', not "
                "the {} field '{}'".format(
                    preset,
                    "/".join(allowed_entity_types),
                    restrict_to_field.get("field_name"),
                    entity_type,
                    field.get("field_name"),
                )
            )

    requires_one_of = preset_values.get("requires_one_of")
    if requires_one_of and not any(key in field for key in requires_one_of):
        raise SchemingException(
            "preset '{}' requires one of {} to be set on field '{}'".format(
                preset, requires_one_of, field.get("field_name")
            )
        )


def _expand(schema, field, entity_type):
    """
    If scheming field f includes a preset value return a new field
    based on the preset with values from f overriding any values in the
    preset.

    raises SchemingException if the preset given is not found, or if the
    field violates a restriction declared on the preset.
    """
    preset = field.get('preset')
    if preset:
        # Use the accessor: `_SchemingMixin._presets` is transiently None after
        # a `plugins_update()` / `sync.reset()` and only reloads on the next read.
        presets = _SchemingMixin.get_presets(p.toolkit.config)
        if preset not in presets:
            raise SchemingException('preset \'{}\' not defined'.format(preset))
        preset_values = presets[preset]
        field = dict(preset_values, **field)
        _check_preset_restrictions(preset, preset_values, field, entity_type)

    if 'repeating_subfields' in field:
        field['repeating_subfields'] = [
            _expand(schema, subfield, entity_type)
            for subfield in field['repeating_subfields']
        ]
    return field


def _expand_schemas(schemas):
    """
    Return a new dict of schemas with all field presets expanded.
    """
    out = {}
    for name, original in schemas.items():
        schema = dict(original)
        for grouping in ('fields', 'dataset_fields', 'resource_fields'):
            if grouping not in schema:
                continue

            entity_type = _entity_type_for_grouping(schema, grouping)

            schema[grouping] = [
                _expand(schema, field, entity_type)
                for field in schema[grouping]
            ]

            for field in schema[grouping]:
                if 'repeating_subfields' in field:
                    field['repeating_subfields'] = [
                        _expand(schema, subfield, entity_type)
                        for subfield in field['repeating_subfields']
                    ]
                elif 'simple_subfields' in field:
                    field['simple_subfields'] = [
                        _expand(schema, subfield, entity_type)
                        for subfield in field['simple_subfields']
                    ]

        out[name] = schema
    return out

def _entity_type_for_grouping(schema, grouping):
    """
    The kind of thing (dataset, resource, group, organization) that fields
    in this grouping of this schema describe, used to check preset
    restrictions.
    """
    if grouping == 'dataset_fields':
        return 'dataset'
    if grouping == 'resource_fields':
        return 'resource'
    if 'organization_type' in schema:
        return 'organization'
    if 'group_type' in schema:
        return 'group'
    return None
