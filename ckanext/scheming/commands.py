from ckan.lib.cli import CkanCommand
import ckan.plugins as p
import paste.script

from ckanext.scheming.plugins import (SchemingDatasetsPlugin,
    SchemingGroupsPlugin, SchemingOrganizationsPlugin)
from ckanext.scheming.workers import worker_pool
from ckanext.scheming.stats import completion_stats

from ckanapi import LocalCKAN, NotFound, ValidationError, SearchIndexError

import sys
import json
from datetime import datetime
from contextlib import contextmanager

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
        for s, n in zip(_get_schemas(), ("Dataset", "Group", "Organization")):
            print n, "schemas:"
            if s is None:
                print "    plugin not loaded\n"
                continue
            if not s:
                print "    no schemas"
            for typ in sorted(s):
                print " * " + json.dumps(typ)
                for field in s[typ]['fields']:
                    print "   - " + json.dumps(field['field_name'])
            print

