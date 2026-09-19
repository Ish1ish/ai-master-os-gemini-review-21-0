from typing import Dict, Any, List
from .compiler import PromptCompiler, PromptSpec
from .techniques import select_techniques
from .adapter import ModelProvider


class RealPromptEngine:
    def __init__(self, provider=None):
        self.compiler = PromptCompiler()
        self.provider = ModelProvider(provider)

    def prepare(self, task: str, role: str = "expert assistant",
                context: str = "", objective: str = "",
                audience: str = "", tone: str = "",
                output_format: str = "structured response",
                constraints: List[str] | None = None,
                examples: List[Dict[str, str]] | None = None,
                knowledge_refs: List[str] | None = None,
                task_type: str = "general") -> Dict[str, Any]:
        examples = list(examples or [])
        knowledge_refs = list(knowledge_refs or [])
        technique_plan = select_techniques(
            task_type=task_type,
            has_examples=bool(examples),
            has_knowledge=bool(knowledge_refs),
            needs_structure=True,
        )

        spec = PromptSpec(
            task=task,
            role=role,
            context=context,
            objective=objective,
            audience=audience,
            tone=tone,
            output_format=output_format,
            constraints=constraints or [],
            examples=examples,
            knowledge_refs=knowledge_refs,
        )
        compiled = self.compiler.compile(spec)

        return {
            "status": "READY",
            "engine_id": "E-01",
            "engine_version": "O10-v1.0",
            "task_type": task_type,
            "technique_plan": technique_plan,
            "execution_prompt": compiled,
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        prepared = self.prepare(**kwargs)
        inference = self.provider.generate(
            prepared["execution_prompt"]["prompt_text"]
        )
        return {
            **prepared,
            "inference": inference,
            "status": "EXECUTED" if inference["status"] == "EXECUTED" else "PROMPT_READY",
        }
