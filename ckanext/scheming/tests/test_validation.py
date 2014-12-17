from nose.tools import assert_raises, assert_equals
from ckanapi import LocalCKAN, ValidationError

from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import get_validator_or_converter
from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin, SchemingGroupsPlugin)

class TestGetValidatorOrConverter(object):
    def test_missing(self):
        assert_raises(SchemingException,
            get_validator_or_converter, 'not_a_real_validator_name')

    def test_validator_name(self):
        assert get_validator_or_converter('not_empty')

    def test_converter_name(self):
        assert get_validator_or_converter('remove_whitespace')


class TestChoices(object):
    def test_choice_field_only_accepts_given_choices(self):
        lc = LocalCKAN()
        assert_raises(ValidationError, lc.action.package_create,
            type='camel-photos',
            name='fred',
            category='rocker',
            )

    def test_choice_field_accepts_valid_choice(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred',
            category='f2hybrid',
            )
        assert_equals(d['category'], 'f2hybrid')


class TestDates(object):
    def test_date_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        assert_raises(ValidationError, lc.action.package_create, 
            type='camel-photos',
            name='fred',
            a_relevant_date='31/11/2014',
        )
        assert_raises(ValidationError, lc.action.package_create, 
            type='camel-photos',
            name='fred',
            a_relevant_date='31/11/abcd',
        )
        assert_raises(ValidationError, lc.action.package_create, 
            type='camel-photos',
            name='fred',
            a_relevant_date='this-is-not-a-date',
        )


class TestInvalidType(object):
    def test_invalid_dataset_type(self):
        p = SchemingDatasetsPlugin.instance
        data, errors = p.validate({}, {'type': 'banana'}, {}, 'dataset_show')
        assert_equals(list(errors), ['type'])

    def test_invalid_group_type(self):
        p = SchemingGroupsPlugin.instance
        data, errors = p.validate({}, {'type': 'banana'}, {}, 'dataset_show')
        assert_equals(list(errors), ['type'])
