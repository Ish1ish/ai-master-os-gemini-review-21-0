import unittest

from core.src.auth import build_default_production_authenticator
from core.src.rbac import RBAC


class TestPatch17ValidationAuthBoundary(unittest.TestCase):
    def test_validator_role_is_narrow_and_dedicated(self):
        scopes = RBAC().scopes_for_roles({"validator"})
        self.assertEqual(
            scopes,
            {"experiment:read", "experiment:write", "experiment:evaluate", "learning:read"},
        )

    def test_operator_and_admin_do_not_receive_validation_scopes(self):
        validator_scopes = {"experiment:read", "experiment:write", "experiment:evaluate", "learning:read"}
        self.assertTrue(validator_scopes.isdisjoint(RBAC().scopes_for_roles({"operator"})))
        self.assertTrue(validator_scopes.isdisjoint(RBAC().scopes_for_roles({"admin"})))

    def test_validator_is_registered_in_production_identity(self):
        auth, identity = build_default_production_authenticator()
        token = identity.issue_token("validator-01")["token"]
        result = auth(token)
        self.assertEqual(result["status"], "ALLOW")
        self.assertEqual(result["principal"], "validator-01")
        self.assertIn("experiment:write", result["scopes"])
        self.assertIn("experiment:evaluate", result["scopes"])
        self.assertIn("learning:read", result["scopes"])


if __name__ == "__main__":
    unittest.main()
