"""initial schema

Revision ID: 202605260001
Revises:
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605260001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "bridges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("subdomain", sa.String(length=40), nullable=False),
        sa.Column("public_url", sa.String(length=255), nullable=False),
        sa.Column("target_ipv6", sa.String(length=64), nullable=False),
        sa.Column("target_port", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_tcp_validation_at", sa.DateTime(), nullable=True),
        sa.Column("last_tcp_validation_result", sa.String(length=32), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat_result", sa.String(length=32), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bridges_subdomain"), "bridges", ["subdomain"], unique=True)
    op.create_index(op.f("ix_bridges_user_id"), "bridges", ["user_id"], unique=False)

    op.create_table(
        "bridge_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("bridge_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bridge_id"], ["bridges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bridge_events_bridge_id"), "bridge_events", ["bridge_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bridge_events_bridge_id"), table_name="bridge_events")
    op.drop_table("bridge_events")
    op.drop_index(op.f("ix_bridges_user_id"), table_name="bridges")
    op.drop_index(op.f("ix_bridges_subdomain"), table_name="bridges")
    op.drop_table("bridges")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
