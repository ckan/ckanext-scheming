# -*- coding: utf-8 -*-

import re
import datetime
import pytz
import json
import six

from jinja2 import Environment
from ckantoolkit import config, _

from ckanapi import LocalCKAN, NotFound, NotAuthorized

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
    "datastore_additional_choices": [
        {
          "value": "none",
          "label": "None"
        },
        "..."
      ]

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

    datastore_choices = [{
        'value': r[fields[0]],
        'label': r[fields[1]]
    } for r in result['records']]

    additional_choices = field.get('datastore_additional_choices', [])

    return additional_choices + datastore_choices


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
    time_tuple = re.split('[^\d]+', date, maxsplit=5)

    # Extract seconds and microseconds
    if len(time_tuple) >= 6:
        m = re.match('(?P<seconds>\d{2})(\.(?P<microseconds>\d{3,6}))?$',
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
        tz_tuple = re.split('[^\d]+', tz)

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
    def to_options(l):
        return [{'value': tz, 'text': tz} for tz in l]

    def validate_tz(l):
        return [tz for tz in l if tz in pytz.all_timezones]

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
def scheming_flatten_subfield(subfield, data):
    """
    Return flattened_data that converts all nested data for this subfield
    into {field_name}-{index}-{subfield_name} values at the top level,
    so that it matches the names of form fields submitted.

    If data already contains flattened subfields (e.g. rendering values
    after a validation error) then they are returned as-is.
    """
    flat = dict(data)

    if subfield['field_name'] not in data:
        return flat

    for i, record in enumerate(data[subfield['field_name']]):
        prefix = '{field_name}-{index}-'.format(
            field_name=subfield['field_name'],
            index=i,
        )
        for k in record:
            flat[prefix + k] = record[k]
    return flat
