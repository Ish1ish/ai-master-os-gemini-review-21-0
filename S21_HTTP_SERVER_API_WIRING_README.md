# S21 Real HTTP Server/API Wiring

Adds a real localhost HTTP server around the S20 authoritative security adapter.

Acceptance coverage:

- Missing bearer token -> HTTP 401
- Invalid bearer token -> HTTP 401
- Untrusted/plain transport (`tls_terminated=False`) -> HTTP 403
- Valid token + trusted TLS termination state -> HTTP 200 / ADMITTED
- HTTP transport reaches the same security boundary used by S20/S19
- Request bodies cannot request external actions through an HTTP bypass
- No automatic external action or memory write is performed

This stage intentionally uses Python's standard library only. It does not claim
that the listener itself provides TLS. `tls_terminated=True` represents a trusted
TLS edge/reverse-proxy deployment boundary and must only be set by the deployment
configuration, never from an untrusted client header.
