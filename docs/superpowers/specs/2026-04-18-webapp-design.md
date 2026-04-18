# Matter Hub Web App — Design

## Purpose

Provide a Docker-based local web UI for managing the SQLite-backed Matter Hub
article database. Replaces ad-hoc CLI invocations for day-to-day browsing.

Supported operations:

- Full-text search (title / author / publisher / note — existing FTS5 trigram)
- Tag filter (multi-select, AND semantics)
- View switching (active / archived / trash)
- Soft delete with restore
- No tag editing (filter only)

Not in scope:

- Authentication (single-user, localhost only)
- Tag CRUD (add/remove) — handled by existing CLI
- Matter API mutations (sync remains one-way, Matter → local)

## Requirements Summary

| Concern | Decision | Source |
|---|---|---|
| Archive semantics | Rely on Matter's `library_state`. No local archive flag. | User Q3-B + follow-up simplification |
| Delete semantics | Soft delete. `deleted=1` skipped on re-sync. Restorable. | User Q2-B |
| Tag filter (multi) | AND (all selected tags must match) | User Q4-A |
| Stack | FastAPI + Jinja2 + HTMX + Tailwind (CDN) | User approval of approach A |
| Deployment | Single Docker container via `compose.yml`, binds `./data` volume | — |

## Schema Changes

One additive migration on `articles`:

```sql
ALTER TABLE articles ADD COLUMN deleted INTEGER DEFAULT 0;  -- 0 | 1
```

Migration lives in `db.py::_migrate()` next to the existing `source` column
migration. Idempotent: guarded by `PRAGMA table_info` column-presence check.

No other schema changes. `library_state` continues to represent Matter-side
archive state (0 = library / active, non-zero = archived in Matter).

## View Model

Three mutually exclusive views selected via header tab:

| View | WHERE clause | Default |
|---|---|---|
| `active`   | `deleted = 0 AND library_state = 0` | yes |
| `archived` | `deleted = 0 AND library_state != 0` | |
| `trash`    | `deleted = 1` | |

`trash` view exposes a **restore** action (sets `deleted = 0`). `active` and
`archived` views expose a **delete** action (sets `deleted = 1`).

## Sync Behavior Change

`matter_hub/cli.py::sync` upserts articles unconditionally today. After this
change, the upsert loop pre-checks `SELECT deleted FROM articles WHERE id=?`:

- Row exists with `deleted = 1` → skip upsert, skip tag/highlight refresh
- Row exists with `deleted = 0` → existing behavior
- Row absent → existing behavior (insert)

The existing "remove articles deleted in Matter" logic (commit `81934d3`) runs
unchanged — if a soft-deleted local article is also gone from Matter, it still
gets hard-deleted from SQLite. This is acceptable: the user already chose to
hide it.

## Backend Structure

New package:

```
matter_hub/webapp/
  __init__.py
  main.py         # FastAPI app factory, mounts static, registers routes
  routes.py       # endpoint handlers
  queries.py      # web-specific SQL helpers (imported/called via Database)
  templates/
    base.html
    index.html           # full page (sidebar + main + header)
    _article_row.html    # HTMX partial: single article card
    _article_list.html   # HTMX partial: list + paginator
    _tag_filter.html     # HTMX partial: tag sidebar with counts
  static/
    app.css              # minimal; Tailwind via CDN
```

Existing `Database` class (`matter_hub/db.py`) gains these methods:

- `set_deleted(article_id: str, flag: bool) -> bool`
- `list_articles_filtered(q: str | None, tags: list[str], view: str, limit: int, offset: int) -> tuple[list[dict], int]`
  returns `(rows, total_count)` for pagination
- `list_tags_filtered(view: str) -> list[tuple[str, int]]`
  tag counts respecting the current view (but not the current tag/search filter, to keep tag list stable)

`list_articles_filtered` composes:

- Base: `SELECT a.* FROM articles a`
- If `q`: `JOIN articles_fts f ON a.rowid = f.rowid WHERE articles_fts MATCH :q`
- If tags: `JOIN tags t ON a.id = t.article_id WHERE t.name IN (...) GROUP BY a.id HAVING COUNT(DISTINCT t.name) = :n`
- AND view filter (see View Model table)
- `ORDER BY a.synced_at DESC LIMIT :limit OFFSET :offset`

`WAL` mode is enabled on connection open (`PRAGMA journal_mode=WAL`) so the CLI
and webapp can share the DB file without write contention.

## Routes

All routes return `text/html` (HTMX-friendly partials). No separate JSON API.

| Method | Path | Purpose | Response |
|---|---|---|---|
| GET  | `/` | Initial full page | full HTML |
| GET  | `/articles` | Filtered list | `_article_list.html` partial |
| GET  | `/tags` | Tag sidebar (view-scoped counts) | `_tag_filter.html` partial |
| POST | `/articles/{id}/delete` | Soft delete | `_article_row.html` removed via `HX-Swap: outerHTML` with empty body, or 204 |
| POST | `/articles/{id}/restore` | Undo soft delete | `_article_row.html` removed from trash view |

Query params for `GET /articles`:

- `q`: search string (FTS5 MATCH). Empty allowed.
- `tags`: comma-separated tag names. Empty allowed. AND semantics.
- `view`: one of `active` (default) / `archived` / `trash`.
- `page`: 1-indexed, default 1. Page size fixed at 50.

`DELETE` uses `POST` with `hx-confirm` prompt; no separate REST `DELETE` verb
for simplicity with HTMX forms.

## UI

Server-rendered via Jinja2. Interactive via HTMX attributes. Styling via
Tailwind CDN (no build step).

Layout (single route `/`):

```
┌──────────────────────────────────────────────────────────┐
│ Matter Hub    [ active | archived | trash ]   N articles │  header
├──────────────┬───────────────────────────────────────────┤
│ Search [___] │ [search box, debounced 300ms → GET /articles]
│              │                                          │
│ Tags         │ ┌──────────────────────────────────────┐│
│ [x] AI    45 │ │ Title (link, target=_blank)          ││
│ [ ] Rust  12 │ │ author · publisher · published_date  ││
│ [ ] Go     8 │ │ #tag #tag                            ││
│ [ ] ...      │ │            [ delete ] / [ restore ]  ││
│              │ └──────────────────────────────────────┘│
│              │ ...                                       │
│              │            [ Load more (page N+1) ]       │
└──────────────┴───────────────────────────────────────────┘
```

Behavior:

- Tag checkboxes toggle and trigger `hx-get /articles` with updated `tags` param.
- Selected tags also re-drive `hx-get /tags` so counts reflect other active filters? **No** — keep sidebar stable per view (see `list_tags_filtered`) to avoid count-collapse confusion.
- Search input uses `hx-trigger="keyup changed delay:300ms"`.
- View tabs at top swap both sidebar and list via two `hx-get` calls.
- Delete button: `hx-post="/articles/{id}/delete"`, `hx-confirm="Delete this article?"`, `hx-target="closest .article-row"`, `hx-swap="outerHTML"` with empty response.
- Restore button (trash view only): analogous, `hx-post="/articles/{id}/restore"`.
- Pagination: "Load more" button with `hx-get` + `hx-swap="beforeend"` into the list container; maintains current filters via encoded query params.

## Docker

`Dockerfile` at project root:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
COPY matter_hub ./matter_hub
RUN uv pip install --system -e .
EXPOSE 8000
CMD ["uvicorn", "matter_hub.webapp.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`compose.yml`:

```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - MATTER_HUB_DB=/app/data/matter-hub.db
```

The CLI continues to run on the host. DB file is shared through the bind mount.
WAL mode (set by webapp on startup) is sticky in the DB file, so the CLI
inherits it automatically on subsequent opens.

## Dependencies

Added to `pyproject.toml`:

- `fastapi>=0.110`
- `uvicorn[standard]>=0.27`
- `jinja2>=3.1`

Tailwind and HTMX loaded via CDN in `base.html`; no npm/node toolchain.

## Error Handling

- `POST /articles/{id}/*` with unknown id → 404.
- Malformed `view` param → fall back to `active`.
- Malformed `q` (FTS5 syntax error) → catch `sqlite3.OperationalError`, return the list without FTS filter and show a small "search syntax error" notice in the partial.
- DB write contention (rare, WAL mitigates) → let FastAPI return 500; user retries.

## Testing

- `tests/test_webapp.py`: FastAPI `TestClient` against a temp SQLite DB seeded with fixtures covering:
  - list filtering by view / tags (AND) / search
  - soft delete + restore round-trip
  - sync skip for `deleted=1` (tests `cli.sync` or the underlying import path)
  - pagination boundaries
- Existing tests continue to pass unchanged.

## Out of Scope / Future

- Authentication: deliberately omitted (localhost + Docker port not published beyond host).
- Tag editing from UI.
- Bulk operations (multi-select delete).
- Highlights display.
- Embedding-based similarity search.
