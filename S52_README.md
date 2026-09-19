# O45-S52 — Real Provider Closed-Loop Validation

Purpose: validate the O45 closed loop with the existing real model/search provider adapters as live evidence inputs.

Path:
real provider evidence -> S51 cycle 1 -> persisted trace -> re-entry -> fresh real provider evidence -> cycle 2

Safety boundary:
- no external side effects
- no memory writes
- no autonomous production approval
- re-entry never auto-executes the next action

Real credentials are read from existing environment variables and never printed.
Required configuration is the existing live provider contract:
- AI_OS_MODEL_BASE_URL
- AI_OS_MODEL_API_KEY
- AI_OS_MODEL_NAME
- AI_OS_SEARCH_BASE_URL
- AI_OS_SEARCH_API_KEY

Targeted tests use deterministic provider fakes only; the release gate additionally requires configured live providers and performs live model + search calls without printing response content.
