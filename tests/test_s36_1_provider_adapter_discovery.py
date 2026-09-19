
import unittest

class TestS361ProviderAdapterDiscovery(unittest.TestCase):
    def test_inventory_script_exists(self):
        from pathlib import Path
        self.assertTrue(Path("scripts/s36_1_provider_adapter_discovery.py").exists())

    def test_windows_wrapper_exists(self):
        from pathlib import Path
        self.assertTrue(Path("scripts/windows_s36_1_provider_adapter_discovery.cmd").exists())

if __name__ == "__main__":
    unittest.main()
