from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "src" / "core" / "scripts" / "windows_21_1_regression_gate.cmd"


def test_patch16_gate_targets_21_1_surfaces():
    text = GATE.read_text(encoding="utf-8")

    for marker in (
        "python -m pytest -q tests",
        'pushd "%ROOT%\\node_bff"',
        "call npm test",
        "python -m compileall -q src tests",
        "ALL 21.1 REGRESSION GATE CHECKS PASSED.",
    ):
        assert marker in text


def test_patch16_gate_does_not_delegate_to_legacy_o40_gate():
    text = GATE.read_text(encoding="utf-8").lower()

    for legacy_marker in (
        "windows_final_release_gate.cmd",
        "unittest discover",
        "all o40 windows final release checks passed.",
    ):
        assert legacy_marker not in text
