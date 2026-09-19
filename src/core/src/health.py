class HealthCheck:
    def check(self,components):
        failures=[{'component':n,'state':s} for n,s in components.items() if s not in {'UP','READY','PASS'}]
        return {'status':'HEALTHY' if not failures else 'DEGRADED','failures':failures,'components':components}
class O27Health:
    def check(self,queue,dead_letter):
        return {'status':'HEALTHY','components':{'queue':'UP','dead_letter':'UP'},'pending_jobs':len(queue.list_status('QUEUED')),'running_jobs':len(queue.list_status('RUNNING')),'dead_letters':len(dead_letter.list_all())}
