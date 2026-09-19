# O39 / S32 — Production Operations Foundation

Status:
- Built for the verified O38 staging release candidate.
- Staging-only operations foundation.
- Internet-facing production approval remains false.

Operational controls:
1. Manifest-driven service definitions.
2. Fail-closed status/start checks.
3. Controlled S21 start/stop through the official CMD wrappers.
4. Caddy validation before acceptance.
5. Secret-safe operational snapshot: metadata and hashes only.
6. No token, Authorization header, API key, or signing secret is printed or persisted by the snapshot script.

Primary files:
- `config\o39_operations_manifest.json`
- `scripts\windows_s32_ops_status.cmd`
- `scripts\windows_s32_ops_start.cmd`
- `scripts\windows_s32_ops_stop.cmd`
- `scripts\windows_s32_ops_snapshot.cmd`
- `scripts\s32_ops_snapshot.py`

Recommended verification:
1. Run `scripts\windows_s32_ops_status.cmd`.
2. Run `scripts\windows_s32_ops_snapshot.cmd`.
3. Inspect `staging\ops_snapshot\snapshot.json` and `staging\ops_snapshot\snapshot.txt`.
4. Do not treat this as production go-live approval.
