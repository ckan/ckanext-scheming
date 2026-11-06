from __future__ import annotations

import pytest

import ckan.plugins.toolkit as tk
from ckan.tests import factories, helpers

AUTH_FUNCTIONS = [
    "scheming_schema_create",
    "scheming_schema_update",
    "scheming_schema_delete",
    "scheming_schema_activity_list",
]

PRESET_AUTH_FUNCTIONS = [
    "scheming_preset_create",
    "scheming_preset_update",
    "scheming_preset_delete",
]


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingSchemaAuth:
    @pytest.mark.parametrize("auth_function", AUTH_FUNCTIONS)
    def test_anonymous_user_is_not_authorized(self, auth_function: str):
        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(auth_function, {"user": ""})

    @pytest.mark.parametrize("auth_function", AUTH_FUNCTIONS)
    def test_regular_user_is_not_authorized(self, auth_function: str):
        user = factories.User()

        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(auth_function, {"user": user["name"]})

    @pytest.mark.parametrize("auth_function", AUTH_FUNCTIONS)
    def test_sysadmin_is_authorized(self, auth_function: str):
        user = factories.Sysadmin()

        assert helpers.call_auth(auth_function, {"user": user["name"]})


@pytest.mark.ckan_config("ckan.plugins", "scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSchemingPresetAuth:
    @pytest.mark.parametrize("auth_function", PRESET_AUTH_FUNCTIONS)
    def test_anonymous_user_is_not_authorized(self, auth_function: str):
        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(auth_function, {"user": ""})

    @pytest.mark.parametrize("auth_function", PRESET_AUTH_FUNCTIONS)
    def test_regular_user_is_not_authorized(self, auth_function: str):
        user = factories.User()

        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(auth_function, {"user": user["name"]})

    @pytest.mark.parametrize("auth_function", PRESET_AUTH_FUNCTIONS)
    def test_sysadmin_is_authorized(self, auth_function: str):
        user = factories.Sysadmin()

        assert helpers.call_auth(auth_function, {"user": user["name"]})
