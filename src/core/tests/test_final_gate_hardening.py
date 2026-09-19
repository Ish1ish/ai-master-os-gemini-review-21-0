import json
import os
import tempfile
import unittest
from pathlib import Path

from src.runtime_adapter import RuntimeAdapter


class TestFinalGateHardening(unittest.TestCase):
    def test_runtime_adapter_close_is_idempotent(self):
        # This lifecycle test must be deterministic regardless of the caller's
        # shell environment. Production provider selection is exercised by the
        # dedicated O38 security tests; this test intentionally uses the local
        # fake-provider runtime.
        previous = os.environ.get("AI_OS_ENV")
        try:
            os.environ["AI_OS_ENV"] = "local"
            with tempfile.TemporaryDirectory() as td:
                adapter = RuntimeAdapter(td)
                adapter.close()
                adapter.close()
        finally:
            if previous is None:
                os.environ.pop("AI_OS_ENV", None)
            else:
                os.environ["AI_OS_ENV"] = previous

    def test_evaluation_entrypoint_creates_report(self):
        # This is intentionally a subprocess so ResourceWarning is observed at process exit.
        import subprocess, sys
        root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        env["PYTHONWARNINGS"] = "error::ResourceWarning"
        proc = subprocess.run([sys.executable, "run_evaluation.py"], cwd=root, env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        self.assertTrue((root / "reports" / "O29_release_evaluation.json").exists())


if __name__ == "__main__":
    unittest.main()
