from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PromptSpec:
    task: str
    role: str = "expert assistant"
    context: str = ""
    objective: str = ""
    audience: str = ""
    tone: str = ""
    output_format: str = "structured response"
    constraints: List[str] = None
    examples: List[Dict[str, str]] = None
    knowledge_refs: List[str] = None

    def __post_init__(self):
        self.constraints = list(self.constraints or [])
        self.examples = list(self.examples or [])
        self.knowledge_refs = list(self.knowledge_refs or [])


class PromptCompiler:
    """
    Real, deterministic prompt compiler.
    It converts normalized runtime inputs into a reusable execution prompt.
    It does not claim to execute a model; a provider adapter handles inference.
    """

    TECHNIQUE_ORDER = [
        "role",
        "context",
        "objective",
        "task",
        "audience",
        "tone",
        "examples",
        "knowledge",
        "format",
        "constraints",
        "quality_gate",
    ]

    def compile(self, spec: PromptSpec) -> Dict[str, Any]:
        sections = {}

        sections["role"] = f"Act as {spec.role}."
        if spec.context:
            sections["context"] = f"Context:\n{spec.context}"
        if spec.objective:
            sections["objective"] = f"Objective:\n{spec.objective}"
        sections["task"] = f"Task:\n{spec.task}"
        if spec.audience:
            sections["audience"] = f"Audience:\n{spec.audience}"
        if spec.tone:
            sections["tone"] = f"Tone:\n{spec.tone}"
        if spec.examples:
            example_lines = []
            for i, ex in enumerate(spec.examples, 1):
                example_lines.append(
                    f"Example {i} input:\n{ex.get('input','')}\n"
                    f"Example {i} output:\n{ex.get('output','')}"
                )
            sections["examples"] = "Examples:\n" + "\n\n".join(example_lines)
        if spec.knowledge_refs:
            sections["knowledge"] = (
                "Use the following knowledge references where relevant. "
                "Do not invent claims unsupported by them:\n- "
                + "\n- ".join(spec.knowledge_refs)
            )
        sections["format"] = f"Output format:\n{spec.output_format}"
        if spec.constraints:
            sections["constraints"] = (
                "Constraints:\n- " + "\n- ".join(spec.constraints)
            )
        sections["quality_gate"] = (
            "Quality gate:\n"
            "1. Follow the requested format.\n"
            "2. Respect constraints.\n"
            "3. Separate known information from uncertainty.\n"
            "4. Do not fabricate evidence, quotes, testimonials, metrics, or current facts."
        )

        ordered = [sections[k] for k in self.TECHNIQUE_ORDER if k in sections]
        prompt_text = "\n\n".join(ordered)

        return {
            "schema": "execution_prompt_v1",
            "prompt_text": prompt_text,
            "sections": sections,
            "techniques_used": [k for k in self.TECHNIQUE_ORDER if k in sections],
            "knowledge_refs": list(spec.knowledge_refs),
            "output_format": spec.output_format,
        }
