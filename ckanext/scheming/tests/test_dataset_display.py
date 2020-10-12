import pytest
import six
from ckantoolkit.tests.factories import Sysadmin, Dataset


@pytest.mark.usefixtures("clean_db")
class TestDatasetDisplay(object):
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
