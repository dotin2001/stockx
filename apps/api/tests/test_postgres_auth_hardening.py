from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi import Response
from sqlalchemy import delete, select, text
from sqlalchemy.orm import sessionmaker

from app.api.errors import APIError
from app.models import RefreshToken, User
from app.services import auth
from tests.postgres_support import create_postgres_test_engine, require_postgres_url


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "202610300001"


def test_refresh_family_migration_backfills_chains_and_detaches_malformed_links(monkeypatch) -> None:
    url = require_postgres_url()
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_postgres_test_engine()
    suffix = uuid4().hex
    first_user, second_user = uuid4(), uuid4()
    independent, chain_first, chain_second, malformed, self_linked = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    command.downgrade(config, PREVIOUS_REVISION)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, name, email, password_hash) VALUES "
                    "(:first, 'First', :first_email, 'unused'), "
                    "(:second, 'Second', :second_email, 'unused')"
                ),
                {
                    "first": first_user,
                    "second": second_user,
                    "first_email": f"family-first-{suffix}@example.test",
                    "second_email": f"family-second-{suffix}@example.test",
                },
            )
            for token_id, user_id, token_hash in (
                (independent, first_user, f"independent-{suffix}"),
                (chain_second, first_user, f"chain-second-{suffix}"),
                (malformed, second_user, f"malformed-{suffix}"),
                (self_linked, first_user, f"self-linked-{suffix}"),
            ):
                connection.execute(
                    text(
                        "INSERT INTO refresh_tokens "
                        "(id, user_id, token_hash, expires_at) "
                        "VALUES (:id, :user_id, :token_hash, now() + interval '1 day')"
                    ),
                    {"id": token_id, "user_id": user_id, "token_hash": token_hash},
                )
            connection.execute(
                text(
                    "INSERT INTO refresh_tokens "
                    "(id, user_id, token_hash, expires_at, replaced_by_token_id) "
                    "VALUES (:id, :user_id, :token_hash, now() + interval '1 day', :replacement)"
                ),
                {
                    "id": chain_first,
                    "user_id": first_user,
                    "token_hash": f"chain-first-{suffix}",
                    "replacement": chain_second,
                },
            )
            connection.execute(
                text("UPDATE refresh_tokens SET replaced_by_token_id = :other WHERE id = :id"),
                {"id": malformed, "other": independent},
            )
            connection.execute(
                text("UPDATE refresh_tokens SET replaced_by_token_id = :id WHERE id = :id"),
                {"id": self_linked},
            )

        command.upgrade(config, "head")
        with engine.connect() as connection:
            rows = {
                row.id: row
                for row in connection.execute(
                    text(
                        "SELECT id, family_id, replaced_by_token_id FROM refresh_tokens "
                        "WHERE id IN (:independent, :chain_first, :chain_second, :malformed, :self_linked)"
                    ),
                    {
                        "independent": independent,
                        "chain_first": chain_first,
                        "chain_second": chain_second,
                        "malformed": malformed,
                        "self_linked": self_linked,
                    },
                ).mappings()
            }
        assert rows[chain_first].family_id == rows[chain_second].family_id
        assert rows[independent].family_id != rows[chain_first].family_id
        assert rows[malformed].family_id != rows[independent].family_id
        assert rows[malformed].replaced_by_token_id is None
        assert rows[self_linked].replaced_by_token_id is None

        first_assignment = {token_id: row.family_id for token_id, row in rows.items()}
        command.downgrade(config, PREVIOUS_REVISION)
        command.upgrade(config, "head")
        with engine.connect() as connection:
            repeated_assignment = dict(
                connection.execute(
                    text(
                        "SELECT id, family_id FROM refresh_tokens "
                        "WHERE id IN (:independent, :chain_first, :chain_second, :malformed, :self_linked)"
                    ),
                    {
                        "independent": independent,
                        "chain_first": chain_first,
                        "chain_second": chain_second,
                        "malformed": malformed,
                        "self_linked": self_linked,
                    },
                ).all()
            )
        assert repeated_assignment == first_assignment
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM users WHERE email LIKE :pattern"),
                {"pattern": f"%{suffix}%"},
            )
        engine.dispose()


def test_two_concurrent_refreshes_cannot_both_issue_a_replacement() -> None:
    engine = create_postgres_test_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(name="Refresh Race", email=f"refresh-race-{suffix}@example.test", password_hash="unused")
        db.add(user)
        db.flush()
        original, raw_token = auth.create_refresh_token_record(db, user)
        family_id = original.family_id
        user_id = user.id
        db.commit()

    barrier = Barrier(2, timeout=10)

    def rotate() -> str:
        with SessionLocal() as db:
            barrier.wait()
            try:
                auth.rotate_refresh_token(db, Response(), raw_token)
                db.commit()
                return "success"
            except APIError as exc:
                db.rollback()
                return exc.code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = [future.result(timeout=20) for future in (executor.submit(rotate), executor.submit(rotate))]
        assert outcomes.count("success") == 1
        assert outcomes.count("invalid_refresh_token") == 1
        with SessionLocal() as db:
            family = list(db.scalars(select(RefreshToken).where(RefreshToken.family_id == family_id)).all())
            assert len(family) == 2
            assert all(token.revoked_at is not None for token in family)
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
        engine.dispose()
