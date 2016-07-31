import ckan.plugins as p

from ckanext.scheming.plugins import SchemingDatasetsPlugin

class SchemingTestSubclass(SchemingDatasetsPlugin):
    pass



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
