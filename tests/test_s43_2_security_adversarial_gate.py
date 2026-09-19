from __future__ import annotations
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "s43_security_abuse_gate.py")], cwd=ROOT, text=True, capture_output=True)
    out = p.stdout + p.stderr
    assert p.returncode == 0 or "S43_SECURITY_ABUSE_" in out
    assert "identity_token_issue_verify_contract" in out
    assert "tenant_security_reference_present" in out
    print("S43_2_GATE_CONTRACT_TEST_PASS")

if __name__ == "__main__":
    main()
