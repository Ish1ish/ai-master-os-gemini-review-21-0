from pathlib import Path
from typing import Dict, Any
from .engine import RealPromptEngine
from .qa_adapter import validate_prompt_output


class O10Runtime:
    def __init__(self, provider=None):
        self.engine = RealPromptEngine(provider=provider)

    def run(self, task: str, **kwargs) -> Dict[str, Any]:
        out = self.engine.execute(task=task, **kwargs)
        qa = validate_prompt_output(out)
        return {
            "status": "COMPLETE" if qa["status"] == "PASS" else "FAILED",
            "engine_id": "E-01",
            "engine": out,
            "qa": qa,
        }
