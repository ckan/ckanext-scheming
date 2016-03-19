from nose.tools import assert_in
from ckantoolkit import h

from ckan.lib.base import render_snippet
import pylons

class FakeSession(object):
    last_accessed = None

class FakeRequest(object):
    def __init__(self):
        self.environ = {}
        self.params = {}

def render_form_snippet(name, data=None, **kwargs):
    # enough pylons to render a snippet
    pylons.response._push_object(pylons.Response())
    pylons.request._push_object(FakeRequest())
    pylons.session._push_object(FakeSession())
    pylons.tmpl_context._push_object({})
    pylons.url._push_object(None)

    try:
        field = {
            'field_name': 'test',
            'label': 'Test',
        }
        field.update(kwargs)
        return render_snippet(
            'scheming/form_snippets/' + name,
            field=field,
            h=h,
            data=data,
            errors=None,
        )
    finally:
        pylons.response._pop_object()
        pylons.request._pop_object()
        pylons.session._pop_object()
        pylons.tmpl_context._pop_object()
        pylons.url._pop_object()


class TestSelectFormSnippet(object):
    def test_choices_visible(self):
        html = render_form_snippet(
            'select.html',
            choices=[{'value': 'one', 'label': 'One'}])
        assert_in('<option value="one">One</option>', html)

