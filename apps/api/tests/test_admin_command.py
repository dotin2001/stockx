from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models import RefreshToken, User
from app.services import auth as auth_service


API_ROOT = Path(__file__).resolve().parents[1]


def test_admin_promote_module_command(tmp_path) -> None:
    db_path = tmp_path / "admin-command.sqlite"
    database_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with SessionLocal() as session:
        session.add(
            User(
                name="CLI Admin",
                email="cli-admin@example.com",
                password_hash=hash_password("password123"),
            )
        )
        session.commit()

    env = {**os.environ, "DATABASE_URL": database_url, "SECRET_KEY": "test-secret"}
    success = subprocess.run(
        [sys.executable, "-m", "app.admin", "promote", " CLI-ADMIN@example.com "],
        cwd=API_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert success.returncode == 0
    assert "Promoted admin: cli-admin@example.com" in success.stdout
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == "cli-admin@example.com"))
        assert user is not None
        assert user.is_admin is True

    missing = subprocess.run(
        [sys.executable, "-m", "app.admin", "promote", "missing@example.com"],
        cwd=API_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 1
    assert "User not found: missing@example.com" in missing.stderr


def test_admin_promote_supreme_module_command_preserves_auth_data(tmp_path) -> None:
    db_path = tmp_path / "supreme-admin-command.sqlite"
    database_url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with SessionLocal() as session:
        user = User(
            name="Supreme CLI Admin",
            email="supreme-cli-admin@example.com",
            password_hash=hash_password("password123"),
        )
        session.add(user)
        session.flush()
        token, _raw_token = auth_service.create_refresh_token_record(session, user)
        user_id = user.id
        token_id = token.id
        password_hash = user.password_hash
        session.commit()

    env = {**os.environ, "DATABASE_URL": database_url, "SECRET_KEY": "test-secret"}
    success = subprocess.run(
        [sys.executable, "-m", "app.admin", "promote-supreme", " SUPREME-CLI-ADMIN@example.com "],
        cwd=API_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert success.returncode == 0
    assert "Promoted supreme admin: supreme-cli-admin@example.com" in success.stdout
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user is not None
        assert user.is_admin is True
        assert user.is_supreme_admin is True
        assert user.password_hash == password_hash
        assert verify_password("password123", user.password_hash)
        assert session.get(RefreshToken, token_id) is not None

    idempotent = subprocess.run(
        [sys.executable, "-m", "app.admin", "promote-supreme", "supreme-cli-admin@example.com"],
        cwd=API_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert idempotent.returncode == 0
    with SessionLocal() as session:
        user = session.get(User, user_id)
        assert user is not None
        assert user.is_admin is True
        assert user.is_supreme_admin is True
        assert len(session.scalars(select(User).where(User.email == "supreme-cli-admin@example.com")).all()) == 1

    missing = subprocess.run(
        [sys.executable, "-m", "app.admin", "promote-supreme", "missing-supreme@example.com"],
        cwd=API_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 1
    assert "User not found: missing-supreme@example.com" in missing.stderr
