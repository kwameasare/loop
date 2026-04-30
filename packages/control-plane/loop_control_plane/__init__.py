"""Loop control-plane package: tenant identity, agents, deploys, audit.

Public surface (so far):

* `auth` -- token verifier abstractions + an HS256 dev impl.
* `workspaces` -- workspace + membership domain (in-memory store).
* `api_keys` -- API key issue / verify / revoke (plaintext returned once).
"""

from loop_control_plane.api_keys import (
    ApiKey,
    ApiKeyError,
    ApiKeyService,
    IssuedApiKey,
)
from loop_control_plane.auth import (
    AuthError,
    HS256Verifier,
    IdentityClaims,
    TokenVerifier,
    has_scope,
)
from loop_control_plane.deploy import (
    BuildResult,
    Deploy,
    DeployArtifact,
    DeployController,
    DeployError,
    DeployPhase,
    ImageBuilder,
    ImageRegistry,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
    KubeClient,
)
from loop_control_plane.workspaces import (
    Membership,
    Role,
    Workspace,
    WorkspaceError,
    WorkspaceService,
)

__all__ = [
    "ApiKey",
    "ApiKeyError",
    "ApiKeyService",
    "AuthError",
    "BuildResult",
    "Deploy",
    "DeployArtifact",
    "DeployController",
    "DeployError",
    "DeployPhase",
    "HS256Verifier",
    "IdentityClaims",
    "ImageBuilder",
    "ImageRegistry",
    "InMemoryImageBuilder",
    "InMemoryImageRegistry",
    "InMemoryKubeClient",
    "IssuedApiKey",
    "KubeClient",
    "Membership",
    "Role",
    "TokenVerifier",
    "Workspace",
    "WorkspaceError",
    "WorkspaceService",
    "has_scope",
]
