from ckan.lib.helpers import url_for_static
from ckan.logic.action.get import organization_show
from ckantoolkit import get_or_bust, side_effect_free, ObjectNotFound

from ckanext.scheming.helpers import (
    scheming_dataset_schemas, scheming_get_dataset_schema,
    scheming_group_schemas, scheming_get_group_schema,
    scheming_organization_schemas, scheming_get_organization_schema,
)


@side_effect_free
def scheming_dataset_schema_list(context, data_dict):
    """
    Return a list of dataset types customized with the scheming extension
    """
    return list(scheming_dataset_schemas())


@side_effect_free
def scheming_dataset_schema_show(context, data_dict):
    """
    Return the scheming schema for a given dataset type

    :param type: the dataset type
    :param expanded: True to expand presets (default)
    """
    t = get_or_bust(data_dict, 'type')
    expanded = data_dict.get('expanded', True)
    s = scheming_get_dataset_schema(t, expanded)
    if s is None:
        raise ObjectNotFound()
    return s


@side_effect_free
def scheming_group_schema_list(context, data_dict):
    """
    Return a list of group types customized with the scheming extension
    """
    return list(scheming_group_schemas())


@side_effect_free
def scheming_group_schema_show(context, data_dict):
    """
    Return the scheming schema for a given group type

    :param type: the group type
    :param expanded: True to expand presets (default)
    """
    t = get_or_bust(data_dict, 'type')
    expanded = data_dict.get('expanded', True)
    s = scheming_get_group_schema(t, expanded)
    if s is None:
        raise ObjectNotFound()
    return s


@side_effect_free
def scheming_organization_schema_list(context, data_dict):
    """
    Return a list of organization types customized with the scheming extension
    """
    return list(scheming_organization_schemas())


@side_effect_free
def scheming_organization_schema_show(context, data_dict):
    """
    Return the scheming schema for a given organization type

    :param type: the organization type
    :param expanded: True to expand presets (default)
    """
    t = get_or_bust(data_dict, 'type')
    expanded = data_dict.get('expanded', True)
    s = scheming_get_organization_schema(t, expanded)
    if s is None:
        raise ObjectNotFound()
    return s


@side_effect_free
def scheming_organization_show(context, data_dict):
    """
    adjust contents of image_display_url
    """
    result_dict = organization_show(context, data_dict)
    image_url = result_dict.get('image_url', '')
    organization_name = result_dict.get('name', None)
    if organization_name and not image_url.startswith(('http', 'https')) and len(image_url) > 0:
        result_dict['image_display_url'] = url_for_static(
            'uploads/organization/{0}/{1}'.format(organization_name, result_dict.get('image_url')),
            qualified=True
        )
    return result_dict
