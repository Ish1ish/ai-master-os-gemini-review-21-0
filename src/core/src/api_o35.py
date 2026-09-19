
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
class H(BaseHTTPRequestHandler):
    service=None
    def sendj(self,c,d):
        b=json.dumps(d).encode(); self.send_response(c); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(n).decode()) if n else {}
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/approvals/pending": return self.sendj(200,{"approvals":self.service.pending()})
        if p.startswith("/approvals/"):
            a=self.service.approvals.get(p.split("/")[-1]); return self.sendj(200 if a else 404,a or {"status":"NOT_FOUND"})
        self.sendj(404,{"status":"NOT_FOUND"})
    def do_POST(self):
        p=urlparse(self.path).path; b=self.body()
        if p=="/approvals":
            a=self.service.approvals.create(b["run_id"],b["action"],b.get("payload",{}),b.get("requested_by","system"),b.get("ttl_seconds",3600))
            return self.sendj(201,a)
        if p.startswith("/approvals/") and p.endswith("/decision"):
            aid=p.split("/")[-2]
            return self.sendj(200,self.service.decide(aid,b.get("decision"),b.get("operator_id","operator"),b.get("reason","")))
        self.sendj(404,{"status":"NOT_FOUND"})
    def log_message(self,*a): pass
class O35ApprovalServer:
    def __init__(self,service,host="127.0.0.1",port=0):
        H.service=service; self.server=ThreadingHTTPServer((host,port),H)
    def start(self): self.server.serve_forever()
    def shutdown(self): self.server.shutdown(); self.server.server_close()
