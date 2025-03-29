import pytest
from ckanapi import LocalCKAN, NotFound
import ckan.plugins.toolkit as tk


@pytest.mark.usefixtures("with_plugins")
class TestGroupSchemaLists(object):
    def test_group_schema_list(self):
        lc = LocalCKAN("visitor")
        group_schemas = lc.action.scheming_group_schema_list()
        assert sorted(group_schemas) == ["group", "theme"]

    def test_group_schema_show(self):
        lc = LocalCKAN("visitor")
        schema = lc.action.scheming_group_schema_show(type="group")
        assert schema["fields"][4]["label"] == "Bookface"

    def test_group_schema_not_found(self):
        lc = LocalCKAN("visitor")
        with pytest.raises(NotFound):
            lc.action.scheming_group_schema_show(type="bert")

    def test_organization_schema_list(self):
        lc = LocalCKAN("visitor")
        org_schemas = lc.action.scheming_organization_schema_list()
        assert sorted(org_schemas) == ["organization", "publisher"]

    def test_organization_schema_show(self):
        lc = LocalCKAN("visitor")
        schema = lc.action.scheming_organization_schema_show(
            type="organization"
        )
        assert schema["fields"][4]["label"] == "Department ID"

    def test_organization_schema_not_found(self):
        lc = LocalCKAN("visitor")
        with pytest.raises(NotFound):
            lc.action.scheming_organization_schema_show(type="elmo")

    @pytest.mark.usefixtures("clean_db")
    def test_is_organization_flag_set_via_web_form(
            self,
            faker,
            app,
            user,
            api_token_factory,
    ):
        lc = LocalCKAN("visitor")
        token = api_token_factory(user=user["name"])

        group_name = faker.slug()
        app.post(tk.url_for("theme.new"), data={
            "name": group_name,
        }, headers={
            "Authorization": token["token"],
        })

        group = lc.action.group_show(id=group_name)
        assert not group["is_organization"]

        org_name = faker.slug()
        app.post(tk.url_for("publisher.new"), data={
            "name": org_name,
        }, headers={
            "Authorization": token["token"],
        })

        org = lc.action.organization_show(id=org_name)
        assert org["is_organization"]
