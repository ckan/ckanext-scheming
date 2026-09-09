from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from typing_extensions import Self  # noqa: UP035

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.model.types import make_uuid

from ckanext.scheming_dynamic.model import _current_datetime

VERSION_COLUMNS = (
    "scheming_schema_version.entity_type",
    "scheming_schema_version.schema_type",
    "scheming_schema_version.version",
)


class SchemaMigration(tk.BaseModel):
    """The field mapping between two versions of one schema."""

    __table__ = sa.Table(
        "scheming_schema_migration",
        tk.BaseModel.metadata,
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, primary_key=True),
        sa.Column("from_version", sa.Integer, primary_key=True),
        sa.Column("to_version", sa.Integer, primary_key=True),
        sa.Column("mapping", JSONB, nullable=False),
        sa.Column("author", sa.Text, nullable=False),
        sa.Column(
            "created",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            default=_current_datetime,
        ),
        sa.Column(
            "updated",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            default=_current_datetime,
            onupdate=_current_datetime,
        ),
        sa.ForeignKeyConstraint(
            ["entity_type", "schema_type", "from_version"],
            VERSION_COLUMNS,
            ondelete="CASCADE",
            name="scheming_schema_migration_from_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["entity_type", "schema_type", "to_version"],
            VERSION_COLUMNS,
            ondelete="CASCADE",
            name="scheming_schema_migration_to_fkey",
        ),
    )

    entity_type: Mapped[str]
    schema_type: Mapped[str]
    from_version: Mapped[int]
    to_version: Mapped[int]
    mapping: Mapped[dict[str, Any]]
    author: Mapped[str]
    created: Mapped[datetime]
    updated: Mapped[datetime]

    @classmethod
    def get(
        cls, entity_type: str, schema_type: str, from_version: int, to_version: int
    ) -> Self | None:
        return model.Session.get(
            cls, (entity_type, schema_type, from_version, to_version)
        )

    @classmethod
    def save(  # noqa: PLR0913 PLR0917
        cls,
        entity_type: str,
        schema_type: str,
        from_version: int,
        to_version: int,
        mapping: dict[str, Any],
        author: str,
    ) -> Self:
        row = cls.get(entity_type, schema_type, from_version, to_version)

        if row is None:
            row = cls(
                entity_type=entity_type,
                schema_type=schema_type,
                from_version=from_version,
                to_version=to_version,
                mapping=mapping,
                author=author,
            )
            model.Session.add(row)
        else:
            row.mapping = mapping
            row.author = author

        model.Session.commit()
        return row

    def delete(self) -> None:
        model.Session.delete(self)
        model.Session.commit()

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "schema_type": self.schema_type,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "mapping": self.mapping,
            "author": self.author,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
        }


class MigrationRun(tk.BaseModel):
    """One invocation of a mapping over one or more datasets."""

    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ACTIVE_STATUSES = (PENDING, RUNNING)

    __table__ = sa.Table(
        "scheming_schema_migration_run",
        tk.BaseModel.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("schema_type", sa.Text, nullable=False),
        sa.Column("from_version", sa.Integer, nullable=False),
        sa.Column("to_version", sa.Integer, nullable=False),
        sa.Column("mapping_used", JSONB, nullable=False),
        sa.Column("status", sa.Text, nullable=False, default=PENDING),
        sa.Column("dry_run", sa.Boolean, nullable=False, default=False),
        sa.Column("total", sa.Integer, nullable=False, default=0),
        sa.Column("ok_count", sa.Integer, nullable=False, default=0),
        sa.Column("failed_count", sa.Integer, nullable=False, default=0),
        sa.Column("skipped_count", sa.Integer, nullable=False, default=0),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "started",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            default=_current_datetime,
        ),
        sa.Column("finished", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Index(
            "scheming_schema_migration_run_active",
            "entity_type",
            "schema_type",
            "from_version",
            "to_version",
            unique=True,
            postgresql_where=sa.text(f"status IN ('{PENDING}', '{RUNNING}')"),
        ),
        sa.Index(
            "scheming_schema_migration_run_listing",
            "entity_type",
            "schema_type",
            "started",
        ),
    )

    id: Mapped[str]
    entity_type: Mapped[str]
    schema_type: Mapped[str]
    from_version: Mapped[int]
    to_version: Mapped[int]
    mapping_used: Mapped[dict[str, Any]]
    status: Mapped[str]
    dry_run: Mapped[bool]
    total: Mapped[int]
    ok_count: Mapped[int]
    failed_count: Mapped[int]
    skipped_count: Mapped[int]
    actor: Mapped[str]
    error: Mapped[str | None]
    started: Mapped[datetime]
    finished: Mapped[datetime | None]

    COUNTERS = {
        "ok": "ok_count",
        "failed": "failed_count",
        "skipped": "skipped_count",
    }

    @classmethod
    def get(cls, run_id: str) -> Self | None:
        return model.Session.get(cls, run_id)

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        row = cls(**kwargs)
        model.Session.add(row)
        model.Session.commit()
        return row

    @classmethod
    def active(
        cls, entity_type: str, schema_type: str, from_version: int, to_version: int
    ) -> Self | None:
        return (
            model.Session.query(cls)
            .filter(
                cls.entity_type == entity_type,
                cls.schema_type == schema_type,
                cls.from_version == from_version,
                cls.to_version == to_version,
                cls.status.in_(cls.ACTIVE_STATUSES),
            )
            .first()
        )

    @classmethod
    def search(
        cls,
        entity_type: str,
        schema_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Self]:
        query = model.Session.query(cls).filter(cls.entity_type == entity_type)

        if schema_type:
            query = query.filter(cls.schema_type == schema_type)

        return query.order_by(cls.started.desc()).limit(limit).offset(offset).all()

    def count_item(self, status: str) -> None:
        counter = self.COUNTERS[status]
        setattr(self, counter, getattr(self, counter) + 1)

    def cancel(self) -> None:
        self.finish(self.CANCELLED)

    def finish(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.error = error
        self.finished = _current_datetime()
        model.Session.commit()

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "schema_type": self.schema_type,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "mapping_used": self.mapping_used,
            "status": self.status,
            "dry_run": self.dry_run,
            "total": self.total,
            "ok_count": self.ok_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "actor": self.actor,
            "error": self.error,
            "started": self.started.isoformat(),
            "finished": self.finished.isoformat() if self.finished else None,
        }


class MigrationRunItem(tk.BaseModel):
    """What happened to one dataset during a run."""

    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"

    __table__ = sa.Table(
        "scheming_schema_migration_run_item",
        tk.BaseModel.metadata,
        sa.Column("id", sa.Text, primary_key=True, default=make_uuid),
        sa.Column(
            "run_id",
            sa.Text,
            sa.ForeignKey(
                "scheming_schema_migration_run.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("entity_id", sa.Text, nullable=False, index=True),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("errors", JSONB, nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column(
            "created",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            default=_current_datetime,
        ),
    )

    id: Mapped[str]
    run_id: Mapped[str]
    entity_id: Mapped[str]
    status: Mapped[str]
    errors: Mapped[dict[str, Any] | None]
    changes: Mapped[dict[str, Any] | None]
    created: Mapped[datetime]

    @classmethod
    def get(cls, item_id: str) -> Self | None:
        return model.Session.get(cls, item_id)

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        row = cls(**kwargs)
        model.Session.add(row)
        model.Session.flush()
        return row

    @classmethod
    def for_run(cls, run_id: str, status: str | None = None) -> list[Self]:
        query = model.Session.query(cls).filter(cls.run_id == run_id)

        if status:
            query = query.filter(cls.status == status)

        return query.order_by(cls.created).all()

    @classmethod
    def prune(cls, before: datetime) -> int:
        """Drop the recorded values from old items, keeping their outcome."""
        return (
            model.Session.query(cls)
            .filter(cls.created < before)
            .update({"changes": None}, synchronize_session=False)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "entity_id": self.entity_id,
            "status": self.status,
            "errors": self.errors,
            "changes": self.changes,
            "created": self.created.isoformat(),
        }
