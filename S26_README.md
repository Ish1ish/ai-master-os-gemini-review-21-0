# S26 — O36 Authenticator Callable Contract Fix

## Problem
S19 invokes the configured authenticator with a bearer-token string. The O36 `Authenticator` implementation exposed only `authenticate(credentials)` and therefore could raise a type/attribute error when the live S21 server passed the O36 authenticator directly.

## Fix
`core.src.auth.Authenticator` now implements `__call__(bearer_token)` and delegates to `authenticate({"bearer_token": bearer_token})`.

This preserves the existing credential-oriented O36 API while making the object directly compatible with the S19/S20 callable authenticator contract.

## Verification targets
- O36 default authenticator accepts a signed bearer token when called with the token string.
- S19 accepts the default O36 authenticator directly and admits a valid staging request.
- External actions remain blocked.
- Automatic memory writes remain blocked.
