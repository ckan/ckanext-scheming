import six
import pytest
import bs4
from ckan.lib.base import render_snippet
from jinja2 import Markup

import ckantoolkit

if ckantoolkit.check_ckan_version(min_version='2.9.0'):
    from contextlib import contextmanager
    @contextmanager
    def mock_pylons_request():
        yield
else:
    from ckanext.scheming.tests.mock_pylons_request import mock_pylons_request


def render_form_snippet(name, data=None, extra_args=None, errors=None, **kwargs):
    field = {"field_name": "test", "label": "Test"}
    field.update(kwargs)
    with mock_pylons_request():
        return render_snippet(
            "scheming/form_snippets/" + name,
            field=field,
            data=data or {},
            errors=errors or {},
            **(extra_args or {})
        )


@pytest.mark.usefixtures("with_request_context")
class TestSelectFormSnippet(object):
    def test_choices_visible(self):
        html = render_form_snippet(
            "select.html", choices=[{"value": "one", "label": "One"}]
        )
        assert '<option value="one">One</option>' in html

    def test_blank_choice_shown(self):
        html = render_form_snippet(
            "select.html", choices=[{"value": "two", "label": "Two"}]
        )
        assert '<option value="">' in html

    def test_no_blank_choice_on_required(self):
        html = render_form_snippet(
            "select.html",
            choices=[{"value": "three", "label": "Three"}],
            required=True,
        )
        assert '<option value="">' not in html

    def test_blank_choice_shown_on_form_include_blank(self):
        html = render_form_snippet(
            "select.html",
            choices=[{"value": "four", "label": "Four"}],
            required=True,
            form_include_blank_choice=True,
        )
        assert '<option value="">' in html

    def test_restrict_choices_to(self):
        html = render_form_snippet(
            "select.html",
            choices=[
                {"value": "five", "label": "Five"},
                {"value": "six", "label": "Six"},
                {"value": "seven", "label": "Seven"},
            ],
            form_restrict_choices_to=["five", "seven"],
        )
        assert '<option value="five">' in html
        assert '<option value="six">' not in html
        assert '<option value="seven">' in html

    def test_choice_order_maintained(self):
        html = render_form_snippet(
            "select.html",
            choices=[
                {"value": "z", "label": "Zee"},
                {"value": "y", "label": "Why"},
                {"value": "x", "label": "Ecks"},
            ],
        )
        first, rest = html.split('<option value="z">', 1)
        assert '<option value="y">' in rest
        middle, last = rest.split('<option value="y">', 1)
        assert '<option value="x">' in last

    def test_choices_sorted_by_label(self):
        html = render_form_snippet(
            "select.html",
            choices=[
                {"value": "a", "label": "Eh"},
                {"value": "c", "label": "Sea"},
                {"value": "b", "label": "Bee"},
            ],
            sorted_choices=True,
        )
        first, rest = html.split('<option value="b">', 1)
        assert '<option value="a">' in rest
        middle, last = rest.split('<option value="a">', 1)
        assert '<option value="c">' in last


def organization_option_tag(organization, selected_org):
    return Markup(
        '<option value="{orgid}"{selected}>'
        "{display_name}</option>".format(
            orgid=organization["id"],
            selected=" selected" if selected_org else "",
            display_name=organization["display_name"],
        )
    )


@pytest.mark.usefixtures("with_request_context")
class TestOrganizationFormSnippet(object):
    # It's hard to unit test 'form_snippets/organization.html' because it
    # fetches lists of orgs for the current user, so here we're just testing
    # the org selection part.
    # XXX: Add functional testing in test_form.py to cover that

    def test_organizations_visible(self):
        html = render_form_snippet(
            "_organization_select.html",
            extra_args={
                "organizations_available": [
                    {"id": "1", "display_name": "One"}
                ],
                "organization_option_tag": organization_option_tag,
                "org_required": False,
            },
        )
        assert '<option value="1">One</option>' in html

    def test_no_organization_shown(self):
        html = render_form_snippet(
            "_organization_select.html",
            extra_args={
                "organizations_available": [
                    {"id": "1", "display_name": "One"}
                ],
                "organization_option_tag": organization_option_tag,
                "org_required": False,
            },
        )
        assert '<option value="">No organization' in html

    def test_no_organization_hidden_when_required(self):
        html = render_form_snippet(
            "_organization_select.html",
            extra_args={
                "organizations_available": [
                    {"id": "1", "display_name": "One"}
                ],
                "organization_option_tag": organization_option_tag,
                "org_required": True,
            },
        )
        assert '<option value="">' not in html

    def test_blank_choice_shown_when_required(self):
        html = render_form_snippet(
            "_organization_select.html",
            form_include_blank_choice=True,
            extra_args={
                "organizations_available": [
                    {"id": "1", "display_name": "One"}
                ],
                "organization_option_tag": organization_option_tag,
                "org_required": True,
            },
        )
        assert '<option value=""></option>' in html


@pytest.mark.usefixtures("with_request_context")
class TestLicenseFormSnippet(object):
    def test_license_choices_visible(self):
        html = render_form_snippet(
            "license.html",
            extra_args={"licenses": [("Aaa", "aa"), ("Bbb", "bb")]},
        )
        assert '<option value="aa">Aaa</option>' in html
        assert '<option value="bb">Bbb</option>' in html

    def test_license_sorted_by_default(self):
        html = render_form_snippet(
            "license.html",
            extra_args={"licenses": [("Zzz", "zz"), ("Bbb", "bb")]},
        )
        assert '<option value="bb">' in html
        first, rest = html.split('<option value="bb">', 1)
        assert '<option value="zz">' in rest

    def test_license_order_maintained_when_sorted_false(self):
        html = render_form_snippet(
            "license.html",
            sorted_choices=False,
            extra_args={"licenses": [("Zzz", "zz"), ("Bbb", "bb")]},
        )
        assert '<option value="zz">' in html
        first, rest = html.split('<option value="zz">', 1)
        assert '<option value="bb">' in rest

    def test_blank_choice_shown_on_form_include_blank(self):
        html = render_form_snippet(
            "license.html",
            form_include_blank_choice=True,
            extra_args={"licenses": [("Aaa", "aa"), ("Bbb", "bb")]},
        )
        assert '<option value=""></option>' in html


@pytest.mark.usefixtures("with_request_context")
class TestJSONFormSnippet(object):
    def test_json_value(self):
        html = render_form_snippet(
            "json.html",
            field_name="a_json_field",
            data={"a_json_field": {"a": "1", "b": "2"}},
        )
        # It may seem unexpected, but JSONEncoder in Py2 adds
        # whitespace after comma for better readability. A lot if
        # editors/IDE strips leading whitespace in a line so it's
        # better to explicitly write expected result using escape
        # sequence.
        if six.PY3:
            expected = """{\n  "a": "1",\n  "b": "2"\n}"""
        else:
            expected = """{\n  "a": "1", \n  "b": "2"\n}"""

        expected = expected.replace('"', "&#34;")  # Ask webhelpers

        assert expected in html

    def test_json_value_no_indent(self):
        html = render_form_snippet(
            "json.html",
            field_name="a_json_field",
            data={"a_json_field": {"a": "1", "b": "2"}},
            indent=None,
        )
        expected = """{"a": "1", "b": "2"}""".replace('"', "&#34;")

        assert expected in html

    def test_json_value_is_empty_with_no_value(self):
        html = render_form_snippet(
            "json.html", field_name="a_json_field", data={"a_json_field": ""}
        )
        expected = "></textarea>"

        assert expected in html

    def test_json_value_is_displayed_correctly_if_string(self):
        value = '{"a": 1, "b": 2}'
        html = render_form_snippet(
            "json.html",
            field_name="a_json_field",
            data={"a_json_field": value},
        )
        expected = value.replace('"', "&#34;")

        assert expected in html


@pytest.mark.usefixtures("with_request_context")
class TestRepeatingSubfieldsFormSnippet(object):
    def test_form_attrs_on_fieldset(self):
        html = render_form_snippet(
            "repeating_subfields.html",
            field_name="repeating",
            repeating_subfields=[{"field_name": "x"}],
            form_attrs={"data-module": "test-attrs"},
        )
        snippet = bs4.BeautifulSoup(html)
        attr_holder = snippet.select_one(".controls").div
        assert attr_holder['data-module'] == 'test-attrs'


@pytest.mark.usefixtures("with_request_context")
class TestRadioFormSnippet(object):
    def test_radio_choices(self):
        html = render_form_snippet(
            "radio.html",
            field_name="radio-group",
            choices=[
                {"value": "one", "label": "One"}
            ],
        )
        snippet = bs4.BeautifulSoup(html)
        attr_holder = snippet.select_one(".controls").label
        assert attr_holder.text.strip() == 'One' \
            and attr_holder.input["value"].strip() == 'one'

    def test_radio_checked(self):
        html = render_form_snippet(
            "radio.html",
            field_name="radio-group",
            data={"radio-group": "one"},
            choices=[
                {"value": "one", "label": "One"}
            ],
        )
        snippet = bs4.BeautifulSoup(html)
        attr_holder = snippet.select_one(".controls").input
        assert attr_holder.has_attr('checked')
