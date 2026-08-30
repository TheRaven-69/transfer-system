"""Add user credentials and rotating refresh tokens.

Revision ID: 20260830_02
Revises: 20260830_01
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_02"
down_revision: str | None = "20260830_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(50), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET username = 'legacy_' || CAST(id AS VARCHAR),
                email = 'legacy_' || CAST(id AS VARCHAR) || '@invalid.local',
                password_hash = 'disabled'
            """
        )
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(50), nullable=False)
        batch_op.alter_column("email", existing_type=sa.String(320), nullable=False)
        batch_op.alter_column(
            "password_hash", existing_type=sa.String(255), nullable=False
        )
        batch_op.create_unique_constraint("uq_users_username", ["username"])
        batch_op.create_unique_constraint("uq_users_email", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")
        batch_op.drop_constraint("uq_users_username", type_="unique")
        batch_op.drop_column("password_hash")
        batch_op.drop_column("email")
        batch_op.drop_column("username")
