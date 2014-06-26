from ckan.lib.helpers import lang
from pylons import config
from pylons.i18n import gettext


def scheming_language_text(text):
    """
    :param text: {lang: text} dict or text string

    Convert "language-text" to users' language by looking up
    languag in dict or using gettext if not a dict
    """
    if hasattr(text, 'get'):
        l = lang()
        v = text.get(l)
        if not v:
            v = text.get(config.get('ckan.locale_default', 'en'))
            if not v:
                # just give me something to display
                l, v = sorted(text.items())[0]
        return v
    else:
        return gettext(text)


def scheming_field_required(field):
    """
    Return field['required'] or guess based on validators if not present.
    """
    if 'required' in field:
        return field['required']
    return 'not_empty' in field.get('validators', '').split()


def scheming_dataset_schemas():
    """
    Return the dict of dataset schemas. Or if scheming_datasets
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingDatasetsPlugin as p
    if p.instance:
        return p.instance._schemas


def scheming_get_dataset_schema(package_type):
    """
    Return the schema for the package_type passed or None if
    no schema is defined for that package_type
    """
    schemas = scheming_dataset_schemas()
    if schemas:
        return schemas.get(package_type)


def scheming_group_schemas():
    """
    Return the dict of group schemas. Or if scheming_groups
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingGroupsPlugin as p
    if p.instance:
        return p.instance._schemas


def scheming_get_group_schema(group_type):
    """
    Return the schema for the group_type passed or None if
    no schema is defined for that group_type
    """
    schemas = scheming_group_schemas()
    if schemas:
        return schemas.get(group_type)


def scheming_organization_schemas():
    """
    Return the dict of organization schemas. Or if scheming_organizations
    plugin is not loaded return None.
    """
    from ckanext.scheming.plugins import SchemingOrganizationsPlugin as p
    if p.instance:
        return p.instance._schemas


def scheming_get_organization_schema(organization_type):
    """
    Return the schema for the organization_type passed or None if
    no schema is defined for that organization_type
    """
    schemas = scheming_organization_schemas()
    if schemas:
        return schemas.get(organization_type)

