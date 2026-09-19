import os
import tempfile
import unittest

from core.src.auth import Authenticator
from core.src.service import ApplicationService


class AuthHardeningTests(unittest.TestCase):
    def setUp(self):
        self.old_env = dict(os.environ)
        os.environ["AI_OS_ENV"] = "local"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)

    def test_default_authenticator_fails_closed(self):
        result = Authenticator().authenticate(None)
        self.assertEqual(result["status"], "UNAUTHENTICATED")
        self.assertEqual(result["reason"], "authenticator_not_configured")

    def test_explicit_local_bypass(self):
        result = Authenticator(allow_local_bypass=True).authenticate(None)
        self.assertEqual(result["status"], "BYPASS_FOR_LOCAL")
        self.assertEqual(result["principal"], "local-dev")

    def test_production_without_verifier_fails_closed(self):
        result = Authenticator(production=True).authenticate(None)
        self.assertEqual(result["status"], "UNAUTHENTICATED")
        self.assertEqual(result["reason"], "production_authenticator_not_configured")

    def test_local_application_service_uses_explicit_local_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(db_path=os.path.join(td, "jobs.sqlite3"))
            try:
                self.assertIsInstance(service.auth, Authenticator)
                self.assertTrue(service.auth.allow_local_bypass)
                self.assertEqual(service.auth.authenticate(None)["status"], "BYPASS_FOR_LOCAL")
                gate = service._authorize(None, "submit", "run:submit")
                self.assertEqual(gate["status"], "ALLOW")
            finally:
                service.close()

    def test_production_application_service_without_authenticator_fails_closed(self):
        old_env = dict(os.environ)
        os.environ["AI_OS_ENV"] = "production"
        try:
            with tempfile.TemporaryDirectory() as td:
                service = ApplicationService(
                    db_path=os.path.join(td, "jobs.sqlite3"),
                    runtime=object(),
                    authenticator=None,
                )
                try:
                    self.assertIsInstance(service.auth, Authenticator)
                    self.assertTrue(service.auth.production)
                    result = service._authorize(None, "submit", "run:submit")
                    self.assertEqual(result["status"], "UNAUTHORIZED")
                    self.assertEqual(
                        result["auth"]["reason"],
                        "production_authenticator_not_configured",
                    )
                finally:
                    service.close()
        finally:
            os.environ.clear()
            os.environ.update(old_env)


if __name__ == "__main__":
    unittest.main()
