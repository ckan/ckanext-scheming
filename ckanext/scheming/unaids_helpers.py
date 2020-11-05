# -*- coding: utf-8 -*-
import datetime
import pycountry
import logging
import ckanext.scheming.helpers as helpers
from ckanapi import NotFound
from ckan.plugins.toolkit import get_action


@helpers.helper
def get_date():
    """
    Returns the current date.
    """
    return datetime.datetime.now()


@helpers.helper
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


@helpers.helper
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


@helpers.helper
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


@helpers.helper
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


@helpers.helper
def get_resource_field(dataset_type, resource_type, field_name):
    """
    Return the field for a particular resource type in a particular package
    type.
    """
    try:
        schema = helpers.scheming_get_dataset_schema(dataset_type)
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
