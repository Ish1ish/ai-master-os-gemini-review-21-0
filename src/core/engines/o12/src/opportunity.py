from __future__ import annotations
import re
from typing import Any, Dict, Iterable, List

def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())

def _refs(values: Iterable[str]) -> List[str]:
    seen=set(); out=[]
    for v in values:
        v=str(v or '').strip()
        if v and v not in seen:
            seen.add(v); out.append(v)
    return out

def _matches(text: str, words: Iterable[str]) -> bool:
    low=text.lower(); return any(w in low for w in words)

def _candidate(title, customer, problem, outcome, solution, refs, themes, evidence_summary, audience, constraints, categories, market_scope="global_signal_requires_local_validation"):

    refs=_refs(refs)
    return {
        'opportunity_id':'', 'title':title, 'customer_segment':customer or audience,
        'problem':problem, 'desired_outcome':outcome, 'solution_format':solution,
        'evidence_summary':evidence_summary[:300], 'source_refs':refs,
        'origin_themes':_refs(themes), 'signal_categories':_refs(categories),
        'market_scope':market_scope,
        'assumptions':[
            'The stated problem is experienced by the target segment.',
            'The target buyer values the stated outcome enough to test or pay.',
            'A lightweight first version can be delivered within the stated constraints.'
        ],
        'resource_fit':'service-first / lightweight MVP',
        'validation_test':{
            'customer_need':'Interview or observe 10 target customers and verify the workflow problem.',
            'willingness_to_pay':'Offer a small paid pilot or explicit pre-order before building substantial software.',
            'competition':'Map current alternatives used by the same segment and identify the specific gap.',
            'distribution':'Test one reachable channel before adding more acquisition channels.'
        },
        'confidence':'medium', 'status':'HYPOTHESIS', 'constraints':list(constraints)
    }

def synthesize_opportunities(market_report: Dict[str, Any], audience: str = '', constraints: List[str] | None = None, max_candidates: int = 5):
    constraints=list(constraints or [])
    findings=[f for f in (market_report.get('findings') or []) if isinstance(f,dict)]
    candidates=[]
    market_scope = str(market_report.get('evidence_boundary') or "global_signal_requires_local_validation")
    local_source_count = int(market_report.get('local_source_count', 0) or 0)
    def add(title, problem, outcome, solution, terms, categories):
        matches=[f for f in findings if _matches(_norm(f.get('statement')),terms) and f.get('source_id')]
        refs=_refs([f.get('source_id') for f in matches]); themes=_refs([f.get('finding_id') for f in matches])
        if not refs: return
        evidence=_norm(' '.join(_norm(f.get('statement')) for f in matches))
        candidates.append(_candidate(title,audience,problem,outcome,solution,refs,themes,evidence,audience,constraints,categories,market_scope=market_scope))
        candidates[-1]["local_evidence_count"] = local_source_count
    add('Productized AI customer-support setup for small businesses',
        'Small businesses may spend too much time handling repetitive customer questions and support workflows.',
        'Faster first-line responses with human escalation for exceptions.',
        'Done-for-you setup of a lightweight FAQ/knowledge workflow with assisted responses and escalation.',
        ['customer support agent','customer support','chatbot','support automation'], ['problem_to_solve','market_signal'])
    add('AI-assisted content repurposing service for small businesses',
        'Small teams may struggle to turn existing material into consistent channel-specific content without adding significant manual work.',
        'Produce more useful social content from existing assets with lower production effort.',
        'Productized content repurposing package with templates, human review, and repeatable delivery.',
        ['content repurposing','social media management','content creation'], ['pricing_signal','market_signal'])
    add('Narrow AI workflow-automation service for small businesses',
        'Small businesses may have one repetitive workflow that creates avoidable manual work or slow decisions.',
        'Reduce manual work and improve speed on one clearly defined workflow.',
        'Service-first workflow audit plus a lightweight AI-assisted automation for one narrow use case.',
        ['workflow automation','automate one painful workflow','workflow friction','automation'], ['problem_to_solve','market_signal'])
    add('Productized AI business-validation research service',
        'Early-stage founders may need faster, simpler market research and validation before committing capital.',
        'Get a structured evidence-backed opportunity brief and validation test before building.',
        'Service-led market research and validation package with evidence synthesis, competitor mapping, and a small validation experiment.',
        ['business idea validation','market validation','viability score','validate your idea','idea validator'], ['competitive_gap','market_signal'])
    add('Productized AI operations-assistant service for small businesses',
        'Small teams may have recurring administrative tasks that consume owner time and are costly to delegate fully.',
        'Offload a narrow set of repeatable tasks with AI-assisted service delivery.',
        'Manual-first AI operations support focused on one narrow, measurable workflow.',
        ['virtual ai assistant','virtual assistant','low-cost','under $5,000'], ['pricing_signal'])
    if not candidates:
        refs=_refs([f.get('source_id') for f in findings if f.get('source_id')])[:5]
        if refs:
            candidates.append(_candidate(
                'Focused AI-enabled service for one recurring small-business workflow', audience,
                'Small businesses may have recurring work that is costly or time-consuming to manage manually.',
                'Reduce effort or improve response speed on one measurable workflow.',
                'Service-first validation with a lightweight AI-assisted delivery process.', refs, ['fallback-market-signal'],
                'Current evidence indicates recurring low-cost AI service opportunities, but the local problem still requires validation.', audience, constraints, ['market_signal'], market_scope=market_scope))
    def score(c):
        breadth=min(len(c['source_refs']),5)/5
        specific=1.0 if ('one ' in c['solution_format'].lower() or 'narrow' in c['solution_format'].lower()) else .8
        return round(10*(breadth*.5 + specific*.3 + (.2 if 'service' in c['solution_format'].lower() else .1)),2)
    for c in candidates: c['opportunity_score']=score(c)
    candidates.sort(key=lambda c:(-c['opportunity_score'], c['title']))
    for i,c in enumerate(candidates[:max_candidates],1):
        c['rank']=i; c['opportunity_id']=f'OPP-{i:03d}'
    return candidates[:max_candidates]
