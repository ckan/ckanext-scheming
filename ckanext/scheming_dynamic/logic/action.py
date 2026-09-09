from __future__ import annotations

import dataclasses
from contextlib import nullcontext
from typing import Any

from click import get_current_context
from flask import current_app, has_app_context

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.logic import validate

from ckanext.scheming_dynamic.const import (
    DEFAULT_ENTITY_TYPE,
    ENTITY_TYPES,
    TYPE_FIELDS,
)
from ckanext.scheming_dynamic.logic import schema
from ckanext.scheming_dynamic.model import (
    SchemingPreset,
    SchemingSchemaActivity,
    SchemingSchemaPin,
    SchemingSchemaVersion,
    SchemingState,
)
from ckanext.scheming_dynamic.preset_resolve import (
    PresetBaseNotFoundError,
    PresetCycleError,
)
from ckanext.scheming_dynamic.render import render_preset_field, render_schema_form
from ckanext.scheming_dynamic.schema_migration import diff, runner, status
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.schema_migration.apply import expanded_definition
from ckanext.scheming_dynamic.schema_migration.model import (
    MigrationRun,
    MigrationRunItem,
    SchemaMigration,
)


@validate(schema.scheming_schema_create)
def scheming_schema_create(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Create a dynamic schema.

    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    :param definition: the ckanext-scheming schema definition; the schema
        type is taken from its type field (e.g. ``dataset_type``)
    :type definition: dict
    """
    tk.check_access("scheming_schema_create", context, data_dict)

    entity_type = data_dict["entity_type"]
    definition = data_dict["definition"]

    schema_type = definition[TYPE_FIELDS[entity_type]]

    if SchemingSchemaVersion.head_version(entity_type, schema_type):
        raise tk.ValidationError(
            {"schema_type": [tk._(f"Schema for '{schema_type}' already exists")]}
        )

    _check_schema_type_not_reserved(entity_type, schema_type)
    _check_schema_type_not_claimed_elsewhere(entity_type, schema_type)
    _check_schema_type_no_blueprint_collision(entity_type, schema_type)
    _check_schema_renders(entity_type, schema_type, definition)

    # locked first: the activity row's FK needs version 1 to already exist
    row = SchemingSchemaVersion.lock(entity_type, schema_type, definition)
    SchemingSchemaActivity.record(
        entity_type,
        schema_type,
        SchemingSchemaActivity.CREATE,
        context["user"],
        definition,
        version=row.version,
    )
    SchemingState.bump(entity_type)
    model.Session.commit()

    return row.as_dict()


@validate(schema.scheming_schema_update)
def scheming_schema_update(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Update a dynamic schema.

    :param schema_type: the schema type whose schema should be updated
    :type schema_type: string
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    :param definition: the schema definition
    :type definition: dict
    """
    tk.check_access("scheming_schema_update", context, data_dict)

    entity_type = data_dict["entity_type"]
    schema_type = data_dict["schema_type"]
    definition = data_dict["definition"]

    head = SchemingSchemaVersion.head(entity_type, schema_type)

    if not head:
        raise tk.ObjectNotFound(tk._(f"Schema for '{schema_type}' not found"))

    type_field = TYPE_FIELDS[entity_type]
    if definition[type_field] != schema_type:
        raise tk.ValidationError(
            {
                "definition": [
                    tk._(f"'{type_field}' must match schema_type '{schema_type}'")
                ]
            }
        )

    _check_schema_renders(entity_type, schema_type, definition)

    row = _lock_or_sync_version(entity_type, schema_type, definition, head)

    SchemingSchemaActivity.record(
        entity_type,
        schema_type,
        SchemingSchemaActivity.UPDATE,
        context["user"],
        definition,
        version=row.version,
    )
    SchemingState.bump(entity_type)
    model.Session.commit()

    return row.as_dict()


def _lock_or_sync_version(
    entity_type: str,
    schema_type: str,
    definition: dict[str, Any],
    head: SchemingSchemaVersion,
) -> SchemingSchemaVersion:
    """Apply an edit to the schema's current (head) version.

    If ``definition`` is unchanged from the head, returns it as-is --
    otherwise, if the head version is already pinned by an entity, it can't
    be changed, so this locks ``definition`` as a new version instead.
    Otherwise nothing depends on the head version yet, so it's safe to
    overwrite its definition directly.

    Returns the version row that now holds ``definition``.
    """
    if head.definition == definition:
        return head

    if SchemingSchemaPin.is_version_locked(entity_type, schema_type, head.version):
        return SchemingSchemaVersion.lock(entity_type, schema_type, definition)

    head.definition = definition
    head.refresh_expanded()
    return head


@validate(schema.scheming_schema_delete)
def scheming_schema_delete(context: Any, data_dict: dict[str, Any]) -> bool:
    """Delete a dynamic schema.

    :param schema_type: the schema type whose schema should be deleted
    :type schema_type: string
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_schema_delete", context, data_dict)

    entity_type = data_dict["entity_type"]
    schema_type = data_dict["schema_type"]

    head = SchemingSchemaVersion.head(entity_type, schema_type)
    if not head:
        raise tk.ObjectNotFound(tk._(f"Schema for '{schema_type}' not found"))

    SchemingSchemaActivity.record(
        entity_type,
        schema_type,
        SchemingSchemaActivity.DELETE,
        context["user"],
        head.definition,
    )
    SchemingSchemaVersion.delete_all(entity_type, schema_type)
    SchemingState.bump(entity_type)
    model.Session.commit()

    return True


@validate(schema.scheming_schema_activity_list)
def scheming_schema_activity_list(
    context: Any, data_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """List a dynamic schema's activity history, oldest first.

    :param schema_type: the schema type whose history should be listed
    :type schema_type: string
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_schema_activity_list", context, data_dict)

    entity_type = data_dict["entity_type"]
    schema_type = data_dict["schema_type"]

    return [
        row.as_dict()
        for row in SchemingSchemaActivity.get_history(entity_type, schema_type)
    ]


def _check_schema_type_not_reserved(entity_type: str, schema_type: str) -> None:
    """Refuse "dataset"/"group"/"organization" for a different entity_type.

    CKAN always serves those names through its own built-in, statically
    registered blueprint for the matching entity type -- ahead of both of
    scheming_dynamic's catch-all blueprints -- regardless of whether a
    dynamic schema exists. A schema using one of those names for a
    different entity_type would be created successfully but have no URL
    that could ever reach it.
    """
    if schema_type in ENTITY_TYPES and schema_type != entity_type:
        raise tk.ValidationError(
            {
                "schema_type": [
                    tk._(
                        "'{schema_type}' is reserved for entity_type "
                        "'{schema_type}'; it can't be used for entity_type "
                        "'{entity_type}'"
                    ).format(schema_type=schema_type, entity_type=entity_type)
                ]
            }
        )


def _check_schema_type_not_claimed_elsewhere(
    entity_type: str, schema_type: str
) -> None:
    """Refuse a schema_type already live under a different entity_type.

    The dataset and group/organization catch-all blueprints match on the
    same URL shape (a single dynamic path segment), so a live schema_type
    under one entity_type shadows -- and makes unreachable through the web
    UI -- the same name under another.
    """
    for other_entity_type in ENTITY_TYPES:
        if other_entity_type == entity_type:
            continue
        if SchemingSchemaVersion.head_version(other_entity_type, schema_type):
            raise tk.ValidationError(
                {
                    "schema_type": [
                        tk._(
                            "'{schema_type}' is already used by entity_type "
                            "'{other_entity_type}'; schema_type must be "
                            "unique across entity types"
                        ).format(
                            schema_type=schema_type,
                            other_entity_type=other_entity_type,
                        )
                    ]
                }
            )


def _current_flask_app() -> Any:
    """Return the active Flask app, or ``None`` if there isn't one.

    Mirrors ``_check_schema_renders``: a web request exposes the app
    through the app context, a Click command carries it in the context
    meta, and anything else (some bare ``ckanapi`` calls) has neither.
    """
    if has_app_context():
        return current_app._get_current_object()

    try:
        return get_current_context().meta.get("flask_app")
    except RuntimeError:
        return None


def _check_schema_type_no_blueprint_collision(
    entity_type: str, schema_type: str
) -> None:
    """Refuse a schema_type that collides with an existing Flask blueprint.

    At startup CKAN registers one blueprint per *custom* dataset/group/
    organization type, named exactly after the type (datasets additionally
    get a ``<type>_resource`` one). ``register_package_blueprints`` /
    ``register_group_blueprints`` raise ``ValueError`` -- aborting startup
    -- when that name is already taken, whether by a CKAN core blueprint
    (``user``, ``dashboard``, ``api``, ...) or one from another extension.
    The cross-``entity_type`` reserved names and the ``_resource`` suffix
    are rejected earlier; this covers every other collision, so a schema
    saved through the UI can't wedge the next restart.
    """
    # Overriding a built-in type (dataset/group/organization) with a schema
    # of the *same* name is the normal case: CKAN serves those through its
    # own blueprint and never registers a per-type one for them. Any
    # ENTITY_TYPES name reaching here matches entity_type --
    # _check_schema_type_not_reserved already rejected the mismatches.
    if schema_type == entity_type:
        return

    app = _current_flask_app()
    if app is None:
        # nothing to inspect here; CKAN's own startup check stays the backstop
        return

    candidates = {schema_type}
    if entity_type == DEFAULT_ENTITY_TYPE:
        candidates.add(f"{schema_type}_resource")

    clashing = sorted(name for name in candidates if name in app.blueprints)
    if clashing:
        raise tk.ValidationError(
            {
                "schema_type": [
                    tk._(
                        "'{schema_type}' collides with an existing route "
                        "({names}); pick a different name"
                    ).format(schema_type=schema_type, names=", ".join(clashing))
                ]
            }
        )


def _check_schema_renders(
    entity_type: str, schema_type: str, definition: dict[str, Any]
) -> None:
    """Raise ValidationError if a schema's form can't render.

    Mirrors the /preview check, so a schema broken the same way can't be
    saved through the create/update actions either.
    """
    # TODO: this is a bit of a hack, but it's the only way to get the
    # render-check of a schema's form work for both CLI (e.g. ckanapi)
    # and web UI.
    if has_app_context():
        ctx = nullcontext()
    else:
        try:
            ctx = get_current_context().meta["flask_app"].test_request_context("/")
        except RuntimeError:
            return

    with ctx:
        try:
            render_schema_form(entity_type, schema_type, definition)
        except Exception as e:  # noqa: BLE001
            raise tk.ValidationError(
                {"definition": [tk._("Schema cannot be rendered: {}").format(e)]}
            ) from e


def _check_preset_renders(preset_name: str, values: dict[str, Any]) -> None:
    """Raise ValidationError if a preset's field snippet can't render.

    Mirrors the /presets/preview check, so a preset broken the same way
    can't be saved through the create/update actions either.
    """
    try:
        render_preset_field(preset_name, values)
    except PresetCycleError as e:
        raise tk.ValidationError(
            {
                "definition": [
                    tk._("Preset cycle detected: {}").format(
                        " -> ".join([*e.chain, e.chain[0]])
                    )
                ]
            }
        ) from e
    except PresetBaseNotFoundError as e:
        raise tk.ValidationError(
            {
                "definition": [
                    tk._(
                        f"Base preset '{e.base}' is not a registered or existing preset"
                    )
                ]
            }
        ) from e
    except Exception as e:  # noqa: BLE001
        raise tk.ValidationError(
            {"definition": [tk._("Form snippet failed to render: {}").format(e)]}
        ) from e


@validate(schema.scheming_preset_create)
def scheming_preset_create(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Create a field preset.

    :param definition: ``{"preset_name": ..., "values": {...}}``; the same
        attribute bag a dataset/resource field can take
    :type definition: dict
    """
    tk.check_access("scheming_preset_create", context, data_dict)

    definition = data_dict["definition"]
    preset_name = definition["preset_name"]

    if SchemingPreset.get(preset_name):
        raise tk.ValidationError(
            {"preset_name": [tk._(f"Preset '{preset_name}' already exists")]}
        )

    _check_preset_renders(preset_name, definition["values"])

    row = SchemingPreset.create(preset_name, definition["values"])

    return row.as_dict()


@validate(schema.scheming_preset_update)
def scheming_preset_update(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Update a field preset.

    :param preset_name: the preset to update
    :type preset_name: string
    :param definition: ``{"preset_name": ..., "values": {...}}``
    :type definition: dict
    """
    tk.check_access("scheming_preset_update", context, data_dict)

    preset_name = data_dict["preset_name"]
    definition = data_dict["definition"]

    preset = SchemingPreset.get(preset_name)
    if not preset:
        raise tk.ObjectNotFound(tk._(f"Preset '{preset_name}' not found"))

    if definition["preset_name"] != preset_name:
        raise tk.ValidationError(
            {
                "definition": [
                    tk._(f"'preset_name' must match preset_name '{preset_name}'")
                ]
            }
        )

    _check_preset_renders(preset_name, definition["values"])

    preset.update_values(definition["values"])

    return preset.as_dict()


@validate(schema.scheming_preset_delete)
def scheming_preset_delete(context: Any, data_dict: dict[str, Any]) -> bool:
    """Delete a field preset.

    :param preset_name: the preset to delete
    :type preset_name: string
    """
    tk.check_access("scheming_preset_delete", context, data_dict)

    preset_name = data_dict["preset_name"]

    preset = SchemingPreset.get(preset_name)
    if not preset:
        raise tk.ObjectNotFound(tk._(f"Preset '{preset_name}' not found"))

    preset.delete()

    return True


def _version_pair(data_dict: dict[str, Any]) -> tuple[str, str, int, int]:
    return (
        data_dict["entity_type"],
        data_dict["schema_type"],
        data_dict["from_version"],
        data_dict["to_version"],
    )


@validate(schema.scheming_migration_status)
def scheming_migration_status(
    context: Any, data_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """Report how many datasets of each schema type lag behind its live version.

    :param entity_type: the entity these schemas apply to (default: ``dataset``)
    :type entity_type: string
    :param schema_type: limit the report to a single schema type
    :type schema_type: string
    """
    tk.check_access("scheming_migration_status", context, data_dict)

    entity_type = data_dict["entity_type"]
    schema_type = data_dict.get("schema_type")

    if not schema_type:
        return status.all_schema_types(entity_type)

    head_version = SchemingSchemaVersion.head_version(entity_type, schema_type)
    if not head_version:
        raise tk.ObjectNotFound(tk._(f"Schema for '{schema_type}' not found"))

    return [status.for_schema_type(entity_type, schema_type, head_version)]


@validate(schema.scheming_migration_mapping_show)
def scheming_migration_mapping_show(
    context: Any, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Show the field mapping between two versions of one schema.

    Returns the stored mapping (or the auto-derived suggestion when nothing is
    stored yet), the field-by-field classification, and whatever still needs a
    decision before the mapping can be applied.

    :param schema_type: the schema being migrated
    :type schema_type: string
    :param from_version: the version datasets are currently pinned to
    :type from_version: int
    :param to_version: the version they should move to
    :type to_version: int
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_migration_mapping_show", context, data_dict)

    entity_type, schema_type, from_version, to_version = _version_pair(data_dict)

    source = expanded_definition(entity_type, schema_type, from_version)
    target = expanded_definition(entity_type, schema_type, to_version)

    changes = diff.compare(source, target)
    suggested = mapping_lib.suggest(changes)

    row = SchemaMigration.get(entity_type, schema_type, from_version, to_version)
    current = row.mapping if row else suggested

    return {
        "entity_type": entity_type,
        "schema_type": schema_type,
        "from_version": from_version,
        "to_version": to_version,
        "stored": row.as_dict() if row else None,
        "mapping": current,
        "suggested": suggested,
        "diff": {
            group: dataclasses.asdict(group_diff)
            for group, group_diff in changes.items()
        },
        "unresolved": mapping_lib.unresolved(changes, current),
    }


@validate(schema.scheming_migration_mapping_update)
def scheming_migration_mapping_update(
    context: Any, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Store the field mapping between two versions of one schema.

    :param schema_type: the schema being migrated
    :type schema_type: string
    :param from_version: the version datasets are currently pinned to
    :type from_version: int
    :param to_version: the version they should move to
    :type to_version: int
    :param mapping: the mapping document
    :type mapping: dict
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_migration_mapping_update", context, data_dict)

    entity_type, schema_type, from_version, to_version = _version_pair(data_dict)

    row = SchemaMigration.save(
        entity_type,
        schema_type,
        from_version,
        to_version,
        data_dict["mapping"],
        context["user"],
    )

    return row.as_dict()


@validate(schema.scheming_migration_mapping_delete)
def scheming_migration_mapping_delete(context: Any, data_dict: dict[str, Any]) -> bool:
    """Delete a stored field mapping.

    :param schema_type: the schema being migrated
    :type schema_type: string
    :param from_version: the source version
    :type from_version: int
    :param to_version: the target version
    :type to_version: int
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_migration_mapping_delete", context, data_dict)

    row = SchemaMigration.get(*_version_pair(data_dict))
    if row is None:
        raise tk.ObjectNotFound(tk._("Mapping not found"))

    row.delete()

    return True


@validate(schema.scheming_migration_apply)
def scheming_migration_apply(context: Any, data_dict: dict[str, Any]) -> dict[str, Any]:
    """Move datasets from one schema version to another.

    With ``id``, migrates that one dataset synchronously and returns the
    finished run. Without it, queues a background run over every dataset still
    pinned to ``from_version`` and returns it as ``pending``.

    :param schema_type: the schema being migrated
    :type schema_type: string
    :param from_version: the version datasets are currently pinned to
    :type from_version: int
    :param to_version: the version they should move to
    :type to_version: int
    :param id: migrate only this dataset, synchronously
    :type id: string
    :param dry_run: validate without writing anything
    :type dry_run: bool
    :param values: with ``id``, answers to the mapping's open questions for
        that dataset, as ``{"dataset_fields": {"<field>": value}}``
    :type values: dict
    :param entity_type: the entity this schema applies to (default: ``dataset``)
    :type entity_type: string
    """
    tk.check_access("scheming_migration_apply", context, data_dict)

    entity_type, schema_type, from_version, to_version = _version_pair(data_dict)
    dry_run = data_dict.get("dry_run", False)

    entity_id = data_dict.get("id")
    values = data_dict.get("values") if entity_id else None

    runner.refuse_while_running(entity_type, schema_type, from_version, to_version)
    mapping = runner.ready_mapping(
        entity_type, schema_type, from_version, to_version, values
    )

    if entity_id:
        run = runner.run_single(
            schema_type,
            entity_type,
            from_version,
            to_version,
            mapping,
            context["user"],
            entity_id,
            dry_run,
        )
    else:
        run = runner.enqueue(
            schema_type,
            entity_type,
            from_version,
            to_version,
            mapping,
            context["user"],
            dry_run,
        )

    return run.as_dict()


@validate(schema.scheming_migration_run_list)
def scheming_migration_run_list(
    context: Any, data_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """List migration runs, newest first.

    :param entity_type: the entity these schemas apply to (default: ``dataset``)
    :type entity_type: string
    :param schema_type: limit to one schema type
    :type schema_type: string
    :param limit: how many runs to return (default: 20)
    :type limit: int
    :param offset: how many runs to skip
    :type offset: int
    """
    tk.check_access("scheming_migration_run_list", context, data_dict)

    rows = MigrationRun.search(
        data_dict["entity_type"],
        data_dict.get("schema_type"),
        data_dict["limit"],
        data_dict["offset"],
    )

    return [row.as_dict() for row in rows]


@validate(schema.scheming_migration_run_show)
def scheming_migration_run_show(
    context: Any, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Show one migration run together with its per-dataset results.

    :param id: the run id
    :type id: string
    """
    tk.check_access("scheming_migration_run_show", context, data_dict)

    run = MigrationRun.get(data_dict["id"])
    if run is None:
        raise tk.ObjectNotFound(tk._("Migration run not found"))

    return {
        **run.as_dict(),
        "items": [item.as_dict() for item in MigrationRunItem.for_run(run.id)],
    }


@validate(schema.scheming_migration_run_cancel)
def scheming_migration_run_cancel(
    context: Any, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Stop a queued or running migration after its current dataset.

    :param id: the run id
    :type id: string
    """
    tk.check_access("scheming_migration_run_cancel", context, data_dict)

    run = MigrationRun.get(data_dict["id"])
    if run is None:
        raise tk.ObjectNotFound(tk._("Migration run not found"))

    if not run.is_active:
        raise tk.ValidationError({"run": [tk._("Run already {}").format(run.status)]})

    run.cancel()

    return run.as_dict()
