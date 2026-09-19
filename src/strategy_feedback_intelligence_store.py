from __future__ import annotations
import json,sqlite3
from pathlib import Path
class StrategyFeedbackIntelligenceStore:
    def __init__(self,path):
        self.path=str(path); Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        c=sqlite3.connect(self.path)
        try:
            c.execute("CREATE TABLE IF NOT EXISTS strategy_feedback(feedback_id TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            c.commit()
        finally:
            c.close()
    def record(self,payload):
        fid=payload["feedback_id"]; raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        c=sqlite3.connect(self.path)
        try:
            row=c.execute("SELECT payload FROM strategy_feedback WHERE feedback_id=?",(fid,)).fetchone()
            if row:
                if row[0]!=raw: raise ValueError("strategy feedback id conflict")
                return json.loads(row[0])
            c.execute("INSERT INTO strategy_feedback VALUES(?,?)",(fid,raw))
            c.commit()
        finally:
            c.close()
        return json.loads(raw)
    def get(self,fid):
        c=sqlite3.connect(self.path)
        try:
            row=c.execute("SELECT payload FROM strategy_feedback WHERE feedback_id=?",(fid,)).fetchone()
            return json.loads(row[0]) if row else None
        finally:
            c.close()
