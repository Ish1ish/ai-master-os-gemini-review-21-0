
# O39 S36.3.1 — Runtime Provider Wiring Gate Fix

The first S36.3 gate incorrectly assumed that the provider callables were exposed
as direct `.provider` / `.search_provider` attributes on runtime child objects.

The current runtime can wrap providers inside nested runtime/engine objects.
This gate therefore verifies provider injection by identity through the runtime
object graph, without depending on a specific private attribute name.

It still verifies:
- service imports live providers
- service passes live model/search providers into runtime construction
- runtime receives the supplied model sentinel
- runtime receives the supplied search sentinel

No external provider call, memory write, or external action is performed.

Expected marker:
`S36_3_1_RUNTIME_PROVIDER_WIRING_PASS`
