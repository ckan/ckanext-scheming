"""Create scheming_preset table.

Revision ID: c2e8f5a91b3d
Revises: a1c4d8e26f90
Create Date: 2026-08-12 10:30:21.102911

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "c2e8f5a91b3d"
down_revision = "a1c4d8e26f90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_preset",
        sa.Column("preset_name", sa.Text, primary_key=True),
        sa.Column("updated", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("values", JSONB, nullable=False),
    )
    op.create_index("ix_scheming_preset_updated", "scheming_preset", ["updated"])


def downgrade():
    op.drop_index("ix_scheming_preset_updated", table_name="scheming_preset")
    op.drop_table("scheming_preset")
