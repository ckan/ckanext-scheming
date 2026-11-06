"""Create schema migration tables.

Revision ID: 5e7a1c3b8d64
Revises: 9a3e5c7b2d4f
Create Date: 2026-08-20 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "5e7a1c3b8d64"
down_revision = "9a3e5c7b2d4f"
branch_labels = None
depends_on = None

VERSION_COLUMNS = [
    "scheming_schema_version.entity_type",
    "scheming_schema_version.schema_type",
    "scheming_schema_version.version",
]


def upgrade():
    op.create_table(
        "scheming_schema_migration",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, primary_key=True),
        sa.Column("from_version", sa.Integer, primary_key=True),
        sa.Column("to_version", sa.Integer, primary_key=True),
        sa.Column("mapping", JSONB, nullable=False),
        sa.Column("author", sa.Text, nullable=False),
        sa.Column("created", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated", sa.TIMESTAMP(timezone=True), nullable=False),
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

    op.create_table(
        "scheming_schema_migration_run",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("schema_type", sa.Text, nullable=False),
        sa.Column("from_version", sa.Integer, nullable=False),
        sa.Column("to_version", sa.Integer, nullable=False),
        sa.Column("mapping_used", JSONB, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("dry_run", sa.Boolean, nullable=False),
        sa.Column("total", sa.Integer, nullable=False),
        sa.Column("ok_count", sa.Integer, nullable=False),
        sa.Column("failed_count", sa.Integer, nullable=False),
        sa.Column("skipped_count", sa.Integer, nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "scheming_schema_migration_run_active",
        "scheming_schema_migration_run",
        ["entity_type", "schema_type", "from_version", "to_version"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )
    op.create_index(
        "scheming_schema_migration_run_listing",
        "scheming_schema_migration_run",
        ["entity_type", "schema_type", "started"],
    )

    op.create_table(
        "scheming_schema_migration_run_item",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "run_id",
            sa.Text,
            sa.ForeignKey("scheming_schema_migration_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("errors", JSONB, nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("created", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheming_schema_migration_run_item_run_id",
        "scheming_schema_migration_run_item",
        ["run_id"],
    )
    op.create_index(
        "ix_scheming_schema_migration_run_item_entity_id",
        "scheming_schema_migration_run_item",
        ["entity_id"],
    )


def downgrade():
    op.drop_table("scheming_schema_migration_run_item")
    op.drop_table("scheming_schema_migration_run")
    op.drop_table("scheming_schema_migration")
