import json

import pytest
from bs4 import BeautifulSoup

from ckan.plugins.toolkit import check_ckan_version, h

from ckan.tests.factories import Dataset
from ckan.tests.helpers import call_action


@pytest.fixture
def sysadmin_env():
    try:
        from ckan.tests.factories import SysadminWithToken
        user = SysadminWithToken()
        return {'Authorization': user['token']}
    except ImportError:
        # ckan <= 2.9
        from ckan.tests.factories import Sysadmin
        user = Sysadmin()
        return {"REMOTE_USER": user["name"].encode("ascii")}


def _get_package_new_page(app, env, type_='test-schema'):
    if check_ckan_version(min_version="2.10.0"):
        return app.get(url="/{0}/new".format(type_), headers=env)
    else:
        return app.get(url="/{0}/new".format(type_), extra_environ=env)


def _get_package_update_page(app, id, env):

    if check_ckan_version(min_version="2.10.0"):
        return app.get(url="/test-schema/edit/{}".format(id), headers=env)
    else:
        return app.get(url="/test-schema/edit/{}".format(id), extra_environ=env)


def _get_resource_new_page(app, id, env):
    url = '/dataset/{}/resource/new'.format(id)

    if check_ckan_version(min_version="2.10.0"):
        return app.get(url, headers=env)
    else:
        return app.get(url, extra_environ=env)


def _get_resource_update_page(app, id, resource_id, env):
    url = '/dataset/{}/resource/{}/edit'.format(id, resource_id)

    if check_ckan_version(min_version="2.10.0"):
        return app.get(url, headers=env)
    else:
        return app.get(url, extra_environ=env)


def _get_organization_new_page(app, env, type_="organization"):

    if check_ckan_version(min_version="2.10.0"):
        return app.get(url="/{0}/new".format(type_), headers=env)
    else:
        return app.get(url="/{0}/new".format(type_), extra_environ=env)


def _get_group_new_page(app, env, type_="group"):

    if check_ckan_version(min_version="2.10.0"):
        return app.get(url="/{0}/new".format(type_), headers=env)
    else:
        return app.get(url="/{0}/new".format(type_), extra_environ=env)


def _get_organization_form(html):
    # FIXME: add an id to this form
    if check_ckan_version(min_version="2.11.0a0"):
        form = BeautifulSoup(html).select("form")[2]
    else:
        form = BeautifulSoup(html).select("form")[1]
    return form


def _get_group_form(html):
    return _get_organization_form(html)


def _post_data(app, url, data, env):
    try:
        if check_ckan_version(min_version="2.11.0a0"):
            app.post(url, headers=env, data=data, follow_redirects=False)
        else:
            app.post(
                url, environ_overrides=env, data=data, follow_redirects=False
            )
    except TypeError:
        app.post(url.encode('ascii'), params=data, extra_environ=sysadmin_env)


@pytest.mark.usefixtures("clean_db")
class TestDatasetFormNew(object):
    def test_dataset_form_includes_custom_fields(self, app, sysadmin_env):
        response = _get_package_new_page(app, sysadmin_env)
        form = BeautifulSoup(response.body).select_one("#dataset-edit")
        assert form.select("input[name=humps]")

    def test_dataset_form_slug_says_dataset(self, app, sysadmin_env):
        """The default prefix shouldn't be /packages?id="""

        response = _get_package_new_page(app, sysadmin_env)
        assert "packages?id=" not in response.body
        assert "/test-schema/" in response.body

    def test_resource_form_includes_custom_fields(self, app, sysadmin_env):
        dataset = Dataset(type="test-schema", name="resource-includes-custom")

        response = _get_resource_new_page(app, dataset["id"], sysadmin_env)

        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select("input[name=camels_in_photo]")

    def test_dataset_form_includes_licenses(self, app, sysadmin_env):
        """Starting from CKAN v2.9, licenses are not available as template
        variable and we are extendisn
        `DefaultDatasetForm::setup_template_variables` in order to change
        it.
        """
        response = _get_package_new_page(app, sysadmin_env, type_="dataset")
        page = BeautifulSoup(response.body)
        licenses = page.select('#field-license_id option')
        assert licenses


@pytest.mark.usefixtures("clean_db")
class TestOrganizationFormNew(object):
    def test_organization_form_includes_custom_field(self, app, sysadmin_env):

        response = _get_organization_new_page(app, sysadmin_env)

        form = _get_organization_form(response.body)

        # FIXME: generate the form for orgs (this is currently missing)
        assert form.select("input[name=department_id]")

    def test_organization_form_slug_says_organization(self, app, sysadmin_env):
        """The default prefix shouldn't be /packages?id="""

        response = _get_organization_new_page(app, sysadmin_env)
        # Commenting until ckan/ckan#4208 is fixed
        # assert_true('packages?id=' not in response.body)
        assert "/organization/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestGroupFormNew(object):
    def test_group_form_includes_custom_field(self, app, sysadmin_env):

        response = _get_group_new_page(app, sysadmin_env)
        form = _get_organization_form(response.body)

        assert form.select("input[name=bookface]")

    def test_group_form_slug_says_group(self, app, sysadmin_env):
        """The default prefix shouldn't be /packages?id="""

        response = _get_group_new_page(app, sysadmin_env)
        # Commenting until ckan/ckan#4208 is fixed
        # assert_true('packages?id=' not in response.body)
        assert "/group/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestCustomGroupFormNew(object):
    def test_group_form_includes_custom_field(self, app, sysadmin_env):
        response = _get_group_new_page(app, sysadmin_env, "theme")

        form = _get_group_form(response.body)

        assert form.select("input[name=status]")

    def test_group_form_slug_uses_custom_type(self, app, sysadmin_env):

        response = _get_group_new_page(app, sysadmin_env, "theme")

        assert "/theme/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestCustomOrgFormNew(object):
    def test_org_form_includes_custom_field(self, app, sysadmin_env):
        response = _get_organization_new_page(
            app, sysadmin_env, "publisher"
        )

        form = _get_organization_form(response.body)
        assert form.select("input[name=address]")

    def test_org_form_slug_uses_custom_type(self, app, sysadmin_env):
        response = _get_organization_new_page(
            app, sysadmin_env, "publisher"
        )

        assert "/publisher/" in response.body


@pytest.mark.usefixtures("clean_db")
class TestJSONDatasetForm(object):
    def test_dataset_form_includes_json_fields(self, app, sysadmin_env):
        response = _get_package_new_page(app, sysadmin_env)
        form = BeautifulSoup(response.body).select("#dataset-edit")[0]
        assert form.select("textarea[name=a_json_field]")

    def test_dataset_form_create(self, app, sysadmin_env):
        data = {"save": "", "_ckan_phase": 1}
        value = {"a": 1, "b": 2}
        json_value = json.dumps(value)

        data["name"] = "json_dataset_1"
        data["a_json_field"] = json_value

        url = '/test-schema/new'

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id="json_dataset_1")
        assert dataset["a_json_field"] == value

    def test_dataset_form_update(self, app, sysadmin_env):
        value = {"a": 1, "b": 2}
        dataset = Dataset(type="test-schema", a_json_field=value)

        response = _get_package_update_page(
            app, dataset["id"], sysadmin_env
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

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["a_json_field"] == value


@pytest.mark.usefixtures("clean_db")
class TestJSONResourceForm(object):
    def test_resource_form_includes_json_fields(self, app, sysadmin_env):
        dataset = Dataset(type="test-schema")

        response = _get_resource_new_page(app, dataset["id"], sysadmin_env)
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select("textarea[name=a_resource_json_field]")

    def test_resource_form_create(self, app, sysadmin_env):
        dataset = Dataset(type="test-schema")

        response = _get_resource_new_page(app, dataset["id"], sysadmin_env)

        url = h.url_for(
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

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["a_resource_json_field"] == value

    def test_resource_form_update(self, app, sysadmin_env):
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

        response = _get_resource_update_page(
            app, dataset["id"], dataset["resources"][0]["id"], sysadmin_env
        )
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select_one(
            "textarea[name=a_resource_json_field]"
        ).text == json.dumps(value, indent=2)

        url = h.url_for(
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

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["a_resource_json_field"] == value


@pytest.mark.usefixtures("clean_db")
class TestSubfieldDatasetForm(object):
    def test_dataset_form_includes_subfields(self, app, sysadmin_env):
        response = _get_package_new_page(app, sysadmin_env, 'test-subfields')
        form = BeautifulSoup(response.body).select("#dataset-edit")[0]
        assert form.select("fieldset[name=scheming-repeating-subfields]")

    def test_dataset_form_create(self, app, sysadmin_env):
        data = {"save": "", "_ckan_phase": 1}

        data["name"] = "subfield_dataset_1"
        data["citation-0-originator"] = ['mei', 'ahmed']
        data["contact_address-0-address"] = 'anyplace'

        url = '/test-subfields/new'

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id="subfield_dataset_1")
        assert dataset["citation"] == [{'originator': ['mei', 'ahmed']}]
        assert dataset["contact_address"] == [{'address': 'anyplace'}]

    def test_dataset_form_update(self, app, sysadmin_env):
        dataset = Dataset(
            type="test-subfields",
            citation=[{'originator': ['mei']}, {'originator': ['ahmed']}],
            contact_address=[{'address': 'anyplace'}])

        response = _get_package_update_page(
            app, dataset["id"], sysadmin_env
        )
        form = BeautifulSoup(response.body).select_one("#dataset-edit")
        assert form.select_one(
            "input[name=citation-1-originator]"
        ).attrs['value'] == 'ahmed'

        data = {"save": ""}
        data["citation-0-originator"] = ['ling']
        data["citation-1-originator"] = ['umet']
        data["contact_address-0-address"] = 'home'
        data["name"] = dataset["name"]

        url = '/test-subfields/edit/' + dataset["id"]

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["citation"] == [{'originator': ['ling']}, {'originator': ['umet']}]
        assert dataset["contact_address"] == [{'address': 'home'}]


@pytest.mark.usefixtures("clean_db")
class TestNestedSubfieldDatasetForm(object):
    def test_dataset_form_includes_nested_subfields(self, app, sysadmin_env):
        response = _get_package_new_page(app, sysadmin_env, 'test-subfields')
        form = BeautifulSoup(response.body).select("#dataset-edit")[0]
        assert form.select("fieldset[name=scheming-repeating-subfields] fieldset[name=scheming-repeating-subfields]")

    def test_dataset_form_create(self, app, sysadmin_env):
        data = {"save": "", "_ckan_phase": 1}

        contact_points = [
            {
                'name': 'representative',
                'ways_of_contact': [
                    {
                        'email': 'email@example.com',
                        'by_letter': [
                            {
                                'name': 'some office',
                                'address': 'some office address'
                            },
                            {
                                'name': 'other office',
                                'address': 'other office address'
                            }
                        ]
                    }
                ]
            },
            {
                'name': 'second representative',
                'ways_of_contact': [
                    {
                        'phone': '01234567'
                    }
                ]
            }
        ]

        data["name"] = "nested_subfield_dataset_1"
        data["contact_points-0-name"] = contact_points[0]['name']
        data["contact_points-0-ways_of_contact-0-email"] = contact_points[0]['ways_of_contact'][0]['email']
        data["contact_points-0-ways_of_contact-0-by_letter-0-name"] = contact_points[0]['ways_of_contact'][0]['by_letter'][0]['name']
        data["contact_points-0-ways_of_contact-0-by_letter-0-address"] = contact_points[0]['ways_of_contact'][0]['by_letter'][0]['address']
        data["contact_points-0-ways_of_contact-0-by_letter-1-name"] = contact_points[0]['ways_of_contact'][0]['by_letter'][1]['name']
        data["contact_points-0-ways_of_contact-0-by_letter-1-address"] = contact_points[0]['ways_of_contact'][0]['by_letter'][1]['address']

        data["contact_points-1-name"] = contact_points[1]['name']
        data["contact_points-1-ways_of_contact-0-phone"] = contact_points[1]['ways_of_contact'][0]['phone']

        url = '/test-subfields/new'

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id="nested_subfield_dataset_1")
        assert dataset["contact_points"] == contact_points

    def test_dataset_form_update(self, app, sysadmin_env):
        dataset = Dataset(
            type="test-subfields",
            contact_points=[
                {'name': 'representative', 'ways_of_contact': [{'email': 'representative@example.com'}]},
                {'name': 'second representative', 'ways_of_contact': [{'email': 'second.representative@example.com'}]}
            ])

        response = _get_package_update_page(
            app, dataset["id"], sysadmin_env
        )
        form = BeautifulSoup(response.body).select_one("#dataset-edit")
        assert form.select_one(
            "input[name=contact_points-1-ways_of_contact-0-email]"
        ).attrs['value'] == 'second.representative@example.com'

        data = {"save": ""}
        data["contact_points-0-name"] = 'representative'
        data["contact_points-0-ways_of_contact-0-email"] = 'modified.representative@example.com'
        data["contact_points-0-ways_of_contact-1-email"] = 'added.representative@example.com'
        data["contact_points-1-name"] = 'second representative'
        data["contact_points-1-ways_of_contact-0-email"] = 'second.representative@example.com'
        data["name"] = dataset["name"]

        url = '/test-subfields/edit/' + dataset["id"]

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["contact_points"] == [
            {'name': 'representative', 'ways_of_contact': [{'email': 'modified.representative@example.com'},
                                                           {'email': 'added.representative@example.com'}]},
            {'name': 'second representative', 'ways_of_contact': [{'email': 'second.representative@example.com'}]}
        ]



@pytest.mark.usefixtures("clean_db")
class TestSubfieldResourceForm(object):
    def test_resource_form_includes_subfields(self, app, sysadmin_env):
        dataset = Dataset(type="test-subfields", citation=[{'originator': 'na'}])

        response = _get_resource_new_page(app, dataset["id"], sysadmin_env)
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        assert form.select("fieldset[name=scheming-repeating-subfields]")

    def test_resource_form_create(self, app, sysadmin_env):
        dataset = Dataset(type="test-subfields", citation=[{'originator': 'na'}])

        response = _get_resource_new_page(app, dataset["id"], sysadmin_env)

        url = h.url_for(
            "test-subfields_resource.new", id=dataset["id"]
        )
        if not url.startswith('/'):  # ckan < 2.9
            url = '/dataset/new_resource/' + dataset["id"]

        data = {"id": "", "save": ""}
        data["schedule-0-impact"] = "P"

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schedule"] == [{"impact": "P"}]

    def test_resource_form_update(self, app, sysadmin_env):
        dataset = Dataset(
            type="test-subfields",
            citation=[{'originator': 'na'}],
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

        response = _get_resource_update_page(
            app, dataset["id"], dataset["resources"][0]["id"], sysadmin_env
        )
        form = BeautifulSoup(response.body).select_one("#resource-edit")
        opt7d = form.find_all('option', {'value': '7d'})
        assert 'selected' not in opt7d[0].attrs
        assert 'selected' in opt7d[1].attrs
        assert 'selected' not in opt7d[2].attrs  # blank subfields

        url = h.url_for(
            "test-schema_resource.edit",
            id=dataset["id"],
            resource_id=dataset["resources"][0]["id"],
        )
        if not url.startswith('/'):  # ckan < 2.9
            url = '/dataset/{ds}/resource_edit/{rs}'.format(
                ds=dataset["id"],
                rs=dataset["resources"][0]["id"]
            )

        data = {"id": dataset["resources"][0]["id"], "save": ""}
        data["schedule-0-frequency"] = '1y'
        data["schedule-0-impact"] = 'A'
        data["schedule-1-frequency"] = '1m'
        data["schedule-1-impact"] = 'P'

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["schedule"] == [
            {"frequency": '1y', "impact": 'A'},
            {"frequency": '1m', "impact": 'P'},
        ]

    def test_resource_form_create_with_datetime_tz(self, app, sysadmin_env):
        dataset = Dataset(type="test-schema")

        url = h.url_for("test-schema_resource.new", id=dataset["id"])
        if not url.startswith("/"):  # ckan < 2.9
            url = "/dataset/new_resource/" + dataset["id"]

        date = "2001-12-12"
        time = "12:12"
        tz = "UTC"

        data = {
            "id": "",
            "save": "",
            "datetime_tz_date": date,
            "datetime_tz_time": time,
            "datetime_tz_tz": tz,
        }

        _post_data(app, url, data, sysadmin_env)

        dataset = call_action("package_show", id=dataset["id"])

        assert dataset["resources"][0]["datetime_tz"] == f"{date}T{time}:00"