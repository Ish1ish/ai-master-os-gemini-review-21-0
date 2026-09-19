# S27 — S21 CMD Staging Launcher

Adds CMD-native start/stop wrappers for the S21 local HTTPS staging server. No inline Python command is required. The launcher loads the callable O36 authenticator contract introduced by S26.

Start: `scripts\windows_s21_staging_start.cmd`
Stop: `scripts\windows_s21_staging_stop.cmd`

The server binds to `127.0.0.1:8091` and expects Caddy to terminate TLS on `localhost:8443`.
