"""Rename scheming_schema_state to scheming_state, entity_type to key.

The table backs a generic named counter (dataset-schema fingerprints and
the preset registry's own counter), not just per-entity_type state, so
both names were misleading.

Revision ID: 313463c1e2db
Revises: c2e8f5a91b3d
Create Date: 2026-08-13 15:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "313463c1e2db"
down_revision = "c2e8f5a91b3d"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("scheming_schema_state", "scheming_state")
    op.alter_column("scheming_state", "entity_type", new_column_name="key")


def downgrade():
    op.alter_column("scheming_state", "key", new_column_name="entity_type")
    op.rename_table("scheming_state", "scheming_schema_state")
