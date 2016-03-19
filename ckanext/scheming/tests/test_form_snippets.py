from nose.tools import assert_in
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

