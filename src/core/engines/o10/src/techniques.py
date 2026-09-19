from typing import Dict, Any


TECHNIQUES = {
    "role_prompting": "Define a clear role appropriate to the task.",
    "context_prompting": "Supply only relevant background and constraints.",
    "structured_output": "Specify an explicit output format/schema.",
    "few_shot": "Use examples when format/style consistency matters.",
    "constraint_prompting": "State limits and non-negotiable rules explicitly.",
    "iterative_refinement": "Allow a QA/refinement loop after generation.",
    "meta_prompting": "Use a prompt that improves/constructs another prompt.",
    "grounded_generation": "Bind non-trivial claims to retrieved knowledge/source references.",
}


def select_techniques(task_type: str, has_examples: bool, has_knowledge: bool,
                      needs_structure: bool = True) -> Dict[str, Any]:
    chosen = ["role_prompting", "context_prompting", "constraint_prompting"]
    if has_examples:
        chosen.append("few_shot")
    if needs_structure:
        chosen.append("structured_output")
    if has_knowledge:
        chosen.append("grounded_generation")
    chosen.append("iterative_refinement")
    if "prompt" in (task_type or "").lower():
        chosen.append("meta_prompting")

    return {
        "techniques": chosen,
        "rationale": {t: TECHNIQUES[t] for t in chosen},
    }
