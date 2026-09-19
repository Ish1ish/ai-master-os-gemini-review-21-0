from .events import EventNormalizer
from .kpis import KPIEngine
from .funnel import FunnelAnalyzer
from .experiments import ExperimentAnalyzer
from .diagnosis import BottleneckDiagnoser
from .attribution import AttributionEngine
from .learning import AnalyticsLearning
from .qa import validate_analytics_output

class RealAnalyticsEngine:
    def __init__(self):
        self.events=EventNormalizer()
        self.kpis=KPIEngine()
        self.funnel=FunnelAnalyzer()
        self.experiments=ExperimentAnalyzer()
        self.diagnoser=BottleneckDiagnoser()
        self.attribution=AttributionEngine()
        self.learning=AnalyticsLearning()

    def analyze(self, raw_events, funnel_stages, experiment_inputs=None, revenue=0.0, customers=0, automation_handoff=None):
        events=self.events.normalize_many(raw_events)
        event_types={}
        for e in events:
            event_types[e["event_type"]]=event_types.get(e["event_type"],0)+1

        kpis={
            "awareness_to_intent":self.kpis.funnel_rate(events,"content_view","qualified_lead"),
            "intent_to_conversion":self.kpis.funnel_rate(events,"qualified_lead","purchase"),
            "retention":self.kpis.retention_rate(
                sum(1 for e in events if e["event_type"]=="signup"),
                sum(1 for e in events if e["event_type"]=="retained_user"),
            ),
            "revenue_per_customer":self.kpis.revenue_per_customer(revenue,customers),
        }

        funnel=self.funnel.analyze(events,funnel_stages)
        exps=[]
        for x in experiment_inputs or []:
            exps.append(self.experiments.compare(
                x["name"], x["control"], x["variant"], x["metric"], x.get("higher_is_better",True)
            ))
        diagnosis=self.diagnoser.diagnose(funnel,exps)
        attribution=self.attribution.summarize(events)
        learning=self.learning.build_learning(diagnosis,exps)

        out={
            "status":"DRAFT",
            "engine_id":"E-12",
            "engine_version":"O21-v1.0",
            "event_summary":{"total_events":len(events),"event_types":event_types},
            "kpis":kpis,
            "funnel":funnel,
            "experiments":exps,
            "diagnosis":diagnosis,
            "attribution":attribution,
            "learning":learning,
            "unsafe_claims":[],
            "automation_to_analytics_handoff": automation_handoff or {},
        }
        qa=validate_analytics_output(out)
        out["qa"]=qa
        out["status"]="COMPLETE" if qa["status"]=="PASS" else "FAILED"
        return out
