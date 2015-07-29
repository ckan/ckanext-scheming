from nose.tools import assert_true

from ckan.new_tests.factories import Sysadmin, Dataset
from ckan.new_tests.helpers import FunctionalTestBase, submit_and_follow


class TestDatasetDisplay(FunctionalTestBase):
    def test_dataset_displays_custom_fields(self):
        user = Sysadmin()
        Dataset(
            user=user,
            type='camel-photos',
            name='set-one',
            humps=3,
            photographer='John Newton',
            photographer_email='john@email.com',
            resources=[{
                'url':"http://example.com/camel.txt",
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
            photographer='John Newton',
            photographer_email='john@email.com',
            resources=[{
                'url':"http://example.com/camel.txt",
                'camels_in_photo': 2}])

        app = self._get_test_app()
        response = app.get(url='/dataset/set-two/resource/' +
            d['resources'][0]['id'])
        assert_true('Camels in Photo' in response.body)

    def test_choice_field_shows_labels(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='camel-photos',
            photographer='John Newton',
            photographer_email='john@email.com',
            name='with-choice',
            category='hybrid',
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/with-choice')
        assert_true('Hybrid Camel' in response.body)
