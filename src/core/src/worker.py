import time, uuid
class QueueWorker:
    def __init__(self,queue,service,dead_letter=None,worker_id=None,max_attempts=3,lease_seconds=60):
        self.queue=queue; self.service=service; self.dead_letter=dead_letter; self.worker_id=worker_id or f'WORKER-{uuid.uuid4().hex[:8].upper()}'; self.max_attempts=max_attempts; self.lease_seconds=lease_seconds
    def run_once(self,now=None):
        now=time.time() if now is None else now; job=self.queue.claim(self.worker_id,now,self.lease_seconds)
        if not job:return {'status':'IDLE','worker_id':self.worker_id}
        try:
            p=job['payload']; result=self.service.execute(p['job_id'],audience=p.get('audience','small businesses using AI tools'),goal=p.get('goal','validate a lean business opportunity'),constraints=p.get('constraints'),internal=True)
            if result.get('status')=='COMPLETE':
                self.queue.complete(job['job_id'],result); return {'status':'COMPLETE','job_id':job['job_id'],'attempts':job['attempts']}
            raise RuntimeError(result.get('error') or 'runtime_failed')
        except Exception as exc:
            error={'type':type(exc).__name__,'message':str(exc)}
            if job['attempts']>=self.max_attempts:
                self.queue.fail(job['job_id'],error)
                if self.dead_letter:self.dead_letter.put(job['job_id'],job['payload'],error,job['attempts'])
                return {'status':'FAILED','job_id':job['job_id'],'attempts':job['attempts']}
            retry_at=time.time()+0.05*(2**(job['attempts']-1)); self.queue.fail(job['job_id'],error,retry_at=retry_at); return {'status':'RETRY_SCHEDULED','job_id':job['job_id'],'attempts':job['attempts'],'retry_at':retry_at}
    def run_until_empty(self,max_cycles=100):
        out=[]
        for _ in range(max_cycles):
            r=self.run_once(); out.append(r)
            if r['status']=='IDLE': break
        return out
