"""Build, check and apply the field mapping between two schema versions.

The mapping document is flat -- one entry per target field:

    {
        "dataset_fields": {"<field>": {"action": ..., ...}},
        "resource_fields": {"<field>": {"action": ..., ...}},
        "dropped": {"dataset_fields": ["<field>"], "resource_fields": []}
    }

``dropped`` lists source fields the admin acknowledged losing. A field with
``repeating_subfields`` is mapped as a whole; its subfield diff is shown for
information only.
"""

from __future__ import annotations

from typing import Any

from ckanext.scheming_dynamic.schema_migration.diff import (
    CONSTANT,
    COPY,
    DEFAULT,
    DROP,
    FIELD_GROUPS,
    MANUAL,
    GroupDiff,
    groups_in,
)

ACTIONS = (COPY, CONSTANT, DEFAULT, DROP, MANUAL)


def _mapping_groups(mapping: dict[str, Any]) -> tuple[str, ...]:
    groups = tuple(g for g in mapping if g != "dropped")
    return groups or FIELD_GROUPS


def empty(groups: tuple[str, ...] = FIELD_GROUPS) -> dict[str, Any]:
    return {
        **{group: {} for group in groups},
        "dropped": {group: [] for group in groups},
    }


def suggest(diff: dict[str, GroupDiff]) -> dict[str, Any]:
    """Auto-derive entries for every field that does not need a decision."""
    mapping = empty(tuple(diff) or FIELD_GROUPS)

    for group, group_diff in diff.items():
        for change in group_diff.fields:
            if change.needs_input:
                continue
            mapping[group][change.field_name] = _entry(change)

    return mapping


def overlay_values(mapping: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    """Answer a mapping's open questions for one dataset with literal values."""
    groups = _mapping_groups(mapping)
    merged = {group: dict(mapping.get(group, {})) for group in groups}
    merged["dropped"] = mapping.get("dropped", {})

    for group, group_values in values.items():
        if group not in groups:
            continue
        for field_name, value in group_values.items():
            merged[group][field_name] = {"action": CONSTANT, "value": value}

    return merged


def unresolved(
    diff: dict[str, GroupDiff], mapping: dict[str, Any]
) -> list[dict[str, str]]:
    """List what the admin still has to decide before the mapping can be used."""
    problems = []

    for group, group_diff in diff.items():
        entries = mapping.get(group, {})

        for change in group_diff.fields:
            entry = entries.get(change.field_name)

            if change.needs_input and entry is None:
                problems.append(_problem(group, change.field_name, change.reason))
                continue

            missing = _unmapped_choices(change.lost_choices, entry)
            if missing:
                problems.append(
                    _problem(
                        group,
                        change.field_name,
                        f"stored values without a replacement: {', '.join(missing)}",
                    )
                )

        acknowledged = set(mapping.get("dropped", {}).get(group, []))
        problems.extend(
            _problem(group, name, "removed field -- its data will be lost")
            for name in group_diff.dropped
            if name not in acknowledged
        )

    return problems


def manual_fields(mapping: dict[str, Any]) -> list[dict[str, str]]:
    """Fields deferred to the guided per-dataset form, so bulk cannot answer them."""
    return [
        _problem(group, field_name, "answered per dataset, not in bulk")
        for group in _mapping_groups(mapping)
        for field_name, entry in mapping.get(group, {}).items()
        if entry.get("action") == MANUAL
    ]


def check(mapping: dict[str, Any], target: dict[str, Any]) -> list[str]:
    """Structural errors in a mapping, independent of any particular dataset."""
    errors = []

    for group in groups_in(target):
        target_fields = {f["field_name"]: f for f in target.get(group, [])}

        for field_name, entry in mapping.get(group, {}).items():
            if field_name not in target_fields:
                errors.append(f"{group}.{field_name}: not a field of the target schema")
                continue
            errors += _check_entry(f"{group}.{field_name}", entry)

    return errors


def _check_entry(location: str, entry: dict[str, Any]) -> list[str]:
    action = entry.get("action")

    if action not in ACTIONS:
        return [f"{location}: unknown action '{action}'"]

    if action == COPY and not entry.get("source"):
        return [f"{location}: 'copy' needs a source field"]

    if action == CONSTANT and "value" not in entry:
        return [f"{location}: 'constant' needs a value"]

    return []


def _entry(change: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"action": change.action}

    if change.action == COPY:
        entry["source"] = change.source

    return entry


def _unmapped_choices(
    lost_choices: list[str], entry: dict[str, Any] | None
) -> list[str]:
    if not lost_choices or entry is None or entry.get("action") != COPY:
        return []

    value_map = entry.get("value_map") or {}
    return [value for value in lost_choices if value not in value_map]


def _problem(group: str, field_name: str, reason: str) -> dict[str, str]:
    return {"group": group, "field_name": field_name, "reason": reason}
