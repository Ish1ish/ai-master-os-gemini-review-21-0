from __future__ import annotations
import json,sqlite3
from .strategy_adaptation_intelligence import StrategyAdaptationContext

class StrategyAdaptationStore:
    def __init__(self,path):
        self.path=path
        self._initialize()
    def _connect(self): return sqlite3.connect(self.path)
    def _initialize(self):
        c=self._connect()
        try:
            c.execute("create table if not exists strategy_adaptation_contexts (adaptation_id text primary key, project_id text not null, strategy_id text not null, payload text not null)")
            c.commit()
        finally: c.close()
    def record(self,ctx:StrategyAdaptationContext):
        payload=json.dumps(ctx.to_dict(),sort_keys=True,separators=(",",":"))
        c=self._connect()
        try:
            row=c.execute("select payload from strategy_adaptation_contexts where adaptation_id=?",(ctx.adaptation_id,)).fetchone()
            if row:
                if row[0]!=payload: raise ValueError("adaptation_id conflict")
                return ctx
            c.execute("insert into strategy_adaptation_contexts(adaptation_id,project_id,strategy_id,payload) values(?,?,?,?)",(ctx.adaptation_id,ctx.project_id,ctx.strategy_id,payload))
            c.commit(); return ctx
        finally: c.close()
    def get(self,adaptation_id):
        c=self._connect()
        try:
            row=c.execute("select payload from strategy_adaptation_contexts where adaptation_id=?",(adaptation_id,)).fetchone()
            return None if not row else json.loads(row[0])
        finally: c.close()
    def list_project(self,project_id):
        c=self._connect()
        try:
            rows=c.execute("select payload from strategy_adaptation_contexts where project_id=? order by adaptation_id",(project_id,)).fetchall()
            return [json.loads(r[0]) for r in rows]
        finally: c.close()
