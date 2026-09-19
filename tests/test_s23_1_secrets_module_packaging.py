import importlib
import unittest


class TestS23_1StdlibSecretsPackaging(unittest.TestCase):
    def test_stdlib_secrets_is_not_shadowed(self):
        mod = importlib.import_module("secrets")
        self.assertTrue(hasattr(mod, "token_hex"))

    def test_o36_identity_issue_token_works_with_project_package(self):
        from core.src.auth import build_default_production_authenticator
        identity = build_default_production_authenticator()[1]
        token = identity.issue_token("operator-01", now=1_700_000_000)["token"]
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 50)
        self.assertIn(".", token)

    def test_o36_authenticator_exposes_normalized_authenticated_contract(self):
        from core.src.auth import build_default_production_authenticator
        authenticator, identity = build_default_production_authenticator()
        token = identity.issue_token("operator-01")["token"]
        result = authenticator.authenticate({"bearer_token": token})
        self.assertEqual(result["status"], "ALLOW")
        self.assertIs(result["authenticated"], True)
        self.assertEqual(result["principal"], "operator-01")
        self.assertEqual(result["auth_method"], "signed-bearer")


if __name__ == "__main__":
    unittest.main()
