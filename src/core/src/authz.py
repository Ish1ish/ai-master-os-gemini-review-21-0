from .identity import IdentityProvider
from .rbac import RBAC
from .resource_policy import ResourceAuthorizer


class AuthorizationService:
    def __init__(self, identity=None, rbac=None, resources=None):
        self.identity=identity or IdentityProvider()
        self.rbac=rbac or RBAC()
        self.resources=resources or ResourceAuthorizer()

    def authenticate(self, credentials):
        return self.identity.authenticate(credentials)

    def authorize(self, credentials, resource, action):
        auth=self.authenticate(credentials or {})
        if auth["status"]!="AUTHENTICATED":
            return auth
        return self.resources.authorize(
            self.rbac,
            auth["principal"],
            resource,
            action,
        )
