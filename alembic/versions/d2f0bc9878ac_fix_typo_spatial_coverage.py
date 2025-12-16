"""empty message

Revision ID: d2f0bc9878ac
Revises: 76f154f02767
Create Date: 2025-09-08 11:26:12.557548

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2f0bc9878ac'
down_revision: Union[str, None] = '76f154f02767'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('Dataset', 'dataset_spatial_covarage_id', new_column_name='dataset_spatial_coverage_id')


def downgrade() -> None:
    op.alter_column('Dataset', 'dataset_spatial_coverage_id', new_column_name='dataset_spatial_covarage_id')
