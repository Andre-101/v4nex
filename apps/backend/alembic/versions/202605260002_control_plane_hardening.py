"""control plane hardening

Revision ID: 202605260002
Revises: 202605260001
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605260002"
down_revision: Union[str, None] = "202605260001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=32), server_default="USER", nullable=False),
    )
    op.alter_column("users", "role", server_default=None)

    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("actor_user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_events_actor_user_id"),
        "admin_audit_events",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_admin_audit_events_actor_user_id"),
        table_name="admin_audit_events",
    )
    op.drop_table("admin_audit_events")
    op.drop_column("users", "role")
