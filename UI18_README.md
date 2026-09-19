# UI18 — Backend Route Alignment

Purpose: restore the HTTP contract required by the wired O46 console.

Fixes:
- Adds GET /runs to the O32 API surface using ApplicationService.list_runs().
- Adds /ready as a compatibility alias for /readiness.
- Keeps authentication gate in front of both routes.
- No new mutation authority or external side effects.

Targeted tests: tests/test_ui18_backend_route_alignment.py
