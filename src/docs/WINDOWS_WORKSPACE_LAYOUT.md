# AI Master OS — Canonical Windows Workspace

Recommended Desktop root:

`C:\Users\PC\Desktop\AI Master OS`

Structure:

```text
AI Master OS\
├── 00_CONTROL\       manifests, canonical paths, operator notes
├── 01_CORE_RUNTIME\  canonical backend runtime
├── 02_UI_CONSOLE\    canonical control center
├── 03_RELEASES\      frozen ZIP releases
├── 04_MILESTONES\    milestone specifications and records
├── 05_AUDITS\        release/go-live audit evidence
├── 06_ARCHIVE\       older verified baselines
└── 07_WORKSPACE\     active experiments / temporary work
```

The one-time organizer is **copy-only**. It does not delete or move the existing `15 AI OS RUNTIME BUILD` project folders.

After the organizer succeeds, use `00_CONTROL\WINDOWS_PATHS.cmd` or `windows\load_project_env.cmd` to establish the canonical runtime paths.
