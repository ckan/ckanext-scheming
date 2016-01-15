from nose.tools import assert_true

from ckantoolkit.tests.factories import Sysadmin, Organization, Group
from ckantoolkit.tests.helpers import FunctionalTestBase


class TestOrganizationDisplay(FunctionalTestBase):
    def test_organization_displays_custom_fields(self):
        user = Sysadmin()
        Organization(
            user=user,
            name='org-one',
            department_id='3008',
            )

        app = self._get_test_app()
        response = app.get(url='/organization/about/org-one')
        assert_true('Department ID' in response.body)


class TestGroupDisplay(FunctionalTestBase):
    def test_group_displays_custom_fields(self):
        user = Sysadmin()
        Group(
            user=user,
            name='group-one',
            bookface='theoneandonly',
            )

        app = self._get_test_app()
        response = app.get(url='/group/about/group-one')
        assert_true('Bookface' in response.body)

