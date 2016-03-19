from nose.tools import assert_in, assert_not_in
from ckantoolkit import h
from ckan.lib.base import render_snippet

from ckanext.scheming.tests.mock_pylons_request import mock_pylons_request

def render_form_snippet(name, data=None, **kwargs):
    field = {
        'field_name': 'test',
        'label': 'Test',
    }
    field.update(kwargs)
    with mock_pylons_request():
        return render_snippet(
            'scheming/form_snippets/' + name,
            field=field,
            h=h,
            data=data,
            errors=None,
        )

class TestSelectFormSnippet(object):
    def test_choices_visible(self):
        html = render_form_snippet(
            'select.html',
            choices=[{'value': 'one', 'label': 'One'}])
        assert_in('<option value="one">One</option>', html)

    def test_blank_choice_shown(self):
        html = render_form_snippet(
            'select.html',
            choices=[{'value': 'two', 'label': 'Two'}])
        assert_in('<option value="">', html)

    def test_no_blank_choice_on_required(self):
        html = render_form_snippet(
            'select.html',
            choices=[{'value': 'three', 'label': 'Three'}],
            required=True)
        assert_not_in('<option value="">', html)

    def test_blank_choice_shown_on_form_include_blank(self):
        html = render_form_snippet(
            'select.html',
            choices=[{'value': 'four', 'label': 'Four'}],
            required=True,
            form_include_blank_choice=True)
        assert_in('<option value="">', html)

    def test_restrict_choices_to(self):
        html = render_form_snippet(
            'select.html',
            choices=[
                {'value': 'five', 'label': 'Five'},
                {'value': 'six', 'label': 'Six'},
                {'value': 'seven', 'label': 'Seven'}],
            form_restrict_choices_to=['five', 'seven'])
        assert_in('<option value="five">', html)
        assert_not_in('<option value="six">', html)
        assert_in('<option value="seven">', html)

    def test_choice_order_maintained(self):
        html = render_form_snippet(
            'select.html',
            choices=[
                {'value': 'z', 'label': 'Zee'},
                {'value': 'y', 'label': 'Why'},
                {'value': 'x', 'label': 'Ecks'}])
        first, rest = html.split('<option value="z">', 1)
        assert_in('<option value="y">', rest)
        middle, last = rest.split('<option value="y">', 1)
        assert_in('<option value="x">', last)

    def test_choices_sorted_by_label(self):
        html = render_form_snippet(
            'select.html',
            choices=[
                {'value': 'a', 'label': 'Eh'},
                {'value': 'c', 'label': 'Sea'},
                {'value': 'b', 'label': 'Bee'}],
            sorted_choices=True)
        first, rest = html.split('<option value="b">', 1)
        assert_in('<option value="a">', rest)
        middle, last = rest.split('<option value="a">', 1)
        assert_in('<option value="c">', last)
