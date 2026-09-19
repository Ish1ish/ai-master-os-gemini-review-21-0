
import sqlite3, os, json, uuid
from datetime import datetime, timezone, timedelta

class ApprovalStore:
    def __init__(self,path):
        self.path=path; os.makedirs(os.path.dirname(os.path.abspath(path)),exist_ok=True)
        self.conn=sqlite3.connect(path,check_same_thread=False)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS approvals(
        approval_id TEXT PRIMARY KEY, run_id TEXT, action TEXT, payload TEXT, status TEXT,
        requested_by TEXT, decided_by TEXT, decision_reason TEXT, created_at TEXT, expires_at TEXT, decided_at TEXT)""")
        self.conn.commit()
    def create(self,run_id,action,payload,requested_by="system",ttl_seconds=3600):
        now=datetime.now(timezone.utc); exp=now+timedelta(seconds=ttl_seconds)
        aid="APR-"+uuid.uuid4().hex[:12].upper()
        self.conn.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (aid,run_id,action,json.dumps(payload or {}),"PENDING",requested_by,None,None,now.isoformat(),exp.isoformat(),None))
        self.conn.commit(); return self.get(aid)
    def get(self,aid):
        r=self.conn.execute("SELECT * FROM approvals WHERE approval_id=?",(aid,)).fetchone()
        if not r:return None
        keys=["approval_id","run_id","action","payload","status","requested_by","decided_by","decision_reason","created_at","expires_at","decided_at"]
        d=dict(zip(keys,r)); d["payload"]=json.loads(d["payload"])
        if d["status"]=="PENDING" and datetime.now(timezone.utc)>=datetime.fromisoformat(d["expires_at"]):
            self.conn.execute("UPDATE approvals SET status='EXPIRED',decision_reason='approval_expired',decided_at=? WHERE approval_id=? AND status='PENDING'",
                              (datetime.now(timezone.utc).isoformat(),aid)); self.conn.commit(); d["status"]="EXPIRED"
        return d
    def decide(self,aid,decision,operator_id,reason=""):
        if decision not in {"APPROVED","REJECTED"}: raise ValueError("invalid decision")
        cur=self.get(aid)
        if not cur:return {"status":"NOT_FOUND","approval_id":aid}
        if cur["status"]!="PENDING":return {"status":"CONFLICT","current_status":cur["status"],"approval_id":aid}
        self.conn.execute("UPDATE approvals SET status=?,decided_by=?,decision_reason=?,decided_at=? WHERE approval_id=? AND status='PENDING'",
                          (decision,operator_id,reason,datetime.now(timezone.utc).isoformat(),aid)); self.conn.commit()
        return self.get(aid)
    def for_run(self,run_id):
        ids=[r[0] for r in self.conn.execute("SELECT approval_id FROM approvals WHERE run_id=? ORDER BY created_at",(run_id,))]
        return [self.get(a) for a in ids]
    def pending(self): return [self.get(r[0]) for r in self.conn.execute("SELECT approval_id FROM approvals WHERE status='PENDING' ORDER BY created_at")]
    def close(self): self.conn.close()
