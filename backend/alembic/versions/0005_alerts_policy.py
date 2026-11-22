"""alertes parent (ASK_ADULT) et version de la politique qui a choisi l'action

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("policy_version", sa.String(32), nullable=True))
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "child_id",
            sa.String(32),
            sa.ForeignKey("children.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.String(32),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("seen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_alerts_child_id", "alerts", ["child_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_child_id", table_name="alerts")
    op.drop_table("alerts")
    op.drop_column("messages", "policy_version")
