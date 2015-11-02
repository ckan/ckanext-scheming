import datetime

from nose.tools import assert_raises, assert_equals
from ckanapi import LocalCKAN, ValidationError

from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import get_validator_or_converter, scheming_required
from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin, SchemingGroupsPlugin)
from ckan.plugins.toolkit import get_validator

ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')

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

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_choices1',
                category='rocker',
            )
        except ValidationError as e:
            assert_equals(
                e.error_dict['category'],
                    ['Value must be one of: bactrian; hybrid; f2hybrid; snowwhite; black (not \'rocker\')']
            )
        else:
            raise AssertionError('ValidationError not raised')

    def test_choice_field_accepts_valid_choice(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_choices2',
            category='f2hybrid',
            )
        assert_equals(d['category'], 'f2hybrid')

class TestRequired(object):
    def test_required_is_set_to_true(self):
        assert_equals(not_empty, scheming_required(
            {'required': True}, {}))

    def test_required_is_set_to_false(self):
        assert_equals(ignore_missing, scheming_required(
            {'required': False}, {}))

    def test_required_is_not_present(self):
        assert_equals(ignore_missing, scheming_required(
            {'other_field': True}, {}))


class TestDates(object):
    def test_date_field_rejects_non_isodates(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_date1',
                a_relevant_date='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                ['Date format incorrect']
            )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_date2',
                a_relevant_date='31/11/abcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                ['Date format incorrect']
            )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_date3',
                a_relevant_date='this-is-not-a-date',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                ['Date format incorrect']
            )
        else:
            raise AssertionError('ValidationError not raised')

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_date4',
            a_relevant_date='2014-01-01',
        )
        assert_equals(d['a_relevant_date'], '2014-01-01')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_date5',
            a_relevant_date=datetime.datetime(2014, 1, 1),
        )
        assert_equals(d['a_relevant_date'], '2014-01-01')

    def test_date_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(type='camel-photos', name='derf_date', resources=[{
                'url': "http://example.com/camel.txt",
                'camels_in_photo': 2,
                'date': '2015-01-01'}])

class TestDateTimes(object):
    def test_datetime_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime1',
                a_relevant_datetime='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime2',
                a_relevant_datetime='31/11/abcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime3',
                a_relevant_datetime='this-is-not-a-date',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime4',
                a_relevant_datetime='2014-11-15Tabcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime5',
                a_relevant_datetime='2014-11-15T12:00:ab',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_datetime6',
            a_relevant_datetime='2014-01-01T12:35:00',
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_datetime7',
            a_relevant_datetime=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_datetime7',
            a_relevant_datetime=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_datetime_field_rejects_invalid_separate_date(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime8',
                a_relevant_datetime_date='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_date'],
                ['Date format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_separate_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime9',
                a_relevant_datetime_date='2014-01-01',
                a_relevant_datetime_time='12:35:aa',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_time'],
                ['Time format incorrect']
        )
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_time_only(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='camel-photos',
                name='fred_datetime10',
                a_relevant_datetime_date='',
                a_relevant_datetime_time='12:35:aa',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_date'],
                ['Date is required when a time is provided']
        )
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_valid_separate_time(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='camel-photos',
            name='fred_datetime11',
            a_relevant_datetime_date='2014-01-01',
            a_relevant_datetime_time='12:35:00',
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_datetime_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(type='camel-photos', name='derf_datetime', resources=[{
                'url': "http://example.com/camel.txt",
                'camels_in_photo': 2,
                'datetime': '2015-01-01T12:35:00'}])


class TestInvalidType(object):
    def test_invalid_dataset_type(self):
        p = SchemingDatasetsPlugin.instance
        data, errors = p.validate({}, {'type': 'banana'}, {}, 'dataset_show')
        assert_equals(list(errors), ['type'])

    def test_invalid_group_type(self):
        p = SchemingGroupsPlugin.instance
        data, errors = p.validate({}, {'type': 'banana'}, {}, 'dataset_show')
        assert_equals(list(errors), ['type'])
