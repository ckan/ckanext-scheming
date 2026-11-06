"""Compare two versions of a schema and classify what happened to each field."""

from __future__ import annotations

import dataclasses
from difflib import SequenceMatcher
from typing import Any


IDENTICAL = "identical"
WIDENED = "widened"
NARROWED = "narrowed"
ADDED = "added"
RENAMED = "renamed"

COPY = "copy"
CONSTANT = "constant"
DEFAULT = "default"
DROP = "drop"
MANUAL = "manual"

DATASET_GROUP = "dataset_fields"
RESOURCE_GROUP = "resource_fields"
FIELDS_GROUP = "fields"
FIELD_GROUPS = (DATASET_GROUP, RESOURCE_GROUP)
GROUP_ORG_FIELD_GROUPS = (FIELDS_GROUP,)


def groups_in(*schemas: dict[str, Any]) -> tuple[str, ...]:
    """The field groups actually present in one of the given expanded schemas."""
    for schema in schemas:
        if DATASET_GROUP in schema or RESOURCE_GROUP in schema:
            return FIELD_GROUPS
        if FIELDS_GROUP in schema:
            return GROUP_ORG_FIELD_GROUPS
    return FIELD_GROUPS


# attributes that decide whether a stored value stays valid; everything else
# (label, help_text, snippets, ordering) is presentation
VALUE_KEYS = (
    "validators",
    "output_validators",
    "choices",
    "choices_helper",
    "repeating_subfields",
)

RENAME_THRESHOLD = 3
SIGNATURE_SCORE = 3
LABEL_SCORE = 2
NAME_SCORE = 1
NAME_SIMILARITY = 0.8


@dataclasses.dataclass
class FieldChange:
    """What a target field needs in order to be filled from the source version."""

    field_name: str
    change: str
    action: str
    source: str | None = None
    needs_input: bool = False
    reason: str = ""
    lost_choices: list[str] = dataclasses.field(default_factory=list)
    subfields: list[FieldChange] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class GroupDiff:
    fields: list[FieldChange] = dataclasses.field(default_factory=list)
    dropped: list[str] = dataclasses.field(default_factory=list)

    @property
    def needs_input(self) -> bool:
        return bool(self.dropped) or any(f.needs_input for f in self.fields)


def compare(source: dict[str, Any], target: dict[str, Any]) -> dict[str, GroupDiff]:
    """Diff two expanded schema definitions, one GroupDiff per field group."""
    return {
        group: _compare_group(source.get(group, []), target.get(group, []))
        for group in groups_in(target, source)
    }


def needs_input(diff: dict[str, GroupDiff]) -> bool:
    return any(group.needs_input for group in diff.values())


def _compare_group(
    source_fields: list[dict[str, Any]], target_fields: list[dict[str, Any]]
) -> GroupDiff:
    source_by_name = {f["field_name"]: f for f in source_fields}
    target_by_name = {f["field_name"]: f for f in target_fields}

    added = [name for name in target_by_name if name not in source_by_name]
    dropped = [name for name in source_by_name if name not in target_by_name]
    renames = _match_renames(source_by_name, target_by_name, added, dropped)

    renamed_from = set(renames.values())
    result = GroupDiff(dropped=[n for n in dropped if n not in renamed_from])

    for name, target_field in target_by_name.items():
        if name in source_by_name:
            result.fields.append(_compare_pair(source_by_name[name], target_field))
        elif name in renames:
            result.fields.append(_renamed(source_by_name[renames[name]], target_field))
        else:
            result.fields.append(_added(target_field))

    return result


def _compare_pair(source: dict[str, Any], target: dict[str, Any]) -> FieldChange:
    change = FieldChange(
        field_name=target["field_name"],
        change=IDENTICAL,
        action=COPY,
        source=source["field_name"],
        subfields=_compare_subfields(source, target),
    )

    if _signature(source) == _signature(target):
        return change

    change.lost_choices = _lost_choices(source, target)
    newly_required = _is_required(target) and not _is_required(source)

    if _is_widening(source, target):
        change.change = WIDENED
        return change

    change.change = NARROWED

    if change.lost_choices:
        change.needs_input = True
        change.reason = "choices no longer accept every stored value"
    elif newly_required:
        change.needs_input = True
        change.reason = "field became required"

    return change


def _renamed(source: dict[str, Any], target: dict[str, Any]) -> FieldChange:
    return FieldChange(
        field_name=target["field_name"],
        change=RENAMED,
        action=COPY,
        source=source["field_name"],
        needs_input=True,
        reason=f"looks like a rename of '{source['field_name']}' -- confirm",
        lost_choices=_lost_choices(source, target),
        subfields=_compare_subfields(source, target),
    )


def _added(target: dict[str, Any]) -> FieldChange:
    if target.get("default") is not None:
        return FieldChange(target["field_name"], ADDED, DEFAULT)

    if not _is_required(target):
        return FieldChange(target["field_name"], ADDED, DROP)

    return FieldChange(
        target["field_name"],
        ADDED,
        MANUAL,
        needs_input=True,
        reason="new required field with no default",
    )


def _compare_subfields(
    source: dict[str, Any], target: dict[str, Any]
) -> list[FieldChange]:
    source_subfields = source.get("repeating_subfields")
    target_subfields = target.get("repeating_subfields")

    if not source_subfields or not target_subfields:
        return []

    return _compare_group(source_subfields, target_subfields).fields


def _match_renames(
    source_by_name: dict[str, dict[str, Any]],
    target_by_name: dict[str, dict[str, Any]],
    added: list[str],
    dropped: list[str],
) -> dict[str, str]:
    """Pair added fields with dropped ones that look like the same field renamed."""
    scored = sorted(
        (
            (_rename_score(source_by_name[old], target_by_name[new]), new, old)
            for new in added
            for old in dropped
        ),
        reverse=True,
    )

    renames: dict[str, str] = {}
    taken: set[str] = set()

    for score, new, old in scored:
        if score < RENAME_THRESHOLD or new in renames or old in taken:
            continue
        renames[new] = old
        taken.add(old)

    return renames


def _rename_score(source: dict[str, Any], target: dict[str, Any]) -> int:
    score = 0
    signature = _signature(source)

    if signature == _signature(target) and _is_distinctive(signature):
        score += SIGNATURE_SCORE

    if _labels(source) & _labels(target):
        score += LABEL_SCORE

    if (
        SequenceMatcher(None, source["field_name"], target["field_name"]).ratio()
        > NAME_SIMILARITY
    ):
        score += NAME_SCORE

    return score


def _signature(field: dict[str, Any]) -> tuple[Any, ...]:
    return (*(_normalize(field.get(key)) for key in VALUE_KEYS), _is_required(field))


def _is_distinctive(signature: tuple[Any, ...]) -> bool:
    """Whether a signature says anything -- two bare fields are not a match."""
    return any(part for part in signature)


def _normalize(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_normalize(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((k, _normalize(v)) for k, v in value.items()))
    return value


def _is_required(field: dict[str, Any]) -> bool:
    if field.get("required"):
        return True
    return "not_empty" in _validators(field)


def _validators(field: dict[str, Any]) -> set[str]:
    return set(str(field.get("validators") or "").split())


def _labels(field: dict[str, Any]) -> set[str]:
    label = field.get("label")
    if isinstance(label, dict):
        return set(label.values())
    return {label} if label else set()


def _choice_values(field: dict[str, Any]) -> set[str] | None:
    """The declared choice values, or None when they cannot be known upfront."""
    if field.get("choices_helper"):
        return None

    if choices := field.get("choices"):
        return {choice["value"] for choice in choices}

    return None


def _lost_choices(source: dict[str, Any], target: dict[str, Any]) -> list[str]:
    source_values = _choice_values(source)
    target_values = _choice_values(target)

    if source_values is None or target_values is None:
        return []

    return sorted(source_values - target_values)


def _is_widening(source: dict[str, Any], target: dict[str, Any]) -> bool:
    if _is_required(target) and not _is_required(source):
        return False

    if _normalize(source.get("repeating_subfields")) != _normalize(
        target.get("repeating_subfields")
    ):
        return False

    if not _validators(target) <= _validators(source):
        return False

    source_values = _choice_values(source)
    target_values = _choice_values(target)

    if source_values is None or target_values is None:
        return source_values == target_values

    return source_values <= target_values
