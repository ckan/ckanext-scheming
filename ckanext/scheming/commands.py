# -*- coding: utf-8 -*-

from __future__ import print_function
import os

import paste.script
from ckantoolkit import CkanCommand

import ckanext.scheming.utils as utils


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
                      default=os.getenv('CKAN_INI', 'development.ini'),
                      help='Config file to use.')

    def command(self):
        self._load_config()
        if not self.args:
            print(self.__doc__)
            return

        cmd = self.args[0]
        if cmd == 'show':
            print(utils.describe_schemas())
        else:
            print(self.__doc__)
