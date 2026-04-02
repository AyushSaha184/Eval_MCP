"""Add password hashes for hosted client authentication."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_client_password_auth"
down_revision = "0002_hosted_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE clients SET password_hash = onboarding_token_hash WHERE password_hash IS NULL")
    op.alter_column("clients", "password_hash", existing_type=sa.String(length=255), nullable=False)


def downgrade() -> None:
    op.drop_column("clients", "password_hash")
