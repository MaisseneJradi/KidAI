"""messages : catégorie de risque, latence des contrôles, modèle facultatif (question bloquée)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("input_category", sa.String(128), nullable=True))
    op.add_column("messages", sa.Column("safety_latency_ms", sa.Integer(), nullable=True))
    # Une question bloquée n'appelle pas le LLM : pas de modèle ni de version de prompt.
    op.alter_column("messages", "model_name", existing_type=sa.String(64), nullable=True)
    op.alter_column("messages", "prompt_version", existing_type=sa.String(32), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE messages SET model_name = 'none' WHERE model_name IS NULL")
    op.execute("UPDATE messages SET prompt_version = 'none' WHERE prompt_version IS NULL")
    op.alter_column("messages", "prompt_version", existing_type=sa.String(32), nullable=False)
    op.alter_column("messages", "model_name", existing_type=sa.String(64), nullable=False)
    op.drop_column("messages", "safety_latency_ms")
    op.drop_column("messages", "input_category")
