import unittest
from pathlib import Path

class TestS362RealProviderStaging(unittest.TestCase):
    def test_gate_exists(self):
        self.assertTrue(Path("scripts/s36_2_real_provider_staging_gate.py").exists())

    def test_wrapper_exists(self):
        self.assertTrue(Path("scripts/windows_s36_2_real_provider_staging_gate.cmd").exists())

if __name__ == "__main__":
    unittest.main()
