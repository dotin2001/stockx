## Purpose

Defines the durable frontend stack standards for the marketplace web app so route, API, session, UI, and verification work stays consistent as the existing Next.js frontend evolves.

## ADDED Requirements

### Requirement: Frontend stack has documented local entry points
The system SHALL provide a documented frontend application with repeatable local commands for development, linting, type checking, and production builds.

#### Scenario: Developer starts the frontend locally
- **WHEN** a developer follows the frontend setup documentation from the repository root
- **THEN** the documented development command starts the marketplace web app without requiring the legacy static HTML files at runtime

#### Scenario: Developer runs frontend quality checks
- **WHEN** a developer runs the documented frontend lint, typecheck, and build commands
- **THEN** each command targets the frontend app consistently from the root workspace or frontend package and reports actionable failures

#### Scenario: Frontend environment is documented
- **WHEN** a developer reads the frontend documentation
- **THEN** it explains the API base URL configuration, the expected local backend dependency, and the backend CORS origin needed for browser requests

### Requirement: Marketplace routes use API-backed data contracts
The system SHALL render marketplace route data through typed frontend data contracts that match the backend API responses used by the web app.

#### Scenario: Public catalog routes render backend data
- **WHEN** the home, category, product detail, or search routes display catalog content
- **THEN** product names, slugs, images, prices, sold counts, categories, variants, and pagination metadata come from backend API responses rather than hardcoded route markup

#### Scenario: API failures preserve honest page state
- **WHEN** a required frontend API request is loading, fails, or returns no matching data
- **THEN** the route displays loading, error, not-found, or empty states instead of stale or misleading marketplace content

#### Scenario: API base URL is configurable
- **WHEN** the frontend runs against a non-default local or deployed API origin
- **THEN** the web app uses documented environment configuration to target that API origin without code changes

### Requirement: Authenticated frontend state follows backend session security
The system SHALL align authenticated frontend behavior with the backend access-token and HTTP-only refresh-cookie session model.

#### Scenario: Session restore uses refresh cookie flow
- **WHEN** a returning user opens the web app with a valid refresh session
- **THEN** the frontend restores authenticated user state through the backend refresh flow before showing protected account or sell data

#### Scenario: Access token is not persisted in long-lived browser storage
- **WHEN** the frontend stores authenticated state for active browser use
- **THEN** it does not persist bearer access tokens in long-lived browser storage such as local storage

#### Scenario: Protected requests include explicit credentials
- **WHEN** the frontend calls protected account, listing, watchlist, cart, or logout behavior
- **THEN** the request uses the backend-required bearer token or refresh-cookie credentials for that operation

#### Scenario: Logout clears authenticated UI state
- **WHEN** an authenticated user logs out
- **THEN** the frontend calls the backend logout flow and returns navigation and protected surfaces to the guest state

### Requirement: UI conventions preserve marketplace usability
The system SHALL use reusable, accessible UI patterns for shared marketplace surfaces across desktop and mobile viewports.

#### Scenario: Shared marketplace surfaces are reusable
- **WHEN** a route needs header navigation, search, category navigation, product cards, product grids, auth forms, protected states, loading states, error states, or empty states
- **THEN** it uses shared frontend patterns rather than duplicating route-specific markup for the same behavior

#### Scenario: Responsive layout remains usable
- **WHEN** a visitor uses the marketplace web app on mobile or desktop viewports
- **THEN** navigation, search, product grids, filters, forms, and account or sell surfaces remain readable, keyboard usable, and free from overlapping controls

#### Scenario: Motion respects accessibility preference
- **WHEN** the app displays reveal, ticker, hover, scroll, or menu motion
- **THEN** non-essential motion is reduced or disabled for visitors who request reduced motion while preserving access to all content and actions

### Requirement: Legacy static storefront remains a migration reference
The system SHALL keep the legacy static storefront files available until a dedicated cleanup change removes them after route and content parity is accepted.

#### Scenario: Static files are retained during stack updates
- **WHEN** frontend stack hardening changes are applied
- **THEN** `index.html`, category static pages, legacy CSS, and legacy JavaScript remain in the repository unless a separate approved cleanup change removes them

#### Scenario: Next.js app does not depend on legacy runtime files
- **WHEN** the web app renders current marketplace routes
- **THEN** those routes do not import or require the legacy static CSS or JavaScript files at runtime

### Requirement: Frontend stack changes are verified
The system SHALL verify frontend stack changes with automated checks and route-level smoke coverage appropriate to the changed surface.

#### Scenario: Automated checks run before handoff
- **WHEN** a frontend stack change modifies web app code, configuration, dependencies, or shared UI behavior
- **THEN** lint, typecheck, and production build checks are run or any unavailable check is documented with the reason

#### Scenario: Route smoke coverage reflects expected marketplace pages
- **WHEN** frontend stack changes affect routing, data loading, auth state, layout, or shared components
- **THEN** route smoke checks cover the home, category, product detail, search, login, signup, account, and sell routes with expected guest and authenticated states where applicable

#### Scenario: Documentation matches implemented commands
- **WHEN** frontend scripts, environment variables, or stack conventions change
- **THEN** frontend documentation is updated so setup, development, verification, API dependency, and static-file migration notes match the implemented project
