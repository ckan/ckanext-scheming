"""``ckan scheming-dynamic migration`` commands."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import click

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.scheming_dynamic.cli.cli_utils import (
    call_action,
    echo_validation_error,
    entity_type_option,
    site_user_context,
)
from ckanext.scheming_dynamic.schema_migration import runner
from ckanext.scheming_dynamic.schema_migration.model import (
    MigrationRun,
    MigrationRunItem,
)


@click.group()
def migration():
    """Move datasets between versions of the same schema."""


@migration.command()
@entity_type_option
@click.argument("schema_type")
@click.argument("from_version", type=int)
@click.argument("to_version", type=int)
@click.option("--json", "as_json", is_flag=True, help="Output the mapping as JSON.")
@click.pass_context
def mapping(
    ctx: click.Context,
    entity_type: str,
    schema_type: str,
    from_version: int,
    to_version: int,
    as_json: bool,
):
    """Show the field mapping between two versions of SCHEMA_TYPE.

    Prints the stored mapping when there is one, otherwise the auto-derived
    suggestion, followed by whatever still needs a decision.

    ckan scheming-dynamic migration mapping --type dataset test-type 1 2
    """
    result = call_action(
        ctx,
        "scheming_migration_mapping_show",
        {
            "entity_type": entity_type,
            "schema_type": schema_type,
            "from_version": from_version,
            "to_version": to_version,
        },
    )

    if as_json:
        click.echo(json.dumps(result["mapping"], indent=2))
        return

    for group in result["diff"]:
        for change in result["diff"][group]["fields"]:
            marker = "?" if change["needs_input"] else " "
            source = change["source"] or "--"
            click.echo(
                f"  {marker} [{group}] {change['field_name']} <- {source} "
                f"({change['change']}/{change['action']})"
            )
        for name in result["diff"][group]["dropped"]:
            click.secho(f"  ? [{group}] {name} -- dropped", fg="yellow")

    if not result["unresolved"]:
        click.secho("Ready to apply", fg="green")
        return

    click.secho(f"{len(result['unresolved'])} decision(s) needed:", fg="yellow")
    for problem in result["unresolved"]:
        click.secho(
            f"  {problem['group']}.{problem['field_name']}: {problem['reason']}",
            fg="yellow",
        )
    ctx.exit(1)


@migration.command()
@entity_type_option
@click.argument("schema_type")
@click.argument("from_version", type=int)
@click.argument("to_version", type=int)
@click.option("--dry-run", is_flag=True, help="Validate without writing anything.")
@click.pass_context
def apply(
    ctx: click.Context,
    entity_type: str,
    schema_type: str,
    from_version: int,
    to_version: int,
    dry_run: bool,
):
    """Migrate every dataset of SCHEMA_TYPE pinned to FROM_VERSION.

    Runs here, so a portal without a job worker can still migrate.

    ckan scheming-dynamic migration apply --type dataset test-type 1 2
    """
    context = site_user_context()

    try:
        mapping_doc = runner.ready_mapping(
            entity_type, schema_type, from_version, to_version
        )
        runner.refuse_while_running(entity_type, schema_type, from_version, to_version)
    except tk.ValidationError as e:
        echo_validation_error(e)
        ctx.exit(1)

    run = runner.start(
        schema_type,
        entity_type,
        from_version,
        to_version,
        mapping_doc,
        context.get("user", ""),
        dry_run,
    )

    with click.progressbar(length=run.total, label="Migrating") as bar:
        runner.execute(run.id, progress=bar.update)

    _echo_run(run)

    ctx.exit(1 if run.failed_count else 0)


@migration.command()
@entity_type_option
@click.option("--schema-type", default=None, help="Limit to one schema type.")
@click.argument("run_id", required=False)
@click.pass_context
def runs(
    ctx: click.Context,
    entity_type: str,
    schema_type: str | None,
    run_id: str | None,
):
    """List migration runs, or show one with its per-dataset results.

    ckan scheming-dynamic migration runs --type dataset
    """
    if run_id:
        run = call_action(ctx, "scheming_migration_run_show", {"id": run_id})
        _echo_run_dict(run)
        for item in run["items"]:
            colour = {"ok": "green", "failed": "red"}.get(item["status"], "cyan")
            click.secho(f"  {item['status']:8} {item['entity_id']}", fg=colour)
            for field, messages in (item["errors"] or {}).items():
                click.secho(f"      {field}: {messages}", fg="red")
        return

    for run in call_action(
        ctx,
        "scheming_migration_run_list",
        {"entity_type": entity_type, "schema_type": schema_type},
    ):
        _echo_run_dict(run)


@migration.command()
@click.argument("run_id")
@click.pass_context
def cancel(ctx: click.Context, run_id: str):
    """Stop a queued or running migration after its current dataset."""
    run = call_action(ctx, "scheming_migration_run_cancel", {"id": run_id})
    click.secho(f"Run {run['id']} cancelled", fg="yellow")


@migration.command()
@click.option(
    "--older-than",
    type=int,
    required=True,
    help="Age in days beyond which recorded values are dropped.",
)
def prune(older_than: int):
    """Drop the recorded before/after values from old run items.

    Their outcome is kept, but the discarded data can no longer be recovered.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=older_than)  # noqa: UP017
    pruned = MigrationRunItem.prune(cutoff)
    model.Session.commit()

    click.secho(f"Pruned {pruned} run item(s)", fg="green")


@migration.command()
@entity_type_option
@click.argument("schema_type", required=False)
@click.pass_context
def status(ctx: click.Context, entity_type: str, schema_type: str | None):
    """Report how far each schema type lags behind its live version."""
    data = {"entity_type": entity_type}
    if schema_type:
        data["schema_type"] = schema_type

    rows = list(call_action(ctx, "scheming_migration_status", data))

    headers = ("Schema type", "Live", "Behind", "Distribution", "Unpinned")
    widths = [
        max(len(headers[i]), *(len(str(row.get(key, ""))) for row in rows))
        for i, key in enumerate(
            ("schema_type", "live_version", "behind", "distribution", "unpinned")
        )
    ]

    def format_row(values: tuple[str, ...]) -> str:
        return "  ".join(
            str(value).ljust(width) for value, width in zip(values, widths, strict=True)
        )

    click.secho(format_row(headers), bold=True)

    for row in rows:
        distribution = " ".join(
            f"v{version}: {count}"
            for version, count in sorted(row["distribution"].items())
        )

        click.secho(
            format_row(
                (
                    row["schema_type"],
                    f"v{row['live_version']}",
                    row["behind"],
                    distribution,
                    row["unpinned"] or "",
                )
            ),
            fg="yellow" if row["behind"] else "green",
        )


def _echo_run(run: MigrationRun) -> None:
    _echo_run_dict(run.as_dict())


def _echo_run_dict(run: dict[str, Any]) -> None:
    label = "dry-run" if run["dry_run"] else "run"
    click.secho(
        f"{run['id']} {label} {run['schema_type']} "
        f"v{run['from_version']} -> v{run['to_version']} "
        f"{run['status']}: {run['ok_count']} ok, {run['failed_count']} failed, "
        f"{run['skipped_count']} skipped",
        fg="red" if run["failed_count"] else "green",
    )
