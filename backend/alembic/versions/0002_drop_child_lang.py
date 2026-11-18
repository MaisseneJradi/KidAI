"""retire la langue du profil enfant (choisie dans les réglages de l'appareil)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("children", "lang")


def downgrade() -> None:
    op.add_column("children", sa.Column("lang", sa.String(5), nullable=False, server_default="fr"))
    op.alter_column("children", "lang", server_default=None)
