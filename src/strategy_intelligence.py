from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "SI-v1.0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_id(prefix: str, value: Any, length: int = 24) -> str:
    h = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{h.upper()}"


class StrategyIntelligence:
    """Ranks bounded strategy candidates using learned context.

    Advisory only. It does not execute strategies, change governance, or mutate
    O43 memory. Scores are prioritization heuristics, not probabilities.
    """

    def rank(
        self,
        *,
        project_id: str,
        decision_context: Optional[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        evidence_sufficient: bool = True,
    ) -> Dict[str, Any]:
        project_id = str(project_id or "").strip()
        if not project_id:
            raise ValueError("project_id_required")
        if not candidates:
            raise ValueError("candidates_required")

        for c in candidates:
            if not isinstance(c, dict) or not c.get("strategy_id"):
                raise ValueError("invalid_strategy_candidate")

        if decision_context is not None:
            if str(decision_context.get("project_id") or "") != project_id:
                raise ValueError("project_mismatch")

        posture = str((decision_context or {}).get("advisory_posture") or "COLD_START")
        advisory_decision = str((decision_context or {}).get("advisory_decision") or "HOLD")

        rows = []
        for candidate in candidates:
            strategy_id = str(candidate["strategy_id"])
            prior_success_rate = float(candidate.get("prior_success_rate", 0.0))
            sample_size = int(candidate.get("sample_size", 0))
            execution_mismatch_rate = float(candidate.get("execution_mismatch_rate", 0.0))
            evidence_strength = float(candidate.get("evidence_strength", 0.0))
            context_match = float(candidate.get("context_match", 0.0))

            score = (
                (0.35 * prior_success_rate)
                + (0.25 * evidence_strength)
                + (0.25 * context_match)
                + (0.15 * min(sample_size / 10.0, 1.0))
                - (0.25 * execution_mismatch_rate)
            )

            caution = posture in {"ELEVATED_CAUTION", "INVESTIGATE_EXECUTION", "COLLECT_MORE_EVIDENCE"}
            if caution:
                score *= 0.85

            rows.append(
                {
                    "strategy_id": strategy_id,
                    "score": round(score, 6),
                    "sample_size": sample_size,
                    "evidence_strength": evidence_strength,
                    "context_match": context_match,
                    "execution_mismatch_rate": execution_mismatch_rate,
                }
            )

        rows.sort(key=lambda x: (-x["score"], x["strategy_id"]))

        route = "RANKED_ADVISORY" if evidence_sufficient and advisory_decision != "BLOCK" else "HOLD"
        if not evidence_sufficient:
            route = "COLLECT_MORE_EVIDENCE"

        payload = {
            "project_id": project_id,
            "context_id": None if decision_context is None else decision_context.get("context_id"),
            "strategy_ids": [r["strategy_id"] for r in rows],
            "route": route,
            "evidence_sufficient": bool(evidence_sufficient),
        }

        return {
            "schema_version": SCHEMA_VERSION,
            "analysis_id": deterministic_id("SIA", payload),
            "project_id": project_id,
            "context_id": None if decision_context is None else decision_context.get("context_id"),
            "route": route,
            "ranked_strategies": rows,
            "top_strategy_id": rows[0]["strategy_id"] if route == "RANKED_ADVISORY" else None,
            "confidence": "medium" if evidence_sufficient and len(rows) >= 2 else "low",
            "governance_authority": "POLICY_AND_GOVERNANCE_REMAIN_AUTHORITATIVE",
            "external_action_executed": False,
            "o43_memory_mutated": False,
            "boundary": (
                "Strategy ranking is advisory prioritization. It is not probability, "
                "authorization, execution, or direct memory mutation."
            ),
        }
