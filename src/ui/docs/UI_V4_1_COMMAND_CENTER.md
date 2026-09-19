# UI V4.1 — Command Center Backend Integration

V4.1 upgrades the Run Center from a browser-local history view to a backend-first command surface.

## Source of truth

`GET /runs?limit=50` is the canonical list when available. The browser-local `aios.runs` store is a fallback/cache only.

## User controls

- Sync from backend
- Search by job/project/request/status
- Filter by status
- Reset filters
- Inspect a run through the authenticated run detail route
- Clear local history with confirmation; durable backend records are untouched

## Safety

No backend deletion route is called by Clear history. Execution and cancellation remain behind the authenticated backend boundary.
