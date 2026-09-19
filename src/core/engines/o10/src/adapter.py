from typing import Callable, Dict, Any, Optional


class ModelProvider:
    """
    Optional inference adapter.
    The host runtime injects a callable provider; O10 never hides credentials
    or assumes a specific vendor/API.
    """
    def __init__(self, provider: Optional[Callable[[str], Any]] = None):
        self.provider = provider

    def generate(self, prompt_text: str) -> Dict[str, Any]:
        if self.provider is None:
            return {
                "status": "NOT_EXECUTED",
                "reason": "model_provider_not_configured",
                "prompt_text": prompt_text,
            }
        result = self.provider(prompt_text)
        return {
            "status": "EXECUTED",
            "result": result,
            "prompt_text": prompt_text,
        }
