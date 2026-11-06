from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import ckan.plugins.toolkit as tk
from ckan import model

from ckanext.scheming_dynamic.model import _current_datetime
from ckanext.scheming_dynamic.schema_migration import diff
from ckanext.scheming_dynamic.schema_migration import mapping as mapping_lib
from ckanext.scheming_dynamic.schema_migration.apply import (
    Migrator,
    entities_at_version,
    expanded_definition,
)
from ckanext.scheming_dynamic.schema_migration.model import (
    MigrationRun,
    MigrationRunItem,
    SchemaMigration,
)

log = logging.getLogger(__name__)

JOB_TIMEOUT_CONFIG = "ckanext.scheming_dynamic.migration_job_timeout"
DEFAULT_JOB_TIMEOUT = 3600


def ready_mapping(  # noqa: PLR0913
    entity_type: str,
    schema_type: str,
    from_version: int,
    to_version: int,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The stored mapping, refusing to hand one back while anything is undecided.

    ``values`` answers the open questions for a single dataset, so the guided
    per-dataset form can migrate one dataset a mapping cannot cover generically.
    """
    row = SchemaMigration.get(entity_type, schema_type, from_version, to_version)

    if row is None:
        raise tk.ValidationError(
            {"mapping": [tk._("No mapping stored for this version pair")]}
        )

    mapping = row.mapping
    if values:
        mapping = mapping_lib.overlay_values(mapping, values)

    source = expanded_definition(entity_type, schema_type, from_version)
    target = expanded_definition(entity_type, schema_type, to_version)

    problems = mapping_lib.unresolved(
        diff.compare(source, target), mapping
    ) + mapping_lib.manual_fields(mapping)
    if problems:
        raise tk.ValidationError(
            {
                "mapping": [
                    tk._("{}.{}: {}").format(p["group"], p["field_name"], p["reason"])
                    for p in problems
                ]
            }
        )

    return mapping


def refuse_while_running(
    entity_type: str, schema_type: str, from_version: int, to_version: int
) -> None:
    active = MigrationRun.active(entity_type, schema_type, from_version, to_version)

    if active is not None:
        raise tk.ValidationError(
            {
                "run": [
                    tk._("A migration for this version pair is already {}").format(
                        active.status
                    )
                ]
            }
        )


def start(  # noqa: PLR0913 PLR0917
    schema_type: str,
    entity_type: str,
    from_version: int,
    to_version: int,
    mapping: dict[str, Any],
    actor: str,
    dry_run: bool = False,
) -> MigrationRun:
    """Record a pending bulk run over every entity pinned to ``from_version``."""
    return MigrationRun.create(
        entity_type=entity_type,
        schema_type=schema_type,
        from_version=from_version,
        to_version=to_version,
        mapping_used=mapping,
        status=MigrationRun.PENDING,
        dry_run=dry_run,
        total=len(entities_at_version(entity_type, schema_type, from_version)),
        actor=actor,
    )


def enqueue(  # noqa: PLR0913 PLR0917
    schema_type: str,
    entity_type: str,
    from_version: int,
    to_version: int,
    mapping: dict[str, Any],
    actor: str,
    dry_run: bool = False,
) -> MigrationRun:
    """Queue a bulk run for a background worker to pick up."""
    run = start(
        schema_type, entity_type, from_version, to_version, mapping, actor, dry_run
    )

    tk.enqueue_job(
        execute,
        [run.id],
        rq_kwargs={"timeout": tk.config.get(JOB_TIMEOUT_CONFIG, DEFAULT_JOB_TIMEOUT)},
    )

    return run


def execute(run_id: str, progress: Callable[[int], Any] | None = None) -> None:
    """Migrate every dataset still pinned to the run's source version.

    Used both as the job body and, by the CLI, inline.
    """
    run = MigrationRun.get(run_id)

    if run is None or run.status != MigrationRun.PENDING:
        return

    run.status = MigrationRun.RUNNING
    model.Session.commit()

    try:
        migrator = _migrator(run)
    except tk.ObjectNotFound as e:
        run.finish(MigrationRun.FAILED, str(e))
        return

    for entity_id in entities_at_version(
        run.entity_type, run.schema_type, run.from_version
    ):
        model.Session.refresh(run)
        if run.status == MigrationRun.CANCELLED:
            run.finish(MigrationRun.CANCELLED)
            return

        record(run, migrator, entity_id)

        if progress:
            progress(1)

    run.finish(MigrationRun.FINISHED)


def run_single(  # noqa: PLR0913 PLR0917
    schema_type: str,
    entity_type: str,
    from_version: int,
    to_version: int,
    mapping: dict[str, Any],
    actor: str,
    entity_id: str,
    dry_run: bool = False,
) -> MigrationRun:
    """Migrate one entity now, recording it as an already-finished run."""
    migrator = Migrator(
        schema_type, entity_type, from_version, to_version, mapping, actor, dry_run
    )
    result = migrator.run_one(entity_id)

    run = MigrationRun.create(
        entity_type=entity_type,
        schema_type=schema_type,
        from_version=from_version,
        to_version=to_version,
        mapping_used=mapping,
        status=MigrationRun.FINISHED,
        dry_run=dry_run,
        total=1,
        actor=actor,
        finished=_current_datetime(),
    )
    run.count_item(result.status)

    MigrationRunItem.create(
        run_id=run.id,
        entity_id=result.entity_id,
        status=result.status,
        errors=result.errors,
        changes=result.changes,
    )
    model.Session.commit()

    return run


def record(run: MigrationRun, migrator: Migrator, entity_id: str) -> None:
    try:
        result = migrator.run_one(entity_id)
    except Exception:  # noqa: BLE001
        log.exception("migrating %s failed unexpectedly", entity_id)
        model.Session.rollback()
        result = migrator.failure(entity_id, "unexpected error, see the server log")

    MigrationRunItem.create(
        run_id=run.id,
        entity_id=result.entity_id,
        status=result.status,
        errors=result.errors,
        changes=result.changes,
    )
    run.count_item(result.status)
    model.Session.commit()


def _migrator(run: MigrationRun) -> Migrator:
    return Migrator(
        run.schema_type,
        run.entity_type,
        run.from_version,
        run.to_version,
        run.mapping_used,
        run.actor,
        run.dry_run,
    )
