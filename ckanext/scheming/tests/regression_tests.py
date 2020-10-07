"""Tests for plugin.py."""
# encoding: utf-8

from ckan.tests.helpers import call_action
from ckan.tests import factories
import ckan.tests.helpers as helpers
import logging
from pprint import pformat


class RegressionTests(helpers.FunctionalTestBase):

    def test_individual_resource_access(self):
        dataset = factories.Dataset(type="test-schema")
        resource1 = factories.Resource(
            package_id=dataset['id'],
            camels_in_photo="1"
        )
        resource2 = factories.Resource(
            package_id=dataset['id'],
            camels_in_photo="2"
        )
        resource1_camels = resource1['camels_in_photo']

        response = call_action(
            'resource_update',
            {},
            id=resource2['id'],
            camels_in_photo="3"
        )
        response = call_action('package_show', {}, id=dataset['id'])

        logging.warning("Updated package is stored as:")
        logging.warning(pformat(response))
        # Assert updating 2nd resource did not affect the 1st resource
        assert response['resources'][0]['camels_in_photo'] == resource1_camels
