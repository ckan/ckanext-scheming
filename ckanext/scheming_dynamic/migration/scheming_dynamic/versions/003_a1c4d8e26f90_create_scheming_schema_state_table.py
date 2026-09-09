"""Create scheming_schema_state table.

Revision ID: a1c4d8e26f90
Revises: f3a6e1c9b7d2
Create Date: 2026-07-28 16:17:53.352042

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c4d8e26f90"
down_revision = "f3a6e1c9b7d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_schema_state",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("scheming_schema_state")
