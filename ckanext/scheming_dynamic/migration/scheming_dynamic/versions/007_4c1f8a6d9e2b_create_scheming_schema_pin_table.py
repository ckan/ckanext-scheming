"""Create scheming_schema_pin table.

Revision ID: 4c1f8a6d9e2b
Revises: 7b9d2e4f1a8c
Create Date: 2026-08-13 09:05:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4c1f8a6d9e2b"
down_revision = "7b9d2e4f1a8c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scheming_schema_pin",
        sa.Column("entity_type", sa.Text, primary_key=True),
        sa.Column("entity_id", sa.Text, primary_key=True),
        sa.Column("schema_type", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_type", "schema_type", "version"],
            [
                "scheming_schema_version.entity_type",
                "scheming_schema_version.schema_type",
                "scheming_schema_version.version",
            ],
        ),
    )
    op.create_index(
        "ix_scheming_schema_pin_schema_type_version",
        "scheming_schema_pin",
        ["entity_type", "schema_type", "version"],
    )


def downgrade():
    op.drop_index(
        "ix_scheming_schema_pin_schema_type_version",
        table_name="scheming_schema_pin",
    )
    op.drop_table("scheming_schema_pin")
