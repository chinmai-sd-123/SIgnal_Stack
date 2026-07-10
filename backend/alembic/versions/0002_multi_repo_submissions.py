"""Add repo_urls to invite_submissions for multi-repo proof of work.

Revision ID: 0002_multi_repo_submissions
Revises: 0001_baseline_schema
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_multi_repo_submissions"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("invite_submissions")}
    if "repo_urls" not in columns:
        op.add_column("invite_submissions", sa.Column("repo_urls", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("invite_submissions", "repo_urls")
