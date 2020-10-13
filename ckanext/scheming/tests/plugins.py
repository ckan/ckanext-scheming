import ckan.plugins as p
import os
import sys
from ckanext.scheming.plugins import SchemingDatasetsPlugin


class SchemingTestSubclass(SchemingDatasetsPlugin):
    def i18n_directory(self):
        '''Change the directory of the *.mo translation files

        The default implementation assumes the plugin is
        ckanext/myplugin/plugin.py and the translations are stored in
        i18n/
        '''
        # assume plugin is called ckanext.<myplugin>.<...>.PluginClass
        extension_module_name = '.'.join(self.__module__.split('.')[:3])
        module = sys.modules[extension_module_name]
        return os.path.join(os.path.dirname(module.__file__), '../i18n')


class SchemingTestSchemaPlugin(p.SingletonPlugin):
    p.implements(p.ITemplateHelpers)

    def get_helpers(self):
        return {
            'scheming_test_schema_choices': schema_choices_helper,
        }


def schema_choices_helper(field):
    """
    Test custom choices helper
    """
    return [
        {
          "value": "friendly",
          "label": "Often friendly"
        },
        {
          "value": "jealous",
          "label": "Jealous of others"
        },
        {
          "value": "spits",
          "label": "Tends to spit"
        }
    ]
