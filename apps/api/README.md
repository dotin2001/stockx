# StockX API Database Foundation

This workspace contains the first FastAPI backend database foundation for the marketplace.

## Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Start PostgreSQL from the repository root:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

## Migrations

```bash
cd apps/api
alembic upgrade head
alembic downgrade base
```

## Seed Data

```bash
cd apps/api
python -m app.db.seed
```

The seed command is idempotent by category and product slug.

## Verification

```bash
cd apps/api
pytest
alembic upgrade head
python -m app.db.seed
python -m app.db.seed
alembic downgrade base
```

