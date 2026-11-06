# StockX API

This workspace contains the FastAPI backend for the store-owned selling site. It exposes versioned API routes, email/password auth, public catalog/search endpoints, admin product management, protected customer cart/watchlist/message actions, admin-managed listings used as store inventory, and the PostgreSQL database foundation.

## Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install uv
uv sync --extra dev --frozen
cp .env.example .env
```

Start PostgreSQL from the repository root:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

Important environment variables:

```text
DATABASE_URL=postgresql+psycopg://stockx:stockx@localhost:5432/stockx
SECRET_KEY=change-me-in-local-env
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
REFRESH_COOKIE_NAME=stockx_refresh
REFRESH_COOKIE_SECURE=false
REFRESH_COOKIE_SAMESITE=lax
CORS_ORIGINS=http://localhost:3000
CHECKOUT_MODE=disabled
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
FRONTEND_BASE_URL=http://localhost:3000
STRIPE_EXPECTED_LIVEMODE=false
STRIPE_RESERVATION_MINUTES=30
STRIPE_USE_FAKE_PROVIDER=false
```

`DATABASE_URL` is consumed by the FastAPI app, Alembic, and seed command. The
`POSTGRES_*` variables in `.env.example` are for Docker Compose's PostgreSQL
container and are intentionally ignored by the API settings loader.

`CHECKOUT_MODE` accepts `disabled`, `manual`, or `stripe` and defaults to
`disabled`. Use `manual` only for local development when you explicitly want
confirmation to create an unpaid order and consume inventory; no provider is
contacted in that mode. Stripe mode requires the secret key, endpoint signing
secret, frontend origin, test/live expectation, and the fixed 30-minute
reservation duration. Test (`sk_test_...`) and live (`sk_live_...`) keys must
never be mixed. The fake provider switch is restricted to a local test-mode
origin and exists only for deterministic smoke testing.

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

The catalog seed is idempotent by category and product slug and creates five
configured products in each of Sneakers, Streetwear, and Collectibles. It does
not create a user or inventory owner.

After registering and promoting an existing admin account, seed one active
quantity-10 inventory listing for every configured product:

```bash
python -m app.admin promote admin@example.com
python -m app.db.seed --inventory-owner-email admin@example.com
```

Inventory seeding uses deterministic `SEED-...` purchase-option SKUs. Running
the command again for the same admin does not create duplicates, but it resets
the managed demo listings to their configured USD price, active status, and
quantity. Unrelated administrator-created variants and listings are preserved.

## API Routes

Health:

```text
GET    /health  process liveness; never probes PostgreSQL
GET    /ready   startup configuration and bounded PostgreSQL readiness
```

Auth:

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
POST   /api/v1/auth/logout-all
POST   /api/v1/auth/verification/request
POST   /api/v1/auth/verification/confirm
POST   /api/v1/auth/password-reset/request
POST   /api/v1/auth/password-reset/confirm
```

Catalog:

```text
GET    /api/v1/categories
GET    /api/v1/products
GET    /api/v1/categories/{slug}/products
GET    /api/v1/products/{slug}
GET    /api/v1/search?q=...
```

Protected customer actions:

```text
GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{id}
GET    /api/v1/cart
POST   /api/v1/cart/items
PATCH  /api/v1/cart/items/{id}
DELETE /api/v1/cart/items/{id}
GET    /api/v1/messages
POST   /api/v1/messages
GET    /api/v1/messages/{id}
GET    /api/v1/checkout/summary
POST   /api/v1/checkout/sessions
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{id}
GET    /api/v1/orders/{id}/payment-session
POST   /api/v1/orders/{id}/cancel-payment
POST   /api/v1/payments/stripe/webhook
```

`POST /api/v1/orders` requires an `Idempotency-Key` header. The request body
contains the server-issued checkout token plus recipient/contact/address data;
product lines and totals are always recalculated from the current account cart.
Orders created in manual mode are `confirmed` and `unpaid`.

`POST /checkout/sessions` uses the same body and header, but creates a pending
30-minute inventory reservation and returns an owner-visible Stripe-hosted URL.
The success URL only means the browser returned; verified webhook state is the
sole authority for paid confirmation. The cancel URL likewise only returns to
order detail. Customers must use `cancel-payment` to expire an open provider
session and release inventory explicitly.

## Stripe Checkout Operations

Create separate Stripe webhook destinations and secrets for CLI development,
sandbox/staging, and production. Register an HTTPS production endpoint at:

```text
POST https://your-api.example.com/api/v1/payments/stripe/webhook
```

Subscribe only to these Checkout event types:

```text
checkout.session.completed
checkout.session.async_payment_succeeded
checkout.session.async_payment_failed
checkout.session.expired
```

In Stripe Dashboard payment-method settings, initially enable only instant test
methods such as cards and compatible wallets. Shipping rates, automatic tax,
discounts, saved methods, subscriptions, Connect, refunds, disputes,
fulfillment, and notification email are intentionally deferred.

For local Stripe sandbox forwarding, start the API with a test key and use the
endpoint secret printed by this Stripe CLI process (it is distinct from a
Dashboard destination secret):

```bash
stripe login
stripe listen \
  --events checkout.session.completed,checkout.session.async_payment_succeeded,checkout.session.async_payment_failed,checkout.session.expired \
  --forward-to http://127.0.0.1:8000/api/v1/payments/stripe/webhook
```

Set `STRIPE_WEBHOOK_SECRET=whsec_...` to the printed value, then restart the
API. Never expose either Stripe secret to `NEXT_PUBLIC_*` variables or browser
logs.

Schedule reconciliation at least every five minutes so interrupted session
creation and locally overdue reservations are recovered:

```bash
stockx-api-reconcile-payments --stale-minutes 5 --limit 100
```

To retry one safely stored anomalous event from Stripe's current Checkout
Session state, use the event ID. This is an operator command, not a public API:

```bash
stockx-api-reconcile-payments --event-id evt_123
```

Guests can browse public catalog data and add active sellable items to a guest
cart. Watchlist and message-admin actions require an authenticated customer.

Normal admin store management:

```text
GET    /api/v1/listings
POST   /api/v1/listings
POST   /api/v1/listings/{id}/cancel
GET    /api/v1/admin/listings
POST   /api/v1/admin/listings/{id}/cancel
POST   /api/v1/admin/listings/{id}/inventory/quantity
PATCH  /api/v1/admin/listings/{id}/inventory/status
GET    /api/v1/admin/messages
GET    /api/v1/admin/messages/{id}
POST   /api/v1/admin/messages/{id}/read
GET    /api/v1/admin/orders
GET    /api/v1/admin/orders/{id}
GET    /api/v1/admin/products
POST   /api/v1/admin/products
PATCH  /api/v1/admin/products/{id}
POST   /api/v1/admin/products/{id}/archive
POST   /api/v1/admin/products/{id}/restore
POST   /api/v1/admin/products/{id}/variants
PATCH  /api/v1/admin/product-variants/{id}
DELETE /api/v1/admin/product-variants/{id}
```

Supreme-admin user management:

```text
GET    /api/v1/admin/users
POST   /api/v1/admin/users/promote
POST   /api/v1/admin/users/{id}/promote
POST   /api/v1/admin/users/{id}/demote
GET    /api/v1/admin/audits
```

`GET /api/v1/admin/products` returns catalog products with inventory summaries
and listing-level inventory items for admin product management. Normal admins
can read these summaries and manage catalog product fields, archive/restore
state, and variants. Listing inventory has durable `available_quantity`; public
cart flows only accept active listings with quantity greater than zero and
reject cart quantities above availability. Quantity adjustments and inventory
status changes under `/api/v1/admin/listings/{id}/inventory/*` require a
supreme admin.

Both normal and supreme admins can review orders through the read-only admin
order endpoints. `GET /api/v1/admin/orders` accepts optional `search`, `status`,
`payment_status`, `limit` (1–100), and `offset` parameters. Search matches an
order number or immutable customer-email snapshot case-insensitively. Supported
order statuses are `pending_payment`, `confirmed`, and `cancelled`; supported
payment statuses are `unpaid`, `paid`, `failed`, and `refunded`.

List responses contain compact customer, total, item-count, lifecycle, and
latest-payment-attempt summaries. Detail responses contain immutable shipping,
item, money, and safe payment-attempt snapshots. Provider URLs and identifiers,
webhook payloads, credentials, request hashes, and idempotency values are never
returned. These endpoints do not refund, fulfill, ship, cancel, resume, or
otherwise mutate orders.

Protected routes require an access token:

```text
Authorization: Bearer <access_token>
```

Refresh tokens are stored in the `stockx_refresh` HTTP-only cookie by default and are rotated on refresh.

Refresh rotation is serialized in PostgreSQL and every session has a family.
Reusing an already-replaced token revokes its active family; ordinary logout or
expiry does not revoke unrelated families. Verification and password-reset
tokens are single-use, expiring, and stored only as SHA-256 digests.

## Production configuration

Copy `.env.production.example` and supply secrets through the deployment secret
store. `APP_ENVIRONMENT=production` rejects weak signing secrets, insecure or
non-HTTP-only refresh cookies, wildcard/local/non-HTTPS CORS origins, a non-
PostgreSQL database, in-process rate limiting, capture delivery, mixed Stripe
test/live settings, and the fake provider. Validation errors name settings but
do not include their secret values.

Production authentication limiting uses the Redis adapter and privacy-preserving
HMAC keys. Configure `TRUSTED_PROXY_ADDRESSES` only with immediate proxy IPs;
otherwise forwarded client headers are ignored. Sensitive delivery endpoints
fail closed when the shared limiter is unavailable. The vendor-neutral HTTPS
delivery webhook receives verification/reset actions. The optional error-
reporter webhook receives only request ID, route template, method, and exception
type and is bounded by `ERROR_REPORTER_TIMEOUT_SECONDS`.

Every response includes `X-Request-ID`. A caller ID must be 1–64 ASCII letters,
digits, dot, underscore, or hyphen; invalid values are replaced. Structured logs
use route templates and allowlisted fields and never include request bodies,
cookies, credentials, action tokens, Stripe secrets, or webhook payloads.

Configure the process liveness probe as `GET /health` and the dependency
readiness probe as `GET /ready`. Liveness intentionally stays successful during
a PostgreSQL outage; readiness executes a bounded `SELECT 1` using
`DATABASE_CONNECT_TIMEOUT_SECONDS` and returns the stable
`service_not_ready` code with HTTP 503 when PostgreSQL is unavailable. Do not
use readiness failures to restart an otherwise-live process.

Forward the `stockx.events` logger as one JSON object per record. Preserve the
`X-Request-ID` response header at gateways and load balancers so callers can
correlate sanitized API errors with `request_completed` and
`application_error` events. `ERROR_REPORTER_BACKEND=disabled` is the safe
default. To enable the isolated adapter, select `webhook`, provide an absolute
HTTPS `ERROR_REPORTER_WEBHOOK_URL`, and keep
`ERROR_REPORTER_TIMEOUT_SECONDS` at or below 2 seconds. Reporter rejection or
timeout produces `error_reporter_failed` and never replaces the API response.

### Payment and webhook alerts

The following event/category pairs are the stable operator contract:

| Event | Categories | Recommended action |
| --- | --- | --- |
| `payment_attempt_failed` | `provider_creation_failed`, `async_payment_failed` | Alert on any sustained increase; reconcile the attempt and provider state. |
| `payment_attempt_failed` | `session_expired`, `customer_cancelled` | Track as workflow outcomes; alert only when expiry volume or rate is abnormal. |
| `payment_webhook_failed` | `verification_failed` | Alert immediately for repeated failures; verify the endpoint secret and delivery source. |
| `payment_webhook_failed` | `unknown_checkout_session`, `missing_order`, `missing_correlated_state` | Reconcile the provider event against local payment records. |
| `payment_webhook_failed` | `missing_provider_object_id`, `session_id_mismatch`, `metadata_mismatch`, `amount_mismatch`, `currency_mismatch`, `livemode_mismatch`, `payment_intent_mismatch`, `ownership_mismatch`, `async_success_not_paid` | Alert immediately and quarantine automatic fulfillment pending reconciliation. |
| `payment_webhook_failed` | `provider_retrieval_failed`, `processing_failed` | Retry reconciliation after provider/database recovery and inspect the durable webhook failure summary. |
| `payment_attempt_transition` | none | Use for lifecycle tracing; alert only on impossible or stalled transition patterns. |

Events contain only safe attempt/provider-event identifiers, stable states,
sources, and categories. Customer details, provider URLs and secrets, raw
payloads, and exception messages are excluded. Duplicate terminal webhook
delivery is acknowledged from the durable ledger without repeating the payment
transition or emitting a new false failure.

## Locked dependencies

`pyproject.toml` declares direct dependencies and `uv.lock` pins production and
development transitives for Python 3.12. Install and test without solving:

```bash
uv sync --extra dev --frozen
uv run --extra dev pytest
```

After an intentional dependency edit, run `uv lock`, review `uv.lock`, then run
`npm run api:lock:check` from the repository root. The check fails when the lock
is stale. Deprecation warnings are errors in the supported backend suite.

## Payment health and audit operations

Run `stockx-api-payment-health --stale-minutes 5` for bounded JSON counts of
failed webhooks/attempts, stale attempts, and overdue reservations. Exit 0 is
healthy; degraded or database-error outcomes are nonzero and never include
customer data, provider payloads, URLs, or credentials. Reconciliation emits
structured examined/recovered/failed/still-stale counts.

Authorized administrators can query `/api/v1/admin/audits` newest-first with
bounded actor, action, target, time, limit, and offset filters. There are no
audit mutation endpoints. Role and inventory audit rows are written in the same
transaction as the privileged change and contain only allowlisted before/after
facts plus actor, target, timestamp, and request ID.

## Admin Bootstrap

Create a normal user through the API first, then promote that existing user from
the backend environment. Normal admins can manage catalog products, store
listings/inventory, and customer messages:

```bash
cd apps/api
python -m app.admin promote admin@example.com
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-admin promote admin@example.com
```

Supreme admins can also manage normal-admin access through
`/api/v1/admin/users`. Grant supreme-admin status only from the backend
environment:

```bash
cd apps/api
python -m app.admin promote-supreme supreme@example.com
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-admin promote-supreme supreme@example.com
```

Both promotion commands normalize the email, require the user to already exist,
do not ask for or change passwords, and leave refresh-token records intact.
`promote-supreme` sets both `users.is_admin` and `users.is_supreme_admin`.
In-app user management can promote or demote normal-admin access, but it cannot
grant or remove supreme-admin status.

## Refresh-token retention

The retention command removes only refresh-token rows whose `expires_at` or
non-null `revoked_at` is at least 30 days old. It never cleans up users,
catalog, listings, orders, payment attempts, webhook events, or other business
records. `stripe_webhook_events` remains a permanent deduplication ledger.

For the first run, back up the database and confirm migrations are current.
Preview the same bounded selection that deletion mode would use, inspect the
reported UTC cutoff and count, and then execute at most one batch:

```bash
stockx-api-cleanup-refresh-tokens --dry-run --batch-size 100
stockx-api-cleanup-refresh-tokens --batch-size 100
```

Each invocation captures one cutoff and processes no more than the specified
positive batch size; it does not loop until the table is drained. A later run
safely continues with the next eligible rows. Run the preview and one deletion
batch daily at first, and monitor their counts before changing the batch size.
Scheduling and overlap policy belong to the deployment operator; this
repository does not install a scheduler or hosted workflow.

Run the normal backend suite separately from the retention integration module:

```bash
cd apps/api
pytest --ignore=tests/test_postgres_refresh_token_retention.py
```

For PostgreSQL-specific retention verification, use an explicitly selected
test database that is migrated to the current revision:

```bash
cd apps/api
export TEST_POSTGRES_DATABASE_URL='postgresql+psycopg://stockx:stockx@localhost:5432/stockx'
ALEMBIC_DATABASE_URL="$TEST_POSTGRES_DATABASE_URL" alembic upgrade head
pytest -q tests/test_postgres_refresh_token_retention.py
```

The PostgreSQL module deletes its own fixture rows and is skipped unless
`TEST_POSTGRES_DATABASE_URL` is present. Never point that variable at a shared
or production database.

## Verification

```bash
cd apps/api
uv sync --extra dev --frozen
uv lock --check
uv run --extra dev pytest
alembic upgrade head
python -m app.db.seed
python -m app.db.seed
```

Optional destructive local rollback:

```bash
alembic downgrade base
```

For this auth/audit migration, deploy schema first, then compatible application
code. Existing refresh chains are deterministically grouped before `family_id`
becomes non-null; cross-user/self legacy links are detached. To roll back,
restore the prior compatible application first, disable verification/reset, and
expect current sessions to require login before downgrading the migration.

The payment migration adds reservation timestamps, `payment_attempts`, and
`stripe_webhook_events`. Before downgrading it, disable new Stripe sessions but
keep webhooks and reconciliation running until every payable session is paid or
terminal. Back up reconciliation data before removing the tables.

The default `pytest` suite uses in-process test clients and does not require a
running API server.

## Running-Service API Smoke Test

Use the smoke test when you want to verify the running FastAPI service,
PostgreSQL-backed seed data, refresh cookies, auth flows, admin-created store
listings, guest/authenticated cart behavior, authenticated watchlist/customer
messages, admin bootstrap, admin
listing management, admin archive/restore behavior, manual checkout, inventory
decrement, cart clearing, order history/detail, normal-admin order
search/filter/detail review, and cross-user nondisclosure
through real HTTP requests.

From the repository root, start PostgreSQL:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

Prepare the database and start the API:

```bash
cd apps/api
alembic upgrade head
python -m app.db.seed
CHECKOUT_MODE=manual uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd apps/api
python -m app.smoke --base-url http://127.0.0.1:8000
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-smoke --base-url http://127.0.0.1:8000
```

You can also set the base URL with `STOCKX_API_BASE_URL`:

```bash
STOCKX_API_BASE_URL=http://127.0.0.1:8000 python -m app.smoke
```

For local HTTP smoke tests, keep `REFRESH_COOKIE_SECURE=false` so the refresh
cookie can round-trip over `http://127.0.0.1:8000`.

The smoke test expects seeded categories `sneakers`, `streetwear`, and
`collectibles`, plus the seeded Jordan product slug
`jordan-1-retro-high-element-gore-tex-black-particle-grey`. It creates a unique
`api-smoke-...@example.test` users on every run, so repeated runs do not fail
because of previous user data. Listings, messages, cart rows, and revoked
refresh-token rows created by smoke runs may remain in the local database. The
admin smoke promotes temporary smoke users, temporarily archives the seeded
product, verifies archived-product listing rejection, restores the product,
and reviews the uniquely created order through the read-only admin API. The
order-review checks verify guest/customer rejection, normal-admin access,
email and order-number search, combined status filters, safe detail fields,
unchanged order state, and cross-customer nondisclosure. To reset local smoke
data, use the optional rollback above and then re-run migrations and seed data.

Common smoke-test failures:

- `Could not connect to API`: start `uvicorn app.main:app --reload`, or pass the
  correct `--base-url`.
- Missing seeded categories or product: run `alembic upgrade head` and
  `python -m app.db.seed` against the same database used by the running API.
- Refresh cookie assertions fail over local HTTP: confirm
  `REFRESH_COOKIE_SECURE=false`.
- Manual checkout prerequisite failure: restart the API with
  `CHECKOUT_MODE=manual`. The smoke flow intentionally fails when order
  placement remains disabled.

For a deterministic running-service payment smoke, start the API and the smoke
command with the same database and these local-only settings:

```bash
CHECKOUT_MODE=stripe \
STRIPE_SECRET_KEY=sk_test_harness \
STRIPE_WEBHOOK_SECRET=whsec_harness \
FRONTEND_BASE_URL=http://localhost:3000 \
STRIPE_EXPECTED_LIVEMODE=false \
STRIPE_USE_FAKE_PROVIDER=true \
uvicorn app.main:app

CHECKOUT_MODE=stripe \
STRIPE_SECRET_KEY=sk_test_harness \
STRIPE_WEBHOOK_SECRET=whsec_harness \
FRONTEND_BASE_URL=http://localhost:3000 \
STRIPE_EXPECTED_LIVEMODE=false \
STRIPE_USE_FAKE_PROVIDER=true \
python -m app.smoke --stripe --base-url http://127.0.0.1:8000
```

Do not use the fake provider in a shared, sandbox, staging, or production
deployment. Real hosted-checkout verification requires Stripe sandbox
credentials and the CLI or an HTTPS webhook destination.

Quick manual API smoke:

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/categories
curl "http://localhost:8000/api/v1/search?q=jordan"
```
