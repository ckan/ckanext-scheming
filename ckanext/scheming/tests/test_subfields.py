from unittest import mock

import pytest
import ckantoolkit

from ckantoolkit.tests.factories import Dataset
from ckantoolkit.tests.helpers import call_action


dataset_dict = {
    "name": "test-dataset",
    "type": "test-subfields",
    # Repeating subfields
    "contact_address": [
        {"address": "Maple Street 123", "city": "New Paris", "country": "Maplonia"},
        {"address": "Rose Avenue 452", "city": "Old York", "country": "Rosestan"},
    ],
}


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_subfields_index")
def test_repeating_subfields_index():

    with mock.patch("ckan.lib.search.index.make_connection") as m:
        call_action("package_create", **dataset_dict)

        # Dict sent to Solr
        search_dict = m.mock_calls[1].kwargs["docs"][0]
        assert search_dict["extras_contact_address__city"] == "New Paris Old York"
        assert search_dict["extras_contact_address__country"] == "Maplonia Rosestan"


@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_subfields_index")
def test_repeating_subfields_search():

    dataset = call_action("package_create", **dataset_dict)

    result = call_action("package_search", q="Old York")

    assert result["results"][0]["id"] == dataset["id"]
