"""Create scheming_schema table.

Revision ID: 8d447c8244e1
Revises:
Create Date: 2026-07-23 17:31:17.776601

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "8d447c8244e1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_schema",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, primary_key=True),
        sa.Column("updated", sa.TIMESTAMP(timezone=True)),
        sa.Column("definition", JSONB),
    )
    op.create_index("ix_scheming_schema_updated", "scheming_schema", ["updated"])


def downgrade():
    op.drop_index("ix_scheming_schema_updated", table_name="scheming_schema")
    op.drop_table("scheming_schema")
