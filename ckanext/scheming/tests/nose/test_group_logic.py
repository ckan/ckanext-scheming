from nose.tools import assert_raises, assert_equals
from ckanapi import LocalCKAN, NotFound

class TestGroupSchemaLists(object):
    def test_group_schema_list(self):
        lc = LocalCKAN('visitor')
        group_schemas = lc.action.scheming_group_schema_list()
        assert_equals(sorted(group_schemas), ['group', 'theme'])

    def test_group_schema_show(self):
        lc = LocalCKAN('visitor')
        schema = lc.action.scheming_group_schema_show(
            type='group')
        assert_equals(schema['fields'][4]['label'], 'Bookface')

    def test_group_schema_not_found(self):
        lc = LocalCKAN('visitor')
        assert_raises(NotFound,
            lc.action.scheming_group_schema_show,
            type='bert')

    def test_organization_schema_list(self):
        lc = LocalCKAN('visitor')
        org_schemas = lc.action.scheming_organization_schema_list()
        assert_equals(sorted(org_schemas), ['organization', 'publisher'])

    def test_organization_schema_show(self):
        lc = LocalCKAN('visitor')
        schema = lc.action.scheming_organization_schema_show(
            type='organization')
        assert_equals(schema['fields'][4]['label'], 'Department ID')

    def test_organization_schema_not_found(self):
        lc = LocalCKAN('visitor')
        assert_raises(NotFound,
            lc.action.scheming_organization_schema_show,
            type='elmo')
