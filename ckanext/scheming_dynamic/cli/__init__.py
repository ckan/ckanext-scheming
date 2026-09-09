from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import click

import ckan.plugins.toolkit as tk
from ckan import model, types
from ckan.lib import plugins as lib_plugins
from ckan.lib.dictization import model_dictize

from ckanext.scheming.plugins import (
    SchemingDatasetsPlugin,
    SchemingGroupsPlugin,
    SchemingOrganizationsPlugin,
)
from ckanext.scheming_dynamic.cli.cli_utils import (
    entity_type_option,
    site_user_context,
)
from ckanext.scheming_dynamic.cli.migration import migration
from ckanext.scheming_dynamic.const import DEFAULT_ENTITY_TYPE
from ckanext.scheming_dynamic.model import (
    SchemingSchemaPin,
    SchemingSchemaVersion,
)
from ckanext.scheming_dynamic.schema import SCHEMA_CLASSES
from ckanext.scheming_dynamic.validator import error_location, iter_errors, load_data


@click.group(short_help="scheming_dynamic commands")
def scheming_dynamic():
    """scheming_dynamic commands."""


scheming_dynamic.add_command(migration)


@scheming_dynamic.command()
@entity_type_option
def validation_schema(entity_type: str):
    """Output the JSON Schema for the given entity type.

    Used to validate ckanext-scheming schemas.

    ckan scheming-dynamic validation-schema --type dataset > dataset_schema.schema.json
    """
    click.echo(json.dumps(SCHEMA_CLASSES[entity_type]().build(), indent=2))


@scheming_dynamic.command()
@entity_type_option
@click.argument("schema_file", nargs=-1, required=True, type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, entity_type: str, schema_file: list[str]):
    """Validate ckanext-scheming schema file(s).

    Validates against JSON Schema for --type (default: dataset).

    ckan scheming-dynamic validate path/to/schema.yaml [more-schemas.json ...]
    """
    any_errors = False
    schema_instance = SCHEMA_CLASSES[entity_type]()

    for f in schema_file:
        data = load_data(Path(f))
        errors = list(iter_errors(data, schema_instance))

        click.secho(f"Validating schema {f}", fg="green")

        if not errors:
            click.secho("OK - no schema violations", fg="cyan")
            continue

        any_errors = True

        for error in errors:
            click.secho(f"  [{error_location(error)}] {error.message}", fg="red")

    ctx.exit(1 if any_errors else 0)


@scheming_dynamic.command()
@entity_type_option
@click.argument("schema_type")
@click.pass_context
def sync(ctx: click.Context, entity_type: str, schema_type: str):
    """Import/refresh a dynamic schema from its static (file-defined) definition.

    Run once per SCHEMA_TYPE when enabling scheming_dynamic on a portal that
    already has entities of that type defined through a file schema:
    creates the dynamic schema and locks version 1 from the static
    definition. Re-running later re-imports the static definition and locks
    a new version if it changed since the last locked version -- reports
    and does nothing if it's unchanged. Existing entities are left
    unpinned; run `pin` afterwards.

    ckan scheming-dynamic sync --type dataset test-type
    """
    definition = _static_schema(entity_type, schema_type)
    if definition is None:
        click.secho(
            f"No static {entity_type} schema found for type '{schema_type}'",
            fg="red",
        )
        ctx.exit(1)

    context = site_user_context()
    head_version = SchemingSchemaVersion.head_version(entity_type, schema_type)

    try:
        if head_version == 0:
            tk.get_action("scheming_schema_create")(
                context, {"entity_type": entity_type, "definition": definition}
            )
            head_version = SchemingSchemaVersion.head_version(entity_type, schema_type)
            click.secho(
                f"Created dynamic schema '{schema_type}' ({entity_type}), "
                f"version {head_version}",
                fg="green",
            )
            return

        existing = cast(
            SchemingSchemaVersion,
            SchemingSchemaVersion.get(entity_type, schema_type, head_version),
        )

        if existing.definition == definition:
            click.secho(
                f"Schema '{schema_type}' ({entity_type}) already matches the "
                f"static schema (version {head_version})",
                fg="cyan",
            )
            return

        tk.get_action("scheming_schema_update")(
            context,
            {"entity_type": entity_type, "definition": definition},
        )
        head_version = SchemingSchemaVersion.head_version(entity_type, schema_type)
        click.secho(
            f"Updated schema '{schema_type}' ({entity_type}); now at version "
            f"{head_version}",
            fg="green",
        )
    except tk.ValidationError as e:
        click.secho(f"Validation error: {e.error_summary}", fg="red")
        ctx.exit(1)


@scheming_dynamic.command()
@entity_type_option
@click.argument("schema_type")
@click.option(
    "-v",
    "--version",
    "version",
    type=int,
    default=None,
    help="Schema version to pin to (default: current locked HEAD version).",
)
@click.option(
    "--no-validate",
    is_flag=True,
    default=False,
    help=(
        "Pin every entity unconditionally, without checking whether its "
        "data would validate against the target version. Risky."
    ),
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Report what would be pinned/fail without actually pinning anything.",
)
@click.pass_context
def pin(
    ctx: click.Context,
    entity_type: str,
    schema_type: str,
    version: int | None,
    no_validate: bool,
    dry_run: bool,
):
    """Pin every not-yet-pinned entity of SCHEMA_TYPE to a locked schema version.

    By default each entity's current data is validated against the target
    version first; entities that fail are reported and left unpinned so they
    can be reviewed later. A failure does not stop the command from continuing
    to the next entity. Pass --no-validate to pin unconditionally.

    Pass --dry-run to see what the command would do -- including running
    validation, unless combined with --no-validate -- without writing any pins.

    ckan scheming-dynamic pin --type dataset test-type -v 1
    """
    target_version = _get_target_version(ctx, entity_type, schema_type, version)

    context = site_user_context()
    validator = Validator(entity_type, schema_type, context["user"])  # type: ignore

    pinned = failed = 0

    for entity in _unpinned_entities(entity_type, schema_type):
        if not no_validate and _validation_failed(validator, entity, target_version):
            failed += 1
            continue

        if not dry_run:
            SchemingSchemaPin.pin(entity_type, entity.id, schema_type, target_version)
            model.Session.commit()
        pinned += 1

    verb = "Would pin" if dry_run else "Pinned"
    summary = f"{verb} {pinned} {entity_type}(s) to version {target_version}"
    if failed:
        would = "would fail" if dry_run else "failed"
        summary += f", {failed} {would} validation and were left unpinned"

    click.secho(summary, fg="yellow" if failed else "green")
    ctx.exit(1 if failed else 0)


def _get_target_version(
    ctx: click.Context,
    entity_type: str,
    schema_type: str,
    version: int | None,
) -> int:
    head = SchemingSchemaVersion.head_version(entity_type, schema_type)

    if head == 0:
        click.secho(
            f"No locked version for '{schema_type}' ({entity_type}) -- `sync` first.",
            fg="red",
        )
        ctx.exit(1)

    target_version = head if version is None else version

    if SchemingSchemaVersion.get(entity_type, schema_type, target_version) is None:
        click.secho(
            f"Version {target_version} does not exist.",
            fg="red",
        )
        ctx.exit(1)

    return target_version


def _validation_failed(
    validator: Validator,
    entity: model.Package | model.Group,
    version: int,
) -> bool:
    errors = validator.validate(entity, version)

    if not errors:
        return False

    click.secho(f"  [{entity.id}] validation failed:", fg="red")
    for field, field_errors in errors.items():
        click.secho(
            f"    {field}: {'; '.join(str(e) for e in field_errors)}",
            fg="red",
        )

    return True


def _static_schema(entity_type: str, schema_type: str) -> dict[str, Any] | None:
    """The file-defined (pre-database-overlay) schema for entity/schema type."""
    plugin_class = {
        DEFAULT_ENTITY_TYPE: SchemingDatasetsPlugin,
        "group": SchemingGroupsPlugin,
        "organization": SchemingOrganizationsPlugin,
    }[entity_type]

    instance = plugin_class.instance

    if instance is None:
        raise click.ClickException(
            f"No scheming plugin for '{entity_type}' entities is loaded"
        )

    # ``_static_schemas`` is the file-defined definition, before the database
    # overlay (all three plugins keep it via _DynamicSchemaSyncMixin).
    return instance._static_schemas.get(schema_type)


def _unpinned_entities(
    entity_type: str, schema_type: str
) -> Iterator[model.Package | model.Group]:
    if entity_type == DEFAULT_ENTITY_TYPE:
        entity_model = model.Package
        filters = [model.Package.type == schema_type]
    else:
        entity_model = model.Group
        filters = [
            model.Group.type == schema_type,
            model.Group.is_organization == (entity_type == "organization"),
        ]

    query = model.Session.query(entity_model).filter(*filters)

    query = query.filter(
        ~model.Session.query(SchemingSchemaPin)
        .filter(SchemingSchemaPin.entity_id == entity_model.id)
        .exists()
    )

    yield from query


class Validator:
    def __init__(self, entity_type: str, schema_type: str, user: str):
        self.entity_type = entity_type
        self.schema_type = schema_type
        self.user = user

        if entity_type == DEFAULT_ENTITY_TYPE:
            self.plugin = lib_plugins.lookup_package_plugin(schema_type)
            self._dictize_func = model_dictize.package_dictize
            self._show_schema = self.plugin.show_package_schema
            self._update_schema = self.plugin.update_package_schema
            self._show_action = "package_show"
            self._update_action = "package_update"
        else:
            self.plugin = lib_plugins.lookup_group_plugin(schema_type)
            self._dictize_func = model_dictize.group_dictize
            self._show_schema = self.plugin.show_group_schema
            self._update_schema = self.plugin.update_group_schema
            self._show_action = f"{entity_type}_show"
            self._update_action = f"{entity_type}_update"

    def validate(
        self,
        entity: model.Package | model.Group,
        version: int,
    ) -> dict[str, Any]:
        """Validate an entity's current data against a specific schema version.

        First runs the raw dict through the *show* schema, then through the
        real *update* schema, which is where required fields
        are actually enforced.

        Both passes go through ckanext-scheming's own ``validate()``.

        Temporarily flushes (never commits) a pin to ``version`` *before* both
        passes so ckanext-scheming's ``validate()``, then always rolls the
        flushed pin back.

        Returns the navl error dict from the update pass -- empty if the data is valid.
        """
        context = types.Context(user=self.user, ignore_auth=True, session=model.Session)

        SchemingSchemaPin.pin(self.entity_type, entity.id, self.schema_type, version)

        try:
            raw_dict = self._dictize_func(entity, context)  # type: ignore
            shown, _ = lib_plugins.plugin_validate(
                self.plugin, context, raw_dict, self._show_schema(), self._show_action
            )
            _, errors = lib_plugins.plugin_validate(
                self.plugin,
                context,
                shown,
                self._update_schema(),
                self._update_action,
            )
        finally:
            model.Session.rollback()

        return errors


def get_commands() -> list[click.Command]:
    return [scheming_dynamic]
