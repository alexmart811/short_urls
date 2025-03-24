"""added metadata

Revision ID: 8417cc587a17
Revises: 177c2b181cb5
Create Date: 2025-03-22 03:02:49.878071

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8417cc587a17'
down_revision: Union[str, None] = '177c2b181cb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('urls_user_id_fkey', 'urls', type_='foreignkey')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key('urls_user_id_fkey', 'urls', 'user', ['user_id'], ['id'])
    # ### end Alembic commands ###
