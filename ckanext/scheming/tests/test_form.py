from nose.tools import assert_true

from ckan.new_tests.factories import Sysadmin
from ckan.new_tests.helpers import FunctionalTestBase

def _get_package_new_page_as_sysadmin(app):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/camel-photos/new',
        extra_environ=env,
    )
    return env, response


class TestDatasetFormNew(FunctionalTestBase):
    def test_form_includes_custom_dataset_fields(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        print list(form.fields)

