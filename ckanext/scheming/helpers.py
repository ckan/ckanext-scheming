# -*- coding: utf-8 -*-

import re
import datetime
import pytz
import json
import pycountry
import logging
from jinja2 import Environment
import six
from ckantoolkit import config, _

from ckanapi import LocalCKAN, NotFound, NotAuthorized
from ckan.plugins.toolkit import get_action
all_helpers = {}


def helper(fn):
    """
    collect helper functions into ckanext.scheming.all_helpers dict
    """
    all_helpers[fn.__name__] = fn
    return fn


def lang():
    # access this function late in case ckan
    # is not set up fully when importing this module
    from ckantoolkit import h
    return h.lang()


def convert(text):
    return int(text) if text.isdigit() else text


@helper
def scheming_resource_view_get_fields(resource):
    '''Returns sorted list of text and time fields of a datastore resource.'''

    if not resource.get('datastore_active'):
        return []

    data = {
        'resource_id': resource['id'],
        'limit': 0
    }
    try:
        result = get_action('datastore_search')({}, data)
    except NotFound:
        return []
    fields = [field['id'] for field in result.get('fields', [])]

    return sorted(fields)


@helper
def scheming_country_list():
    """
    Returns a list of all countries taken from pycountry
    """
    countries = [{"text": "", "value": ""}]
    for country in pycountry.countries:
        countries.append({
            "text": country.name,
            "value": country.name
        })
    return sorted(countries, key=lambda k: k['value'])


@helper
def scheming_natural_sort(llist):
    """
    Sorts a list of tuples with strings "naturally". I.e 1,2...11 and not 1,11,2..
    """

    llist.sort(key=lambda key: [convert(c) for c in re.split('([0-9]+)', key[0])])
    return llist


@helper
def get_missing_resources(pkg, schema):
    """
    Identify which pre-specified resources are defined in the package
    schema but currently missing from the actual package. Return the
    details of those missing resources. A pre-specified resource is
    defined in the package schema e.g a HIVE package should contain ART
    data, ANC data and SVY data.
    """
    pkg_res = [r['resource_type'] for r in pkg.get('resources', [])]

    ret = []
    for r in schema.get('resources', []):
        if r['resource_type'] not in pkg_res:
            ret.append(r)

    return ret


@helper
def scheming_language_text(text, prefer_lang=None):
    """
    :param text: {lang: text} dict or text string
    :param prefer_lang: choose this language version if available

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if not text:
        return u''

    assert text != {}
    if hasattr(text, 'get'):
        try:
            if prefer_lang is None:
                prefer_lang = lang()
        except TypeError:
            pass  # lang() call will fail when no user language available
        else:
            try:
                return text[prefer_lang]
            except KeyError:
                pass

        default_locale = config.get('ckan.locale_default', 'en')
        try:
            return text[default_locale]
        except KeyError:
            pass

        l, v = sorted(text.items())[0]
        return v

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')
    t = _(text)
    return t


@helper
def scheming_field_choices(field):
    """
    :param field: scheming field definition
    :returns: choices iterable or None if not found.
    """
    if 'choices' in field:
        return field['choices']
    if 'choices_helper' in field:
        from ckantoolkit import h
        choices_fn = getattr(h, field['choices_helper'])
        return choices_fn(field)


@helper
def scheming_choices_label(choices, value):
    """
    :param choices: choices list of {"label": .., "value": ..} dicts
    :param value: value selected

    Return the label from choices with a matching value, or
    the value passed when not found. Result is passed through
    scheming_language_text before being returned.
    """
    for c in choices:
        if c['value'] == value:
            return scheming_language_text(c.get('label', value))
    return scheming_language_text(value)


@helper
def scheming_datastore_choices(field):
    """
    Required scheming field:
    "datastore_choices_resource": "resource_id_or_alias"

    Optional scheming fields:
    "datastore_choices_columns": {
        "value": "value_column_name",
        "label": "label_column_name" }
    "datastore_choices_limit": 1000 (default)

    When columns aren't specified the first column is used as value
    and second column used as label.
    """
    resource_id = field['datastore_choices_resource']
    limit = field.get('datastore_choices_limit', 1000)
    columns = field.get('datastore_choices_columns')
    fields = None
    if columns:
        fields = [columns['value'], columns['label']]

    # anon user must be able to read choices or this helper
    # could be used to leak data from private datastore tables
    lc = LocalCKAN(username='')
    try:
        result = lc.action.datastore_search(
            resource_id=resource_id,
            limit=limit,
            fields=fields)
    except (NotFound, NotAuthorized):
        return []

    if not fields:
        fields = [f['id'] for f in result['fields'] if f['id'] != '_id']

    return [{
        'value': r[fields[0]],
        'label': r[fields[1]]
    } for r in result['records']]


@helper
def scheming_field_required(field):
    """
    Return field['required'] or guess based on validators if not present.
    """
    if 'required' in field:
        return field['required']
    return 'not_empty' in field.get('validators', '').split()


@helper
def scheming_dataset_schemas(expanded=True):
    """
    Return the dict of dataset schemas. Or if scheming_datasets
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingDatasetsPlugin as p
    if p.instance:
        if expanded:
            return p.instance._expanded_schemas
        return p.instance._schemas


@helper
def scheming_get_presets():
    """
    Returns a dict of all defined presets. If the scheming_datasets
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingDatasetsPlugin as p
    if p.instance:
        return p._presets


@helper
def scheming_get_preset(preset_name):
    """
    Returns the preset by the name `preset_name`.. If the scheming_datasets
    plugin is not loaded or the preset does not exist, return None.

    :param preset_name: The preset to lookup.
    :returns: The preset or None if not found.
    :rtype: None or dict
    """
    schemas = scheming_get_presets()
    if schemas:
        return schemas.get(preset_name)


@helper
def scheming_get_dataset_schema(dataset_type, expanded=True):
    """
    Return the schema for the dataset_type passed or None if
    no schema is defined for that dataset_type
    """
    schemas = scheming_dataset_schemas(expanded)
    if schemas:
        return schemas.get(dataset_type)


@helper
def get_resource_field(dataset_type, resource_type, field_name):
    """
    Return the field for a particular resource type in a particular package type.
    """
    try:
        schema = scheming_get_dataset_schema(dataset_type)
        resource = filter(
            lambda x: x.get('resource_type') == resource_type,
            schema.get('resources', [])
        )[0]
        fields = resource.get('resource_fields') + schema.get('resource_fields', [])
        field = filter(
            lambda x: x.get('field_name') == field_name,
            fields
        )[0]
        return field
    except IndexError:
        return {}


@helper
def scheming_group_schemas(expanded=True):
    """
    Return the dict of group schemas. Or if scheming_groups
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingGroupsPlugin as p
    if p.instance:
        if expanded:
            return p.instance._expanded_schemas
        return p.instance._schemas


@helper
def scheming_get_group_schema(group_type, expanded=True):
    """
    Return the schema for the group_type passed or None if
    no schema is defined for that group_type
    """
    schemas = scheming_group_schemas(expanded)
    if schemas:
        return schemas.get(group_type)


@helper
def scheming_organization_schemas(expanded=True):
    """
    Return the dict of organization schemas. Or if scheming_organizations
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingOrganizationsPlugin as p
    if p.instance:
        if expanded:
            return p.instance._expanded_schemas
        return p.instance._schemas


@helper
def scheming_get_organization_schema(organization_type, expanded=True):
    """
    Return the schema for the organization_type passed or None if
    no schema is defined for that organization_type
    """
    schemas = scheming_organization_schemas(expanded)
    if schemas:
        return schemas.get(organization_type)


@helper
def scheming_get_schema(entity_type, object_type, expanded=True):
    """
    Return the schema for the entity and object types passed
    or None if no schema is defined for the passed types
    """
    if entity_type == 'dataset':
        return scheming_get_dataset_schema(object_type, expanded)
    elif entity_type == 'organization':
        return scheming_get_organization_schema(object_type, expanded)
    elif entity_type == 'group':
        return scheming_get_group_schema(object_type, expanded)


@helper
def scheming_field_by_name(fields, name):
    """
    Simple helper to grab a field from a schema field list
    based on the field name passed. Returns None when not found.
    """
    for f in fields:
        if f.get('field_name') == name:
            return f


def date_tz_str_to_datetime(date_str):
    """Convert ISO-like formatted datestring with timezone to datetime object.

    This function converts ISO format datetime-strings into datetime objects.
    Times may be specified down to the microsecond.  UTC offset or timezone
    information be included in the string.

    Note - Although originally documented as parsing ISO date(-times), this
           function doesn't fully adhere to the format.  It allows microsecond
           precision, despite that not being part of the ISO format.
    """
    split = date_str.split('T')

    if len(split) < 2:
        raise ValueError('Unable to parse time')

    tz_split = re.split('([Z+-])', split[1])

    date = split[0] + 'T' + tz_split[0]
    time_tuple = re.split(r'[^\d]+', date, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match(r'(?P<seconds>\d{2})(\.(?P<microseconds>\d{3,6}))?$',
                     time_tuple[5])
        if not m:
            raise ValueError('Unable to parse %s as seconds.microseconds' %
                             time_tuple[5])
        seconds = int(m.groupdict().get('seconds'))
        microseconds = int(m.groupdict(0).get('microseconds'))
        time_tuple = time_tuple[:5] + [seconds, microseconds]

    final_date = datetime.datetime(*(int(x) for x in time_tuple))

    # Apply the timezone offset
    if len(tz_split) > 1 and not tz_split[1] == 'Z':
        tz = tz_split[2]
        tz_tuple = re.split(r'[^\d]+', tz)

        if tz_tuple[0] == '':
            raise ValueError('Unable to parse timezone')
        offset = int(tz_tuple[0]) * 60

        if len(tz_tuple) > 1 and not tz_tuple[1] == '':
            offset += int(tz_tuple[1])

        if tz_split[1] == '+':
            offset *= -1

        final_date += datetime.timedelta(minutes=offset)

    return final_date


@helper
def scheming_datetime_to_utc(date):
    if date.tzinfo:
        date = date.astimezone(pytz.utc)

    # Make date naive before returning
    return date.replace(tzinfo=None)


@helper
def scheming_datetime_to_tz(date, tz):
    if isinstance(tz, six.string_types):
        tz = pytz.timezone(tz)

    # Make date naive before returning
    return pytz.utc.localize(date).astimezone(tz).replace(tzinfo=None)


@helper
def scheming_get_timezones(field):
    def to_options(llist):
        return [{'value': tz, 'text': tz} for tz in llist]

    def validate_tz(llist):
        return [tz for tz in llist if tz in pytz.all_timezones]

    timezones = field.get('timezones')
    if timezones == 'all':
        return to_options(pytz.all_timezones)
    elif isinstance(timezones, list):
        return to_options(validate_tz(timezones))

    return to_options(pytz.common_timezones)


@helper
def scheming_display_json_value(value, indent=2):
    """
    Returns the object passed serialized as a JSON string.

    :param value: The object to serialize.
    :param indent: Indentation level to pass through to json.dumps().
    :returns: The serialized object, or the original value if it could not be
        serialized.
    :rtype: string
    """
    if isinstance(value, six.string_types):
        return value
    try:
        return json.dumps(value, indent=indent, sort_keys=True)
    except (TypeError, ValueError):
        return value


@helper
def scheming_render_from_string(source, **kwargs):
    # Temporary solution for rendering defaults and including the CKAN
    # helpers. The core CKAN lib does not include a string rendering
    # utility that works across 2.6-2.8.
    from ckantoolkit import h

    env = Environment(autoescape=True)
    template = env.from_string(
        source,
        globals={
            'h': h
        }
    )

    return template.render(**kwargs)


@helper
def scheming_massage_subfield(field, subfield, index, data):
    # Subfield & data are re-used, we must not modify the original!
    sf = subfield.copy()
    data = data.copy()

    new_field_name = '{field_name}-{index}-{subfield_name}'.format(
        field_name=field['field_name'],
        index=index,
        subfield_name=subfield['field_name']
    )

    field_data = data.pop(sf['field_name'], None)
    if field_data is not None:
        data[new_field_name] = field_data

    sf['field_name'] = new_field_name

    return sf, data


@helper
def scheming_composite_load(value):
    if value:
        value = json.loads(value)
        return [value] if isinstance(value, dict) else value
    return []


@helper
def scheming_non_empty_fields(field_list, pkg_dict, exclude):
    r = []
    for field in field_list:
        if field['field_name'] in exclude:
            continue

        if field.get('display_snippet', False) is None:
            continue

        if pkg_dict.get(field['field_name']):
            r.append(field)
    return r


@helper
def get_date():
    """
    Returns the current date.
    """
    return datetime.datetime.now()


@helper
def get_user(user_id):
    """
    Returns the user object for a given user_id.
    """
    try:
        result = get_action('user_show')({}, {'id': user_id})
        return result
    except Exception as e:
        logging.exception(e)
        return {}
