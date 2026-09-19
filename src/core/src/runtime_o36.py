import os
from .control_service_o35 import O35ControlService
from .identity import IdentityProvider, Principal
from .rbac import RBAC
from .authz import AuthorizationService
from .governed_control import GovernedControl
from .approval_authority import ApprovalAuthority


class O36Runtime:
    def __init__(self,root):
        self.o35=O35ControlService(root)
        self.identity=IdentityProvider()
        self.rbac=RBAC()
        self.authz=AuthorizationService(self.identity,self.rbac)
        self.governed=GovernedControl(self.o35,self.authz)
        self.register_default_principals()

    def register_default_principals(self):
        self.identity.register(Principal(
            "viewer-01","human",frozenset({"viewer"}),
            frozenset(self.rbac.scopes_for_roles({"viewer"}))
        ))
        self.identity.register(Principal(
            "operator-01","human",frozenset({"operator"}),
            frozenset(self.rbac.scopes_for_roles({"operator"}))
        ))
        self.identity.register(Principal(
            "approver-01","human",frozenset({"approver"}),
            frozenset(self.rbac.scopes_for_roles({"approver"}))
        ))
        self.identity.register(Principal(
            "worker-01","service",frozenset({"worker"}),
            frozenset(self.rbac.scopes_for_roles({"worker"}))
        ))
        self.identity.register(Principal(
            "admin-01","human",frozenset({"admin"}),
            frozenset(self.rbac.scopes_for_roles({"admin"}))
        ))

    def issue_credentials(self,principal_id):
        # O36 internal issuance now uses the same signed-bearer mechanism as production.
        return {"bearer_token": self.identity.issue_token(principal_id)["token"]}

    def request_approval(self,run_id,action,payload,requested_by="system"):
        return self.o35.request_approval(run_id,action,payload,requested_by)

    def decide(self,principal_id,approval_id,decision,reason=""):
        return self.governed.decide(
            self.issue_credentials(principal_id),
            approval_id,decision,reason
        )

    def execute(self,principal_id,run_id,action,payload,execute_fn=None):
        return self.governed.execute(
            self.issue_credentials(principal_id),
            run_id,action,payload,execute_fn
        )
