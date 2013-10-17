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
        if hasattr(plugin, 'group_types'):
            group_schemas = plugin._schemas
        else:
            dataset_schemas = plugin._schemas
    return (dataset_schemas, group_schemas)


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

