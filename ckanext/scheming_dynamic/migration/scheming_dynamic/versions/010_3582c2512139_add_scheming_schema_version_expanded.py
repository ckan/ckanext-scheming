"""Add scheming_schema_version.expanded.

Snapshots the preset-expanded form of a version's definition at lock time,
so a preset edited later can't change what an already-pinned version
validates against or renders as. Nullable and left unbackfilled: rows
locked before this column existed fall back to expanding their
``definition`` live, exactly as every row did before this migration.

Revision ID: 3582c2512139
Revises: 5e7a1c3b8d64
Create Date: 2026-09-09 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "3582c2512139"
down_revision = "5e7a1c3b8d64"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "scheming_schema_version",
        sa.Column("expanded", JSONB, nullable=True),
    )


def downgrade():
    op.drop_column("scheming_schema_version", "expanded")
