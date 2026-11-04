"""harden auth persistence and add administrative audit

Revision ID: 202611040001
Revises: 202610300001
Create Date: 2026-11-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202611040001"
down_revision: Union[str, None] = "202610300001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_refresh_families() -> None:
    # Legacy links that cross users or point to themselves cannot describe a
    # safe session family. Detach them before deriving connected components.
    op.execute(
        """
        UPDATE refresh_tokens AS current
        SET replaced_by_token_id = NULL
        FROM refresh_tokens AS replacement
        WHERE current.replaced_by_token_id = replacement.id
          AND (current.user_id <> replacement.user_id OR current.id = replacement.id)
        """
    )
    # UNION (rather than UNION ALL) makes same-user cycles finite. Each token
    # receives a stable UUID derived from the lexicographically smallest member
    # of its undirected replacement component; independent tokens stay apart.
    op.execute(
        """
        WITH RECURSIVE connected(start_id, member_id, user_id) AS (
            SELECT id, id, user_id FROM refresh_tokens
            UNION
            SELECT connected.start_id,
                   CASE
                       WHEN candidate.id = connected.member_id
                           THEN candidate.replaced_by_token_id
                       ELSE candidate.id
                   END,
                   connected.user_id
            FROM connected
            JOIN refresh_tokens AS candidate
              ON candidate.user_id = connected.user_id
             AND (
                 candidate.id = connected.member_id
                 OR candidate.replaced_by_token_id = connected.member_id
             )
            WHERE CASE
                    WHEN candidate.id = connected.member_id
                        THEN candidate.replaced_by_token_id
                    ELSE candidate.id
                  END IS NOT NULL
        ), component_roots AS (
            SELECT member_id, min(start_id::text) AS root_id
            FROM connected
            GROUP BY member_id
        )
        UPDATE refresh_tokens AS token
        SET family_id = (
            substr(md5('stockx-refresh-family:' || roots.root_id), 1, 8) || '-' ||
            substr(md5('stockx-refresh-family:' || roots.root_id), 9, 4) || '-' ||
            '5' || substr(md5('stockx-refresh-family:' || roots.root_id), 14, 3) || '-' ||
            'a' || substr(md5('stockx-refresh-family:' || roots.root_id), 18, 3) || '-' ||
            substr(md5('stockx-refresh-family:' || roots.root_id), 21, 12)
        )::uuid
        FROM component_roots AS roots
        WHERE roots.member_id = token.id
        """
    )
    missing = op.get_bind().execute(
        sa.text("SELECT count(*) FROM refresh_tokens WHERE family_id IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError("refresh-token family backfill did not classify every legacy row")


def upgrade() -> None:
    op.add_column("users", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refresh_tokens", sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True))
    _backfill_refresh_families()
    op.alter_column("refresh_tokens", "family_id", nullable=False)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], unique=False)
    op.create_index(
        "ix_refresh_tokens_family_active",
        "refresh_tokens",
        ["family_id", "revoked_at"],
        unique=False,
    )

    op.create_table(
        "account_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('email_verification', 'password_reset')",
            name=op.f("ck_account_challenges_purpose_known"),
        ),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_account_challenges_expires_after_creation")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_account_challenges_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_account_challenges")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_account_challenges_token_hash")),
    )
    op.create_index(op.f("ix_account_challenges_user_id"), "account_challenges", ["user_id"], unique=False)
    op.create_index(
        "ix_account_challenges_user_purpose_created",
        "account_challenges",
        ["user_id", "purpose", "created_at"],
        unique=False,
    )

    op.create_table(
        "administrative_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("facts", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("btrim(action) <> ''", name=op.f("ck_administrative_audits_action_not_blank")),
        sa.CheckConstraint("btrim(target_type) <> ''", name=op.f("ck_administrative_audits_target_type_not_blank")),
        sa.CheckConstraint("btrim(request_id) <> ''", name=op.f("ck_administrative_audits_request_id_not_blank")),
        sa.CheckConstraint(
            "octet_length(facts::text) <= 16384",
            name=op.f("ck_administrative_audits_facts_bounded"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_administrative_audits_actor_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_administrative_audits")),
    )
    op.create_index("ix_administrative_audits_created_id", "administrative_audits", ["created_at", "id"])
    op.create_index("ix_administrative_audits_actor_created", "administrative_audits", ["actor_user_id", "created_at"])
    op.create_index("ix_administrative_audits_action_created", "administrative_audits", ["action", "created_at"])
    op.create_index(
        "ix_administrative_audits_target_created",
        "administrative_audits",
        ["target_type", "target_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_administrative_audits_target_created", table_name="administrative_audits")
    op.drop_index("ix_administrative_audits_action_created", table_name="administrative_audits")
    op.drop_index("ix_administrative_audits_actor_created", table_name="administrative_audits")
    op.drop_index("ix_administrative_audits_created_id", table_name="administrative_audits")
    op.drop_table("administrative_audits")
    op.drop_index("ix_account_challenges_user_purpose_created", table_name="account_challenges")
    op.drop_index(op.f("ix_account_challenges_user_id"), table_name="account_challenges")
    op.drop_table("account_challenges")
    op.drop_index("ix_refresh_tokens_family_active", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
    op.drop_column("users", "verified_at")
