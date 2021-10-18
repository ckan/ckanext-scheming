import datetime
import pytz

import pytest
from ckanapi import LocalCKAN, ValidationError


from ckanext.scheming.errors import SchemingException
from ckanext.scheming.validation import (
    get_validator_or_converter,
    scheming_required,
)
from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin,
    SchemingGroupsPlugin,
)
from ckantoolkit import get_validator, check_ckan_version

ignore_missing = get_validator("ignore_missing")
not_empty = get_validator("not_empty")


class TestGetValidatorOrConverter(object):
    def test_missing(self):
        with pytest.raises(SchemingException):
            get_validator_or_converter("not_a_real_validator_name")

    def test_validator_name(self):
        assert get_validator_or_converter("not_empty")

    def test_converter_name(self):
        assert get_validator_or_converter("remove_whitespace")


@pytest.mark.usefixtures("clean_db")
class TestChoices(object):
    def test_choice_field_only_accepts_given_choices(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type="test-schema", name="fred_choices1", category="rocker"
            )
        except ValidationError as e:
            if check_ckan_version("2.9"):
                expected = "Value must be one of {}".format(
                    [
                        u"bactrian",
                        u"hybrid",
                        u"f2hybrid",
                        u"snowwhite",
                        u"black",
                    ]
                )
            else:
                expected = (
                    "Value must be one of: bactrian; hybrid; f2hybrid; "
                    "snowwhite; black (not 'rocker')"
                )
            assert e.error_dict["category"] == [expected]
        else:
            raise AssertionError("ValidationError not raised")

    def test_choice_field_accepts_valid_choice(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema", name="fred_choices2", category="f2hybrid"
        )
        assert d["category"] == "f2hybrid"


class TestRequired(object):
    def test_required_is_set_to_true(self):
        assert not_empty == scheming_required({"required": True}, {})

    def test_required_is_set_to_false(self):
        assert ignore_missing == scheming_required({"required": False}, {})

    def test_required_is_not_present(self):
        assert ignore_missing == scheming_required({"other_field": True}, {})


class TestDates(object):
    def test_date_field_rejects_non_isodates(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_date1",
                a_relevant_date="31/11/2014",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_date"] == ["Date format incorrect"]
        else:
            raise AssertionError("ValidationError not raised")

        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_date2",
                a_relevant_date="31/11/abcd",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_date"] == ["Date format incorrect"]
        else:
            raise AssertionError("ValidationError not raised")

        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_date3",
                a_relevant_date="this-is-not-a-date",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_date"] == ["Date format incorrect"]
        else:
            raise AssertionError("ValidationError not raised")

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema", name="fred_date4", a_relevant_date="2014-01-01"
        )
        assert d["a_relevant_date"] == "2014-01-01"

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_date5",
            a_relevant_date=datetime.datetime(2014, 1, 1),
        )
        assert d["a_relevant_date"] == "2014-01-01"

    def test_date_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type="test-schema",
            name="derf_date",
            resources=[
                {
                    "url": "http://example.com/camel.txt",
                    "camels_in_photo": 2,
                    "date": "2015-01-01",
                }
            ],
        )


class TestDateTimes(object):
    def test_datetime_field_rejects_non_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime1",
                a_relevant_datetime="this-is-not-a-date",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_in_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime2",
                a_relevant_datetime="31/11/abcd",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_as_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime3",
                a_relevant_datetime="2014-11-15Tabcd",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_in_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime4",
                a_relevant_datetime="2014-11-15T12:00:ab",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime5",
                a_relevant_datetime="31/11/2014",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime6",
            a_relevant_datetime="2014-01-01T12:35:00",
        )
        assert d["a_relevant_datetime"] == "2014-01-01T12:35:00"

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime7",
            a_relevant_datetime=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert d["a_relevant_datetime"] == "2014-01-01T12:35:00"

    def test_datetime_field_rejects_invalid_separate_date(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime8",
                a_relevant_datetime_date="31/11/2014",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_date"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_invalid_separate_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime9",
                a_relevant_datetime_date="2014-01-01",
                a_relevant_datetime_time="12:35:aa",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_time"] == [
                "Time format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_time_only(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime10",
                a_relevant_datetime_time="12:35:00",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_date"] == [
                "Date is required when a time is provided"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_valid_separate_time(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime11",
            a_relevant_datetime_date="2014-01-01",
            a_relevant_datetime_time="12:35:00",
        )
        assert d["a_relevant_datetime"] == "2014-01-01T12:35:00"

    def test_datetime_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type="test-schema",
            name="derf_datetime",
            resources=[
                {
                    "url": "http://example.com/camel.txt",
                    "camels_in_photo": 2,
                    "datetime": "2015-01-01T12:35:00",
                }
            ],
        )


class TestDateTimesTZ(object):
    def test_datetime_field_rejects_non_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz1",
                a_relevant_datetime_tz="this-is-not-a-date",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_in_dates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz2",
                a_relevant_datetime_tz="31/11/abcd",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_as_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz3",
                a_relevant_datetime_tz="2014-11-15Tabcd",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_text_in_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz4",
                a_relevant_datetime_tz="2014-11-15T12:00:ab",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_non_isodates(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz5",
                a_relevant_datetime_tz="31/11/2014",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_invalid_timezone_identifier(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz6",
                a_relevant_datetime_tz="2014-11-15T12:00:00A",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_invalid_timezone_offset(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz5",
                a_relevant_datetime_tz="2014-11-15T12:00:00+abc",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_date_field_valid_date_str(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz6",
            a_relevant_datetime_tz="2014-01-01T12:35:00",
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T12:35:00"

        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz7",
            a_relevant_datetime_tz="2014-01-01T12:35:00Z",
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T12:35:00"

        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz8",
            a_relevant_datetime_tz="2014-01-01T12:35:00+00:00",
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T12:35:00"

    def test_date_field_str_convert_to_utc(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz9",
            a_relevant_datetime_tz="2014-01-01T12:35:00-05:00",
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T17:35:00"

    def test_date_field_valid_date_datetime(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz10",
            a_relevant_datetime_tz=datetime.datetime(2014, 1, 1, 12, 35),
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T12:35:00"

    def test_date_field_datetime_convert_to_utc(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz11",
            a_relevant_datetime_tz=datetime.datetime(
                2014, 1, 1, 12, 35, tzinfo=pytz.timezone("America/New_York")
            ),
        )

    def test_datetime_field_rejects_invalid_separate_date(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz12",
                a_relevant_datetime_tz_date="31/11/2014",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz_date"] == [
                "Date format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_invalid_separate_time(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz13",
                a_relevant_datetime_tz_date="2014-01-01",
                a_relevant_datetime_tz_time="12:35:aa",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz_time"] == [
                "Time format incorrect"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_invalid_separate_tz(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz14",
                a_relevant_datetime_tz_date="2014-01-01",
                a_relevant_datetime_tz_time="12:35:00",
                a_relevant_datetime_tz_tz="Krypton/Argo City",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz_tz"] == [
                "Invalid timezone"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_rejects_time_only(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="fred_datetime_tz15",
                a_relevant_datetime_tz_time="12:35:00",
            )
        except ValidationError as e:
            assert e.error_dict["a_relevant_datetime_tz_date"] == [
                "Date is required when a time is provided"
            ]
        else:
            raise AssertionError("ValidationError not raised")

    def test_datetime_field_valid_separate_time(self):
        lc = LocalCKAN()
        d = lc.action.package_create(
            type="test-schema",
            name="fred_datetime_tz16",
            a_relevant_datetime_tz_date="2014-01-01",
            a_relevant_datetime_tz_time="12:35:00",
            a_relevant_datetime_tz_tz="America/New_York",
        )
        assert d["a_relevant_datetime_tz"] == "2014-01-01T17:35:00"

    def test_datetime_field_in_resource(self):
        lc = LocalCKAN()
        lc.action.package_create(
            type="test-schema",
            name="derf_datetime_tz",
            resources=[
                {
                    "url": "http://example.com/camel.txt",
                    "camels_in_photo": 2,
                    "datetime_tz": "2015-01-01T12:35:00-05:00",
                }
            ],
        )


class TestInvalidType(object):
    def test_invalid_dataset_type(self):
        p = SchemingDatasetsPlugin.instance
        data, errors = p.validate({}, {"type": "banana"}, {}, "dataset_show")
        assert list(errors) == ["type"]

    def test_invalid_group_type(self):
        p = SchemingGroupsPlugin.instance
        data, errors = p.validate({}, {"type": "banana"}, {}, "dataset_show")
        assert list(errors) == ["type"]


@pytest.mark.usefixtures("clean_db")
class TestJSONValidatorsDatasetValid(object):
    def test_valid_json_string_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-schema",
            name="bob_json_1",
            a_json_field='{"a": 1, "b": 2}',
        )

        assert dataset["a_json_field"] == {"a": 1, "b": 2}

    def test_valid_json_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-schema",
            name="bob_json_1",
            a_json_field={"a": 1, "b": 2},
        )

        assert dataset["a_json_field"] == {"a": 1, "b": 2}


@pytest.mark.usefixtures("clean_db")
class TestJSONValidatorsResourceValid(object):
    def test_valid_json_string_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-schema",
            name="bob_json_1",
            resources=[
                {
                    "url": "http://example.com/data.csv",
                    "a_resource_json_field": '{"a": 1, "b": 2}',
                }
            ],
        )

        assert dataset["resources"][0]["a_resource_json_field"] == {
            "a": 1,
            "b": 2,
        }

    def test_valid_json_object(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-schema",
            name="bob_json_1",
            resources=[
                {
                    "url": "http://example.com/data.csv",
                    "a_resource_json_field": {"a": 1, "b": 2},
                }
            ],
        )

        assert dataset["resources"][0]["a_resource_json_field"] == {
            "a": 1,
            "b": 2,
        }


class TestJSONValidatorsDatasetInvalid(object):
    def test_invalid_json_string_not_json(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type="test-schema", name="bob_json_1", a_json_field="not-json"
            )
        except ValidationError as e:
            assert e.error_dict["a_json_field"][0].startswith(
                "Invalid JSON string:"
            )
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_string_values(self):
        lc = LocalCKAN()
        values = ["22", "true", "false", "null", "[1,2,3]"]
        for value in values:
            try:
                lc.action.package_create(
                    type="test-schema", name="bob_json_1", a_json_field=value
                )
            except ValidationError as e:
                assert e.error_dict["a_json_field"][0].startswith(
                    "Unsupported value for JSON field"
                )
            else:
                raise AssertionError("ValidationError not raised")

    def test_invalid_json_string(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="bob_json_1",
                a_json_field='{"type": "walnut", "codes": 1, 2 ,3}',
            )
        except ValidationError as e:
            assert e.error_dict["a_json_field"][0].startswith(
                "Invalid JSON string: Expecting property name"
            )
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_object(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="bob_json_1",
                a_json_field={
                    "type": "walnut",
                    "date": datetime.datetime.utcnow(),
                },
            )
        except ValidationError as e:
            assert e.error_dict["a_json_field"][0].startswith(
                "Invalid JSON object:"
            )
            assert e.error_dict["a_json_field"][0].endswith(
                "is not JSON serializable"
            )
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_value(self):
        lc = LocalCKAN()

        values = [True, datetime.datetime.utcnow(), (2, 3), 23, [1, 2, 3]]
        for value in values:
            try:
                lc.action.package_create(
                    type="test-schema", name="bob_json_1", a_json_field=value
                )
            except ValidationError as e:
                assert e.error_dict["a_json_field"][0].startswith(
                    "Unsupported type for JSON field:"
                )
            else:
                raise AssertionError("ValidationError not raised")


class TestJSONValidatorsResourceInvalid(object):
    def test_invalid_json_string_not_json(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="bob_json_1",
                resources=[
                    {
                        "url": "http://example.com/data.csv",
                        "a_resource_json_field": "not-json",
                    }
                ],
            )
        except ValidationError as e:
            assert e.error_dict["resources"][0]["a_resource_json_field"][
                0
            ].startswith("Invalid JSON string:")
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_string_values(self):
        lc = LocalCKAN()
        values = ["22", "true", "false", "null", "[1,2,3]"]
        for value in values:
            try:
                lc.action.package_create(
                    type="test-schema",
                    name="bob_json_1",
                    resources=[
                        {
                            "url": "http://example.com/data.csv",
                            "a_resource_json_field": value,
                        }
                    ],
                )
            except ValidationError as e:
                assert e.error_dict["resources"][0]["a_resource_json_field"][
                    0
                ].startswith("Unsupported value for JSON field")
            else:
                raise AssertionError("ValidationError not raised")

    def test_invalid_json_string(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="bob_json_1",
                resources=[
                    {
                        "url": "http://example.com/data.csv",
                        "a_resource_json_field": '{"type": "walnut", "codes": 1, 2 ,3}',
                    }
                ],
            )
        except ValidationError as e:
            assert e.error_dict["resources"][0]["a_resource_json_field"][
                0
            ].startswith("Invalid JSON string: Expecting property name")
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_object(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-schema",
                name="bob_json_1",
                resources=[
                    {
                        "url": "http://example.com/data.csv",
                        "a_resource_json_field": {
                            "type": "walnut",
                            "date": datetime.datetime.utcnow(),
                        },
                    }
                ],
            )
        except ValidationError as e:
            assert e.error_dict["resources"][0]["a_resource_json_field"][
                0
            ].startswith("Invalid JSON object:")
            assert e.error_dict["resources"][0]["a_resource_json_field"][
                0
            ].endswith("is not JSON serializable")
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_json_value(self):
        lc = LocalCKAN()

        values = [True, datetime.datetime.utcnow(), (2, 3), [2, 3], 23]
        for value in values:
            try:
                lc.action.package_create(
                    type="test-schema",
                    name="bob_json_1",
                    resources=[
                        {
                            "url": "http://example.com/data.csv",
                            "a_resource_json_field": value,
                        }
                    ],
                )
            except ValidationError as e:
                assert e.error_dict["resources"][0]["a_resource_json_field"][
                    0
                ].startswith("Unsupported type for JSON field:")
            else:
                raise AssertionError("ValidationError not raised")


@pytest.mark.usefixtures("clean_db")
class TestSubfieldDatasetValid(object):
    def test_valid_subfields(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-subfields",
            name="a_sf_1",
            citation=[
                {"originator": ["mei"], "publication_date": "2021-01-01"},
                {"originator": ["ahmed"]}
            ],
            contact_address=[{"address": "anyplace"}],
        )

        assert dataset["citation"] == [
            {"originator": ["mei"], "publication_date": "2021-01-01"},
            {"originator": ["ahmed"]}
        ]
        assert dataset["contact_address"] == [{"address": "anyplace"}]

    def test_empty_subfields(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-subfields",
            name="a_sf_1",
            citation=[],
            contact_address=[],
        )

        # current behaviour, would empty lists be better?
        assert "citation" not in dataset
        assert "contact_address" not in dataset


class TestSubfieldDatasetInvalid(object):
    def test_invalid_missing_required_subfield(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type="test-subfields",
                name="b_sf_1",
                citation=[{"publication_date": "2021-01-01"}, {"originator": ["ahmed"]}],
                contact_address=[{"address": "anyplace"}],
            )
        except ValidationError as e:
            assert e.error_dict["citation"][0]["originator"] == ["Missing value"]
        else:
            raise AssertionError("ValidationError not raised")

    def test_invalid_bad_date_subfield(self):
        lc = LocalCKAN()

        try:
            lc.action.package_create(
                type="test-subfields",
                name="b_sf_1",
                citation=[
                    {"originator": ["mei"], "publication_date": "yesterday"},
                    {"originator": ["ahmed"]}
                ],
                contact_address=[{"address": "anyplace"}],
            )
        except ValidationError as e:
            assert e.error_dict["citation"][0]["publication_date"] == ["Date format incorrect"]
        else:
            raise AssertionError("ValidationError not raised")


@pytest.mark.usefixtures("clean_db")
class TestSubfieldResourceValid(object):
    def test_simple(self):
        lc = LocalCKAN()
        dataset = lc.action.package_create(
            type="test-subfields",
            name="c_sf_1",
            resources=[
                {
                    "url": "http://example.com/data.csv",
                    "schedule": [
                        {"impact": "A", "frequency": "1m"},
                        {"impact": "P", "frequency": "7d"},
                    ]
                }
            ],
        )

        assert dataset["resources"][0]["schedule"] == [
            {"impact": "A", "frequency": "1m"},
            {"impact": "P", "frequency": "7d"},
        ]


class TestSubfieldResourceInvalid(object):
    def test_invalid_choice(self):
        lc = LocalCKAN()
        try:
            lc.action.package_create(
                type="test-subfields",
                name="c_sf_1",
                resources=[
                    {
                        "url": "http://example.com/data.csv",
                        "schedule": [
                            {"impact": "Q", "frequency": "1m"},
                            {"impact": "P", "frequency": "7d"},
                        ]
                    }
                ],
            )
        except ValidationError as e:
            assert e.error_dict["resources"][0]["schedule"][0]["impact"][0
                ].startswith("Value must be one of")
        else:
            raise AssertionError("ValidationError not raised")
