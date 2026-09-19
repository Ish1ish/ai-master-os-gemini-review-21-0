import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


class AIInvocationError(RuntimeError):
    def __init__(self, message: str, subtype: str = "UNKNOWN", raw_output: str = "", retry_count: int = 0):
        super().__init__(message)
        self.subtype = subtype
        self.raw_output = raw_output
        self.retry_count = retry_count


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.3
    max_output_tokens: int = 4000
    max_retries: int = 2
    timeout_s: float = 30.0


class AIRuntime:
    """Shared AI infrastructure; engine-specific prompts and policy stay outside."""

    def __init__(self, provider: Callable[..., Any], config: Optional[GenerationConfig] = None):
        if provider is None:
            raise ValueError("AIRuntime requires an explicit provider; silent template fallback is forbidden.")
        self.provider = provider
        self.config = config or GenerationConfig()

    @staticmethod
    def prompt_hash(system_prompt: str, user_prompt: str) -> str:
        canonical = json.dumps(
            {"system": system_prompt, "user": user_prompt},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def raw_output_hash(raw_output: str) -> str:
        return hashlib.sha256(raw_output.encode("utf-8")).hexdigest()

    def generate_structured(self, *, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        started = time.perf_counter()
        p_hash = self.prompt_hash(system_prompt, user_prompt)
        max_attempts = self.config.max_retries + 1
        last_raw = ""

        for attempt in range(max_attempts):
            try:
                raw = self.provider(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_output_tokens,
                    timeout_s=self.config.timeout_s,
                )

                if isinstance(raw, dict):
                    # Live provider envelope: {provider, model, text}.
                    # Structured generation must parse the text payload, not treat
                    # the provider envelope itself as the model result.
                    if "text" in raw:
                        text = raw.get("text")
                        if isinstance(text, dict):
                            data = text
                            raw_text = json.dumps(
                                text, ensure_ascii=False, sort_keys=True
                            )
                        elif isinstance(text, str):
                            raw_text = text
                            last_raw = text
                            data = json.loads(text)
                        else:
                            raise AIInvocationError(
                                "Provider envelope contains unsupported text type.",
                                "INVALID_PROVIDER_OUTPUT",
                                "",
                                attempt,
                            )
                    else:
                        data = raw
                        raw_text = json.dumps(
                            raw, ensure_ascii=False, sort_keys=True
                        )
                elif isinstance(raw, str):
                    raw_text = raw
                    last_raw = raw
                    data = json.loads(raw)
                else:
                    raise AIInvocationError(
                        "Provider returned unsupported output type.",
                        "INVALID_PROVIDER_OUTPUT",
                        "",
                        attempt,
                    )

                if not isinstance(data, dict):
                    raise AIInvocationError(
                        "Structured model output must be a JSON object.",
                        "MALFORMED_JSON",
                        raw_text,
                        attempt,
                    )

                return {
                    "data": data,
                    "raw_output": raw_text,
                    "prompt_hash": p_hash,
                    "raw_output_hash": self.raw_output_hash(raw_text),
                    "retry_count": attempt,
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                }
            except AIInvocationError:
                raise
            except json.JSONDecodeError as exc:
                last_raw = getattr(exc, "doc", "") or last_raw
                if attempt >= max_attempts - 1:
                    raise AIInvocationError(
                        "LLM output was not valid JSON after retries.",
                        "MALFORMED_JSON",
                        last_raw,
                        attempt,
                    ) from exc
                time.sleep(min(2 ** (attempt + 1), 4))
            except TimeoutError as exc:
                if attempt >= max_attempts - 1:
                    raise AIInvocationError(
                        "LLM request timed out after retries.",
                        "TIMEOUT",
                        last_raw,
                        attempt,
                    ) from exc
                time.sleep(min(2 ** (attempt + 1), 4))
            except Exception as exc:
                if attempt >= max_attempts - 1:
                    raise AIInvocationError(
                        f"LLM provider failed after retries: {exc}",
                        "PROVIDER_ERROR",
                        last_raw,
                        attempt,
                    ) from exc
                time.sleep(min(2 ** (attempt + 1), 4))

        raise AIInvocationError("Unreachable AI runtime failure.", "UNKNOWN")
