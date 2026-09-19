import unittest
from pathlib import Path
class TestS365(unittest.TestCase):
    def test_gate_exists(self):
        self.assertTrue((Path(__file__).resolve().parents[1]/"scripts/s36_5_provider_evidence_integrity_gate.py").is_file())
    def test_secret_safe(self):
        t=(Path(__file__).resolve().parents[1]/"scripts/s36_5_provider_evidence_integrity_gate.py").read_text(encoding="utf-8")
        for x in ["AI_OS_MODEL_API_KEY","AI_OS_SEARCH_API_KEY","OPENROUTER_API_KEY","TAVILY_API_KEY"]:
            self.assertNotIn(x,t)
if __name__=="__main__": unittest.main()
