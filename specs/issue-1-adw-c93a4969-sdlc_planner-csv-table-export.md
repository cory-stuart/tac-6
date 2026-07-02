# Feature: One Click Table & Query Result CSV Exports

## Metadata
issue_number: `1`
adw_id: `c93a4969`
issue_json: `{"number":1,"title":"One Click Table Exports","body":"Using adw_plan_build_review add one click table exports and once click result export feature to get results as csv files.\n\nCreate two new endpoints to support these features. One exporting tables, one for exporting query results.\n\nPlace a download button directly to the left of the 'x' icon for available tables.\nPlace a download button directly to the left of the 'hide' button for query results.\n\nUse the appropriate download icon."}`

## Feature Description
Add one-click CSV export capabilities to the Natural Language SQL Interface. Users will be able to:

1. **Export any available table** to a `.csv` file with a single click via a download button placed directly to the left of the existing `×` (remove) icon in each table's header row.
2. **Export the current query results** to a `.csv` file with a single click via a download button placed directly to the left of the existing `Hide` toggle button in the Query Results header.

Two new backend endpoints support these actions: one that streams a full table as CSV, and one that regenerates the last query's results as CSV. The downloaded files use the table name (e.g. `users.csv`) or a query-results name (e.g. `query_results.csv`) respectively, and are returned with the proper `text/csv` content type and `Content-Disposition: attachment` header so the browser triggers a native download.

This gives users a frictionless way to pull their data out of the tool for use in spreadsheets or other systems, complementing the existing upload workflow.

## User Story
As a data analyst using the Natural Language SQL Interface
I want to download tables and query results as CSV files with one click
So that I can analyze, share, or archive my data outside the application without manually copying rows

## Problem Statement
The application lets users upload data and run natural-language queries, but there is no way to get data back out. Users who want to work with a full table or with the results of a specific query in a spreadsheet or downstream tool must manually select and copy rows from the HTML table — an error-prone, tedious process that does not scale to large result sets. There is no export functionality and no API surface to support it.

## Solution Statement
Introduce two new FastAPI endpoints in `app/server/server.py`:

1. `GET /api/export/table/{table_name}` — validates the table identifier via the existing `sql_security` module, confirms the table exists, selects all rows, serializes them to CSV using Python's stdlib `csv` module, and returns a downloadable `text/csv` response.
2. `POST /api/export/results` — accepts the SQL of the last executed query, re-executes it through the existing `execute_sql_safely` path (which enforces SQL-injection protections), serializes the result rows to CSV, and returns a downloadable `text/csv` response.

On the frontend (`app/client`), add a download icon button next to the `×` remove button in each table header, and a download icon button next to the `Hide` toggle button in the query results header. New API client methods trigger the downloads via the blob → anchor-click pattern. No new dependencies are required — CSV generation uses Python's standard library and the frontend uses standard browser APIs.

## Relevant Files
Use these files to implement the feature:

- `README.md` — Project overview, commands, API endpoint list, and security guidance. The API Endpoints section must be updated to document the two new endpoints.
- `app/server/server.py` — Hosts all FastAPI route handlers. The two new export endpoints are added here, following the existing handler patterns (logging, try/except, `traceback`).
- `app/server/core/data_models.py` — Pydantic request/response models. Add an `ExportResultsRequest` model for the results-export endpoint body.
- `app/server/core/sql_processor.py` — Contains `execute_sql_safely` and `get_database_schema`. Reused by the results-export endpoint to re-run the query safely.
- `app/server/core/sql_security.py` — Contains `validate_identifier`, `check_table_exists`, `execute_query_safely`, and `SQLSecurityError`. Reused by the table-export endpoint to validate/escape the table name and safely select rows.
- `app/server/tests/core/test_sql_processor.py` — Example test patterns (in-memory SQLite fixture, mocking `sqlite3.connect`). Reference for new export unit tests.
- `app/server/tests/test_sql_injection.py` — Security test patterns. Reference to ensure new endpoints do not open injection vectors.
- `app/client/index.html` — Static markup. The table header and results header structure live here (results header contains the `#toggle-results` "Hide" button); confirm structure but note table rows are built dynamically in `main.ts`.
- `app/client/src/main.ts` — Renders the tables list (`displayTables`, where the `remove-table-button` is created) and the results section (`displayResults`, where the toggle button lives). Add the download buttons and their click handlers here.
- `app/client/src/api/client.ts` — Typed API client. Add `exportTable(tableName)` and `exportResults(sql)` methods.
- `app/client/src/types.d.ts` — Frontend type declarations mirroring the Pydantic models. Add `ExportResultsRequest`.
- `app/client/src/style.css` — Styling. Add styles for the new download buttons consistent with `.remove-table-button` and `.toggle-button`.
- `.claude/commands/test_e2e.md` — Read this to understand how E2E tests are executed and how to structure a new E2E test file.
- `.claude/commands/e2e/test_basic_query.md` — Read this as the template/example for creating the new E2E test file (User Story, Test Steps, Success Criteria structure).

### New Files
- `.claude/commands/e2e/test_csv_table_export.md` — New E2E test file validating that the table download button and the query-results download button trigger CSV downloads. Modeled on `test_basic_query.md`.

## Implementation Plan
### Phase 1: Foundation
Add the shared CSV serialization approach and the request model. Both endpoints convert a list of row dicts + ordered column names into CSV text using Python's stdlib `csv` module with an `io.StringIO` buffer. Add the `ExportResultsRequest` Pydantic model (`sql: str`) to `data_models.py` and the matching `ExportResultsRequest` interface to `types.d.ts`. This establishes the contract before wiring endpoints and UI.

### Phase 2: Core Implementation
Implement the two backend endpoints in `server.py`:
- `GET /api/export/table/{table_name}`: validate identifier, check existence, `SELECT * FROM {table}` via `execute_query_safely`, serialize to CSV, return `fastapi.responses.Response` with `media_type="text/csv"` and `Content-Disposition: attachment; filename="{table_name}.csv"`.
- `POST /api/export/results`: take `request.sql`, run through `execute_sql_safely`, serialize `results`/`columns` to CSV, return the same downloadable response type with filename `query_results.csv`.

Both handlers mirror the existing logging/try-except/`traceback` conventions and raise/handle errors gracefully (HTTP 400 for invalid identifiers, 404 for missing tables, 500 for unexpected errors).

### Phase 3: Integration
Wire the frontend:
- Add `exportTable` and `exportResults` methods to `api/client.ts` that fetch the endpoints, obtain a `Blob`, and trigger a browser download via a temporary anchor element (create object URL, set `download`, click, revoke).
- In `main.ts` `displayTables`, insert a download button immediately before the `removeButton` in each table header, wired to `api.exportTable(table.name)`.
- In `main.ts` `displayResults`, insert a download button immediately to the left of the `#toggle-results` "Hide" button, wired to `api.exportResults(lastSql)`. Track the last executed SQL (from `QueryResponse.sql`) so it can be re-exported; disable/hide the results download button when there are no results or an error occurred.
- Add CSS for the download buttons consistent with existing button styles. Use an appropriate download icon (inline SVG download glyph or a `⬇` download symbol).
- Update the README API Endpoints section.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Read documentation and confirm conventions
- Read `README.md`, `.claude/commands/test_e2e.md`, and `.claude/commands/e2e/test_basic_query.md` to understand project structure, commands, and E2E test format.
- Confirm no new Python or JS dependency is needed (stdlib `csv`/`io` on backend; browser APIs on frontend). Do NOT run `uv add`.

### 2. Add the results-export request model
- In `app/server/core/data_models.py`, add:
  ```python
  # Export Models
  class ExportResultsRequest(BaseModel):
      sql: str = Field(..., description="SQL of the query results to export as CSV")
  ```
- Keep it simple; no decorators.

### 3. Implement the table export endpoint
- In `app/server/server.py`, add imports: `from fastapi.responses import Response`, `import csv`, `import io`.
- Add a small helper (module-level function, not a decorator) `rows_to_csv(columns: list[str], rows: list[dict]) -> str` that writes a header row + data rows to an `io.StringIO` using `csv.writer` and returns the string. Handle `None` values as empty strings to mirror the frontend's rendering.
- Add endpoint `GET /api/export/table/{table_name}`:
  - `validate_identifier(table_name, "table")` inside try/except `SQLSecurityError` → `HTTPException(400, ...)`.
  - Open `sqlite3.connect("db/database.db")`; if `not check_table_exists(conn, table_name)` → `HTTPException(404, ...)`.
  - Use `execute_query_safely(conn, "SELECT * FROM {table}", identifier_params={'table': table_name})` with `conn.row_factory = sqlite3.Row` to get named columns; build `columns` from cursor description / row keys and `rows` as list of dicts.
  - Serialize with `rows_to_csv`, close the connection.
  - Return `Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{table_name}.csv"'})`.
  - Follow the existing logging (`logger.info` on success, `logger.error` + `traceback.format_exc()` on failure). Re-raise `HTTPException`; wrap other errors in `HTTPException(500, ...)`.

### 4. Implement the query results export endpoint
- In `app/server/server.py`, add endpoint `POST /api/export/results` accepting `ExportResultsRequest`:
  - Import `ExportResultsRequest` in the `core.data_models` import block.
  - Call `execute_sql_safely(request.sql)`; if `result['error']` → `HTTPException(400, result['error'])`.
  - Serialize `result['columns']` / `result['results']` with `rows_to_csv`.
  - Return `Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="query_results.csv"'})`.
  - Follow existing logging and error-handling conventions.

### 5. Add frontend types
- In `app/client/src/types.d.ts`, add:
  ```ts
  // Export Types
  interface ExportResultsRequest {
    sql: string;
  }
  ```

### 6. Add API client methods
- In `app/client/src/api/client.ts`, add a private helper that performs a download from a `Response`/endpoint: fetch the URL (with method/body as needed), read `await response.blob()`, create an object URL, create a temporary `<a>` with the `download` attribute set to the desired filename, click it, then revoke the URL and remove the anchor. Derive the filename from the `Content-Disposition` header when present, else fall back to a provided default.
  - `async exportTable(tableName: string): Promise<void>` → `GET /export/table/{tableName}`, default filename `${tableName}.csv`.
  - `async exportResults(sql: string): Promise<void>` → `POST /export/results` with JSON body `{ sql }` and `Content-Type: application/json`, default filename `query_results.csv`.
- Ensure non-OK responses throw so callers can display an error.

### 7. Add table download button in the tables list
- In `app/client/src/main.ts` `displayTables`, create a `downloadButton` element with class `download-table-button`, an appropriate download icon (inline SVG download glyph), `title="Download table as CSV"`, and `onclick` calling `api.exportTable(table.name)` (wrap in try/catch → `displayError`).
- Append it to `tableHeader` BEFORE `removeButton` so it sits directly to the left of the `×` icon.

### 8. Add query-results download button
- In `app/client/src/main.ts` `displayResults`, add a `downloadButton` with class `download-results-button`, the same download icon, `title="Download results as CSV"`, placed in the results header directly to the left of the `#toggle-results` "Hide" button (insert before it in the `.results-header`).
- Store the current query's SQL (e.g. a module-scoped `lastQuerySql` variable, or read from the rendered SQL) so the button calls `api.exportResults(sql)`.
- Only enable/show the download button when `response.results.length > 0` and there is no `response.error`; otherwise disable or hide it.
- Ensure the button is created/attached once (avoid duplicate handlers if `displayResults` runs multiple times) — mirror how the existing toggle button is handled or guard against duplicate listeners.

### 9. Style the download buttons
- In `app/client/src/style.css`, add `.download-table-button` styled consistently with `.remove-table-button` (transparent background, icon-sized, hover state using an accent/primary color) and `.download-results-button` styled consistently with `.toggle-button` sizing/spacing so it visually pairs with "Hide". Ensure adequate gap between the download button and its neighbor.

### 10. Update README
- In `README.md`, add the two new endpoints to the `## API Endpoints` section:
  - `GET /api/export/table/{table_name}` - Export a table as CSV
  - `POST /api/export/results` - Export query results as CSV

### 11. Create the E2E test file
- Create `.claude/commands/e2e/test_csv_table_export.md` modeled on `.claude/commands/e2e/test_basic_query.md` with a `User Story`, `Test Steps`, and `Success Criteria`. The test should (minimal steps): load sample data (Users), verify a download button appears to the left of the `×` on the `users` table, run a simple query so results appear, verify a download button appears to the left of the `Hide` button, click each download button, verify the browser initiates a CSV download (e.g. via Playwright download event / no error), and capture screenshots proving both download buttons are present.

### 12. Add backend unit tests
- Add tests (e.g. in `app/server/tests/core/` or a new `app/server/tests/test_export.py`) using the in-memory SQLite + `mock_connect` pattern from `test_sql_processor.py`:
  - `rows_to_csv` produces correct header + rows, handles `None` as empty.
  - Table export returns CSV text and correct `Content-Disposition` filename for an existing table.
  - Table export returns 404 for a non-existent table and 400 for an invalid identifier.
  - Results export returns CSV for a valid `SELECT` and 400 for a dangerous/invalid SQL.
- Prefer testing via FastAPI `TestClient` for the endpoints where practical, or test the helper + underlying logic directly, matching existing test style.

### 13. Run validation
- Run every command in the `Validation Commands` section and fix any failures until all pass with zero regressions.

## Testing Strategy
### Unit Tests
- `rows_to_csv` helper: correct CSV serialization of header and rows; `None` values rendered as empty strings; empty result set yields header-only or empty output as designed.
- `GET /api/export/table/{table_name}`: returns 200 with `text/csv` body and `attachment; filename="<table>.csv"` for an existing table; 404 for a missing table; 400 for an invalid/injection identifier.
- `POST /api/export/results`: returns 200 with CSV for a valid SELECT; 400 when `execute_sql_safely` reports an error (dangerous SQL, syntax error).
- Reuse the in-memory SQLite fixture and `patch('...sqlite3.connect')` pattern from `test_sql_processor.py`.

### Edge Cases
- Table with zero rows (export produces a valid CSV, header-only or empty per design).
- Values containing commas, quotes, and newlines (must be properly quoted by `csv.writer`).
- `NULL`/`None` cell values.
- Column names/table names with spaces or underscores (allowed by `validate_identifier`).
- Invalid table name / SQL-injection attempt in the path parameter → rejected with 400, no query executed.
- Exporting results when the last query returned an error or zero rows → the results download button is disabled/hidden.
- Unicode content in cells (ensure CSV text encodes correctly).

## Acceptance Criteria
- A `GET /api/export/table/{table_name}` endpoint exists and returns a downloadable `text/csv` response for an existing table, with `Content-Disposition: attachment; filename="<table_name>.csv"`.
- A `POST /api/export/results` endpoint exists and returns a downloadable `text/csv` response for the provided query SQL, with filename `query_results.csv`.
- Invalid table identifiers return 400; missing tables return 404; dangerous/invalid SQL for results export returns 400 — no injection is possible.
- Each available table in the UI shows a download button with an appropriate download icon directly to the left of the `×` remove icon; clicking it downloads that table as CSV.
- The Query Results header shows a download button with an appropriate download icon directly to the left of the `Hide` button; clicking it downloads the current results as CSV.
- The results download button is disabled/hidden when there are no results or an error occurred.
- README API Endpoints section documents both new endpoints.
- A new E2E test file `.claude/commands/e2e/test_csv_table_export.md` exists and passes.
- All validation commands pass with zero regressions.

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `cd app/server && uv run pytest` - Run server tests (including new export tests) to validate the feature works with zero regressions.
- `cd app/server && uv run pytest tests/test_sql_injection.py -v` - Confirm SQL injection protections still pass with the new endpoints.
- `cd app/client && bun tsc --noEmit` - Type-check the frontend to validate the new client code and types.
- `cd app/client && bun run build` - Build the frontend to validate there are no build regressions.
- `Read .claude/commands/test_e2e.md`, then read and execute the new E2E `.claude/commands/e2e/test_csv_table_export.md` test file to validate this functionality works end-to-end (both download buttons present and functional).

## Notes
- No new dependencies are required. CSV generation uses Python's standard library (`csv`, `io`); the frontend download uses standard browser APIs (`Blob`, object URLs, a temporary `<a download>` element). Do not run `uv add`.
- The results-export endpoint re-executes the last query's SQL rather than accepting raw rows from the client. This reuses the existing `execute_sql_safely` validation path (SQL-injection protection, dangerous-operation blocking) and keeps payloads small. The client already has `QueryResponse.sql` available to send.
- The table-export endpoint reuses `validate_identifier` / `check_table_exists` / `execute_query_safely` so it inherits the same identifier validation and escaping used everywhere else in the app.
- Use `fastapi.responses.Response` (or `StreamingResponse` if preferred for large tables) with an explicit `Content-Disposition` header so browsers trigger a native "Save as" download rather than rendering the CSV inline.
- Keep the download icon consistent between both buttons for a cohesive UI (a single inline SVG download glyph reused in both places is recommended).
- Future consideration: support additional export formats (JSON, XLSX) and streaming for very large tables to avoid buffering the entire CSV in memory.
