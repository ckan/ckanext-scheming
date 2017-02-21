from ckantoolkit import CkanCommand
import paste.script

from ckanext.scheming.helpers import (
    scheming_dataset_schemas,
    scheming_group_schemas,
    scheming_organization_schemas,
    scheming_language_text,
    )

import json


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
                      default='development.ini',
                      help='Config file to use.')

    def command(self):
        cmd = self.args[0]
        self._load_config()

        if cmd == 'show':
            self._show()
        else:
            print self.__doc__

    def _show(self):
        schemas = [
            ("Dataset", scheming_dataset_schemas()),
            ("Group", scheming_group_schemas()),
            ("Organization", scheming_organization_schemas()),
        ]

        for n, s in schemas:
            print n, "schemas:"
            if s is None:
                print "    plugin not loaded or schema not specified\n"
                continue
            if not s:
                print "    no schemas"
            for typ in sorted(s):
                print " * " + json.dumps(typ)
                field_names = ('dataset_fields', 'fields', 'resource_fields')

                for field_name in field_names:
                    if s[typ].get(field_name):
                        if field_name == 'resource_fields':
                            print " * " + json.dumps("resource")
                        for field in s[typ][field_name]:
                            print "   - " + json.dumps(field['field_name']),
                            print scheming_language_text(field.get('label'))
            print
