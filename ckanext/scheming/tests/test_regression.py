"""Tests for plugin.py."""
# encoding: utf-8

from ckan.tests.helpers import call_action
from ckan.tests import factories
import logging
from pprint import pformat
import pytest

log = logging.getLogger(__name__)


@pytest.mark.usefixtures('clean_db')
class TestRegression(object):

    def test_updating_second_resource_not_affects_first_resource(self):
        resource1_expected_camels = 1
        dataset = factories.Dataset(type="test-schema")
        factories.Resource(
            package_id=dataset['id'],
            camels_in_photo=resource1_expected_camels
        )
        resource2 = factories.Resource(
            package_id=dataset['id'],
            camels_in_photo="2"
        )
        call_action(
            'resource_update',
            {},
            id=resource2['id'],
            camels_in_photo="3"
        )
        response = call_action('package_show', {}, id=dataset['id'])
        log.debug("Updated package is stored as:")
        log.debug(pformat(response))
        assert response['resources'][0]['camels_in_photo'] == resource1_expected_camels
