from ckan.lib.cli import CkanCommand
import ckan.plugins as p
import paste.script

from ckanext.scheming.plugins import (SchemingDatasetsPlugin,
    SchemingGroupsPlugin, SchemingOrganizationsPlugin)

import json

def _get_schemas():
    """
    Find the scheming plugins and return (dataset_schemas, group_schemas,
        organization_schemas)

    If any plugin is not loaded, return None instead of schema dicts
    for that value.
    """
    schema_types = []
    for s in (SchemingDatasetsPlugin, SchemingGroupsPlugin,
            SchemingOrganizationsPlugin):
        if s.instance is None:
            schema_types.append(None)
            continue
        schema_types.append(s.instance._schemas)
    return schema_types


class SchemingCommand(CkanCommand):
    """
    ckanext-scheming schema management commands

    Usage::

        paster scheming show
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    parser = paste.script.command.Command.standard_parser(verbose=True)
    parser.add_option('-c', '--config', dest='config',
        default='development.ini', help='Config file to use.')

    def command(self):
        cmd = self.args[0]
        self._load_config()

        if cmd == 'show':
            self._show()
        else:
            print self.__doc__

    def _show(self):
        print json.dumps(_get_schemas(), indent=2)

