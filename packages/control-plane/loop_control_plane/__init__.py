"""Loop control-plane package: tenant identity, agents, deploys, audit.

Public surface (so far):

* `auth` -- token verifier abstractions + an HS256 dev impl.
* `workspaces` -- workspace + membership domain (in-memory store).
* `api_keys` -- API key issue / verify / revoke (plaintext returned once).
* `authorize` -- workspace-scope RBAC helper used by every facade.
* `workspace_api` -- HTTP-shaped facade over the workspace service.
* `api_keys_api` -- HTTP-shaped facade over the API-key service.
* `errors` -- canonical LOOP-API-* error mapper.
* `logging` -- structlog wiring + per-request log context.
"""

from loop_control_plane.api_keys import (
    ApiKey,
    ApiKeyError,
    ApiKeyService,
    IssuedApiKey,
)
from loop_control_plane.api_keys_api import ApiKeyAPI
from loop_control_plane.auth import (
    AuthError,
    HS256Verifier,
    IdentityClaims,
    TokenVerifier,
    has_scope,
)
from loop_control_plane.authorize import (
    AuthorisationError,
    authorize_workspace_access,
    role_satisfies,
)
from loop_control_plane.billing import (
    BillingError,
    BillingService,
    InMemoryStripe,
    StripeClient,
    StripeCustomer,
    StripeInvoice,
    StripeUsageRecord,
)
from loop_control_plane.deploy import (
    BaselineRegistry,
    BuildResult,
    Deploy,
    DeployArtifact,
    DeployController,
    DeployError,
    DeployPhase,
    EvalGate,
    EvalReport,
    ImageBuilder,
    ImageRegistry,
    InMemoryBaselineRegistry,
    InMemoryEvalGate,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
    KubeClient,
)
from loop_control_plane.errors import (
    LoopApiError,
    map_to_loop_api_error,
)
from loop_control_plane.inbox import (
    InboxError,
    InboxItem,
    InboxQueue,
    InboxStatus,
)
from loop_control_plane.inbox_api import InboxAPI
from loop_control_plane.usage import (
    DAY_MS,
    UsageEvent,
    UsageLedger,
    UsageRollup,
    aggregate,
)
from loop_control_plane.workspace_api import WorkspaceAPI
from loop_control_plane.workspaces import (
    Membership,
    Role,
    Workspace,
    WorkspaceError,
    WorkspaceService,
)

__all__ = [
    "DAY_MS",
    "ApiKey",
    "ApiKeyAPI",
    "ApiKeyError",
    "ApiKeyService",
    "AuthError",
    "AuthorisationError",
    "BaselineRegistry",
    "BillingError",
    "BillingService",
    "BuildResult",
    "Deploy",
    "DeployArtifact",
    "DeployController",
    "DeployError",
    "DeployPhase",
    "EvalGate",
    "EvalReport",
    "HS256Verifier",
    "IdentityClaims",
    "ImageBuilder",
    "ImageRegistry",
    "InMemoryBaselineRegistry",
    "InMemoryEvalGate",
    "InMemoryImageBuilder",
    "InMemoryImageRegistry",
    "InMemoryKubeClient",
    "InMemoryStripe",
    "InboxAPI",
    "InboxError",
    "InboxItem",
    "InboxQueue",
    "InboxStatus",
    "IssuedApiKey",
    "KubeClient",
    "LoopApiError",
    "Membership",
    "Role",
    "StripeClient",
    "StripeCustomer",
    "StripeInvoice",
    "StripeUsageRecord",
    "TokenVerifier",
    "UsageEvent",
    "UsageLedger",
    "UsageRollup",
    "Workspace",
    "WorkspaceAPI",
    "WorkspaceError",
    "WorkspaceService",
    "aggregate",
    "authorize_workspace_access",
    "has_scope",
    "map_to_loop_api_error",
    "role_satisfies",
]
