from __future__ import annotations

import sqlalchemy as sa

from ckan import model

from ckanext.scheming_dynamic.model import SchemingSchemaPin, SchemingSchemaVersion


def _advisory_key(entity_type: str, schema_type: str) -> str:
    return f"scheming_dynamic:{entity_type}:{schema_type}"


def lock_schema(entity_type: str, schema_type: str) -> None:
    """Take the exclusive per-schema-type lock, for a schema mutation.

    A Postgres transaction-level advisory lock (released on commit/rollback).
    Every ``scheming_schema_*`` write holds this so they run one at a time,
    and it conflicts with the shared lock ``lock_schema_shared`` that pin
    creation takes -- so the check-then-act in ``_lock_or_sync_version``
    (is the head version pinned? -> overwrite in place, else lock a new
    version) can't race a concurrent edit or a concurrent pin.
    """
    model.Session.execute(
        sa.text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": _advisory_key(entity_type, schema_type)},
    )


def lock_schema_shared(entity_type: str, schema_type: str) -> None:
    """Take the shared per-schema-type lock, for pinning an entity.

    Concurrent pin creations for the same schema type don't block each
    other (they only need to exclude an in-flight schema mutation), so this
    is the shared companion to ``lock_schema``.
    """
    model.Session.execute(
        sa.text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:key, 0))"),
        {"key": _advisory_key(entity_type, schema_type)},
    )


def ensure_pinned(entity_type: str, entity_id: str, schema_type: str) -> None:
    """Pin an entity to the schema's current head version.

    Called once, at entity-creation time. A no-op when ``schema_type`` has
    no dynamic (database) schema at all -- e.g. a file-defined-only type.
    """
    if SchemingSchemaPin.get(entity_type, entity_id):
        return

    # fast path: most types have no dynamic schema, so skip the lock entirely
    if SchemingSchemaVersion.head_version(entity_type, schema_type) == 0:
        return

    lock_schema_shared(entity_type, schema_type)

    # authoritative read, under the lock: a concurrent create/delete of the
    # schema can't now change head_version until this transaction commits
    head_version = SchemingSchemaVersion.head_version(entity_type, schema_type)
    if head_version == 0:
        return

    SchemingSchemaPin.pin(entity_type, entity_id, schema_type, head_version)


def remove_pin(entity_type: str, entity_id: str) -> None:
    """Drop an entity's schema pin.

    The counterpart to ``ensure_pinned``, called from the entity-delete
    hook so a pin never outlives the entity it belongs to. Runs inside the
    delete action's transaction -- no commit of its own. A no-op when the
    entity was never pinned."""
    model.Session.query(SchemingSchemaPin).filter(
        SchemingSchemaPin.entity_type == entity_type,
        SchemingSchemaPin.entity_id == entity_id,
    ).delete()
