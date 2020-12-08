import pytest
from ckanapi import LocalCKAN


@pytest.mark.usefixtures(u'clean_db')
@pytest.mark.usefixtures(u'clean_index')
class TestAutoCreateValidName(object):
    def test_prevents_duplicates(self):
        lc = LocalCKAN()
        dataset1, dataset2 = [lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        ) for i in range(2)]

        assert dataset1['name'] == u'north-pole-autogenerate-2020'
        assert dataset2['name'] == u'north-pole-autogenerate-2020-1'

    def test_preserves_existing_dataset_name(self):
        lc = LocalCKAN()
        dataset1 = lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        )
        dataset2 = lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        )
        lc.action.package_delete(id=dataset1['id'])

        updated_dataset2 = lc.action.package_update(**dataset2)
        assert updated_dataset2['name'] == updated_dataset2['name']

    def test_handles_deleted_datasets(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        )
        dataset2 = lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        )
        lc.action.package_delete(id=dataset2['id'])

        dataset3 = lc.action.package_create(
            type="auto-create-valid-name", year="2020", location="north-pole"
        )
        assert dataset3['name'] == u'north-pole-autogenerate-2020-1'
