"""Create scheming_schema_activity table.

Revision ID: 9a3e5c7b2d4f
Revises: 4c1f8a6d9e2b
Create Date: 2026-08-13 09:10:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "9a3e5c7b2d4f"
down_revision = "4c1f8a6d9e2b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_schema_activity",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("schema_type", sa.Text, nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("actor", sa.Text, nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("version", sa.Integer, nullable=True),
        sa.Column("created", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_scheming_schema_activity_schema_type_created",
        "scheming_schema_activity",
        ["entity_type", "schema_type", "created"],
    )


def downgrade():
    op.drop_index(
        "ix_scheming_schema_activity_schema_type_created",
        table_name="scheming_schema_activity",
    )
    op.drop_table("scheming_schema_activity")
