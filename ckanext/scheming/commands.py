from ckan.lib.cli import CkanCommand
import ckan.plugins as p
import paste.script

from ckanext.scheming.plugins import _IScheming

def _get_schemas():
    """
    Find the scheming plugins and return (dataset_schemas, group_schemas)

    If either plugin is not loaded, return None instead of schema dicts
    for that value.
    """
    dataset_schemas = None
    group_schemas = None
    for plugin in p.PluginImplementations(_IScheming):
        if hasattr(plugin, 'group_form'):
            group_schemas = plugin._schemas
        else:
            dataset_schemas = plugin._schemas
    return (dataset_schemas, group_schemas)

