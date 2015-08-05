from ckan.lib.helpers import lang
from pylons import config
from pylons.i18n import gettext


def scheming_language_text(text, prefer_lang=None, _gettext=None):
    """
    :param text: {lang: text} dict or text string
    :param prefer_lang: choose this language version if available

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if hasattr(text, 'get'):
        if not text:
            return ''

        prefer_lang = prefer_lang or lang()
        default_locale = config.get('ckan.locale_default', 'en')

        try:
            v = text[prefer_lang]
        except KeyError:
            try:
                v = text[default_locale]
            except KeyError:
                # just give me something to display
                l, v = sorted(text.items())[0]

        return v
    else:
        if _gettext is None:
            _gettext = gettext

        t = _gettext(text)
        if isinstance(t, str):
            return t.decode('utf-8')
        return t


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
            return scheming_language_text(c['label'])
    return scheming_language_text(value)


def scheming_field_required(field):
    """
    Return field['required'] or guess based on validators if not present.
    """
    if 'required' in field:
        return field['required']
    return 'not_empty' in field.get('validators', '').split()


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


def scheming_get_presets():
    """
    Returns a dict of all defined presets. If the scheming_datasets
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingDatasetsPlugin as p
    if p.instance:
        return p._presets


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


def scheming_get_dataset_schema(dataset_type, expanded=True):
    """
    Return the schema for the dataset_type passed or None if
    no schema is defined for that dataset_type
    """
    schemas = scheming_dataset_schemas(expanded)
    if schemas:
        return schemas.get(dataset_type)


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


def scheming_get_group_schema(group_type, expanded=True):
    """
    Return the schema for the group_type passed or None if
    no schema is defined for that group_type
    """
    schemas = scheming_group_schemas(expanded)
    if schemas:
        return schemas.get(group_type)


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


def scheming_get_organization_schema(organization_type, expanded=True):
    """
    Return the schema for the organization_type passed or None if
    no schema is defined for that organization_type
    """
    schemas = scheming_organization_schemas(expanded)
    if schemas:
        return schemas.get(organization_type)


def scheming_field_by_name(fields, name):
    """
    Simple helper to grab a field from a schema field list
    based on the field name passed. Returns None when not found.
    """
    for f in fields:
        if f.get('field_name') == name:
            return f
