from __future__ import annotations

from typing import Any

from ckanext.scheming_dynamic.schema_migration import diff


def schema(*fields: dict[str, Any]) -> dict[str, Any]:
    return {"dataset_fields": list(fields), "resource_fields": []}


def compare_one(source: dict[str, Any], target: dict[str, Any]) -> diff.FieldChange:
    return diff.compare(schema(source), schema(target))["dataset_fields"].fields[0]


class TestUnchangedFields:
    def test_identical_field_is_copied_without_input(self):
        field = {"field_name": "title", "validators": "not_empty"}

        change = compare_one(field, dict(field))

        assert change.change == diff.IDENTICAL
        assert change.action == diff.COPY
        assert change.source == "title"
        assert not change.needs_input

    def test_presentation_only_change_is_still_identical(self):
        source = {"field_name": "title", "label": "Title", "validators": "not_empty"}
        target = {
            "field_name": "title",
            "label": "Different",
            "help_text": "New",
            "form_snippet": "large_text.html",
            "validators": "not_empty",
        }

        assert compare_one(source, target).change == diff.IDENTICAL


class TestWidenedFields:
    def test_dropping_a_validator_is_widening(self):
        source = {"field_name": "x", "validators": "not_empty unicode_safe"}
        target = {"field_name": "x", "validators": "unicode_safe"}

        change = compare_one(source, target)

        assert change.change == diff.WIDENED
        assert not change.needs_input

    def test_adding_a_choice_is_widening(self):
        source = {"field_name": "x", "choices": [{"value": "a"}]}
        target = {"field_name": "x", "choices": [{"value": "a"}, {"value": "b"}]}

        assert compare_one(source, target).change == diff.WIDENED

    def test_relaxing_required_is_widening(self):
        source = {"field_name": "x", "required": True}
        target = {"field_name": "x", "required": False}

        assert compare_one(source, target).change == diff.WIDENED


class TestNarrowedFields:
    def test_removing_a_choice_needs_input_and_reports_the_lost_value(self):
        source = {"field_name": "x", "choices": [{"value": "a"}, {"value": "b"}]}
        target = {"field_name": "x", "choices": [{"value": "a"}]}

        change = compare_one(source, target)

        assert change.change == diff.NARROWED
        assert change.needs_input
        assert change.lost_choices == ["b"]

    def test_becoming_required_needs_input(self):
        source = {"field_name": "x"}
        target = {"field_name": "x", "required": True}

        change = compare_one(source, target)

        assert change.change == diff.NARROWED
        assert change.needs_input

    def test_adding_a_validator_narrows_without_needing_input(self):
        source = {"field_name": "x", "validators": "unicode_safe"}
        target = {"field_name": "x", "validators": "unicode_safe isodate"}

        change = compare_one(source, target)

        assert change.change == diff.NARROWED
        assert not change.needs_input

    def test_a_choices_helper_is_never_assumed_compatible(self):
        source = {"field_name": "x", "choices": [{"value": "a"}]}
        target = {"field_name": "x", "choices_helper": "some_helper"}

        assert compare_one(source, target).change == diff.NARROWED


class TestAddedFields:
    def test_optional_field_is_dropped_without_input(self):
        result = diff.compare(schema(), schema({"field_name": "notes"}))
        change = result["dataset_fields"].fields[0]

        assert change.change == diff.ADDED
        assert change.action == diff.DROP
        assert not change.needs_input

    def test_field_with_a_default_uses_it(self):
        result = diff.compare(
            schema(), schema({"field_name": "x", "default": "y", "required": True})
        )

        assert result["dataset_fields"].fields[0].action == diff.DEFAULT

    def test_required_field_without_a_default_needs_input(self):
        result = diff.compare(
            schema(), schema({"field_name": "x", "validators": "not_empty"})
        )
        change = result["dataset_fields"].fields[0]

        assert change.action == diff.MANUAL
        assert change.needs_input


class TestDroppedFields:
    def test_removed_field_is_listed_as_dropped(self):
        result = diff.compare(schema({"field_name": "legacy"}), schema())

        assert result["dataset_fields"].dropped == ["legacy"]
        assert result["dataset_fields"].needs_input


class TestRenameDetection:
    def test_matching_signature_and_label_is_proposed_as_a_rename(self):
        source = {
            "field_name": "contact",
            "label": "Contact",
            "validators": "not_empty",
        }
        target = {
            "field_name": "contact_email",
            "label": "Contact",
            "validators": "not_empty",
        }

        result = diff.compare(schema(source), schema(target))
        change = result["dataset_fields"].fields[0]

        assert change.change == diff.RENAMED
        assert change.source == "contact"
        assert result["dataset_fields"].dropped == []

    def test_a_rename_always_needs_confirmation(self):
        source = {"field_name": "contact", "label": "C", "validators": "not_empty"}
        target = {
            "field_name": "contact_email",
            "label": "C",
            "validators": "not_empty",
        }

        result = diff.compare(schema(source), schema(target))

        assert result["dataset_fields"].fields[0].needs_input

    def test_two_bare_fields_are_not_a_rename(self):
        result = diff.compare(
            schema({"field_name": "legacy"}), schema({"field_name": "notes"})
        )

        assert result["dataset_fields"].fields[0].change == diff.ADDED
        assert result["dataset_fields"].dropped == ["legacy"]

    def test_one_dropped_field_is_claimed_by_a_single_rename(self):
        source = schema({"field_name": "contact", "label": "C", "required": True})
        target = schema(
            {"field_name": "contact_email", "label": "C", "required": True},
            {"field_name": "contact_phone", "label": "C", "required": True},
        )

        result = diff.compare(source, target)
        renamed = [
            f for f in result["dataset_fields"].fields if f.change == diff.RENAMED
        ]

        assert len(renamed) == 1


class TestRepeatingSubfields:
    def test_subfield_changes_are_reported_for_display(self):
        source = {
            "field_name": "contacts",
            "repeating_subfields": [{"field_name": "name"}],
        }
        target = {
            "field_name": "contacts",
            "repeating_subfields": [
                {"field_name": "name"},
                {"field_name": "email", "validators": "not_empty"},
            ],
        }

        change = compare_one(source, target)

        assert change.change == diff.NARROWED
        assert [sub.field_name for sub in change.subfields] == ["name", "email"]


class TestResourceFields:
    def test_resource_fields_are_diffed_separately(self):
        source = {
            "dataset_fields": [],
            "resource_fields": [{"field_name": "format"}],
        }
        target = {"dataset_fields": [], "resource_fields": []}

        result = diff.compare(source, target)

        assert result["resource_fields"].dropped == ["format"]
        assert result["dataset_fields"].dropped == []
