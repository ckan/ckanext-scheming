from contextlib import contextmanager

import pylons

class FakeSession(object):
    last_accessed = None

class FakeRequest(object):
    def __init__(self):
        self.environ = {}
        self.params = {}

@contextmanager
def mock_pylons_request():
    # enough pylons to render a snippet
    pylons.response._push_object(pylons.Response())
    pylons.request._push_object(FakeRequest())
    pylons.session._push_object(FakeSession())
    pylons.tmpl_context._push_object({})
    pylons.url._push_object(None)
    yield
    pylons.response._pop_object()
    pylons.request._pop_object()
    pylons.session._pop_object()
    pylons.tmpl_context._pop_object()
    pylons.url._pop_object()
