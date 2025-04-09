"""added total duration to the course model

Revision ID: 0baf18b6fc98
Revises: 987480aa8584
Create Date: 2025-04-04 21:45:06.113961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0baf18b6fc98'
down_revision = '987480aa8584'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_duration', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('total_duration')

    # ### end Alembic commands ###
