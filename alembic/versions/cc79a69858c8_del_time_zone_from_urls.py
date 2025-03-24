"""del time zone from urls

Revision ID: cc79a69858c8
Revises: 8c06db821dc5
Create Date: 2025-03-22 20:07:05.890573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cc79a69858c8'
down_revision: Union[str, None] = '8c06db821dc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('urls', 'date_of_create',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('urls', 'last_usage',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               type_=sa.TIMESTAMP(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('urls', 'last_usage',
               existing_type=sa.TIMESTAMP(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('urls', 'date_of_create',
               existing_type=sa.TIMESTAMP(),
               type_=postgresql.TIMESTAMP(timezone=True),
               existing_nullable=True)
    # ### end Alembic commands ###
