import json
import unittest
from pathlib import Path


class TestSchema(unittest.TestCase):
    def test_schema(self):
        p = Path(__file__).resolve().parents[1] / "schemas" / "tenant_isolation_v1.json"
        o = json.loads(p.read_text(encoding="utf-8"))
        self.assertIn("tenant_id", o["required"])
        self.assertIn("project_id", o["required"])
        self.assertIn("owner_principal_id", o["required"])
        self.assertFalse(o["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
