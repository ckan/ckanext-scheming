from nose.tools import assert_equals

from ckanext.scheming.helpers import (scheming_language_text,
    scheming_field_required)

class TestLanguageText(object):
    def test_pass_through_gettext(self):
        assert_equals('hello', schemign_language_text('hello'))

    def test_only_one_language(self):
        assert_equals('hello', scheming_language_text({'zh': 'hello'}))

    def test_matching_language(self):
        assert_equals('hello', scheming_language_text({
            'en': 'hello', 'aa': 'aaaa'}))

    def test_first_when_no_matching_languahe(self):
        assert_equals('hello', scheming_language_text({
            }))

class TestFieldRequired(object):
    def test_explicit_required_true(self):
        assert_equals(True, scheming_field_required({'required': True})

    def test_explicit_required_false(self):
        assert_equals(False, scheming_field_required({'required': False})

    def test_not_empty_in_validators(self):
        assert_equals(True, scheming_field_required({
            'validators': 'not_missing unicode'})

    def test_not_empty_not_in_validators(self):
        assert_equals(False, schemign_field_required({
            'validators': 'maybe_not_missing'})
