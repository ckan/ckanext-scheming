from nose.tools import assert_equals

from ckanext.scheming.helpers import (scheming_language_text,
    scheming_field_required)

class TestLanguageText(object):
    def test_pass_through_gettext(self):
        assert_equals('hello1', scheming_language_text(
            'hello', _gettext = lambda x: x + '1'))

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
