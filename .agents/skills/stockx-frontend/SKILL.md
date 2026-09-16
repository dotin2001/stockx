---
name: stockx-frontend
description: Use when planning, building, reviewing, or refactoring this project's Next.js TypeScript Tailwind CSS frontend for the StockX-style marketplace.
---

# StockX Frontend Skill

Use this skill for work in the planned `apps/web` frontend or for migrating the current static storefront into that frontend.

## Project Context

The current repository starts as static HTML/CSS/JS:

- `index.html`
- `streetwear.html`
- `collectibles.html`
- `css/`
- `js/`

The target frontend is:

- Next.js App Router
- TypeScript
- Tailwind CSS
- Data loaded from the FastAPI backend

Keep the static files available until the Next.js routes reach useful parity.

## Frontend Shape

Expected routes:

```text
/
/category/[slug]
/product/[slug]
/search
/login
/signup
/account
/sell
```

Expected components:

- `Header`
- `SearchBar`
- `CategoryNav`
- `ProductCard`
- `ProductGrid`
- `ProductDetail`
- `AuthForm`
- Account, empty, loading, and error states

## Guidance

- Prefer reusable components over copying static page sections.
- Keep products and categories data-driven; do not hardcode catalog records into route markup.
- Keep guest and authenticated navigation states explicit.
- Use semantic links, buttons, forms, labels, and headings.
- Use Tailwind utilities consistently; introduce shared component classes only when they reduce real repetition.
- Preserve the current marketplace feel while improving layout, accessibility, and responsiveness.
- Treat `/account`, `/sell`, watchlist, and listing actions as authenticated surfaces.

## Verification

When frontend tooling exists, verify with the project's documented commands for:

- Type checking
- Linting
- Build
- Route smoke checks for home, category, product detail, search, login, signup, account, and sell

If tooling has not been scaffolded yet, state that verification is blocked by missing frontend setup.
