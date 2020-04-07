import pytest

from ckanapi import LocalCKAN, NotFound


class TestDatasetSchemaLists(object):
    def test_dataset_schema_list(self):
        lc = LocalCKAN("visitor")
        dataset_schemas = lc.action.scheming_dataset_schema_list()
        assert "test-schema" in dataset_schemas

    def test_dataset_schema_show(self):
        lc = LocalCKAN("visitor")
        schema = lc.action.scheming_dataset_schema_show(type="test-schema")
        assert schema["dataset_fields"][2]["label"] == "Humps"

    def test_dataset_schema_not_found(self):
        lc = LocalCKAN("visitor")
        with pytest.raises(NotFound):
            lc.action.scheming_dataset_schema_show(type="ernie")
