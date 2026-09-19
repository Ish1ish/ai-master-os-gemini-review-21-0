# AI Master OS — O42 Validation & Evidence Loop v1.0.0

O42 is the next layer after O41.4 Decision Surface Integrity.

It turns a decision recommendation into a durable validation experiment, accepts measured evidence, evaluates it deterministically, stores the conclusion and learning, and exposes the cycle for re-run.

## Core loop

`Hypothesis → Experiment → Evidence → Evaluate → GO / REFINE / NO-GO → Learn → Remember → Re-run`

## Verification
Run:

```cmd
cd /d "PROJECT_PATH"
set PYTHONPATH=%CD%
set PYTHONWARNINGS=error::ResourceWarning
python -m unittest discover -s tests -p "test_*.py" -v
```

O42 intentionally keeps consequential actions behind the existing human gate.
