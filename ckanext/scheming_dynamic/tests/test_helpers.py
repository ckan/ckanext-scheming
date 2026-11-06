from __future__ import annotations

import pytest

from ckan.tests import factories, helpers

from ckanext.scheming_dynamic.helpers import (
    dynamic_scheming_get_entity_pin_version,
    dynamic_scheming_get_entity_schema,
)
from ckanext.scheming_dynamic.model import SchemingSchemaVersion

pytestmark = [
    pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic"),
    pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context"),
]


class TestDynamicSchemingGetEntitySchema:
    def test_unknown_schema_type_returns_none(self):
        assert dynamic_scheming_get_entity_schema("never-created") is None

    def test_no_entity_id_returns_live_schema(
        self, dataset_schema: SchemingSchemaVersion
    ):
        schema = dynamic_scheming_get_entity_schema(dataset_schema.schema_type)

        assert schema
        field_names = [f["field_name"] for f in schema["dataset_fields"]]
        assert field_names == ["temporal_coverage"]

    def test_unpinned_entity_id_returns_live_schema(
        self, dataset_schema: SchemingSchemaVersion
    ):
        schema = dynamic_scheming_get_entity_schema(
            dataset_schema.schema_type, entity_id="never-pinned-id"
        )
        assert schema
        field_names = [f["field_name"] for f in schema["dataset_fields"]]
        assert field_names == ["temporal_coverage"]

    def test_pinned_entity_at_head_returns_live_schema(
        self, dataset_schema: SchemingSchemaVersion
    ):
        dataset = factories.Dataset(
            type=dataset_schema.schema_type
        )  # locks + pins version 1

        schema = dynamic_scheming_get_entity_schema(
            dataset_schema.schema_type, entity_id=dataset["id"]
        )
        assert schema
        field_names = [f["field_name"] for f in schema["dataset_fields"]]
        assert field_names == ["temporal_coverage"]

    def test_pinned_entity_behind_head_returns_locked_schema(
        self, dataset_schema: SchemingSchemaVersion
    ):
        dataset = factories.Dataset(type=dataset_schema.schema_type)

        updated = {
            **dataset_schema.definition,
            "dataset_fields": [{"field_name": "brand_new_field"}],
        }
        helpers.call_action(
            "scheming_schema_update",
            definition=updated,
        )

        schema = dynamic_scheming_get_entity_schema(
            dataset_schema.schema_type, entity_id=dataset["id"]
        )

        assert schema
        field_names = [f["field_name"] for f in schema["dataset_fields"]]
        assert field_names == ["temporal_coverage"]
        assert "brand_new_field" not in field_names

    def test_new_entity_after_edit_sees_the_new_schema(
        self, dataset_schema: SchemingSchemaVersion
    ):
        factories.Dataset(type=dataset_schema.schema_type)

        updated = {
            **dataset_schema.definition,
            "dataset_fields": [{"field_name": "brand_new_field"}],
        }
        helpers.call_action(
            "scheming_schema_update",
            definition=updated,
        )
        new_dataset = factories.Dataset(type=dataset_schema.schema_type)

        schema = dynamic_scheming_get_entity_schema(
            dataset_schema.schema_type, entity_id=new_dataset["id"]
        )
        assert schema
        field_names = [f["field_name"] for f in schema["dataset_fields"]]
        assert field_names == ["brand_new_field"]


class TestDynamicSchemingGetEntityPinVersion:
    def test_no_entity_id_returns_none(self):
        assert dynamic_scheming_get_entity_pin_version("dataset", None) is None

    def test_unpinned_entity_returns_none(self):
        assert dynamic_scheming_get_entity_pin_version("dataset", "missing") is None

    def test_wrong_entity_type_returns_none(self):
        assert dynamic_scheming_get_entity_pin_version("test", "test") is None

    def test_pinned_entity_returns_its_version(
        self, dataset_schema: SchemingSchemaVersion
    ):
        dataset = factories.Dataset(type=dataset_schema.schema_type)

        assert dynamic_scheming_get_entity_pin_version("dataset", dataset["id"]) == 1

    def test_version_reflects_pin_time_not_head(
        self, dataset_schema: SchemingSchemaVersion
    ):
        old_dataset = factories.Dataset(type=dataset_schema.schema_type)

        updated = {
            **dataset_schema.definition,
            "dataset_fields": [{"field_name": "brand_new_field"}],
        }
        helpers.call_action(
            "scheming_schema_update",
            definition=updated,
        )
        new_dataset = factories.Dataset(type=dataset_schema.schema_type)

        assert (
            dynamic_scheming_get_entity_pin_version("dataset", old_dataset["id"]) == 1
        )
        assert (
            dynamic_scheming_get_entity_pin_version("dataset", new_dataset["id"]) == 2
        )
