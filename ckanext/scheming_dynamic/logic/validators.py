import logging
from typing import Any

import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.lib.navl.dictization_functions import missing

from ckanext.scheming.plugins import _expand_schemas
from ckanext.scheming_dynamic import sync
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE, TYPE_FIELDS
from ckanext.scheming_dynamic.model import SchemingPreset, SchemingSchemaVersion
from ckanext.scheming_dynamic.preset_resolve import (
    PresetBaseNotFoundError,
    PresetCycleError,
    resolve_preset_values,
)
from ckanext.scheming_dynamic.schema import SCHEMA_CLASSES, PresetSchema
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.validator import error_location, iter_errors

log = logging.getLogger(__name__)


def scheming_default_entity_type(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    entity_type_key = ("entity_type",)
    value = data.get(entity_type_key)

    if value is None or value == "" or value is missing:
        data[entity_type_key] = DEFAULT_ENTITY_TYPE


def scheming_definition_valid(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    if errors.get(key):
        return

    entity_type = data[("entity_type",)]
    definition = data[key]

    schema_cls = SCHEMA_CLASSES.get(entity_type)
    if not schema_cls:
        raise tk.Invalid(tk._(f"Entity type '{entity_type}' is not supported"))

    errs = list(iter_errors(definition, schema_cls()))
    if errs:
        raise tk.Invalid("; ".join(f"{error_location(e)}: {e.message}" for e in errs))

    type_field = TYPE_FIELDS[entity_type]
    if definition[type_field].endswith("_resource"):
        raise tk.Invalid(tk._(f"'{type_field}' must not end with '_resource'."))

    try:
        _expand_schemas({definition[type_field]: definition})
    except Exception as e:
        raise tk.Invalid(tk._("Schema cannot be expanded: {}").format(e)) from e


def scheming_schema_exists(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    entity_type = data[("entity_type",)]
    schema_type = data[("schema_type",)]

    if SchemingSchemaVersion.head_version(entity_type, schema_type):
        return

    raise tk.Invalid(tk._(f"Scheming schema {entity_type}:{schema_type} not found."))


def scheming_schema_not_in_use(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    """Refuse to delete a schema while an entity still uses its type."""
    entity_type = data[("entity_type",)]
    schema_type = data[key]

    if entity_type == DEFAULT_ENTITY_TYPE:
        in_use = (
            model.Session.query(model.Package.id)
            .filter(model.Package.type == schema_type)
            .first()
            is not None
        )
        noun = "datasets"
    else:
        in_use = (
            model.Session.query(model.Group.id)
            .filter(
                model.Group.type == schema_type,
                model.Group.is_organization == (entity_type == "organization"),
                model.Group.state != model.State.DELETED,
            )
            .first()
            is not None
        )
        noun = "organizations" if entity_type == "organization" else "groups"

    if in_use:
        raise tk.Invalid(
            tk._(
                f"Cannot delete schema '{schema_type}': {noun} of this "
                "type still exist."
            )
        )


def scheming_preset_definition_valid(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    if errors.get(key):
        return

    definition = data[key]

    preset_name = definition.get("preset_name")

    errs = list(iter_errors(definition, PresetSchema(exclude_preset_name=preset_name)))
    if errs:
        raise tk.Invalid("; ".join(f"{error_location(e)}: {e.message}" for e in errs))

    # overlay the candidate on top of the other stored presets: covers both
    # create (a brand new name) and update (replacing the stored values)
    raw = {row.preset_name: row.values for row in SchemingPreset.get_all()}
    raw[preset_name] = definition["values"]

    try:
        resolve_preset_values(preset_name, raw, sync.get_static_presets())
    except PresetCycleError as e:
        raise tk.Invalid(
            tk._("Preset cycle detected: {}").format(
                " -> ".join([*e.chain, e.chain[0]])
            )
        ) from e
    except PresetBaseNotFoundError as e:
        raise tk.Invalid(
            tk._(f"Base preset '{e.base}' is not a registered or existing preset")
        ) from e


def scheming_preset_exists(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    preset_name = data[key]

    if SchemingPreset.get(preset_name):
        return

    raise tk.Invalid(tk._(f"Preset '{preset_name}' not found."))


def scheming_preset_not_in_use(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    """Refuse to delete a preset while something still depends on it.

    Two ways a preset counts as "in use":
    - another stored preset bases on it (``values.preset``), even if that
      preset isn't used by any schema yet — deleting the base would leave
      it unresolvable;
    - a DB schema field uses it, directly or through such a base chain.

    File-defined schemas are out of scope: they already fail to load at
    startup if they reference an unregistered preset, so there's nothing to
    protect there.
    """
    preset_name = data[key]

    raw = {row.preset_name: row.values for row in SchemingPreset.get_all()}
    dependents = _preset_dependents(preset_name, raw)

    other_dependents = dependents - {preset_name}
    if other_dependents:
        raise tk.Invalid(
            tk._(
                f"Cannot delete preset '{preset_name}': preset(s) "
                f"{', '.join(sorted(other_dependents))} are based on it."
            )
        )

    for entity_type in SCHEMA_CLASSES:
        for row in SchemingSchemaVersion.get_heads_of_type(entity_type):
            if not _definition_uses_any_preset(row.definition, dependents):
                continue

            raise tk.Invalid(
                tk._(
                    f"Cannot delete preset '{preset_name}': still used by "
                    f"the '{row.schema_type}' schema."
                )
            )


def _preset_dependents(preset_name: str, raw: dict[str, Any]) -> set[str]:
    """Return ``preset_name`` plus every preset that bases on it, transitively."""
    dependents = {preset_name}
    changed = True
    while changed:
        changed = False
        for name, values in raw.items():
            if name not in dependents and values.get("preset") in dependents:
                dependents.add(name)
                changed = True
    return dependents


def _definition_uses_any_preset(definition: dict[str, Any], names: set[str]) -> bool:
    return any(
        _field_uses_any_preset(field, names)
        for grouping in ("fields", "dataset_fields", "resource_fields")
        for field in definition.get(grouping, [])
    )


def _field_uses_any_preset(field: dict[str, Any], names: set[str]) -> bool:
    if field.get("preset") in names:
        return True
    return any(
        _field_uses_any_preset(sub, names)
        for grouping in ("repeating_subfields", "simple_subfields")
        for sub in field.get(grouping, [])
    )


def scheming_migration_versions_valid(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    """Both versions must exist and belong to the same schema."""
    if errors.get(key):
        return

    entity_type = data[("entity_type",)]
    schema_type = data[("schema_type",)]
    from_version = data[("from_version",)]
    to_version = data[key]

    if from_version == to_version:
        raise tk.Invalid(tk._("A migration needs two different versions."))

    for version in (from_version, to_version):
        if SchemingSchemaVersion.get(entity_type, schema_type, version) is None:
            raise tk.Invalid(
                tk._(f"Version {version} of '{schema_type}' does not exist.")
            )


def scheming_migration_mapping_valid(
    key: types.FlattenKey,
    data: types.FlattenDataDict,
    errors: types.FlattenErrorDict,
    context: types.Context,
) -> Any:
    """The mapping must only name fields the target schema actually has."""
    if errors.get(key):
        return

    entity_type = data[("entity_type",)]
    schema_type = data[("schema_type",)]
    to_version = data[("to_version",)]

    target = SchemingSchemaVersion.get(entity_type, schema_type, to_version)
    if target is None:
        return

    expanded = _expand_schemas({schema_type: target.definition})[schema_type]

    problems = mapping_lib.check(data[key], expanded)
    if problems:
        raise tk.Invalid("; ".join(problems))


def get_validators():
    return {
        "scheming_default_entity_type": scheming_default_entity_type,
        "scheming_definition_valid": scheming_definition_valid,
        "scheming_schema_exists": scheming_schema_exists,
        "scheming_schema_not_in_use": scheming_schema_not_in_use,
        "scheming_preset_definition_valid": scheming_preset_definition_valid,
        "scheming_preset_exists": scheming_preset_exists,
        "scheming_preset_not_in_use": scheming_preset_not_in_use,
        "scheming_migration_versions_valid": scheming_migration_versions_valid,
        "scheming_migration_mapping_valid": scheming_migration_mapping_valid,
    }
