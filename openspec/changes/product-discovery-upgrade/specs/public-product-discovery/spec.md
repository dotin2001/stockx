## Purpose

Defines the public product discovery behavior that lets shoppers filter, sort, and inspect marketplace catalog results across category and search experiences.

## ADDED Requirements

### Requirement: Public catalog queries support discovery filters
The system SHALL let unauthenticated clients query public products with category, search text, brand, size, price range, available-only, sorting, limit, and offset parameters.

#### Scenario: Category products are filtered by brand
- **WHEN** a client requests category products with one or more supported brand filters
- **THEN** the system returns only non-archived products in that category whose brand matches one of the selected brands

#### Scenario: Search results are filtered by brand
- **WHEN** a client searches with text and one or more supported brand filters
- **THEN** the system returns only non-archived matching products whose brand matches one of the selected brands

#### Scenario: Products are filtered by size
- **WHEN** a client requests products with one or more supported size filters
- **THEN** the system returns only non-archived products that have at least one matching product variant size

#### Scenario: Products are filtered by price range
- **WHEN** a client requests products with minimum or maximum price filters
- **THEN** the system returns only products whose sellable active listing price is within the requested inclusive range

#### Scenario: Products are filtered to available only
- **WHEN** a client requests available-only products
- **THEN** the system returns only products that have at least one active listing with available quantity greater than zero

#### Scenario: Archived products remain hidden
- **WHEN** a client requests discovery results with any supported filter combination
- **THEN** the system excludes archived products from the returned items and discovery metadata

### Requirement: Discovery sorting is stable and explicit
The system SHALL allow clients to sort public discovery results by supported sort values while returning stable paginated ordering.

#### Scenario: Results are sorted by newest
- **WHEN** a client requests newest sorting
- **THEN** the system returns matching products ordered by newest product creation first with a deterministic tie-breaker

#### Scenario: Results are sorted by price low to high
- **WHEN** a client requests price ascending sorting
- **THEN** the system returns matching products ordered by lowest sellable active listing price from low to high with products without sellable listings after sellable products

#### Scenario: Results are sorted by price high to low
- **WHEN** a client requests price descending sorting
- **THEN** the system returns matching products ordered by lowest sellable active listing price from high to low with products without sellable listings after sellable products

#### Scenario: Results are sorted by popularity
- **WHEN** a client requests popular sorting
- **THEN** the system returns matching products ordered by sold count from high to low with a deterministic tie-breaker

#### Scenario: Results are sorted alphabetically
- **WHEN** a client requests name ascending sorting
- **THEN** the system returns matching products ordered by product name from A to Z with a deterministic tie-breaker

#### Scenario: Unsupported sort is rejected
- **WHEN** a client requests an unsupported sort value
- **THEN** the system returns a validation-style error without falling back silently to a different sort

### Requirement: Discovery responses include filter metadata
The system SHALL return discovery metadata that describes result totals and available filter options for the current category or search context.

#### Scenario: Metadata includes result count and active filters
- **WHEN** a client requests discovery results with filters or sorting
- **THEN** the system returns the total matching result count, pagination data, selected filter values, and selected sort value

#### Scenario: Metadata includes available brands
- **WHEN** a client requests discovery results for a category or search context
- **THEN** the system returns available brand options with counts scoped to that context

#### Scenario: Metadata includes available sizes
- **WHEN** a client requests discovery results for a category or search context
- **THEN** the system returns available size options with counts scoped to that context

#### Scenario: Metadata includes price bounds
- **WHEN** a client requests discovery results for a category or search context with sellable products
- **THEN** the system returns minimum and maximum sellable active listing prices for that context

#### Scenario: Metadata handles no matches
- **WHEN** a client requests a filter combination that matches no products
- **THEN** the system returns an empty item list, total zero, and metadata sufficient for the UI to show active filters and a reset path

### Requirement: Discovery UI preserves shareable filter state
The system SHALL expose category and search filters through URL query parameters so shoppers can share, reload, and navigate filtered result states.

#### Scenario: Category filter state loads from the URL
- **WHEN** a visitor opens a category URL containing supported filter and sort parameters
- **THEN** the page loads products using those parameters and displays the matching controls as selected

#### Scenario: Search filter state loads from the URL
- **WHEN** a visitor opens a search URL containing query text plus supported filter and sort parameters
- **THEN** the page loads products using those parameters and displays the matching controls as selected

#### Scenario: Changing a filter updates results and URL state
- **WHEN** a visitor changes a supported discovery filter or sort option
- **THEN** the page requests updated results and updates the URL query string without losing the category or search context

#### Scenario: Clearing filters preserves context
- **WHEN** a visitor clears active filters
- **THEN** the page removes filter-specific URL parameters while preserving the category route or search text and resets results for that context

### Requirement: Discovery UI remains usable across states
The system SHALL provide accessible filter controls, sort controls, active filter summaries, loading states, error states, and empty states on category and search result pages.

#### Scenario: Filters are keyboard usable
- **WHEN** a visitor navigates the discovery controls with a keyboard
- **THEN** the controls expose visible focus states, usable labels, and operable form elements without requiring pointer interaction

#### Scenario: Active filters are visible
- **WHEN** a visitor applies one or more filters
- **THEN** the page displays active filter summaries with controls to remove individual filters

#### Scenario: Loading state preserves layout
- **WHEN** filtered discovery results are loading
- **THEN** the page displays a loading state that does not replace the whole browsing context with misleading stale content

#### Scenario: Error state offers recovery
- **WHEN** filtered discovery results fail to load
- **THEN** the page displays an error state with a recovery path such as retrying, clearing filters, searching, or returning to a category

#### Scenario: Empty state explains no matches
- **WHEN** filtered discovery results return no matching products
- **THEN** the page displays an empty state that acknowledges the active filters and offers a way to clear or broaden them
