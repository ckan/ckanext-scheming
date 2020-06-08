import json

import pytest
import ckantoolkit
from bs4 import BeautifulSoup

from ckantoolkit.tests.factories import Sysadmin, Dataset
from ckantoolkit.tests.helpers import call_action


@pytest.fixture
def sysadmin_env():
    user = Sysadmin()
    return {"REMOTE_USER": user["name"].encode("ascii")}


def _get_package_new_page_as_sysadmin(app):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(url="/test-schema/new", extra_environ=env)
    return env, response


def _get_package_update_page_as_sysadmin(app, id):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(
        url="/test-schema/edit/{}".format(id), extra_environ=env
    )
    return env, response


def _get_resource_new_page_as_sysadmin(app, id):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(
        url="/dataset/new_resource/{}".format(id), extra_environ=env
    )
    return env, response


def _get_resource_update_page_as_sysadmin(app, id, resource_id):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(
        url="/dataset/{}/resource_edit/{}".format(id, resource_id),
        extra_environ=env,
    )
    return env, response


def _get_organization_new_page_as_sysadmin(app, type="organization"):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(url="/{0}/new".format(type), extra_environ=env)
    return env, response


def _get_group_new_page_as_sysadmin(app, type="group"):
    user = Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(url="/{0}/new".format(type), extra_environ=env)
    return env, response


@pytest.mark.usefixtures("clean_db")
class TestDatasetFormNew(object):
    def test_dataset_form_includes_custom_fields(self, app):
        env, response = _get_package_new_page_as_sysadmin(app)
        form = BeautifulSoup(response.body).select_one("#dataset-edit")
        assert form.select("input[name=humps]")

    def test_dataset_form_slug_says_dataset(self, app):
        """The default prefix shouldn't be /packages?id="""

        env, response = _get_package_new_page_as_sysadmin(app)
        assert "packages?id=" not in response.body
        assert "/test-schema/" in response.body

    def test_resource_form_includes_custom_fields(self, app, sysadmin_env):
        dataset = Dataset(type="test-schema", name="resource-includes-custom")
        response = app.get(
            '/dataset/new_resource/' + dataset["id"],
            extra_environ=sysadmin_env,
        )
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select("input[name=camels_in_photo]")

    def test_dataset_form_includes_licenses(self, app, sysadmin_env):
        """Starting from CKAN v2.9, licenses are not available as template
        variable and we are extendisn
        `DefaultDatasetForm::setup_template_variables` in order to change
        it.
        """
        response = app.get(url="/dataset/new", extra_environ=sysadmin_env)
        page = BeautifulSoup(response.body)
        licenses = page.select('#field-license_id option')
        assert licenses

@pytest.mark.usefixtures("clean_db")
class TestOrganizationFormNew(object):
    def test_organization_form_includes_custom_field(self, app):

        env, response = _get_organization_new_page_as_sysadmin(app)
        # FIXME: add an id to this form
        form = BeautifulSoup(response.body).select("form")[1]

        # FIXME: generate the form for orgs (this is currently missing)
        assert form.select("input[name=department_id]")

    def test_organization_form_slug_says_organization(self, app):
        """The default prefix shouldn't be /packages?id="""

        env, response = _get_organization_new_page_as_sysadmin(app)
        # Commenting until ckan/ckan#4208 is fixed
        # assert_true('packages?id=' not in response.body)
        assert "/organization/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestGroupFormNew(object):
    @pytest.mark.skipif(
        not ckantoolkit.check_ckan_version(min_version="2.7.0"),
        reason="Unspecified"
    )
    def test_group_form_includes_custom_field(self, app):

        env, response = _get_group_new_page_as_sysadmin(app)
        # FIXME: add an id to this form
        form = BeautifulSoup(response.body).select("form")[1]

        assert form.select("input[name=bookface]")

    def test_group_form_slug_says_group(self, app):
        """The default prefix shouldn't be /packages?id="""

        env, response = _get_group_new_page_as_sysadmin(app)
        # Commenting until ckan/ckan#4208 is fixed
        # assert_true('packages?id=' not in response.body)
        assert "/group/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestCustomGroupFormNew(object):
    @pytest.mark.skipif(
        not ckantoolkit.check_ckan_version(min_version="2.8.0"),
        reason="Unspecified"
    )
    def test_group_form_includes_custom_field(self, app):
        env, response = _get_group_new_page_as_sysadmin(app, type="theme")
        form = BeautifulSoup(response.body).select("form")[1]
        assert form.select("input[name=status]")

    def test_group_form_slug_uses_custom_type(self, app):

        env, response = _get_group_new_page_as_sysadmin(app, type="theme")

        assert "/theme/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestCustomOrgFormNew(object):
    @pytest.mark.skipif(
        not ckantoolkit.check_ckan_version(min_version="2.8.0"),
        reason="Unspecified"
    )
    def test_org_form_includes_custom_field(self, app):
        env, response = _get_organization_new_page_as_sysadmin(
            app, type="publisher"
        )
        form = BeautifulSoup(response.body).select("form")[1]
        assert form.select("input[name=address]")

    def test_org_form_slug_uses_custom_type(self, app):
        env, response = _get_organization_new_page_as_sysadmin(
            app, type="publisher"
        )

        assert "/publisher/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestJSONDatasetForm(object):
    def test_dataset_form_includes_json_fields(self, app):
        env, response = _get_package_new_page_as_sysadmin(app)
        form = BeautifulSoup(response.body).select("form")[1]
        assert form.select("textarea[name=a_json_field]")

    def test_dataset_form_create(self, app, sysadmin_env):
        data = {"save": "", "_ckan_phase": 1}
        value = {"a": 1, "b": 2}
        json_value = json.dumps(value)

        data["name"] = "json_dataset_1"
        data["a_json_field"] = json_value

        url = '/test-schema/new'
        try:
            app.post(url, environ_overrides=sysadmin_env, data=data, follow_redirects=False)
        except TypeError:
            app.post(url.encode('ascii'), params=data, extra_environ=sysadmin_env)

        dataset = call_action("package_show", id="json_dataset_1")
        assert dataset["a_json_field"] == value

    def test_dataset_form_update(self, app):
        value = {"a": 1, "b": 2}
        dataset = Dataset(type="test-schema", a_json_field=value)

        env, response = _get_package_update_page_as_sysadmin(
            app, dataset["id"]
        )
        form = BeautifulSoup(response.body).select_one("#dataset-edit")
        assert form.select_one(
            "textarea[name=a_json_field]"
        ).text == json.dumps(value, indent=2)

        value = {"a": 1, "b": 2, "c": 3}
        json_value = json.dumps(value)

        data = {
            "save": "",
            "a_json_field": json_value,
            "name": dataset["name"],
        }

        url = '/dataset/edit/' + dataset["id"]
        try:
            app.post(url, environ_overrides=env, data=data, follow_redirects=False)
        except TypeError:
            app.post(url.encode('ascii'), params=data, extra_environ=env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["a_json_field"] == value


@pytest.mark.usefixtures("clean_db")
class TestJSONResourceForm(object):
    def test_resource_form_includes_json_fields(self, app):
        dataset = Dataset(type="test-schema")

        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select("textarea[name=a_resource_json_field]")

    def test_resource_form_create(self, app):
        dataset = Dataset(type="test-schema")

        env, response = _get_resource_new_page_as_sysadmin(app, dataset["id"])

        url = ckantoolkit.h.url_for(
            "test-schema_resource.new", id=dataset["id"]
        )
        if not url.startswith('/'):  # ckan < 2.9
            url = '/dataset/new_resource/' + dataset["id"]

        value = {"a": 1, "b": 2}
        json_value = json.dumps(value)

        data = {
            "id": "",
            "save": "",
            "url": "http://example.com/data.csv",
            "a_resource_json_field": json_value,
            "name": dataset["name"],
        }
        try:
            app.post(url, environ_overrides=env, data=data, follow_redirects=False)
        except TypeError:
            app.post(url.encode('ascii'), params=data, extra_environ=env)
        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["a_resource_json_field"] == value

    def test_resource_form_update(self, app):
        value = {"a": 1, "b": 2}
        dataset = Dataset(
            type="test-schema",
            resources=[
                {
                    "url": "http://example.com/data.csv",
                    "a_resource_json_field": value,
                }
            ],
        )

        env, response = _get_resource_update_page_as_sysadmin(
            app, dataset["id"], dataset["resources"][0]["id"]
        )
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select_one(
            "textarea[name=a_resource_json_field]"
        ).text == json.dumps(value, indent=2)

        url = ckantoolkit.h.url_for(
            "test-schema_resource.edit",
            id=dataset["id"],
            resource_id=dataset["resources"][0]["id"],
        )
        if not url.startswith('/'):  # ckan < 2.9
            url = '/dataset/{ds}/resource_edit/{rs}'.format(
                ds=dataset["id"],
                rs=dataset["resources"][0]["id"]
            )

        value = {"a": 1, "b": 2, "c": 3}
        json_value = json.dumps(value)

        data = {
            "id": dataset["resources"][0]["id"],
            "save": "",
            "a_resource_json_field": json_value,
            "name": dataset["name"],
        }
        try:
            app.post(url, environ_overrides=env, data=data, follow_redirects=False)
        except TypeError:
            app.post(url.encode('ascii'), params=data, extra_environ=env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["a_resource_json_field"] == value
