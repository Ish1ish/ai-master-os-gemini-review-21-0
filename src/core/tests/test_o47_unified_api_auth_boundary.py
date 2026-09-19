import os
import tempfile
import unittest

from core.src.unified_api import O34Handler, UnifiedAPIServer


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class _App:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def _authorize(self, credentials, action, scope):
        self.calls.append((credentials, action, scope))
        return self.result


class _Service:
    def __init__(self, result):
        self.app = _App(result)


class UnifiedAPIAuthBoundaryTests(unittest.TestCase):
    def _handler(self, service, authorization=None, require_auth=True):
        handler = object.__new__(O34Handler)
        handler.service = service
        handler.require_auth = require_auth
        handler.headers = _Headers()
        if authorization is not None:
            handler.headers["Authorization"] = authorization
        sent = []
        handler._send = lambda status, payload: sent.append((status, payload))
        return handler, sent

    def test_production_missing_bearer_is_rejected(self):
        service = _Service({"status": "UNAUTHORIZED", "reason": "signed_bearer_token_required"})
        handler, sent = self._handler(service)
        self.assertIs(handler._auth_gate("read_run", "run:read"), False)
        self.assertEqual(sent[0][0], 401)
        self.assertEqual(service.app.calls[0][0], {})

    def test_production_scope_denial_is_rejected(self):
        service = _Service({"status": "FORBIDDEN", "reason": "scope_missing", "scope": "run:submit"})
        handler, sent = self._handler(service, "Bearer token")
        self.assertIs(handler._auth_gate("submit_run", "run:submit"), False)
        self.assertEqual(sent[0][0], 403)
        self.assertEqual(service.app.calls[0][0], {"bearer_token": "token"})

    def test_authenticated_request_forwards_credentials(self):
        service = _Service({"status": "ALLOW", "auth": {"principal": "operator-01"}})
        handler, sent = self._handler(service, "Bearer token")
        credentials = handler._auth_gate("cancel_run", "run:cancel")
        self.assertEqual(credentials, {"bearer_token": "token"})
        self.assertEqual(sent, [])
        self.assertEqual(service.app.calls[0], ({"bearer_token": "token"}, "cancel_run", "run:cancel"))

    def test_local_mode_keeps_explicit_dev_bypass(self):
        service = _Service({"status": "ALLOW"})
        handler, sent = self._handler(service, require_auth=False)
        self.assertEqual(handler._auth_gate("read_run", "run:read"), {})
        self.assertEqual(service.app.calls, [])
        self.assertEqual(sent, [])

    def test_unified_server_derives_production_auth_requirement(self):
        old = os.environ.get("AI_OS_ENV")
        try:
            os.environ["AI_OS_ENV"] = "production"
            service = _Service({"status": "ALLOW"})
            server = UnifiedAPIServer(service, host="127.0.0.1", port=0)
            try:
                self.assertTrue(O34Handler.require_auth)
            finally:
                server.server.server_close()
        finally:
            if old is None:
                os.environ.pop("AI_OS_ENV", None)
            else:
                os.environ["AI_OS_ENV"] = old


if __name__ == "__main__":
    unittest.main()
