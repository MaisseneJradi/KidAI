"""parents et profils enfants

Revision ID: 0001
Revises:
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("pin_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_parents_email", "parents", ["email"], unique=True)

    op.create_table(
        "children",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "parent_id",
            sa.String(32),
            sa.ForeignKey("parents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(50), nullable=False),
        sa.Column("avatar", sa.String(16), nullable=False),
        # Chiffrés par l'application (Fernet) : stockés en texte opaque.
        sa.Column("birth_date", sa.Text(), nullable=False),
        sa.Column("sex", sa.String(20), nullable=False),
        sa.Column("grade", sa.String(20), nullable=False),
        sa.Column("lang", sa.String(5), nullable=False),
        sa.Column("caution_level", sa.String(20), nullable=False),
        sa.Column("interests", sa.JSON(), nullable=False),
        sa.Column("needs", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_children_parent_id", "children", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_children_parent_id", table_name="children")
    op.drop_table("children")
    op.drop_index("ix_parents_email", table_name="parents")
    op.drop_table("parents")
