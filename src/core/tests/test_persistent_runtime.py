import os
import tempfile
import unittest

from engines.o7.src.integration import MemoryLearningRuntime
from engines.o8.src.runtime import O8Runtime


class TestPersistentRuntime(unittest.TestCase):
    def test_memory_store_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "memory.sqlite3")
            runtime = MemoryLearningRuntime(storage_path=path)
            obj = {
                "object_type": "Lesson", "object_id": "LESSON-1", "version": "v1",
                "project_id": "P1", "summary": "test", "scope": "project", "confidence": 0.9,
            }
            runtime.store.write(obj)
            runtime.close()
            reopened = MemoryLearningRuntime(storage_path=path)
            try:
                self.assertEqual(reopened.store.latest("LESSON-1")["summary"], "test")
            finally:
                reopened.close()


    def test_memory_write_is_idempotent_for_same_version_and_payload(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "memory.sqlite3")
            runtime = MemoryLearningRuntime(storage_path=path)
            obj = {
                "object_type": "Lesson", "object_id": "LESSON-IDEMP", "version": "v1",
                "project_id": "P1", "summary": "stable lesson", "scope": "project", "confidence": "high",
                "source_refs": ["SRC-1"],
            }
            first = runtime.store.write(obj)
            second = runtime.store.write(obj)
            try:
                self.assertEqual(first, second)
                self.assertEqual(len(runtime.store.history("LESSON-IDEMP")), 1)
            finally:
                runtime.close()

    def test_memory_write_rejects_true_version_conflict(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "memory.sqlite3")
            runtime = MemoryLearningRuntime(storage_path=path)
            obj = {
                "object_type": "Lesson", "object_id": "LESSON-CONFLICT", "version": "v1",
                "project_id": "P1", "summary": "first", "scope": "project", "confidence": "high",
            }
            runtime.store.write(obj)
            conflicting = dict(obj, summary="different")
            try:
                with self.assertRaisesRegex(ValueError, "memory version conflict"):
                    runtime.store.write(conflicting)
            finally:
                runtime.close()

    def test_audit_log_persists_across_instances(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "audit.sqlite3")
            runtime = O8Runtime(audit_path=path)
            runtime.start_run("R1", "P1", "hello")
            runtime.end_run("R1", "COMPLETE")
            self.assertEqual(len(runtime.audit.for_run("R1")), 2)
            runtime.close()
            reopened = O8Runtime(audit_path=path)
            try:
                self.assertEqual(len(reopened.audit.for_run("R1")), 2)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
