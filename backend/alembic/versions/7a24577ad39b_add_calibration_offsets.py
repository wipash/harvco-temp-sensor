"""Add calibration offsets

Revision ID: 7a24577ad39b
Revises: 9c17177c3600
Create Date: 2024-12-27 21:47:55.695221

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a24577ad39b'
down_revision: Union[str, None] = '9c17177c3600'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('devices', sa.Column('temperature_offset', sa.Float(), nullable=True))
    op.add_column('devices', sa.Column('humidity_offset', sa.Float(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('devices', 'humidity_offset')
    op.drop_column('devices', 'temperature_offset')
    # ### end Alembic commands ###