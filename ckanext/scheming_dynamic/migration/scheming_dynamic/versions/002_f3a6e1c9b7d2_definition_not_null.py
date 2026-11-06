"""Make scheming_schema.definition NOT NULL.

Revision ID: f3a6e1c9b7d2
Revises: 8d447c8244e1
Create Date: 2026-07-28 14:08:37.612601

"""

from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "f3a6e1c9b7d2"
down_revision = "8d447c8244e1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "scheming_schema", "definition", existing_type=JSONB, nullable=False
    )


def downgrade():
    op.alter_column("scheming_schema", "definition", existing_type=JSONB, nullable=True)
