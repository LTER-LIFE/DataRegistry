"""nullable_spatial_resolution

Revision ID: 251acb193b99
Revises: c5e2b4007cda
Create Date: 2026-03-23 10:09:12.478161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '251acb193b99'
down_revision: Union[str, None] = 'c5e2b4007cda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('Dataset', 'spatial_resolution',
               existing_type=sa.String(length=255),
               nullable=True)
    op.alter_column('DatasetStaging', 'spatial_resolution',
               existing_type=sa.String(length=255),
               nullable=True)


def downgrade() -> None:
    # set Null values to empty string before downgrade
    op.execute(
        "UPDATE \"DatasetStaging\" SET spatial_resolution = '' WHERE spatial_resolution IS NULL"
    )
    op.execute(
        "UPDATE \"Dataset\" SET spatial_resolution = '' WHERE spatial_resolution IS NULL"
    )
    op.alter_column('DatasetStaging', 'spatial_resolution',
               existing_type=sa.String(length=255),
               nullable=False)
    op.alter_column('Dataset', 'spatial_resolution',
               existing_type=sa.String(length=255),
               nullable=False)
