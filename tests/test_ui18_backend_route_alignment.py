import json
import os
import tempfile
import threading
import unittest
import sys
from pathlib import Path
from http.client import HTTPConnection

CORE_SRC = Path(__file__).resolve().parents[1] / "src" / "core"
sys.path.insert(0, str(CORE_SRC))

from core.src.api_adapter import O32APIAdapter
from core.src.http_server import O32HTTPServer
from core.src.service import ApplicationService

class TestUI18BackendRouteAlignment(unittest.TestCase):
    def test_api_exposes_list_runs(self):
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(db_path=os.path.join(td, 'jobs.sqlite3'))
            try:
                out = O32APIAdapter(service).list_runs(limit=25, credentials=None)
                self.assertEqual(out.get('status'), 'OK')
                self.assertIsInstance(out.get('runs'), list)
            finally:
                service.close()

    def test_http_get_runs_and_ready_routes_exist(self):
        with tempfile.TemporaryDirectory() as td:
            service = ApplicationService(db_path=os.path.join(td, 'jobs.sqlite3'))
            api = O32APIAdapter(service)
            server = O32HTTPServer(api, '127.0.0.1', 0, require_auth=False)
            thread = threading.Thread(target=server.start, daemon=True)
            thread.start()
            try:
                host, port = server.server.server_address
                conn = HTTPConnection(host, port, timeout=3)
                conn.request('GET', '/ready')
                ready = conn.getresponse()
                ready_body = json.loads(ready.read().decode('utf-8'))
                self.assertEqual(ready.status, 200)
                self.assertEqual(ready_body.get('status'), 'HEALTHY')
                conn.request('GET', '/runs?limit=25')
                runs = conn.getresponse()
                runs_body = json.loads(runs.read().decode('utf-8'))
                self.assertEqual(runs.status, 200)
                self.assertEqual(runs_body.get('status'), 'OK')
                self.assertIsInstance(runs_body.get('runs'), list)
                conn.close()
            finally:
                server.shutdown()
                service.close()

if __name__ == '__main__':
    unittest.main()
