"""Create scheming_schema_version table, replacing scheming_schema.

Revision ID: 7b9d2e4f1a8c
Revises: 313463c1e2db
Create Date: 2026-08-13 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "7b9d2e4f1a8c"
down_revision = "313463c1e2db"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_schema_version",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, primary_key=True),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("created", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheming_schema_version_created", "scheming_schema_version", ["created"]
    )

    op.drop_index("ix_scheming_schema_updated", table_name="scheming_schema")
    op.drop_table("scheming_schema")


def downgrade():
    op.create_table(
        "scheming_schema",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, primary_key=True),
        sa.Column("updated", sa.TIMESTAMP(timezone=True)),
        sa.Column("definition", JSONB),
    )
    op.create_index("ix_scheming_schema_updated", "scheming_schema", ["updated"])

    op.drop_index(
        "ix_scheming_schema_version_created", table_name="scheming_schema_version"
    )
    op.drop_table("scheming_schema_version")
