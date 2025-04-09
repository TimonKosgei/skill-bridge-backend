"""completed_date and is_completed to enrollment table

Revision ID: ee1f467dcbc6
Revises: 1021e89a5d02
Create Date: 2025-04-04 21:27:56.514781

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee1f467dcbc6'
down_revision = '1021e89a5d02'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completed_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_completed', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_column('is_completed')
        batch_op.drop_column('completed_date')

    # ### end Alembic commands ###
