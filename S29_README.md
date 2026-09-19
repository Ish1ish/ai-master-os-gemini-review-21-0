# S29 — S21 O36 Adapter Wiring Fix

The live 401 was not a token problem. S19 invokes its authenticator as:
`authenticator(token)`

O36's production authenticator expects credentials shaped as:
`{"bearer_token": token}`

This patch supplies the missing callable adapter without changing S19, S20, S21, or O36 contracts.

Apply the scripts overlay, stop the old S21 process, then start S21 using the bundled CMD launcher.
