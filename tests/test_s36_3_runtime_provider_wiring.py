
import unittest
from pathlib import Path

class TestS363RuntimeProviderWiring(unittest.TestCase):
    def test_gate_exists(self):
        self.assertTrue(Path("scripts/s36_3_runtime_provider_wiring_gate.py").exists())

    def test_wrapper_exists(self):
        self.assertTrue(Path("scripts/windows_s36_3_runtime_provider_wiring_gate.cmd").exists())

if __name__ == "__main__":
    unittest.main()
