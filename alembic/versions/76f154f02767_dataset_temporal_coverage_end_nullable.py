"""Dataset.temporal_coverage_end nullable

Revision ID: 76f154f02767
Revises: 00adc47bf122
Create Date: 2025-03-18 12:10:02.552692

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '76f154f02767'
down_revision: Union[str, None] = '00adc47bf122'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Alter column temporal_coverage_end on Dataset to make it nullable
    """
    op.alter_column('Dataset', 'temporal_coverage_end', existing_type=sa.TIMESTAMP(),
                        nullable=True)


def downgrade() -> None:
    """
    Alter column temporal_coverage_end on Dataset to make it not nullable again,
    the database will then be at revision 00adc47bf122
    """
    op.alter_column('Dataset', 'temporal_coverage_end', existing_type=sa.TIMESTAMP(),
                    nullable=False)