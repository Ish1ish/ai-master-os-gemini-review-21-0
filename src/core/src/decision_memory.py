from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DECISION_ORDER = {"AUTO_ALLOW": 1, "REVIEW": 2, "BLOCK": 3}
RISK_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CounterfactualDecisionMemory:
    """Durable memory for prediction -> outcome -> learning signals.

    Recording and observing are stateful backend operations, but neither operation
    executes tools or creates external side effects. The stored prediction is
    immutable except for the single explicit outcome observation transition.
    """

    def __init__(self, path: str = "./data/counterfactual_memory.sqlite3"):
        self.path = str(path)
        if self.path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS counterfactual_predictions(
                prediction_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                requester TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                predicted_decision TEXT NOT NULL,
                predicted_risk TEXT NOT NULL,
                prediction_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                observed_at TEXT,
                actual_json TEXT,
                learning_json TEXT,
                status TEXT NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cfm_project ON counterfactual_predictions(project_id, created_at DESC)")
        self.conn.commit()
        self._closed = False

    @staticmethod
    def _prediction_fingerprint(project_id: str, plan_hash: str, predicted: Dict[str, Any]) -> str:
        raw = json.dumps({
            "project_id": project_id,
            "plan_hash": plan_hash,
            "decision": predicted.get("decision"),
            "risk": predicted.get("risk"),
            "actions": predicted.get("actions") or [],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20].upper()

    def record_prediction(self, *, project_id: str, requested_by: str, prediction: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("decision_memory_closed")
        if not isinstance(prediction, dict) or prediction.get("side_effects") not in (None, "NONE"):
            raise ValueError("prediction_must_be_side_effect_free")
        if not project_id or not requested_by:
            raise ValueError("project_id_and_requested_by_required")
        plan_hash = str(prediction.get("plan_hash") or "").strip()
        decision = str(prediction.get("decision") or "").upper()
        risk = str(prediction.get("risk") or "").upper()
        if not plan_hash or decision not in DECISION_ORDER or risk not in RISK_ORDER:
            raise ValueError("prediction_requires_plan_hash_decision_and_risk")
        prediction_id = f"CFP-{self._prediction_fingerprint(project_id, plan_hash, prediction)}"
        row = self.conn.execute("SELECT * FROM counterfactual_predictions WHERE prediction_id=?", (prediction_id,)).fetchone()
        if row:
            return self._row(row)
        now = _utc_now()
        payload = json.dumps(prediction, ensure_ascii=False, sort_keys=True)
        self.conn.execute(
            "INSERT INTO counterfactual_predictions(prediction_id,project_id,requester,plan_hash,predicted_decision,predicted_risk,prediction_json,created_at,status) VALUES(?,?,?,?,?,?,?,?,?)",
            (prediction_id, str(project_id), str(requested_by), plan_hash, decision, risk, payload, now, "PREDICTED"),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM counterfactual_predictions WHERE prediction_id=?", (prediction_id,)).fetchone()
        return self._row(row)

    def observe_outcome(self, *, prediction_id: str, actual: Dict[str, Any]) -> Dict[str, Any]:
        if self._closed:
            raise RuntimeError("decision_memory_closed")
        if not prediction_id or not isinstance(actual, dict):
            raise ValueError("prediction_id_and_actual_required")
        row = self.conn.execute("SELECT * FROM counterfactual_predictions WHERE prediction_id=?", (str(prediction_id),)).fetchone()
        if not row:
            raise KeyError("prediction_not_found")
        if row["status"] == "OBSERVED":
            return self._row(row)
        actual_decision = str(actual.get("decision") or "").upper()
        actual_risk = str(actual.get("risk") or "").upper()
        if actual_decision not in DECISION_ORDER or actual_risk not in RISK_ORDER:
            raise ValueError("actual_requires_decision_and_risk")
        predicted_decision = row["predicted_decision"]
        predicted_risk = row["predicted_risk"]
        decision_delta = DECISION_ORDER[actual_decision] - DECISION_ORDER[predicted_decision]
        risk_delta = RISK_ORDER[actual_risk] - RISK_ORDER[predicted_risk]
        if decision_delta == 0 and risk_delta == 0:
            calibration = "EXACT_MATCH"
            score = 1.0
        elif decision_delta > 0 or risk_delta > 0:
            calibration = "UNDERPREDICTED_RISK"
            score = -1.0
        else:
            calibration = "OVERPREDICTED_RISK"
            score = 0.5
        learning = {
            "calibration": calibration,
            "score": score,
            "decision_delta": decision_delta,
            "risk_delta": risk_delta,
            "prediction_accuracy": "MATCH" if calibration == "EXACT_MATCH" else "MISMATCH",
            "learning_rule": "Underprediction is a caution signal; overprediction is a bounded conservatism signal; exact match is positive calibration evidence.",
        }
        observed_at = _utc_now()
        self.conn.execute(
            "UPDATE counterfactual_predictions SET observed_at=?, actual_json=?, learning_json=?, status='OBSERVED' WHERE prediction_id=?",
            (observed_at, json.dumps(actual, ensure_ascii=False, sort_keys=True), json.dumps(learning, ensure_ascii=False, sort_keys=True), str(prediction_id)),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM counterfactual_predictions WHERE prediction_id=?", (str(prediction_id),)).fetchone()
        return self._row(row)

    def get(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM counterfactual_predictions WHERE prediction_id=?", (str(prediction_id),)).fetchone()
        return self._row(row) if row else None

    def list_by_project(self, project_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        rows = self.conn.execute(
            "SELECT * FROM counterfactual_predictions WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (str(project_id), limit),
        ).fetchall()
        return [self._row(r) for r in rows]

    def calibration_context(self, project_id: str, limit: int = 20) -> Dict[str, Any]:
        rows = self.list_by_project(project_id, limit=limit)
        observed = [r for r in rows if r["status"] == "OBSERVED"]
        exact = [r for r in observed if (r.get("learning") or {}).get("calibration") == "EXACT_MATCH"]
        under = [r for r in observed if (r.get("learning") or {}).get("calibration") == "UNDERPREDICTED_RISK"]
        over = [r for r in observed if (r.get("learning") or {}).get("calibration") == "OVERPREDICTED_RISK"]
        avg = None
        if observed:
            avg = round(sum(float((r.get("learning") or {}).get("score", 0.0)) for r in observed) / len(observed), 3)
        return {
            "status": "READY" if rows else "EMPTY",
            "project_id": str(project_id),
            "prediction_count": len(rows),
            "observed_count": len(observed),
            "pending_observations": len(rows) - len(observed),
            "calibration": {
                "exact_match": len(exact),
                "underpredicted_risk": len(under),
                "overpredicted_risk": len(over),
                "average_learning_score": avg,
            },
            "prediction_boundary": "Observed outcomes calibrate prior predictions; they do not prove future outcomes.",
            "records": rows,
        }

    @staticmethod
    def _row(row: sqlite3.Row) -> Dict[str, Any]:
        if row is None:
            return None
        return {
            "prediction_id": row["prediction_id"],
            "project_id": row["project_id"],
            "requested_by": row["requester"],
            "plan_hash": row["plan_hash"],
            "predicted_decision": row["predicted_decision"],
            "predicted_risk": row["predicted_risk"],
            "prediction": json.loads(row["prediction_json"]),
            "created_at": row["created_at"],
            "observed_at": row["observed_at"],
            "actual": json.loads(row["actual_json"]) if row["actual_json"] else None,
            "learning": json.loads(row["learning_json"]) if row["learning_json"] else None,
            "status": row["status"],
        }

    def close(self):
        if not self._closed:
            self.conn.close()
            self._closed = True
