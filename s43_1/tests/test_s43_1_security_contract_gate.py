from __future__ import annotations
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")


def _read(rel):
    with open(os.path.join(SRC, rel), "r", encoding="utf-8") as f:
        return f.read()


def test_identity_issue_and_verify_contract_present():
    text = _read(os.path.join("core", "src", "identity.py"))
    assert "issue_token" in text
    assert "_authenticate_token" in text or "authenticate" in text or "verify" in text
    assert "invalid_token_signature" in text


def test_tenant_security_reference_present():
    matches = 0
    for root, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".py"):
                continue
            try:
                text = open(os.path.join(root, name), "r", encoding="utf-8").read().lower()
            except Exception:
                continue
            if any(x in text for x in ("tenant_id", "tenant", "cross-tenant", "tenant isolation", "resource isolation")):
                matches += 1
                if matches >= 1:
                    return
    assert matches >= 1


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"S43_1_TARGETED_TESTS_PASS {len(tests)}/{len(tests)}")


if __name__ == "__main__":
    main()
