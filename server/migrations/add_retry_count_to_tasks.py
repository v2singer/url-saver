"""add retry_count to tasks

Revision ID: add_retry_count
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_retry_count'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 添加 retry_count 列
    op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    
    # 添加 current_stage 列
    op.add_column('tasks', sa.Column('current_stage', sa.String(50), nullable=False, server_default='init'))

def downgrade():
    # 删除 retry_count 列
    op.drop_column('tasks', 'retry_count')
    
    # 删除 current_stage 列
    op.drop_column('tasks', 'current_stage') 