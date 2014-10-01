from nose.tools import assert_true

from ckan.new_tests.factories import Sysadmin, Dataset
from ckan.new_tests.helpers import FunctionalTestBase, submit_and_follow


class TestDatasetFormNew(FunctionalTestBase):
    def test_dataset_displays_custom_fields(self):
        user = Sysadmin()
        Dataset(
            user=user,
            type='camel-photos',
            name='set-one',
            humps=3,
            resources=[{
                'url':"http://example.com/camel.jpg",
                'camels_in_photo': 2}])

        app = self._get_test_app()
        response = app.get(url='/dataset/set-one')
        assert_true('Humps' in response.body)

    def test_resource_displays_custom_fields(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='camel-photos',
            name='set-two',
            humps=3,
            resources=[{
                'url':"http://example.com/camel.jpg",
                'camels_in_photo': 2}])

        app = self._get_test_app()
        response = app.get(url='/dataset/set-two/resource/' +
            d['resources'][0]['id'])
        assert_true('Camels in Photo' in response.body)

