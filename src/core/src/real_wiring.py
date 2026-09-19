import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import os
from engines.o3.src.runtime import O3Runtime
from .jobs import normalize_constraints
from .handoff_contracts import (
    build_market_to_idea_handoff,
    build_idea_to_strategy_handoff,
    build_strategy_to_product_handoff,
    build_product_to_brand_handoff,
    build_brand_to_content_handoff,
    build_content_to_visual_handoff,
    build_visual_to_marketing_handoff,
    build_marketing_to_sales_handoff,
    build_sales_to_automation_handoff,
    build_automation_to_analytics_handoff,
    build_analytics_to_approval_handoff,
    build_approval_to_memory_handoff,
    build_memory_to_monitoring_handoff,
    validate_semantic_handoff,
    validate_handoff_chain,
)
from engines.o10.src.engine import RealPromptEngine
from engines.o11.src.engine import RealMarketIntelligenceEngine
from engines.o12.src.engine import RealIdeaEngine
from engines.o13.src.engine import RealStrategyEngine
from engines.o14.src.engine import RealProductEngine
from engines.o15.src.engine import RealBrandEngine
from engines.o16.src.engine import RealContentEngine
from engines.o17.src.engine import RealVisualDesignEngine
from engines.o18.src.engine import RealMarketingEngine
from engines.o19.src.engine import RealSalesEngine
from engines.o20.src.engine import RealAutomationEngine
from engines.o21.src.engine import RealAnalyticsEngine
from engines.o5.src.controller import ApprovalController
from engines.o7.src.integration import MemoryLearningRuntime
from engines.o8.src.runtime import O8Runtime
from .providers import fake_model_provider, fake_search_provider
from .localization import build_arabic_decision_summary, build_decision_surface


def _build_execution_outcome_contract(approval):
    """Expose the consequential-action outcome without changing legacy run status."""
    approval_status = str((approval or {}).get("status") or "UNKNOWN").upper()
    if approval_status == "PENDING":
        execution_status = "AWAITING_APPROVAL"
    elif approval_status == "APPROVED":
        execution_status = "RELEASED"
    elif approval_status == "REJECTED":
        execution_status = "REJECTED"
    else:
        execution_status = approval_status
    return {
        "execution_status": execution_status,
        "approval_status": approval_status,
        "external_action_executed": False,
    }
from .context_firewall import (
    market_context_for_strategy, strategy_context_for_product, product_context_for_brand,
    brand_context_for_content, content_context_for_visual, visual_context_for_marketing,
    marketing_context_for_sales, sales_context_for_automation, automation_context_for_analytics,
)

class O23Runtime:
    def __init__(self, model_provider=fake_model_provider, search_provider=fake_search_provider,
                 memory_path=None, audit_path=None):
        self.knowledge=O3Runtime(os.path.join(os.path.dirname(os.path.dirname(__file__)),"knowledge"))
        self.prompt=RealPromptEngine(provider=model_provider)
        self.market=RealMarketIntelligenceEngine(search_provider=search_provider)
        self.ideas=RealIdeaEngine()
        self.strategy=RealStrategyEngine()
        self.product=RealProductEngine()
        self.brand=RealBrandEngine()
        self.content=RealContentEngine()
        self.visual=RealVisualDesignEngine()
        self.marketing=RealMarketingEngine()
        self.sales=RealSalesEngine()
        self.automation=RealAutomationEngine()
        self.analytics=RealAnalyticsEngine()
        self.approvals=ApprovalController()
        self._approval_requester=None
        self.memory=MemoryLearningRuntime(storage_path=memory_path)
        self.monitoring=O8Runtime(audit_path=audit_path)

    def set_approval_requester(self, requester):
        self._approval_requester = requester

    def run(self, run_id, project_id, request,
            audience="small businesses using AI tools",
            goal="validate a lean business opportunity",
            constraints=None, language="en"):
        constraints=normalize_constraints(constraints) or ["low startup cost","simple MVP"]

        knowledge=self.knowledge.execute_engine(
            "E-02",request,{"audience":audience,"goal":goal,"scope":"global"}
        )

        try:
            prompt=self.prompt.execute(
                task=f"Prepare a market research prompt for: {request}",
                role="senior market research analyst",
                context="O23 real engine wiring validation.",
                objective=goal,
                audience=audience,
                tone="clear and evidence-led",
                output_format="structured research brief",
                constraints=["Do not fabricate sources",*constraints],
                knowledge_refs=knowledge["execution_contract"]["knowledge_ids"],
                task_type="research"
            )
        except Exception as exc:
            return {
                "status":"FAILED", "run_id":run_id,
                "failed_stage":"prompt",
                "error": {"type": type(exc).__name__, "reason":"model_provider_failure"},
            }

        market=self.market.research(
            request=request,goal=goal,
            dimensions=["customer_problem","competitor_landscape","offer_gaps","pricing_context"]
        )
        if market["status"]!="COMPLETE":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"market"}

        known_source_refs = {f.get("source_id") for f in market["report"].get("findings", []) if f.get("source_id")}
        market_handoff = build_market_to_idea_handoff(market["report"])
        market_handoff_qa = validate_semantic_handoff(market_handoff, contract="market_to_idea_v1", known_source_refs=known_source_refs)
        if market_handoff_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"market_to_idea_handoff_validation","handoff_qa":market_handoff_qa}

        ideas=self.ideas.build(market["report"],audience=audience,constraints=constraints,max_ideas=10)
        if ideas.get("status")!="COMPLETE" or not ideas["scores"]["ranked_ideas"]:
            return {"status":"FAILED","run_id":run_id,"failed_stage":"ideas"}

        idea_handoff = ideas.get("strategy_handoff", {})
        idea_handoff_qa = validate_semantic_handoff(idea_handoff, contract="idea_to_strategy_v1", known_source_refs=known_source_refs)
        if idea_handoff_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"idea_to_strategy_handoff_validation","handoff_qa":idea_handoff_qa}

        strategy_context = market_context_for_strategy(market["report"], idea_handoff)
        strategy=self.strategy.build(idea_handoff,strategy_context,goal=goal,constraints=constraints)
        if strategy["status"]!="COMPLETE":
            return {"status":"FAILED","run_id":run_id,"failed_stage":strategy.get("failed_stage", "strategy")}
        strategy_handoff = build_strategy_to_product_handoff(strategy)
        strategy_handoff_qa = validate_semantic_handoff(strategy_handoff, contract="strategy_to_product_v1", known_source_refs=known_source_refs)
        if strategy_handoff_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"strategy_to_product_handoff_validation","handoff_qa":strategy_handoff_qa}

        product_input = strategy_context_for_product(strategy, strategy_handoff)
        product=self.product.build(product_input,audience=audience,constraints=constraints)
        if product["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"product"}
        product_definition = product.get("product_definition") or {}
        if str(product_definition.get("product_type") or "").strip().lower() == "unspecified" or not str(product_definition.get("product_type") or "").strip():
            return {"status":"FAILED","run_id":run_id,"failed_stage":"product_identity","error":{"reason":"product_type_unspecified"}}

        product_brand_handoff = build_product_to_brand_handoff(product)
        product_brand_qa = validate_semantic_handoff(product_brand_handoff, contract="product_to_brand_v1", required_fields=("problem","promise","audience"), known_source_refs=known_source_refs)
        if product_brand_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"product_to_brand_handoff_validation","handoff_qa":product_brand_qa}

        brand_input = product_context_for_brand(product, product_brand_handoff)
        brand=self.brand.build(brand_input,audience=audience,name_candidates=["O23 Working Name"])
        if brand["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"brand"}

        brand_content_handoff = build_brand_to_content_handoff(brand, product_brand_handoff)
        brand_content_qa = validate_semantic_handoff(brand_content_handoff, contract="brand_to_content_v1", required_fields=("audience","message"), known_source_refs=known_source_refs)
        if brand_content_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"brand_to_content_handoff_validation","handoff_qa":brand_content_qa}

        content_input = {"product_definition": {
            "core_problem": product_brand_handoff.get("problem", ""),
            "core_promise": product_brand_handoff.get("promise", ""),
            "target_audience": product_brand_handoff.get("audience", audience),
            "product_type": (product.get("product_definition") or {}).get("product_type", ""),
        }, "product_to_brand_handoff": product_brand_handoff}
        brand_for_content = brand_context_for_content(brand, brand_content_handoff, product_brand_handoff)
        content=self.content.build(content_input,brand_for_content,platforms=["Instagram","TikTok"],topics_per_pillar=1)
        if content["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"content"}

        content_visual_handoff = build_content_to_visual_handoff(content, brand_content_handoff)
        content_visual_qa = validate_semantic_handoff(content_visual_handoff, contract="content_to_visual_v1", required_fields=("topic","objective","platform"), known_source_refs=known_source_refs)
        if content_visual_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"content_to_visual_handoff_validation","handoff_qa":content_visual_qa}

        first_topic = ((content.get("topics") or {}).get("topics") or [{}])[0]
        visual_input = content_context_for_visual(content, content_visual_handoff, brand_content_handoff)
        visual=self.visual.build(visual_input,brand_context_for_content(brand, brand_content_handoff, product_brand_handoff),platform="Instagram")
        if visual["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"visual"}

        visual_marketing_handoff = build_visual_to_marketing_handoff(visual, content_visual_handoff)
        visual_marketing_qa = validate_semantic_handoff(visual_marketing_handoff, contract="visual_to_marketing_v1", required_fields=("asset_summary","platform"), known_source_refs=known_source_refs)
        if visual_marketing_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"visual_to_marketing_handoff_validation","handoff_qa":visual_marketing_qa}

        marketing_input_product = {"product_definition": product.get("product_definition", {}), "product_to_brand_handoff": product_brand_handoff}
        marketing_input_brand = {"brand_dna": {
            "audience": brand_content_handoff.get("audience", audience),
            "personality": (brand.get("brand_dna") or {}).get("personality", []),
        }, "brand_to_content_handoff": brand_content_handoff, "visual_to_marketing_handoff": visual_marketing_handoff}
        marketing_input_content = {
            "content_strategy": (content.get("content_strategy") or {}),
            "topics": {"topics": [content_context_for_visual(content, content_visual_handoff, brand_content_handoff)]},
            "visual_to_marketing_handoff": visual_marketing_handoff,
        }
        marketing_market = market_context_for_strategy(market["report"], idea_handoff)
        marketing=self.marketing.build(marketing_input_product,marketing_input_brand,market_report=marketing_market,content_output=marketing_input_content)
        if marketing["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"marketing"}

        marketing_sales_handoff = build_marketing_to_sales_handoff(marketing, visual_marketing_handoff)
        marketing_sales_qa = validate_semantic_handoff(marketing_sales_handoff, contract="marketing_to_sales_v1", required_fields=("offer_summary","audience","primary_channel"), known_source_refs=known_source_refs)
        if marketing_sales_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"marketing_to_sales_handoff_validation","handoff_qa":marketing_sales_qa}

        sales_input_product = {"product_definition": product.get("product_definition", {})}
        sales_input_brand = {"brand_dna": (brand.get("brand_dna") or {}), "voice": (brand.get("voice") or {})}
        sales_input_marketing = marketing_context_for_sales(marketing, marketing_sales_handoff)
        sales=self.sales.build(sales_input_product,sales_input_brand,sales_input_marketing)
        if sales["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"sales"}

        sales_automation_handoff = build_sales_to_automation_handoff(sales, marketing_sales_handoff)
        sales_automation_qa = validate_semantic_handoff(sales_automation_handoff, contract="sales_to_automation_v1", required_fields=("workflow_summary", "qualification_summary"), known_source_refs=known_source_refs)
        if sales_automation_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"sales_to_automation_handoff_validation","handoff_qa":sales_automation_qa}

        process={
            "name":"O23 Validation Workflow","purpose":"Governed validation workflow","trigger":"schedule",
            "sales_to_automation_handoff": sales_automation_handoff,
            "steps":[
                {"step_id":"S1","name":"Collect","type":"action","action":"Collect analytics","action_key":"read_metrics"},
                {"step_id":"S2","name":"Validate","type":"condition","action":"Validate freshness"},
                {"step_id":"S3","name":"Publish","type":"action","action":"Publish report","action_key":"publish_public_content"},
            ],
        }
        automation=self.automation.build(process,{"type":"schedule","schedule":"weekly"})
        if automation["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"automation"}

        automation_analytics_handoff = build_automation_to_analytics_handoff(automation, sales_automation_handoff)
        automation_analytics_qa = validate_semantic_handoff(automation_analytics_handoff, contract="automation_to_analytics_v1", required_fields=("workflow_summary", "metric_intent"), known_source_refs=known_source_refs)
        if automation_analytics_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"automation_to_analytics_handoff_validation","handoff_qa":automation_analytics_qa}

        events=[
            {"event_id":"EV1","event_type":"content_view","timestamp":"2026-08-29T10:00:00Z","user_id":"U1","properties":{"channel":"organic"}},
            {"event_id":"EV2","event_type":"content_view","timestamp":"2026-08-29T10:01:00Z","user_id":"U2","properties":{"channel":"paid"}},
            {"event_id":"EV3","event_type":"qualified_lead","timestamp":"2026-08-29T10:03:00Z","user_id":"U1","properties":{"channel":"organic"}},
            {"event_id":"EV4","event_type":"purchase","timestamp":"2026-08-29T10:05:00Z","user_id":"U1","properties":{"channel":"organic"}},
        ]
        analytics=self.analytics.analyze(
            events,["content_view","qualified_lead","purchase"],
            experiment_inputs=[{"name":"Problem-first Message Test","control":{"conversion":0.10},"variant":{"conversion":0.15},"metric":"conversion"}],
            revenue=100,customers=1,
            automation_handoff=automation_context_for_analytics(automation_analytics_handoff),
        )
        if analytics["status"]!="COMPLETE": return {"status":"FAILED","run_id":run_id,"failed_stage":"analytics"}

        analytics_approval_handoff = build_analytics_to_approval_handoff(analytics, automation_analytics_handoff)
        analytics_approval_qa = validate_semantic_handoff(analytics_approval_handoff, contract="analytics_to_approval_v1", required_fields=("decision_summary", "learning_summary"), known_source_refs=known_source_refs)
        if analytics_approval_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"analytics_to_approval_handoff_validation","handoff_qa":analytics_approval_qa}

        if self._approval_requester is not None:
            approval=self._approval_requester(
                run_id=run_id,
                project_id=project_id,
                action="publish_public_content",
                context={"asset":"validated-report","external_effect":True},
            )
        else:
            approval=self.approvals.request_gate(
                run_id,"publish_public_content",{"asset":"validated-report"},external_effect=True
            )
        approval_memory_handoff = build_approval_to_memory_handoff(approval, analytics_approval_handoff)
        approval_memory_qa = validate_semantic_handoff(approval_memory_handoff, contract="approval_to_memory_v1", required_fields=("decision_summary", "action"), known_source_refs=known_source_refs)
        if approval_memory_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"approval_to_memory_handoff_validation","handoff_qa":approval_memory_qa}

        memory=self.memory.process_run(
            {"run_id":run_id,"project_id":project_id,
             "learning":analytics["learning"]["summary"],
             "source_refs":[x["source_id"] for x in market["report"]["findings"] if x.get("source_id")]},
            {"status":"PASS"}
        )
        memory_monitoring_handoff = build_memory_to_monitoring_handoff(memory, approval_memory_handoff)
        memory_monitoring_qa = validate_semantic_handoff(memory_monitoring_handoff, contract="memory_to_monitoring_v1", required_fields=("learning_summary", "memory_status"), known_source_refs=known_source_refs)
        if memory_monitoring_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"memory_to_monitoring_handoff_validation","handoff_qa":memory_monitoring_qa}

        handoff_records = {
            "market_to_idea": {"contract": market_handoff, "qa": market_handoff_qa},
            "idea_to_strategy": {"contract": idea_handoff, "qa": idea_handoff_qa},
            "strategy_to_product": {"contract": strategy_handoff, "qa": strategy_handoff_qa},
            "product_to_brand": {"contract": product_brand_handoff, "qa": product_brand_qa},
            "brand_to_content": {"contract": brand_content_handoff, "qa": brand_content_qa},
            "content_to_visual": {"contract": content_visual_handoff, "qa": content_visual_qa},
            "visual_to_marketing": {"contract": visual_marketing_handoff, "qa": visual_marketing_qa},
            "marketing_to_sales": {"contract": marketing_sales_handoff, "qa": marketing_sales_qa},
            "sales_to_automation": {"contract": sales_automation_handoff, "qa": sales_automation_qa},
            "automation_to_analytics": {"contract": automation_analytics_handoff, "qa": automation_analytics_qa},
            "analytics_to_approval": {"contract": analytics_approval_handoff, "qa": analytics_approval_qa},
            "approval_to_memory": {"contract": approval_memory_handoff, "qa": approval_memory_qa},
            "memory_to_monitoring": {"contract": memory_monitoring_handoff, "qa": memory_monitoring_qa},
        }
        chain_qa = validate_handoff_chain(handoff_records)
        if chain_qa["status"]!="PASS":
            return {"status":"FAILED","run_id":run_id,"failed_stage":"handoff_chain_validation","handoff_chain_qa":chain_qa}

        for eid in ["E-02","E-03","E-04","E-05","E-06","E-07","E-08","E-09","E-10","E-11","E-12"]:
            self.monitoring.log_engine(run_id,eid,"SUCCESS")
        execution_outcome = _build_execution_outcome_contract(approval)
        self.monitoring.log_approval(run_id,execution_outcome["approval_status"],approval["approval_id"],action="publish_public_content")
        self.monitoring.log_qa(run_id,"PASS")
        self.monitoring.log_memory(run_id,memory["status"],refs=memory.get("memory_refs",[]))
        self.monitoring.end_run(run_id,"COMPLETE")

        result_payload = {
            "status":"COMPLETE","run_id":run_id,"project_id":project_id,
            "qa": {
                "status": "PASS",
                "checks": {"runtime": "PASS", "handoff_chain": chain_qa["status"]},
                "handoff_count": len(handoff_records),
            },
            "handoff_chain_qa": chain_qa,
            "handoffs": handoff_records,
            "knowledge":knowledge,"prompt":prompt,"market":market,"ideas":ideas,
            "strategy":strategy,"product":product,"brand":brand,"content":content,
            "visual":visual,"marketing":marketing,"sales":sales,"automation":automation,
            "analytics":analytics,"approval":approval,"memory":memory,
            "execution_outcome": execution_outcome,
            "monitoring":self.monitoring.run_summary(run_id)
        }
        result_payload["decision_surface"] = build_decision_surface(result_payload)
        result_payload["arabic_decision_summary"] = build_arabic_decision_summary(result_payload)
        result_payload["requested_language"] = (language or "en").lower()
        return result_payload

    def close(self):
        for obj in (self.memory, self.monitoring):
            close = getattr(obj, "close", None)
            if callable(close):
                close()
