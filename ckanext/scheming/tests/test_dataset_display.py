from nose.tools import assert_true, assert_in

from ckantoolkit.tests.factories import Sysadmin, Dataset
from ckantoolkit.tests.helpers import FunctionalTestBase, submit_and_follow


class TestDatasetDisplay(FunctionalTestBase):
    def test_dataset_displays_custom_fields(self):
        user = Sysadmin()
        Dataset(
            user=user,
            type='test-schema',
            name='set-one',
            humps=3,
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
            type='test-schema',
            name='set-two',
            humps=3,
            resources=[{
                'url':"http://example.com/camel.txt",
                'camels_in_photo': 2,
                'date': '2015-01-01'}])

        app = self._get_test_app()
        response = app.get(url='/dataset/set-two/resource/' +
            d['resources'][0]['id'])
        assert_true('Camels in Photo' in response.body)
        assert_true('Date' in response.body)

    def test_choice_field_shows_labels(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='test-schema',
            name='with-choice',
            category='hybrid',
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/with-choice')
        assert_true('Hybrid Camel' in response.body)

    def test_notes_field_displayed(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='dataset',
            name='plain-jane',
            notes='# styled notes',
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/plain-jane')
        assert_true('<h1>styled notes' in response.body)

    def test_choice_field_shows_list_if_multiple_options(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='test-schema',
            name='with-multiple-choice-n',
            personality=['friendly', 'spits'],
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/with-multiple-choice-n')

        assert_true('<ul><li>Often friendly</li><li>Tends to spit</li></ul>'
                    in response.body)

    def test_choice_field_does_not_show_list_if_one_options(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='test-schema',
            name='with-multiple-choice-one',
            personality=['friendly'],
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/with-multiple-choice-one')

        assert_true('Often friendly'
                    in response.body)
        assert_true('<ul><li>Often friendly</li></ul>'
                    not in response.body)

    def test_json_field_displayed(self):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type='test-schema',
            name='plain-json',
            a_json_field={'a': '1', 'b': '2'},
            )
        app = self._get_test_app()
        response = app.get(url='/dataset/plain-json')

        expected = '''{
  "a": "1", 
  "b": "2"
}'''.replace('"', '&#34;')   # Ask webhelpers

        assert_in(expected, response.body)
        assert_in('Example JSON', response.body)
