from ckan.lib.cli import CkanCommand
import ckan.plugins as p
import paste.script

from ckanext.scheming.helpers import (
    scheming_dataset_schemas,
    scheming_group_schemas,
    scheming_organization_schemas,
    )

import sys
import json
from datetime import datetime
from contextlib import contextmanager


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
        dataset_schema = scheming_dataset_schemas()

        resource_schema = None
        if dataset_schema and dataset_schema['dataset'].get('resource_fields'):
            resource_schema = \
                {'resource':
                    {'fields':
                     dataset_schema['dataset'].get('resource_fields')}}

        schemas = [
            ("Dataset", dataset_schema),
            ("Resource", resource_schema),
            ("Group", scheming_group_schemas()),
            ("Organization", scheming_organization_schemas()),
        ]
        # and the resource schema...
        print scheming_group_schemas()

        for n, s in schemas:
            print n, "schemas:"
            if s is None:
                print "    plugin not loaded or schema not specified\n"
                continue
            if not s:
                print "    no schemas"
            for typ in sorted(s):
                print " * " + json.dumps(typ)
                field_name = 'dataset_fields' if s[typ].get('dataset_fields') \
                    else 'fields'
                for field in s[typ][field_name]:
                    print "   - " + json.dumps(field['field_name'])

            print
