from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _refs(values: Iterable[str]) -> List[str]:
    seen = set(); out=[]
    for v in values:
        v = str(v or '').strip()
        if v and v not in seen:
            seen.add(v); out.append(v)
    return out


def _matches(text: str, words: Iterable[str]) -> bool:
    low = text.lower()
    return any(w in low for w in words)


def _candidate(title: str, customer: str, problem: str, outcome: str, solution: str,
               refs: List[str], themes: List[str], evidence_summary: str,
               audience: str, constraints: List[str], category: str,
               confidence: str = 'medium') -> Dict[str, Any]:
    return {
        'opportunity_id': f'OPP-{len(refs):03d}',
        'title': title,
        'customer_segment': customer or audience,
        'problem': problem,
        'desired_outcome': outcome,
        'solution_format': solution,
        'evidence_summary': evidence_summary,
        'source_refs': _refs(refs),
        'origin_themes': _refs(themes),
        'signal_categories': [category] if category else [],
        'market_scope': 'global_signal_requires_local_validation',
        'assumptions': [
            'The stated problem is experienced by the target segment.',
            'The target buyer values the stated outcome enough to test or pay.',
            'A lightweight first version can be delivered within the stated constraints.',
        ],
        'resource_fit': 'service-first / lightweight MVP',
        'validation_test': {
            'customer_need': 'Interview or observe 10 target customers and verify the workflow problem.',
            'willingness_to_pay': 'Offer a small paid pilot or explicit pre-order before building substantial software.',
            'competition': 'Map current alternatives used by the same segment and identify the specific gap.',
            'distribution': 'Test one reachable channel before adding more acquisition channels.',
        },
        'confidence': confidence,
        'status': 'HYPOTHESIS',
        'constraints': list(constraints),
    }


def synthesize_opportunities(market_report: Dict[str, Any], audience: str = '',
                             constraints: List[str] | None = None,
                             max_candidates: int = 5) -> List[Dict[str, Any]]:
    constraints = list(constraints or [])
    findings = [f for f in (market_report.get('findings') or []) if isinstance(f, dict)]
    joined = ' '.join(_norm(f.get('statement')) for f in findings).lower()
    candidates: List[Dict[str, Any]] = []

    def add_candidate(title, customer, problem, outcome, solution, refs, themes, cats):
        refs = _refs(refs)
        if not refs or any(c['title'] == title for c in candidates):
            return
        evidence = _norm(' '.join(_norm(f.get('statement')) for f in findings if f.get('source_id') in refs))[:300]
        candidates.append(_candidate(title, customer, problem, outcome, solution, refs, themes, evidence, audience, constraints, ','.join(cats)))

    support_refs=[]; support_themes=[]
    for f in findings:
        t=_norm(f.get('statement')); sid=f.get('source_id','')
        if _matches(t, ['customer support agent','customer support','chatbot','support automation','support']) and sid:
            support_refs.append(sid); support_themes.append(f.get('finding_id',''))
    if support_refs or _matches(joined, ['customer support', 'chatbot']):
        add_candidate(
            'Productized AI customer-support setup for small businesses',
            audience,
            'Small businesses may spend too much time handling repetitive customer questions and support workflows.',
            'Faster first-line responses with human escalation for exceptions.',
            'Done-for-you setup of a lightweight FAQ/knowledge workflow with assisted responses and escalation.',
            support_refs or [f.get('source_id','') for f in findings[:2] if f.get('source_id')],
            support_themes or ['market-support-signal'],
            ['problem_to_solve','market_signal'])

    content_refs=[]; content_themes=[]
    for f in findings:
        t=_norm(f.get('statement')); sid=f.get('source_id','')
        if _matches(t, ['content repurposing','social media management','content creation']) and sid:
            content_refs.append(sid); content_themes.append(f.get('finding_id',''))
    if content_refs:
        add_candidate(
            'AI-assisted content repurposing service for small businesses',
            audience,
            'Small teams may struggle to turn existing material into consistent channel-specific content without adding significant manual work.',
            'Produce more useful social content from existing assets with lower production effort.',
            'Productized content repurposing package with templates, human review, and repeatable delivery.',
            content_refs, content_themes, ['pricing_signal','market_signal'])

    automation_refs=[]; automation_themes=[]
    for f in findings:
        t=_norm(f.get('statement')); sid=f.get('source_id','')
        if _matches(t, ['workflow automation','automate one painful workflow','automation','workflow friction']) and sid:
            automation_refs.append(sid); automation_themes.append(f.get('finding_id',''))
    if automation_refs:
        add_candidate(
            'Narrow AI workflow-automation service for small businesses',
            audience,
            'Small businesses may have one repetitive workflow that creates avoidable manual work or slow decisions.',
            'Reduce manual work and improve speed on one clearly defined workflow.',
            'Service-first workflow audit plus a lightweight AI-assisted automation for one narrow use case.',
            automation_refs, automation_themes, ['problem_to_solve','market_signal'])

    validation_refs=[]; validation_themes=[]
    for f in findings:
        t=_norm(f.get('statement')); sid=f.get('source_id','')
        if _matches(t, ['business idea validation','market validation','viability score','validate your idea','idea validator']) and sid:
            validation_refs.append(sid); validation_themes.append(f.get('finding_id',''))
    if validation_refs:
        add_candidate(
            'Productized AI business-validation research service',
            audience,
            'Early-stage founders may need faster, simpler market research and validation before committing capital.',
            'Get a structured evidence-backed opportunity brief and validation test before building.',
            'Service-led market research and validation package with evidence synthesis, competitor mapping, and a small validation experiment.',
            validation_refs, validation_themes, ['competitive_gap','market_signal'])

    low_cost_refs=[]; low_cost_themes=[]
    for f in findings:
        t=_norm(f.get('statement')); sid=f.get('source_id','')
        if _matches(t, ['virtual ai assistant','virtual assistant','low-cost','under $5,000']) and sid:
            low_cost_refs.append(sid); low_cost_themes.append(f.get('finding_id',''))
    if low_cost_refs:
        add_candidate(
            'Productized AI operations-assistant service for small businesses',
            audience,
            'Small teams may have recurring administrative tasks that consume owner time and are costly to delegate fully.',
            'Offload a narrow set of repeatable tasks with AI-assisted service delivery.',
            'Manual-first AI operations support focused on one narrow, measurable workflow.',
            low_cost_refs, low_cost_themes, ['pricing_signal'])

    if not candidates:
        refs=[f.get('source_id','') for f in findings if f.get('source_id')]
        add_candidate(
            'Focused AI-enabled service for one recurring small-business workflow',
            audience,
            'Small businesses may have recurring work that is costly or time-consuming to manage manually.',
            'Reduce effort or improve response speed on one measurable workflow.',
            'Service-first validation with a lightweight AI-assisted delivery process.',
            refs[:5], ['fallback-market-signal'], ['market_signal'])

    # Deterministic prioritization: breadth of evidence, constraint fit, specificity.
    def score(c):
        breadth = min(len(c['source_refs']), 5) / 5
        specificity = 1.0 if 'one ' in c['solution_format'].lower() or 'narrow' in c['solution_format'].lower() else 0.8
        return (breadth * 0.5) + (specificity * 0.3) + (0.2 if 'service' in c['solution_format'].lower() else 0.1)

    ranked=[]
    for c in candidates:
        c['opportunity_score']=round(score(c)*10,2)
        ranked.append(c)
    ranked.sort(key=lambda x: (-x['opportunity_score'], x['title']))
    for idx,c in enumerate(ranked,1):
        c['rank']=idx
        c['opportunity_id']=f'OPP-{idx:03d}'
    return ranked[:max_candidates]
