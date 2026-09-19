"""Canonical S21 HTTP route adapter over the existing unified runtime/O45 bundle.

This module owns transport routing only. It does not create persistence,
governance, identity, or execution authorities; all stateful operations are
delegated to the already-owned runtime instance.
"""
from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlsplit


class CanonicalHTTPAPI:
    """Small route adapter for the canonical Python/O45 surface."""

    def __init__(self, entrypoint) -> None:
        if entrypoint is None:
            raise ValueError("entrypoint_required")
        self.entrypoint = entrypoint
        self.runtime = entrypoint.runtime

    @staticmethod
    def _principal(value: Mapping[str, Any] | None) -> dict[str, Any]:
        value = dict(value or {})
        nested = value.get("principal")
        if isinstance(nested, Mapping):
            value = {
                **dict(nested),
                **{k: v for k, v in value.items() if k != "principal"},
            }
        elif nested and not value.get("principal_id"):
            value["principal_id"] = str(nested)
        if value.get("principal_id") and not value.get("principal"):
            value["principal"] = value["principal_id"]
        return value

    def _authorize(
        self,
        principal: Mapping[str, Any] | None,
        scope: str,
    ) -> dict[str, Any] | None:
        principal = self._principal(principal)
        if principal.get("authenticated") is False:
            return {
                "status": "UNAUTHORIZED",
                "reason": "principal_not_authenticated",
                "required_scope": scope,
            }
        principal_id = str(
            principal.get("principal_id")
            or principal.get("principal")
            or ""
        ).strip()
        if not principal_id:
            return {
                "status": "UNAUTHORIZED",
                "reason": "principal_required",
                "required_scope": scope,
            }
        scopes = {str(item) for item in (principal.get("scopes") or [])}
        if scope not in scopes:
            return {
                "status": "FORBIDDEN",
                "reason": "scope_not_granted",
                "required_scope": scope,
            }
        return None

    @staticmethod
    def _http_status(result: Mapping[str, Any]) -> int:
        status = str(result.get("status", ""))
        if status == "NOT_FOUND":
            return 404
        if status == "UNAUTHORIZED":
            return 401
        if status in {"FORBIDDEN", "DENY"}:
            return 403
        if status == "BAD_REQUEST":
            return 400
        if status == "CONFLICT":
            return 409
        return 200

    def handle(
        self,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any] | None,
        principal: Mapping[str, Any] | None,
    ) -> tuple[int, dict[str, Any]]:
        route = urlsplit(path).path.rstrip("/") or "/"
        body = dict(body or {})
        principal = self._principal(principal)

        if method == "POST" and route == "/api/runs":
            denied = self._authorize(principal, "run:submit")
            if denied:
                return self._http_status(denied), denied
            result = self.entrypoint.run(body, principal=principal)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/intents/")
            and route.endswith("/execute")
        ):
            intent_id = route[len("/api/intents/") : -len("/execute")].strip("/")
            if not intent_id:
                result = {"status": "BAD_REQUEST", "reason": "intent_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "run:execute")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.execute_governed_intent(
                intent_id,
                principal=principal,
            )
            return self._http_status(result), result

        if method == "GET" and route == "/api/approvals":
            denied = self._authorize(principal, "approval:read")
            if denied:
                return self._http_status(denied), denied
            return 200, {
                "status": "OK",
                "approvals": self.runtime.list_approvals(),
            }

        if method == "GET" and route.startswith("/api/approvals/"):
            approval_id = route[len("/api/approvals/") :].strip("/")
            if not approval_id:
                result = {"status": "BAD_REQUEST", "reason": "approval_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "approval:read")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.get_approval(approval_id)
            return self._http_status(result), result

        if (
            method == "POST"
            and route.startswith("/api/approvals/")
            and route.endswith("/decision")
        ):
            approval_id = route[len("/api/approvals/") : -len("/decision")].strip("/")
            if not approval_id:
                result = {"status": "BAD_REQUEST", "reason": "approval_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "approval:decide")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.decide_approval(
                approval_id,
                principal=principal,
                decision=str(body.get("decision") or ""),
                reason=str(body.get("reason") or ""),
            )
            return self._http_status(result), result

        if method == "GET" and route.startswith("/api/executions/"):
            execution_id = route[len("/api/executions/") :].strip("/")
            if not execution_id:
                result = {"status": "BAD_REQUEST", "reason": "execution_id_required"}
                return self._http_status(result), result
            denied = self._authorize(principal, "run:read")
            if denied:
                return self._http_status(denied), denied
            result = self.runtime.get_execution(execution_id)
            return self._http_status(result), result

        return 404, {
            "status": "NOT_FOUND",
            "reason": "canonical_route_not_found",
        }
