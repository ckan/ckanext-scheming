from __future__ import annotations

from typing import Any

from ckanext.scheming_dynamic.schema_migration import diff
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib


def schema(*fields: dict[str, Any]) -> dict[str, Any]:
    return {"dataset_fields": list(fields), "resource_fields": []}


class TestSuggest:
    def test_only_fields_needing_no_decision_are_suggested(self):
        source = schema(
            {"field_name": "title", "validators": "not_empty"},
            {"field_name": "legacy"},
        )
        target = schema(
            {"field_name": "title", "validators": "not_empty"},
            {"field_name": "quality", "validators": "not_empty"},
        )

        suggested = mapping_lib.suggest(diff.compare(source, target))

        assert suggested["dataset_fields"] == {
            "title": {"action": "copy", "source": "title"}
        }

    def test_added_optional_field_is_suggested_as_drop(self):
        suggested = mapping_lib.suggest(
            diff.compare(schema(), schema({"field_name": "notes"}))
        )

        assert suggested["dataset_fields"]["notes"] == {"action": "drop"}


class TestUnresolved:
    def test_a_field_needing_input_without_an_entry_is_unresolved(self):
        changes = diff.compare(
            schema(), schema({"field_name": "quality", "validators": "not_empty"})
        )

        problems = mapping_lib.unresolved(changes, mapping_lib.empty())

        assert [p["field_name"] for p in problems] == ["quality"]

    def test_answering_a_field_resolves_it(self):
        changes = diff.compare(
            schema(), schema({"field_name": "quality", "validators": "not_empty"})
        )
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["quality"] = {"action": "constant", "value": "high"}

        assert mapping_lib.unresolved(changes, mapping) == []

    def test_dropped_field_stays_unresolved_until_acknowledged(self):
        changes = diff.compare(schema({"field_name": "legacy"}), schema())
        mapping = mapping_lib.empty()

        assert len(mapping_lib.unresolved(changes, mapping)) == 1

        mapping["dropped"]["dataset_fields"] = ["legacy"]

        assert mapping_lib.unresolved(changes, mapping) == []

    def test_a_lost_choice_needs_a_replacement(self):
        source = schema(
            {"field_name": "theme", "choices": [{"value": "a"}, {"value": "b"}]}
        )
        target = schema({"field_name": "theme", "choices": [{"value": "a"}]})
        changes = diff.compare(source, target)

        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["theme"] = {"action": "copy", "source": "theme"}

        assert "b" in mapping_lib.unresolved(changes, mapping)[0]["reason"]

        mapping["dataset_fields"]["theme"]["value_map"] = {"b": "a"}

        assert mapping_lib.unresolved(changes, mapping) == []


class TestManualFields:
    def test_manual_entries_are_reported_so_bulk_cannot_run(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["quality"] = {"action": "manual"}
        mapping["dataset_fields"]["title"] = {"action": "copy", "source": "title"}

        assert [p["field_name"] for p in mapping_lib.manual_fields(mapping)] == [
            "quality"
        ]

    def test_overlaying_a_value_answers_a_manual_field(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["quality"] = {"action": "manual"}

        merged = mapping_lib.overlay_values(
            mapping, {"dataset_fields": {"quality": "high"}}
        )

        assert merged["dataset_fields"]["quality"] == {
            "action": "constant",
            "value": "high",
        }
        assert mapping_lib.manual_fields(merged) == []

    def test_overlaying_does_not_mutate_the_stored_mapping(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["quality"] = {"action": "manual"}

        mapping_lib.overlay_values(mapping, {"dataset_fields": {"quality": "high"}})

        assert mapping["dataset_fields"]["quality"] == {"action": "manual"}


class TestCheck:
    def test_unknown_target_field_is_rejected(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["nope"] = {"action": "drop"}

        errors = mapping_lib.check(mapping, schema({"field_name": "title"}))

        assert "not a field of the target schema" in errors[0]

    def test_copy_without_a_source_is_rejected(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["title"] = {"action": "copy"}

        errors = mapping_lib.check(mapping, schema({"field_name": "title"}))

        assert "needs a source field" in errors[0]

    def test_constant_without_a_value_is_rejected(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["title"] = {"action": "constant"}

        errors = mapping_lib.check(mapping, schema({"field_name": "title"}))

        assert "needs a value" in errors[0]

    def test_unknown_action_is_rejected(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["title"] = {"action": "teleport"}

        errors = mapping_lib.check(mapping, schema({"field_name": "title"}))

        assert "unknown action" in errors[0]

    def test_a_valid_mapping_has_no_errors(self):
        mapping = mapping_lib.empty()
        mapping["dataset_fields"]["title"] = {"action": "copy", "source": "title"}

        assert mapping_lib.check(mapping, schema({"field_name": "title"})) == []
