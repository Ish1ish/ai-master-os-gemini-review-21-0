#!/usr/bin/env python3
"""Local console server with a same-origin /api reverse proxy for O38."""
from __future__ import annotations

import argparse
import http.client
import http.server
import os
import re
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui"
EXECUTE_PATH = re.compile(r"^/api/runs/([^/]+)/execute$")
EXECUTOR = ThreadPoolExecutor(max_workers=int(os.getenv("AI_OS_CONSOLE_EXECUTE_WORKERS", "4")))



BRIDGE_PATH = '/api/strategy/adaptation'

def _load_strategy_feedback(project_id: str, strategy_id: str):
    """Read-only bridge over the v1.9 strategy_feedback store. Never writes state."""
    candidates=[]
    env=os.getenv('AI_OS_STRATEGY_FEEDBACK_DB','').strip()
    if env: candidates.append(Path(env))
    configured_root=os.getenv('AI_OS_PROJECT_ROOT','').strip()
    project_candidates=([Path(configured_root)] if configured_root else []) + [ROOT, ROOT.parent, ROOT.parent.parent, ROOT.parent.parent.parent]
    for project_root in project_candidates:
        candidates.append(project_root / 'data' / 'strategy_feedback.sqlite3')
    for db in candidates:
        if not db.exists(): continue
        try:
            con=sqlite3.connect(str(db), timeout=2)
            try:
                row=con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='strategy_feedback'").fetchone()
                if not row: continue
                rows=con.execute('SELECT payload FROM strategy_feedback ORDER BY feedback_id').fetchall()
                out=[]
                for (raw,) in rows:
                    try: payload=json.loads(raw) if isinstance(raw,str) else raw
                    except Exception: continue
                    if not isinstance(payload,dict): continue
                    if payload.get('project_id')!=project_id: continue
                    if payload.get('selected_strategy_id')!=strategy_id: continue
                    out.append(payload)
                return db, out
            finally:
                con.close()
        except Exception:
            continue
    return None, []

def _build_adaptation_payload(query):
    project_id=(query.get('project_id',['PROJ-001'])[0] or 'PROJ-001').strip()
    strategy_id=(query.get('strategy_id',['A'])[0] or 'A').strip()
    db, feedback=_load_strategy_feedback(project_id,strategy_id)
    if not feedback:
        return {'status':'NO_FEEDBACK_DATA','project_id':project_id,'strategy_id':strategy_id,'message':'No strategy feedback records are exposed by the current local API bridge.'}
    try:
        import sys
        configured_root=os.getenv('AI_OS_PROJECT_ROOT','').strip()
        project_roots=([Path(configured_root)] if configured_root else []) + [ROOT, ROOT.parent, ROOT.parent.parent, ROOT.parent.parent.parent]
        source_root=next((r for r in project_roots if (r/'src'/'strategy_adaptation_intelligence.py').exists()), None)
        if source_root is None:
            return {'status':'UNAVAILABLE','project_id':project_id,'strategy_id':strategy_id,'message':'Strategy adaptation runtime is not available in the current UI package.'}
        if str(source_root) not in sys.path: sys.path.insert(0,str(source_root))
        from src.strategy_adaptation_intelligence import StrategyAdaptationIntelligence
        context=StrategyAdaptationIntelligence().build(project_id=project_id,strategy_id=strategy_id,feedback_items=feedback,adaptive_posture='NORMAL')
        payload=context.to_dict() if hasattr(context,'to_dict') else dict(context)
        return {'status':'OK','source_db':str(db),'context':payload}
    except Exception as exc:
        return {'status':'UNAVAILABLE','project_id':project_id,'strategy_id':strategy_id,'message':f'{type(exc).__name__}: {exc}'}

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, api_target: str, **kwargs):
        self.api_target = api_target.rstrip("/")
        super().__init__(*args, directory=str(UI_ROOT), **kwargs)

    def _read_request_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length) if length else None

    def _request_headers(self):
        headers = {k: v for k, v in self.headers.items() if k.lower() not in {"host", "content-length", "connection"}}
        headers["Host"] = urlsplit(self.api_target).netloc
        return headers

    def _proxy_sync(self, path, body, headers, timeout):
        target = urlsplit(self.api_target)
        conn = http.client.HTTPConnection(target.hostname, target.port or 80, timeout=timeout)
        try:
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, resp.getheaders(), data
        finally:
            conn.close()

    def _write_response(self, status, response_headers, data):
        self.send_response(status)
        for key, value in response_headers:
            if key.lower() in {"transfer-encoding", "connection", "server", "date", "content-length"}:
                continue
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _background_execute(self, path, body, headers, timeout, job_id):
        try:
            status, _, data = self._proxy_sync(path, body, headers, timeout)
            print(f"[console] async execute complete job={job_id} upstream_status={status} bytes={len(data)}")
        except Exception as exc:
            print(f"[console] async execute error job={job_id} error={type(exc).__name__}:{exc}")

    def _proxy(self):
        proxy_timeout = float(os.getenv("AI_OS_CONSOLE_PROXY_TIMEOUT", "300"))
        body = self._read_request_body()
        headers = self._request_headers()
        path = self.path[len("/api") :] or "/"
        match = EXECUTE_PATH.match(self.path)
        if self.command == "POST" and match:
            job_id = match.group(1)
            EXECUTOR.submit(self._background_execute, path, body, headers, proxy_timeout, job_id)
            payload = (f'{{"status":"EXECUTION_ACCEPTED","job_id":"{job_id}"}}').encode("utf-8")
            self._write_response(202, [("Content-Type", "application/json")], payload)
            return
        status, response_headers, data = self._proxy_sync(path, body, headers, proxy_timeout)
        self._write_response(status, response_headers, data)

    def do_GET(self):
        if self.path.startswith(BRIDGE_PATH):
            parsed=urlsplit(self.path)
            payload=json.dumps(_build_adaptation_payload(parse_qs(parsed.query)),ensure_ascii=False).encode('utf-8')
            return self._write_response(200,[('Content-Type','application/json; charset=utf-8')],payload)
        if self.path.startswith("/api/") or self.path == "/api":
            return self._proxy()
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") or self.path == "/api":
            return self._proxy()
        self.send_error(405)

    def log_message(self, fmt, *args):
        print(f"[console] {self.address_string()} - {fmt % args}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8090)
    p.add_argument("--api", default=os.getenv("AI_OS_CONSOLE_API", "http://127.0.0.1:8080"))
    args = p.parse_args()

    def factory(*a, **kw):
        return Handler(*a, api_target=args.api, **kw)

    server = http.server.ThreadingHTTPServer((args.host, args.port), factory)
    print(f"AI Master OS Console: http://{args.host}:{args.port}")
    print(f"API proxy target: {args.api}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
