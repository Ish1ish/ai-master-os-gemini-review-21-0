from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence


SCHEMA_VERSION = "AOA-v1.0"
ANALYSIS_STATUSES = {"ANALYZED", "INSUFFICIENT_SAMPLE"}
ROUTES = {
    "MAINTAIN",
    "REFINE_DECISION",
    "INVESTIGATE_EXECUTION",
    "COLLECT_MORE_EVIDENCE",
    "MONITOR",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_id(prefix: str, value: Any, length: int = 24) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}-{digest.upper()}"


class AdvancedOutcomeAnalysis:
    """Deterministic, read-only analysis across observed v1.5 assessments.

    This layer aggregates recorded evidence. It never executes actions,
    mutates policy/governance, or writes O43 memory.
    """

    def analyze(
        self,
        *,
        project_id: str,
        assessments: Sequence[Dict[str, Any]],
        window_size: int = 20,
        minimum_sample_size: int = 3,
    ) -> Dict[str, Any]:
        project_id = str(project_id or "").strip()
        if not project_id:
            raise ValueError("project_id_required")
        if window_size < 1:
            raise ValueError("invalid_window_size")
        if minimum_sample_size < 1:
            raise ValueError("invalid_minimum_sample_size")

        normalized = self._normalize_assessments(project_id, assessments)
        selected = normalized[: max(1, int(window_size))]
        sample_size = len(selected)

        payload_key = {
            "project_id": project_id,
            "assessment_ids": [a["assessment_id"] for a in selected],
            "window_size": int(window_size),
            "minimum_sample_size": int(minimum_sample_size),
        }
        analysis_id = deterministic_id("AOA", payload_key)

        if sample_size < minimum_sample_size:
            return self._base(
                analysis_id=analysis_id,
                project_id=project_id,
                selected=selected,
                analysis_status="INSUFFICIENT_SAMPLE",
                minimum_sample_size=minimum_sample_size,
                window_size=window_size,
                route="COLLECT_MORE_EVIDENCE",
                findings=["INSUFFICIENT_SAMPLE_FOR_PATTERN_ANALYSIS"],
            )

        return self._analyze_sufficient(
            analysis_id=analysis_id,
            project_id=project_id,
            selected=selected,
            all_assessments=normalized,
            minimum_sample_size=minimum_sample_size,
            window_size=window_size,
        )

    @staticmethod
    def _normalize_assessments(
        project_id: str,
        assessments: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if assessments is None:
            raise ValueError("assessments_required")
        if not isinstance(assessments, Iterable):
            raise ValueError("assessments_required")

        seen = set()
        rows = []
        for item in assessments:
            if not isinstance(item, dict):
                raise ValueError("assessment_must_be_object")
            aid = str(item.get("assessment_id") or "").strip()
            pid = str(item.get("project_id") or "").strip()
            if not aid or not pid:
                raise ValueError("assessment_identity_required")
            if pid != project_id:
                raise ValueError("project_mismatch")
            if aid in seen:
                continue
            seen.add(aid)
            rows.append(dict(item))

        # v1.5 store returns newest first; analysis remains deterministic even
        # when callers provide an already timestamped list.
        return rows

    def _analyze_sufficient(
        self,
        *,
        analysis_id: str,
        project_id: str,
        selected: List[Dict[str, Any]],
        all_assessments: List[Dict[str, Any]],
        minimum_sample_size: int,
        window_size: int,
    ) -> Dict[str, Any]:
        n = len(selected)
        eligible = [
            a for a in selected
            if bool(a.get("evidence_sufficient"))
            and a.get("target_status") != "UNKNOWN"
            and a.get("learning_signal") != "DO_NOT_LEARN"
        ]
        sufficient = [
            a for a in selected
            if bool(a.get("evidence_sufficient"))
        ]

        oq = Counter(str(a.get("outcome_quality") or "UNKNOWN") for a in selected)
        dq = Counter(str(a.get("decision_quality") or "UNKNOWN") for a in selected)
        attr = Counter(str(a.get("attribution") or "UNKNOWN") for a in selected)
        sig = Counter(str(a.get("learning_signal") or "UNKNOWN") for a in selected)

        met = sum(a.get("target_status") == "MET" for a in selected)
        partial = sum(a.get("target_status") == "PARTIAL" for a in selected)
        missed = sum(a.get("target_status") == "MISSED" for a in selected)
        unknown = sum(a.get("target_status") == "UNKNOWN" for a in selected)
        success = sum(bool(a.get("outcome_success")) for a in eligible)

        evidence_rate = len(sufficient) / n
        eligible_rate = len(eligible) / n
        success_rate = success / len(eligible) if eligible else None
        decision_miss_rate = (
            (dq["TARGET_MISSED"] + sig["NEGATIVE_SIGNAL"]) / len(eligible)
            if eligible else None
        )
        execution_mismatch_rate = (
            dq["EXECUTION_MISMATCH"] / len(sufficient)
            if sufficient else None
        )

        trend = self._trend(all_assessments, selected, minimum_sample_size)
        findings: List[str] = []

        if decision_miss_rate is not None and decision_miss_rate >= 0.40 and len(eligible) >= 3:
            findings.append("REPEATED_DECISION_MISSES")
        if execution_mismatch_rate is not None and execution_mismatch_rate >= 0.30 and len(sufficient) >= 3:
            findings.append("REPEATED_EXECUTION_MISMATCH")
        if evidence_rate < 0.70:
            findings.append("EVIDENCE_COVERAGE_WEAK")
        if sig["POSITIVE_CALIBRATION"] >= max(3, int(round(len(eligible) * 0.60))) and len(eligible) >= 3:
            findings.append("REPEATED_POSITIVE_CALIBRATION")
        if unknown / n >= 0.30:
            findings.append("TARGET_UNKNOWN_PATTERN")
        if not findings:
            findings.append("NO_DOMINANT_PATTERN")

        route = self._route(
            findings=findings,
            trend=trend,
            evidence_rate=evidence_rate,
            sample_size=n,
        )

        return {
            "schema_version": SCHEMA_VERSION,
            "analysis_id": analysis_id,
            "project_id": project_id,
            "analysis_status": "ANALYZED",
            "window_size": window_size,
            "minimum_sample_size": minimum_sample_size,
            "sample_size": n,
            "eligible_learning_sample": len(eligible),
            "evidence_sufficiency_rate": round(evidence_rate, 6),
            "eligible_learning_rate": round(eligible_rate, 6),
            "target_rates": {
                "met": round(met / n, 6),
                "partial": round(partial / n, 6),
                "missed": round(missed / n, 6),
                "unknown": round(unknown / n, 6),
            },
            "outcome_quality_counts": dict(oq),
            "decision_quality_counts": dict(dq),
            "attribution_counts": dict(attr),
            "learning_signal_counts": dict(sig),
            "eligible_success_rate": None if success_rate is None else round(success_rate, 6),
            "decision_miss_rate": None if decision_miss_rate is None else round(decision_miss_rate, 6),
            "execution_mismatch_rate": None if execution_mismatch_rate is None else round(execution_mismatch_rate, 6),
            "trend": trend,
            "findings": findings,
            "advisory_route": route,
            "confidence": self._confidence(
                sample_size=n,
                evidence_rate=evidence_rate,
                eligible_size=len(eligible),
                trend=trend,
            ),
            "assessment_refs": [a["assessment_id"] for a in selected],
            "boundary": (
                "Advanced outcome analysis summarizes observed evidence; "
                "it does not prove future outcomes, change governance, execute actions, "
                "or mutate O43 memory."
            ),
        }

    def _base(
        self,
        *,
        analysis_id: str,
        project_id: str,
        selected: List[Dict[str, Any]],
        analysis_status: str,
        minimum_sample_size: int,
        window_size: int,
        route: str,
        findings: List[str],
    ) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "analysis_id": analysis_id,
            "project_id": project_id,
            "analysis_status": analysis_status,
            "window_size": window_size,
            "minimum_sample_size": minimum_sample_size,
            "sample_size": len(selected),
            "eligible_learning_sample": 0,
            "evidence_sufficiency_rate": 0.0,
            "eligible_learning_rate": 0.0,
            "target_rates": {"met": 0.0, "partial": 0.0, "missed": 0.0, "unknown": 1.0 if selected else 0.0},
            "outcome_quality_counts": {},
            "decision_quality_counts": {},
            "attribution_counts": {},
            "learning_signal_counts": {},
            "eligible_success_rate": None,
            "decision_miss_rate": None,
            "execution_mismatch_rate": None,
            "trend": {"status": "UNKNOWN", "recent_rate": None, "prior_rate": None, "delta": None},
            "findings": findings,
            "advisory_route": route,
            "confidence": "unknown",
            "assessment_refs": [a["assessment_id"] for a in selected],
            "boundary": (
                "Advanced outcome analysis summarizes observed evidence; "
                "it does not prove future outcomes, change governance, execute actions, "
                "or mutate O43 memory."
            ),
        }

    @staticmethod
    def _trend(
        all_assessments: List[Dict[str, Any]],
        selected: List[Dict[str, Any]],
        minimum_sample_size: int,
    ) -> Dict[str, Any]:
        if len(selected) < minimum_sample_size * 2:
            return {"status": "UNKNOWN", "recent_rate": None, "prior_rate": None, "delta": None}

        split = len(selected) // 2
        recent = selected[:split]
        prior = selected[split:split * 2]

        def rate(rows: List[Dict[str, Any]]) -> float | None:
            eligible = [
                a for a in rows
                if bool(a.get("evidence_sufficient"))
                and a.get("learning_signal") != "DO_NOT_LEARN"
            ]
            if not eligible:
                return None
            return sum(bool(a.get("outcome_success")) for a in eligible) / len(eligible)

        rr = rate(recent)
        pr = rate(prior)
        if rr is None or pr is None:
            return {"status": "UNKNOWN", "recent_rate": rr, "prior_rate": pr, "delta": None}
        delta = rr - pr
        if delta >= 0.10:
            status = "IMPROVING"
        elif delta <= -0.10:
            status = "DETERIORATING"
        else:
            status = "STABLE"
        return {
            "status": status,
            "recent_rate": round(rr, 6),
            "prior_rate": round(pr, 6),
            "delta": round(delta, 6),
        }

    @staticmethod
    def _route(
        *,
        findings: List[str],
        trend: Dict[str, Any],
        evidence_rate: float,
        sample_size: int,
    ) -> str:
        if evidence_rate < 0.70:
            return "COLLECT_MORE_EVIDENCE"
        if "REPEATED_EXECUTION_MISMATCH" in findings:
            return "INVESTIGATE_EXECUTION"
        if "REPEATED_DECISION_MISSES" in findings:
            return "REFINE_DECISION"
        if trend.get("status") == "DETERIORATING":
            return "MONITOR"
        return "MAINTAIN" if sample_size >= 3 else "MONITOR"

    @staticmethod
    def _confidence(
        *,
        sample_size: int,
        evidence_rate: float,
        eligible_size: int,
        trend: Dict[str, Any],
    ) -> str:
        if sample_size < 3 or eligible_size < 3 or evidence_rate < 0.50:
            return "low"
        if sample_size >= 10 and eligible_size >= 8 and evidence_rate >= 0.80 and trend.get("status") != "UNKNOWN":
            return "high"
        return "medium"
