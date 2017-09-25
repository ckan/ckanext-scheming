import datetime
import pytz

from nose.tools import assert_raises, assert_equals
from ckanapi import LocalCKAN, ValidationError

from ckan.tests.helpers import FunctionalTestBase
from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import get_validator_or_converter, scheming_required
from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin, SchemingGroupsPlugin)
from ckantoolkit import get_validator

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


class TestChoices(FunctionalTestBase):
    def test_choice_field_only_accepts_given_choices(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type='test-schema',
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
            type='test-schema',
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
                type='test-schema',
                name='fred_date1',
                a_relevant_date='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_date2',
                a_relevant_date='31/11/abcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_date3',
                a_relevant_date='this-is-not-a-date',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_date'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_date4',
            a_relevant_date='2014-01-01',
        )
        assert_equals(d['a_relevant_date'], '2014-01-01')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_date5',
            a_relevant_date=datetime.datetime(2014, 1, 1),
        )
        assert_equals(d['a_relevant_date'], '2014-01-01')

    def test_date_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type='test-schema',
            name='derf_date', resources=[{
                'url': "http://example.com/camel.txt",
                'camels_in_photo': 2,
                'date': '2015-01-01'
            }]
        )


class TestDateTimes(object):
    def test_datetime_field_rejects_non_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime1',
                a_relevant_datetime='this-is-not-a-date',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_in_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime2',
                a_relevant_datetime='31/11/abcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_as_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime3',
                a_relevant_datetime='2014-11-15Tabcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_in_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime4',
                a_relevant_datetime='2014-11-15T12:00:ab',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime5',
                a_relevant_datetime='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime6',
            a_relevant_datetime='2014-01-01T12:35:00',
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime7',
            a_relevant_datetime=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_datetime_field_rejects_invalid_separate_date(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime8',
                a_relevant_datetime_date='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_date'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_separate_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime9',
                a_relevant_datetime_date='2014-01-01',
                a_relevant_datetime_time='12:35:aa',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_time'],
                          ['Time format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_time_only(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime10',
                a_relevant_datetime_time='12:35:00',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_date'],
                          ['Date is required when a time is provided'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_valid_separate_time(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime11',
            a_relevant_datetime_date='2014-01-01',
            a_relevant_datetime_time='12:35:00',
        )
        assert_equals(d['a_relevant_datetime'], '2014-01-01T12:35:00')

    def test_datetime_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type='test-schema',
            name='derf_datetime',
            resources=[{
                'url': "http://example.com/camel.txt",
                'camels_in_photo': 2,
                'datetime': '2015-01-01T12:35:00'
            }]
        )


class TestDateTimesTZ(object):
    def test_datetime_field_rejects_non_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz1',
                a_relevant_datetime_tz='this-is-not-a-date',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_in_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz2',
                a_relevant_datetime_tz='31/11/abcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_as_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz3',
                a_relevant_datetime_tz='2014-11-15Tabcd',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_text_in_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz4',
                a_relevant_datetime_tz='2014-11-15T12:00:ab',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz5',
                a_relevant_datetime_tz='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_timezone_identifier(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz6',
                a_relevant_datetime_tz='2014-11-15T12:00:00A',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_timezone_offset(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz5',
                a_relevant_datetime_tz='2014-11-15T12:00:00+abc',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz6',
            a_relevant_datetime_tz='2014-01-01T12:35:00',
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T12:35:00')

        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz7',
            a_relevant_datetime_tz='2014-01-01T12:35:00Z',
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T12:35:00')

        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz8',
            a_relevant_datetime_tz='2014-01-01T12:35:00+00:00',
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T12:35:00')

    def test_date_field_str_convert_to_utc(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz9',
            a_relevant_datetime_tz='2014-01-01T12:35:00-05:00',
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T17:35:00')

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz10',
            a_relevant_datetime_tz=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T12:35:00')

    def test_date_field_datetime_convert_to_utc(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz11',
            a_relevant_datetime_tz=datetime.datetime(
                2014, 1, 1, 12, 35, tzinfo=pytz.timezone('America/New_York')
            ),
        )

    def test_datetime_field_rejects_invalid_separate_date(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz12',
                a_relevant_datetime_tz_date='31/11/2014',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz_date'],
                          ['Date format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_separate_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz13',
                a_relevant_datetime_tz_date='2014-01-01',
                a_relevant_datetime_tz_time='12:35:aa',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz_time'],
                          ['Time format incorrect'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_invalid_separate_tz(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz14',
                a_relevant_datetime_tz_date='2014-01-01',
                a_relevant_datetime_tz_time='12:35:00',
                a_relevant_datetime_tz_tz='Krypton/Argo City',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz_tz'],
                          ['Invalid timezone'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_rejects_time_only(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='fred_datetime_tz15',
                a_relevant_datetime_tz_time='12:35:00',
            )
        except ValidationError as e:
            assert_equals(e.error_dict['a_relevant_datetime_tz_date'],
                          ['Date is required when a time is provided'])
        else:
            raise AssertionError('ValidationError not raised')

    def test_datetime_field_valid_separate_time(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type='test-schema',
            name='fred_datetime_tz16',
            a_relevant_datetime_tz_date='2014-01-01',
            a_relevant_datetime_tz_time='12:35:00',
            a_relevant_datetime_tz_tz='America/New_York',
        )
        assert_equals(d['a_relevant_datetime_tz'], '2014-01-01T17:35:00')

    def test_datetime_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type='test-schema',
            name='derf_datetime_tz',
            resources=[{
                'url': "http://example.com/camel.txt",
                'camels_in_photo': 2,
                'datetime_tz': '2015-01-01T12:35:00-05:00'
            }]
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


class TestJSONValidatorsDatasetValid(FunctionalTestBase):

    def test_valid_json_string_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type='test-schema',
            name='bob_json_1',
            a_json_field='{"a": 1, "b": 2}',
        )

        assert_equals(dataset['a_json_field'], {'a': 1, 'b': 2})

    def test_valid_json_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type='test-schema',
            name='bob_json_1',
            a_json_field={'a': 1, 'b': 2},
        )

        assert_equals(dataset['a_json_field'], {'a': 1, 'b': 2})


class TestJSONValidatorsResourceValid(FunctionalTestBase):

    def test_valid_json_string_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type='test-schema',
            name='bob_json_1',
            resources=[{
                'url': 'http://example.com/data.csv',
                'a_resource_json_field': '{"a": 1, "b": 2}'
            }],
        )

        assert_equals(
                dataset['resources'][0]['a_resource_json_field'],
                {'a': 1, 'b': 2})

    def test_valid_json_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type='test-schema',
            name='bob_json_1',
            resources=[{
                'url': 'http://example.com/data.csv',
                'a_resource_json_field': {'a': 1, 'b': 2}
            }],
        )

        assert_equals(
                dataset['resources'][0]['a_resource_json_field'],
                {'a': 1, 'b': 2})


class TestJSONValidatorsDatasetInvalid(object):

    def test_invalid_json_string_not_json(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                a_json_field='not-json',
            )
        except ValidationError as e:
            assert e.error_dict['a_json_field'][0].startswith(
                'Invalid JSON string: No JSON object could be decoded')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_string_values(self):
        lc = LocalCKAN()
        values = [
            '22',
            'true',
            'false',
            'null',
            '[1,2,3]',
        ]
        for value in values:
            try:
                lc.action.package_create(
                    type='test-schema',
                    name='bob_json_1',
                    a_json_field=value,
                )
            except ValidationError as e:
                assert e.error_dict['a_json_field'][0].startswith(
                    'Unsupported value for JSON field')
            else:
                raise AssertionError('ValidationError not raised')

    def test_invalid_json_string(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                a_json_field='{"type": "walnut", "codes": 1, 2 ,3}',
            )
        except ValidationError as e:
            assert e.error_dict['a_json_field'][0].startswith(
                'Invalid JSON string: Expecting property name')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_object(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                a_json_field={
                    'type': 'walnut',
                    'date': datetime.datetime.utcnow()
                },
            )
        except ValidationError as e:
            assert e.error_dict['a_json_field'][0].startswith(
                'Invalid JSON object:')
            assert e.error_dict['a_json_field'][0].endswith(
                'is not JSON serializable')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_value(self):
        lc = LocalCKAN()

        values = [
            True,
            datetime.datetime.utcnow(),
            (2, 3),
            23,
            [1, 2, 3],
        ]
        for value in values:
            try:
                lc.action.package_create(
                    type='test-schema',
                    name='bob_json_1',
                    a_json_field=value,
                )
            except ValidationError as e:
                assert e.error_dict['a_json_field'][0].startswith(
                    'Unsupported type for JSON field:')
            else:
                raise AssertionError('ValidationError not raised')


class TestJSONValidatorsResourceInvalid(object):

    def test_invalid_json_string_not_json(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                resources=[{
                    'url': 'http://example.com/data.csv',
                    'a_resource_json_field': 'not-json',
                }],
            )
        except ValidationError as e:
            assert e.error_dict['resources'][0]['a_resource_json_field'][0].startswith(
                'Invalid JSON string: No JSON object could be decoded')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_string_values(self):
        lc = LocalCKAN()
        values = [
            '22',
            'true',
            'false',
            'null',
            '[1,2,3]',
        ]
        for value in values:
            try:
                lc.action.package_create(
                    type='test-schema',
                    name='bob_json_1',
                    resources=[{
                        'url': 'http://example.com/data.csv',
                        'a_resource_json_field': value
                    }],
                )
            except ValidationError as e:
                assert e.error_dict['resources'][0]['a_resource_json_field'][0].startswith(
                    'Unsupported value for JSON field')
            else:
                raise AssertionError('ValidationError not raised')

    def test_invalid_json_string(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                resources=[{
                    'url': 'http://example.com/data.csv',
                    'a_resource_json_field': '{"type": "walnut", "codes": 1, 2 ,3}'
                }],
            )
        except ValidationError as e:
            assert e.error_dict['resources'][0]['a_resource_json_field'][0].startswith(
                'Invalid JSON string: Expecting property name')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_object(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type='test-schema',
                name='bob_json_1',
                resources=[{
                    'url': 'http://example.com/data.csv',
                    'a_resource_json_field': {
                        'type': 'walnut',
                        'date': datetime.datetime.utcnow()
                    }
                }],
            )
        except ValidationError as e:
            assert e.error_dict['resources'][0]['a_resource_json_field'][0].startswith(
                'Invalid JSON object:')
            assert e.error_dict['resources'][0]['a_resource_json_field'][0].endswith(
                'is not JSON serializable')
        else:
            raise AssertionError('ValidationError not raised')

    def test_invalid_json_value(self):
        lc = LocalCKAN()

        values = [
            True,
            datetime.datetime.utcnow(),
            (2, 3),
            [2, 3],
            23
        ]
        for value in values:
            try:
                lc.action.package_create(
                    type='test-schema',
                    name='bob_json_1',
                    resources=[{
                        'url': 'http://example.com/data.csv',
                        'a_resource_json_field': value
                    }],
                )
            except ValidationError as e:
                assert e.error_dict['resources'][0]['a_resource_json_field'][0].startswith(
                    'Unsupported type for JSON field:')
            else:
                raise AssertionError('ValidationError not raised')
