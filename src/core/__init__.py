"""AI Master OS `core` package root.

This file makes `core.src.*` importable from clean editable and wheel
installations without manual `sys.path` manipulation at runtime.

The distribution retains the broader `core*` package surface because
legacy O23/engine components remain part of the repository and must stay
importable from packaged installations.
"""
