import json

from nose import SkipTest
from nose.tools import assert_true, assert_in, assert_equals


from ckantoolkit.tests.factories import Sysadmin, Dataset
from ckantoolkit.tests.helpers import (
    FunctionalTestBase, submit_and_follow, call_action
)


def _get_package_new_page_as_sysadmin(app):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/test-schema/new',
        extra_environ=env,
    )
    return env, response


def _get_package_update_page_as_sysadmin(app, id):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/test-schema/edit/{}'.format(id),
        extra_environ=env,
    )
    return env, response


def _get_resource_new_page_as_sysadmin(app, id):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/dataset/new_resource/{}'.format(id),
        extra_environ=env,
    )
    return env, response


def _get_resource_update_page_as_sysadmin(app, id, resource_id):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/dataset/{}/resource_edit/{}'.format(id, resource_id),
        extra_environ=env,
    )
    return env, response


def _get_organization_new_page_as_sysadmin(app):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/organization/new',
        extra_environ=env,
    )
    return env, response


def _get_group_new_page_as_sysadmin(app):
    user = Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url='/group/new',
        extra_environ=env,
    )
    return env, response



class TestDatasetFormNew(FunctionalTestBase):
    def test_dataset_form_includes_custom_fields(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        assert_true('humps' in form.fields)

    def test_dataset_form_slug_says_dataset(self):
        """The default prefix shouldn't be /packages?id="""
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        assert_true('packages?id=' not in response.body)
        assert_true('/dataset/' in response.body)

    def test_resource_form_includes_custom_fields(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        form['name'] = 'resource-includes-custom'

        response = submit_and_follow(app, form, env, 'save')
        form = response.forms['resource-edit']
        assert_true('camels_in_photo' in form.fields)


class TestOrganizationFormNew(FunctionalTestBase):
    def test_organization_form_includes_custom_field(self):
        app = self._get_test_app()
        env, response = _get_organization_new_page_as_sysadmin(app)
        form = response.forms[1]  # FIXME: add an id to this form

        # FIXME: generate the form for orgs (this is currently missing)
        assert_true('department_id' in form.fields)


class TestGroupFormNew(FunctionalTestBase):
    def test_group_form_includes_custom_field(self):
        app = self._get_test_app()
        env, response = _get_group_new_page_as_sysadmin(app)
        form = response.forms[1]  # FIXME: add an id to this form

        # FIXME: generate the form for orgs (this is currently missing)
        # Failing until https://github.com/ckan/ckan/pull/2617 is merged
        # assert_true('bookface' in form.fields)
        raise SkipTest


class TestJSONDatasetForm(FunctionalTestBase):

    def test_dataset_form_includes_json_fields(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']
        assert_in('a_json_field', form.fields)
        assert_equals(form.fields['a_json_field'][0].tag, 'textarea')

    def test_dataset_form_create(self):
        app = self._get_test_app()
        env, response = _get_package_new_page_as_sysadmin(app)
        form = response.forms['dataset-edit']

        value = {
            'a': 1,
            'b': 2,
        }
        json_value = json.dumps(value)

        form['name'] = 'json_dataset_1'
        form['a_json_field'] = json_value

        submit_and_follow(app, form, env, 'save')

        dataset = call_action('package_show', id='json_dataset_1')

        assert_equals(dataset['a_json_field'], value)

    def test_dataset_form_update(self):
        value = {
            'a': 1,
            'b': 2,
        }
        dataset = Dataset(
            type='test-schema',
            a_json_field=value)

        app = self._get_test_app()
        env, response = _get_package_update_page_as_sysadmin(
            app, dataset['id'])
        form = response.forms['dataset-edit']

        assert_equals(form['a_json_field'].value, json.dumps(value, indent=2))

        value = {
            'a': 1,
            'b': 2,
            'c': 3,
        }
        json_value = json.dumps(value)

        form['a_json_field'] = json_value

        submit_and_follow(app, form, env, 'save')

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['a_json_field'], value)


class TestJSONResourceForm(FunctionalTestBase):

    def test_resource_form_includes_json_fields(self):
        dataset = Dataset(type='test-schema')

        app = self._get_test_app()
        env, response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        form = response.forms['resource-edit']
        assert_in('a_resource_json_field', form.fields)
        assert_equals(form.fields['a_resource_json_field'][0].tag, 'textarea')

    def test_resource_form_create(self):
        dataset = Dataset(type='test-schema')

        app = self._get_test_app()
        env, response = _get_resource_new_page_as_sysadmin(app, dataset['id'])
        form = response.forms['resource-edit']

        value = {
            'a': 1,
            'b': 2,
        }
        json_value = json.dumps(value)

        form['url'] = 'http://example.com/data.csv'
        form['a_resource_json_field'] = json_value

        submit_and_follow(app, form, env, 'save')

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['a_resource_json_field'], value)

    def test_resource_form_update(self):
        value = {
            'a': 1,
            'b': 2,
        }
        dataset = Dataset(
            type='test-schema',
            resources=[{
                'url': 'http://example.com/data.csv',
                'a_resource_json_field': value
            }]
        )

        app = self._get_test_app()
        env, response = _get_resource_update_page_as_sysadmin(
            app, dataset['id'], dataset['resources'][0]['id'])
        form = response.forms['resource-edit']

        assert_equals(form['a_resource_json_field'].value, json.dumps(value, indent=2))

        value = {
            'a': 1,
            'b': 2,
            'c': 3,
        }
        json_value = json.dumps(value)

        form['a_resource_json_field'] = json_value

        submit_and_follow(app, form, env, 'save')

        dataset = call_action('package_show', id=dataset['id'])

        assert_equals(dataset['resources'][0]['a_resource_json_field'], value)
