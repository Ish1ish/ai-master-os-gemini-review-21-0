import unittest
from core.src.ai_runtime import AIRuntime, AIInvocationError


class TestS3651AIRuntimeLiveTextContract(unittest.TestCase):
    def test_provider_envelope_text_is_parsed_as_json(self):
        calls = []
        def provider(**kwargs):
            calls.append(kwargs)
            return {
                "provider": "live-test",
                "model": "test-model",
                "text": '{"status":"OK","value":123}',
            }
        result = AIRuntime(provider).generate_structured(system_prompt="s", user_prompt="u")
        self.assertEqual(result["data"], {"status":"OK","value":123})
        self.assertEqual(result["retry_count"], 0)
        self.assertEqual(len(calls), 1)

    def test_invalid_provider_text_retries_and_fails_closed(self):
        calls = []
        def provider(**kwargs):
            calls.append(kwargs)
            return {"provider":"live-test","model":"test-model","text":"not-json"}
        with self.assertRaises(AIInvocationError) as ctx:
            AIRuntime(provider).generate_structured(system_prompt="s", user_prompt="u")
        self.assertEqual(ctx.exception.subtype, "MALFORMED_JSON")
        self.assertEqual(len(calls), 3)

    def test_dict_text_payload_is_accepted(self):
        result = AIRuntime(lambda **kwargs: {"provider":"live-test","model":"test-model","text":{"status":"OK"}}).generate_structured(system_prompt="s", user_prompt="u")
        self.assertEqual(result["data"], {"status":"OK"})


if __name__ == "__main__":
    unittest.main()
