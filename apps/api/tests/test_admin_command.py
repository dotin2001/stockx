from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.base import Base
from app.models import User


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
