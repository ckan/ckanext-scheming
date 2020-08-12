import pytest
from ckantoolkit.tests.factories import Sysadmin, Organization, Group


@pytest.mark.usefixtures("clean_db")
class TestOrganizationDisplay(object):
    def test_organization_displays_custom_fields(self, app):
        user = Sysadmin()
        Organization(user=user, name="org-one", department_id="3008")

        response = app.get("/organization/about/org-one")
        assert "Department ID" in response.body


@pytest.mark.usefixtures("clean_db")
class TestGroupDisplay(object):
    def test_group_displays_custom_fields(self, app):
        user = Sysadmin()
        Group(user=user, name="group-one", bookface="theoneandonly")

        response = app.get("/group/about/group-one")
        assert "Bookface" in response.body
