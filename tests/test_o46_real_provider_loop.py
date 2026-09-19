from core.src.real_provider_governed_autonomous_loop import RealProviderGovernedAutonomousLoop
from core.src.multi_dimensional_resource_governor import ResourceLimits

def model_stub(prompt):
    import json
    payload=json.loads(prompt)
    if payload['task'].startswith('Return JSON only with fields decision'):
        return {'text':json.dumps({'decision':'PROCEED_WITH_BOUNDED_VALIDATION','rationale':'stub'})}
    return {'text':json.dumps({'status':'SUCCESS','result':'bounded'})}

def search_stub(query):
    return {'results':[{'title':'stub evidence','url':'stub://evidence-1','snippet':'evidence'}]}

def main():
    loop=RealProviderGovernedAutonomousLoop(
        model_fn=model_stub, search_fn=search_stub,
        limits=ResourceLimits(max_time_ms=5000,max_provider_calls=8,max_retry_attempts=2,max_concurrency=1,max_cycles=2))
    result=loop.run()
    checks=[
        result.status=='PASS', result.closed_loop, result.reentered,
        len(result.cycles)==2, all(c.execution_status=='SUCCESS' for c in result.cycles),
        result.cycles[0].next_decision=='REENTER_WITH_REFRESHED_REAL_EVIDENCE',
        result.cycles[1].next_decision=='STOP_OR_REQUEST_APPROVAL',
        all(c.provider_calls==3 for c in result.cycles),
        result.external_action_executed is False,
        result.memory_write_executed is False,
        result.execution_triggered_by_reentry is False,
        result.cycles[0].evidence_hash != result.cycles[1].evidence_hash or result.cycles[0].trace_id != result.cycles[1].trace_id,
    ]
    assert len(checks)==12 and all(checks), [i for i,v in enumerate(checks,1) if not v]
    print('S60_TARGETED_TESTS_PASS 12/12')

if __name__=='__main__': main()
