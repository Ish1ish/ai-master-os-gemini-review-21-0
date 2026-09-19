import unittest
from unittest.mock import patch
import os

from src.live_providers import search_provider


class TestTavilyProvider(unittest.TestCase):
    @patch.dict(os.environ, {
        "AI_OS_SEARCH_BASE_URL": "https://api.tavily.com/search",
        "AI_OS_SEARCH_API_KEY": "test-key",
        "AI_OS_REQUEST_TIMEOUT_S": "5",
    }, clear=False)
    def test_tavily_content_is_normalized_to_snippet(self):
        with patch("src.live_providers._http_json", return_value={
            "results": [
                {
                    "title": "Example",
                    "url": "https://example.org",
                    "content": "Useful evidence text",
                    "score": 0.8,
                }
            ]
        }):
            out = search_provider("AI automation")
        self.assertEqual(out["results"][0]["snippet"], "Useful evidence text")
        self.assertEqual(out["results"][0]["content"], "Useful evidence text")

    @patch.dict(os.environ, {
        "AI_OS_SEARCH_BASE_URL": "https://api.tavily.com/search",
        "AI_OS_SEARCH_API_KEY": "test-key",
    }, clear=False)
    def test_existing_snippet_is_preserved(self):
        with patch("src.live_providers._http_json", return_value={
            "results": [{"url": "https://example.org", "snippet": "Existing"}]
        }):
            out = search_provider("AI automation")
        self.assertEqual(out["results"][0]["snippet"], "Existing")


if __name__ == "__main__":
    unittest.main()
