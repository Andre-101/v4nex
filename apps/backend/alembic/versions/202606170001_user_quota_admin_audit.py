"""user quota and admin audit targets

Revision ID: 202606170001
Revises: 202605260002
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202606170001"
down_revision: Union[str, None] = "202605260002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("admin_audit_events", "actor_user_id", nullable=True)

    op.add_column(
        "users",
        sa.Column("bridge_limit", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.alter_column("users", "bridge_limit", server_default=None)
    op.alter_column("users", "is_active", server_default=None)

    op.add_column("admin_audit_events", sa.Column("target_user_id", sa.String(), nullable=True))
    op.add_column("admin_audit_events", sa.Column("bridge_id", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_admin_audit_events_target_user_id"),
        "admin_audit_events",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_events_bridge_id"),
        "admin_audit_events",
        ["bridge_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_admin_audit_events_target_user_id_users"),
        "admin_audit_events",
        "users",
        ["target_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("fk_admin_audit_events_bridge_id_bridges"),
        "admin_audit_events",
        "bridges",
        ["bridge_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_admin_audit_events_bridge_id_bridges"),
        "admin_audit_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_admin_audit_events_target_user_id_users"),
        "admin_audit_events",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_admin_audit_events_bridge_id"), table_name="admin_audit_events")
    op.drop_index(op.f("ix_admin_audit_events_target_user_id"), table_name="admin_audit_events")
    op.drop_column("admin_audit_events", "bridge_id")
    op.drop_column("admin_audit_events", "target_user_id")
    op.alter_column("admin_audit_events", "actor_user_id", nullable=False)
    op.drop_column("users", "is_active")
    op.drop_column("users", "bridge_limit")
