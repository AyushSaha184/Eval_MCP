"""Add clients and db-backed API keys for hosted onboarding."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_hosted_onboarding"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("onboarding_token_hash", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.UniqueConstraint("account_identifier", name=op.f("uq_clients_account_identifier")),
    )
    op.create_index(op.f("ix_clients_account_identifier"), "clients", ["account_identifier"], unique=False)

    op.add_column("projects", sa.Column("owner_client_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_projects_owner_client_id"), "projects", ["owner_client_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_projects_owner_client_id_clients"),
        "projects",
        "clients",
        ["owner_client_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "client_api_keys",
        sa.Column("client_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_client_api_keys_client_id_clients"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_client_api_keys_project_id_projects"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_api_keys")),
    )
    op.create_index(op.f("ix_client_api_keys_client_id"), "client_api_keys", ["client_id"], unique=False)
    op.create_index(op.f("ix_client_api_keys_is_active"), "client_api_keys", ["is_active"], unique=False)
    op.create_index(op.f("ix_client_api_keys_key_prefix"), "client_api_keys", ["key_prefix"], unique=False)
    op.create_index(op.f("ix_client_api_keys_project_id"), "client_api_keys", ["project_id"], unique=False)
    op.create_index(
        "ix_client_api_keys_client_project_active",
        "client_api_keys",
        ["client_id", "project_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_client_api_keys_client_project_active", table_name="client_api_keys")
    op.drop_index(op.f("ix_client_api_keys_project_id"), table_name="client_api_keys")
    op.drop_index(op.f("ix_client_api_keys_key_prefix"), table_name="client_api_keys")
    op.drop_index(op.f("ix_client_api_keys_is_active"), table_name="client_api_keys")
    op.drop_index(op.f("ix_client_api_keys_client_id"), table_name="client_api_keys")
    op.drop_table("client_api_keys")

    op.drop_constraint(op.f("fk_projects_owner_client_id_clients"), "projects", type_="foreignkey")
    op.drop_index(op.f("ix_projects_owner_client_id"), table_name="projects")
    op.drop_column("projects", "owner_client_id")

    op.drop_index(op.f("ix_clients_account_identifier"), table_name="clients")
    op.drop_table("clients")
