#!/usr/bin/env python
# encoding: utf-8
from nose.tools import assert_equals
from mock import patch, Mock

from ckanext.scheming.helpers import (
    scheming_language_text,
    scheming_field_required,
    scheming_get_preset,
    scheming_get_presets,
    scheming_datastore_choices,
)

from ckanapi import NotFound


class TestLanguageText(object):
    @patch('ckanext.scheming.helpers._')
    def test_pass_through_gettext(self, _):
        _.side_effect = lambda x: x + '1'
        assert_equals('hello1', scheming_language_text('hello'))

    def test_only_one_language(self):
        assert_equals('hello', scheming_language_text(
            {'zh': 'hello'},
            prefer_lang='en'))

    def test_matching_language(self):
        assert_equals('hello', scheming_language_text(
            {'en': 'hello', 'aa': 'aaaa'},
            prefer_lang='en'))

    def test_first_when_no_matching_language(self):
        assert_equals('hello', scheming_language_text(
            {'aa': 'hello', 'bb': 'no'},
            prefer_lang='en'))

    def test_decodes_utf8(self):
        assert_equals(u'\xa1Hola!', scheming_language_text('\xc2\xa1Hola!'))

    @patch('ckanext.scheming.helpers.lang')
    def test_no_user_lang(self, lang):
        lang.side_effect = TypeError()
        assert_equals('hello', scheming_language_text(
            {'en': 'hello', 'aa': 'aaaa'}))


class TestFieldRequired(object):
    def test_explicit_required_true(self):
        assert_equals(True, scheming_field_required({'required': True}))

    def test_explicit_required_false(self):
        assert_equals(False, scheming_field_required({'required': False}))

    def test_not_empty_in_validators(self):
        assert_equals(True, scheming_field_required({
            'validators': 'not_empty unicode'}))

    def test_not_empty_not_in_validators(self):
        assert_equals(False, scheming_field_required({
            'validators': 'maybe_not_empty'}))


class TestGetPreset(object):
    def test_scheming_get_presets(self):
        presets = scheming_get_presets()
        assert_equals(sorted((
            u'title',
            u'tag_string_autocomplete',
            u'select',
            u'resource_url_upload',
            u'resource_format_autocomplete',
            u'multiple_select',
            u'multiple_checkbox',
            u'date',
            u'datetime',
            u'datetime_tz',
            u'dataset_slug',
            u'dataset_organization',
            u'json_object',
        )), sorted(presets.iterkeys()))

    def test_scheming_get_preset(self):
        preset = scheming_get_preset(u'date')
        assert_equals(sorted((
            (u'display_snippet', u'date.html'),
            (u'form_snippet', u'date.html'),
            (u'validators', u'scheming_required isodate convert_to_json_if_date')
        )), sorted(preset.iteritems()))


class TestDatastoreChoices(object):
    @patch('ckanext.scheming.helpers.LocalCKAN')
    def test_no_choices_on_not_found(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert_equals(scheming_datastore_choices(
            {'datastore_choices_resource': 'not-found'}), [])
        lc.action.datastore_search.assert_called_once()

    @patch('ckanext.scheming.helpers.LocalCKAN')
    def test_no_choices_on_not_authorized(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert_equals(scheming_datastore_choices(
            {'datastore_choices_resource': 'not-allowed'}), [])
        lc.action.datastore_search.assert_called_once()

    @patch('ckanext.scheming.helpers.LocalCKAN')
    def test_no_choices_on_not_authorized(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.side_effect = NotFound()
        LocalCKAN.return_value = lc
        assert_equals(scheming_datastore_choices(
            {'datastore_choices_resource': 'not-allowed'}), [])
        lc.action.datastore_search.assert_called_once()

    @patch('ckanext.scheming.helpers.LocalCKAN')
    def test_simple_call_with_defaults(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.return_value = {
            'fields': [{'id': '_id'}, {'id': 'a'}, {'id': 'b'}],
            'records': [{'a': 'one', 'b': 'two'}, {'a': 'three', 'b': 'four'}],
            }
        LocalCKAN.return_value = lc
        assert_equals(scheming_datastore_choices(
            {'datastore_choices_resource': 'simple-one'}),
            [{'value': 'one', 'label': 'two'}, {'value': 'three', 'label': 'four'}])

        LocalCKAN.asset_called_once_with(username='')
        lc.action.datastore_search.assert_called_once_with(
            resource_id='simple-one',
            limit=1000,
            fields=None)

    @patch('ckanext.scheming.helpers.LocalCKAN')
    def test_call_with_all_params(self, LocalCKAN):
        lc = Mock()
        lc.action.datastore_search.return_value = {
            'records': [{'a': 'one', 'b': 'two'}, {'a': 'three', 'b': 'four'}],
            }
        LocalCKAN.return_value = lc
        assert_equals(
            scheming_datastore_choices({
                'datastore_choices_resource': 'all-params',
                'datastore_choices_limit': 5,
                'datastore_choices_columns': {'value': 'a', 'label': 'b'}}),
            [{'value': 'one', 'label': 'two'}, {'value': 'three', 'label': 'four'}])

        LocalCKAN.asset_called_once_with(username='')
        lc.action.datastore_search.assert_called_once_with(
            resource_id='all-params',
            limit=5,
            fields=['a', 'b'])
