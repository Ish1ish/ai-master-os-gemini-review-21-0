# 21.0 S2 O42 Confidence Contract Fix

The first S2 integration test incorrectly expected the zero-sample O42 confidence
to be the string `low`. The authoritative O42 implementation returns numeric
`0.0` on the zero-sample early exit. This patch updates only the integration test
to preserve the existing O42 output contract; runtime code is unchanged.
