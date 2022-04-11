#!/usr/bin/env python
# encoding: utf-8
try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock

import datetime
import six

from ckanext.scheming.helpers import (
    scheming_language_text,
    scheming_field_required,
    scheming_get_preset,
    scheming_get_presets,
    scheming_datastore_choices,
    scheming_display_json_value,
)

from ckanapi import NotFound


class TestLanguageText(object):
    @patch("ckanext.scheming.helpers._")
    def test_pass_through_gettext(self, _):
        _.side_effect = lambda x: x + "1"
        assert "hello1" == scheming_language_text("hello")

    def test_only_one_language(self):
        assert "hello" == scheming_language_text(
            {"zh": "hello"}, prefer_lang="en"
        )

    def test_matching_language(self):
        assert "hello" == scheming_language_text(
            {"en": "hello", "aa": "aaaa"}, prefer_lang="en"
        )

    def test_first_when_no_matching_language(self):
        assert "hello" == scheming_language_text(
            {"aa": "hello", "bb": "no"}, prefer_lang="en"
        )

    def test_decodes_utf8(self):
        assert u"\xa1Hola!" == scheming_language_text(six.b("\xc2\xa1Hola!"))

    @patch("ckanext.scheming.helpers.lang")
    def test_no_user_lang(self, lang):
        lang.side_effect = TypeError()
        assert "hello" == scheming_language_text({"en": "hello", "aa": "aaaa"})


class TestFieldRequired(object):
    def test_explicit_required_true(self):
        assert scheming_field_required({"required": True})

    def test_explicit_required_false(self):
        assert not scheming_field_required({"required": False})

    def test_not_empty_in_validators(self):
        assert scheming_field_required({"validators": "not_empty unicode_safe"})

    def test_not_empty_not_in_validators(self):
        assert not scheming_field_required({"validators": "maybe_not_empty"})


class TestGetPreset(object):
    def test_scheming_get_presets(self):
        presets = scheming_get_presets()
        assert sorted(
            (
                u'title',
                u'tag_string_autocomplete',
                u'select',
                u'resource_url_upload',
                u'organization_url_upload',
                u'resource_format_autocomplete',
                u'multiple_select',
                u'multiple_checkbox',
                u'multiple_text',
                u'date',
                u'datetime',
                u'datetime_tz',
                u'dataset_slug',
                u'dataset_organization',
                u'json_object',
                u'markdown',
                u'radio',
            )
        ) == sorted(presets.keys())

    def test_scheming_get_preset(self):
        preset = scheming_get_preset(u"date")
        assert sorted(
            (
                (u"display_snippet", u"date.html"),
                (u"form_snippet", u"date.html"),
                (
                    u"validators",
                    u"scheming_required isodate convert_to_json_if_date",
                ),
            )
        ) == sorted(preset.items())


class TestDatastoreChoices(object):
    @patch("ckanext.scheming.helpers.LocalCKAN")
    def test_no_choices_on_not_found(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert (
            scheming_datastore_choices(
                {"datastore_choices_resource": "not-found"}
            )
            == []
        )
        lc.action.datastore_search.assert_called_once()

    @patch("ckanext.scheming.helpers.LocalCKAN")
    def test_no_choices_on_not_authorized(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert (
            scheming_datastore_choices(
                {"datastore_choices_resource": "not-allowed"}
            )
            == []
        )
        lc.action.datastore_search.assert_called_once()

    @patch("ckanext.scheming.helpers.LocalCKAN")
    def test_no_choices_on_not_authorized(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert (
            scheming_datastore_choices(
                {"datastore_choices_resource": "not-allowed"}
            )
            == []
        )
        lc.action.datastore_search.assert_called_once()

    @patch("ckanext.scheming.helpers.LocalCKAN")
    def test_simple_call_with_defaults(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.return_value = {
            "fields": [{"id": "_id"}, {"id": "a"}, {"id": "b"}],
            "records": [{"a": "one", "b": "two"}, {"a": "three", "b": "four"}],
        }
        LocalCKAN.return_value = lc
        assert scheming_datastore_choices(
            {"datastore_choices_resource": "simple-one"}
        ) == [
            {"value": "one", "label": "two"},
            {"value": "three", "label": "four"},
        ]

        LocalCKAN.asset_called_once_with(username="")
        lc.action.datastore_search.assert_called_once_with(
            resource_id="simple-one", limit=1000, fields=None
        )

    @patch("ckanext.scheming.helpers.LocalCKAN")
    def test_call_with_all_params(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.return_value = {
            "records": [{"a": "one", "b": "two"}, {"a": "three", "b": "four"}]
        }
        LocalCKAN.return_value = lc
        assert scheming_datastore_choices(
            {
                "datastore_choices_resource": "all-params",
                "datastore_choices_limit": 5,
                "datastore_choices_columns": {"value": "a", "label": "b"},
                "datastore_additional_choices":
                    [{"value": "none", "label": "None"},
                     {"value": "na", "label": "N/A"}]
            }
        ) == [
            {"value": "none", "label": "None"},
            {"value": "na", "label": "N/A"},
            {"value": "one", "label": "two"},
            {"value": "three", "label": "four"},
        ]

        LocalCKAN.asset_called_once_with(username="")
        lc.action.datastore_search.assert_called_once_with(
            resource_id="all-params", limit=5, fields=["a", "b"]
        )


class TestJSONHelpers(object):
    def test_display_json_value_default(self):

        value = {"a": "b"}

        assert scheming_display_json_value(value) == '{\n  "a": "b"\n}'

    def test_display_json_value_indent(self):

        value = {"a": "b"}

        assert (
            scheming_display_json_value(value, indent=4)
            == '{\n    "a": "b"\n}'
        )

    def test_display_json_value_no_indent(self):

        value = {"a": "b"}

        assert scheming_display_json_value(value, indent=None) == '{"a": "b"}'

    def test_display_json_value_keys_are_sorted(self):

        value = {"c": "d", "a": "b"}
        if six.PY3:
            expected = '{\n    "a": "b",\n    "c": "d"\n}'
        else:
            expected = '{\n    "a": "b", \n    "c": "d"\n}'

        assert (
            scheming_display_json_value(value, indent=4) == expected
        )

    def test_display_json_value_json_error(self):

        date = datetime.datetime.now()
        value = ("a", date)

        assert scheming_display_json_value(value) == ("a", date)
