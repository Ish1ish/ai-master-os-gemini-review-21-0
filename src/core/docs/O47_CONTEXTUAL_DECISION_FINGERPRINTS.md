# v0.6 Contextual Decision Fingerprints

The adaptive decision layer now identifies the decision context before applying historical calibration.

## Why
A project-wide calibration score can be too coarse. Two decisions inside the same project may have different action types, tools, risk classes, tenants, or evidence patterns. v0.6 keeps those contexts distinct.

## Boundary
The fingerprint layer does not execute tools, mutate external systems, or override governance. It only supplies an advisory posture and contextual evidence for later governed decisioning.

## Learned dimensions
Historical accuracy and calibration drift are exposed as descriptors. They are not part of the stable matching key because doing so would make the system match a candidate on the learned signal it is trying to estimate.
