from nose.tools import assert_raises, assert_equals
from ckanapi import LocalCKAN, ValidationError

from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import get_validator_or_converter

class TestGetValidatorOrConverter(object):
    def test_missing(self):
        assert_raises(SchemingException,
            get_validator_or_converter, 'not_a_real_validator_name')

    def test_validator_name(self):
        assert get_validator_or_converter('not_empty')

    def test_converter_name(self):
        assert get_validator_or_converter('date_to_db')

class TestChoices(object):
    def test_choice_field_only_accepts_given_choices(self):
        lc = LocalCKAN()
        assert_raises(ValidationError, lc.action.package_create, **{
            'type':'camel-photos',
            'name':'fred',
            'class': 'rocker',
            })
