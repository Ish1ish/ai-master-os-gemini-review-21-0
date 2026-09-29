import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.s36_4_live_provider_service_execution_gate import _configuration_flags


class TestS364LiveProviderServiceExecution(unittest.TestCase):
    def test_gate_exists(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "s36_4_live_provider_service_execution_gate.py"
        self.assertTrue(path.is_file())

    def test_configuration_flags_match_required_environment_shape(self):
        with patch.dict(os.environ, {
            "AI_OS_MODEL_BASE_URL": "set",
            "AI_OS_MODEL_API_KEY": "set",
            "AI_OS_MODEL_NAME": "set",
            "AI_OS_SEARCH_BASE_URL": "set",
            "AI_OS_SEARCH_API_KEY": "set",
        }, clear=False):
            model_configured, search_configured = _configuration_flags()
        self.assertTrue(model_configured)
        self.assertTrue(search_configured)

        with patch.dict(os.environ, {"AI_OS_MODEL_NAME": ""}, clear=False):
            model_configured, search_configured = _configuration_flags()
        self.assertFalse(model_configured)
        self.assertTrue(search_configured)

    def test_gate_is_secret_safe(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "s36_4_live_provider_service_execution_gate.py"
        text = path.read_text(encoding="utf-8")
        forbidden = [
            "AI_OS_MODEL_API_KEY",
            "AI_OS_SEARCH_API_KEY",
            "OPENROUTER_API_KEY",
            "TAVILY_API_KEY",
        ]
        for token_name in forbidden:
            self.assertNotIn(token_name + "\")] =", text)
            self.assertNotIn("print(" + token_name, text)


if __name__ == "__main__":
    unittest.main()
