import pytest
import six
from ckan.lib.helpers import url_for
from ckantoolkit.tests.factories import Sysadmin, User, Dataset
from bs4 import BeautifulSoup


@pytest.mark.usefixtures("clean_db")
class TestDatasetDisplay(object):

    core_resource = {
        'name': 'Core Resource',
        'url': 'http://example.com/camel.txt',
        'resource_type': 'awesome-resource'
    }
    extra_resource = {
        'name': 'Extra Resource',
        'url': 'http://example.com/camel.txt',
    }

    def test_core_resources(self, app):
        user = User()
        dataset = Dataset(
            user=user,
            type='test-schema',
            resources=[self.core_resource],
        )
        response = app.get(
            url_for('dataset.read', id=dataset['name']),
            extra_environ={'REMOTE_USER': six.ensure_str(user['name'])},
        )
        soup = BeautifulSoup(response.body)
        core_resources_container = soup.select('.core-resources')[0]
        assert self.core_resource['name'] in str(core_resources_container)

    def test_extra_resources(self, app):
        user = User()
        dataset = Dataset(
            user=user,
            type='test-schema',
            resources=[self.extra_resource],
        )
        response = app.get(
            url_for('dataset.read', id=dataset['name']),
            extra_environ={'REMOTE_USER': six.ensure_str(user['name'])},
        )
        soup = BeautifulSoup(response.body)
        extra_resources_container = soup.select('.extra-resources')[0]
        assert self.extra_resource['name'] in str(extra_resources_container)

    def test_having_both_core_and_extra_resources(self, app):
        user = User()
        dataset = Dataset(
            user=user,
            type='test-schema',
            resources=[self.core_resource, self.extra_resource],
        )
        response = app.get(
            url_for('dataset.read', id=dataset['name']),
            extra_environ={'REMOTE_USER': six.ensure_str(user['name'])},
        )
        soup = BeautifulSoup(response.body)
        core_resources_container = soup.select('.core-resources')[0]
        extra_resources_container = soup.select('.extra-resources')[0]
        assert self.core_resource['name'] in str(core_resources_container)
        assert self.core_resource['name'] not in str(extra_resources_container)
        assert self.extra_resource['name'] in str(extra_resources_container)
        assert self.extra_resource['name'] not in str(core_resources_container)

    def test_dataset_displays_custom_fields(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="test-schema",
            name="set-one",
            humps=3,
            resources=[
                {"url": "http://example.com/camel.txt", "camels_in_photo": 2}
            ],
        )

        response = app.get("/dataset/set-one")
        assert "Humps" in response.body

    def test_resource_displays_custom_fields(self, app):
        user = Sysadmin()
        d = Dataset(
            user=user,
            type="test-schema",
            name="set-two",
            humps=3,
            resources=[
                {
                    "url": "http://example.com/camel.txt",
                    "camels_in_photo": 2,
                    "date": "2015-01-01",
                }
            ],
        )

        response = app.get(
            "/dataset/set-two/resource/" + d["resources"][0]["id"]
        )
        assert "Camels in Photo" in response.body
        assert "Date" in response.body

    def test_choice_field_shows_labels(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="test-schema",
            name="with-choice",
            category="hybrid",
        )
        response = app.get("/dataset/with-choice")
        assert "Hybrid Camel" in response.body

    def test_notes_field_displayed(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="dataset",
            name="plain-jane",
            notes="# styled notes",
        )

        response = app.get("/dataset/plain-jane")
        assert "<h1>styled notes" in response.body

    def test_choice_field_shows_list_if_multiple_options(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="test-schema",
            name="with-multiple-choice-n",
            personality=["friendly", "spits"],
        )

        response = app.get("/dataset/with-multiple-choice-n")

        assert (
            "<ul><li>Often friendly</li><li>Tends to spit</li></ul>"
            in response.body
        )

    def test_choice_field_does_not_show_list_if_one_options(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="test-schema",
            name="with-multiple-choice-one",
            personality=["friendly"],
        )

        response = app.get("/dataset/with-multiple-choice-one")

        assert "Often friendly" in response.body
        assert "<ul><li>Often friendly</li></ul>" not in response.body

    def test_json_field_displayed(self, app):
        user = Sysadmin()
        Dataset(
            user=user,
            type="test-schema",
            name="plain-json",
            a_json_field={"a": "1", "b": "2"},
        )
        response = app.get("/dataset/plain-json")

        if six.PY3:
            expected = """{\n  "a": "1",\n  "b": "2"\n}"""
        else:
            expected = """{\n  "a": "1", \n  "b": "2"\n}"""
        expected = expected.replace(
            '"', "&#34;"
        )  # Ask webhelpers

        assert expected in response.body
        assert "Example JSON" in response.body
