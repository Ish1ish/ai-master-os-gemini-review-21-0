import os
import tempfile
import unittest
from pathlib import Path

from scripts.backup_sqlite import backup, verify
from scripts.go_live_gate import sqlite_drill
from src.migrations import init_all

ROOT = Path(__file__).resolve().parents[1]


class TestO38GoLiveGate(unittest.TestCase):
    def test_sqlite_drill_reports_all_existing_databases_pass(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            init_all(data)
            keys = ("AI_OS_MEMORY_DB_PATH", "AI_OS_AUDIT_DB_PATH", "AI_OS_JOBS_DB_PATH", "AI_OS_ENV")
            old = {k: os.environ.get(k) for k in keys}
            try:
                os.environ["AI_OS_MEMORY_DB_PATH"] = str(data / "memory.sqlite3")
                os.environ["AI_OS_AUDIT_DB_PATH"] = str(data / "audit.sqlite3")
                os.environ["AI_OS_JOBS_DB_PATH"] = str(data / "jobs.sqlite3")
                os.environ["AI_OS_ENV"] = "production"
                results = sqlite_drill()
                self.assertEqual([r["status"] for r in results], ["PASS", "PASS", "PASS"])
            finally:
                for k, value in old.items():
                    if value is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = value

    def test_backup_verify_releases_file_handle(self):
        with tempfile.TemporaryDirectory() as td:
            data = Path(td) / "data"
            init_all(data)
            src = data / "jobs.sqlite3"
            dst = Path(td) / "jobs.backup.sqlite3"
            backup(src, dst)
            self.assertTrue(verify(dst))
            dst.unlink()
            self.assertFalse(dst.exists())

    def test_wrapper_fails_closed_on_unexpected_gate_error(self):
        text = (ROOT / "scripts" / "windows_go_live_verify_o38.cmd").read_text(encoding="utf-8")
        self.assertIn('if "%GATE_RC%"=="0"', text)
        self.assertIn('O38 GO-LIVE GATE FAILED.', text)
        self.assertNotIn('echo [3/3] Go-Live gate READY.\nexit /b 0', text)

    def test_gate_contains_sqlite_error_fallback(self):
        text = (ROOT / "scripts" / "go_live_gate.py").read_text(encoding="utf-8")
        self.assertIn('sqlite drill failed:', text)
        self.assertIn('results.append(status("backup_restore", "FAIL"', text)


if __name__ == "__main__":
    unittest.main()
