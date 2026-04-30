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
    "ApiKeyError",
    "ApiKeyService",
    "AuthError",
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
    "WorkspaceError",
    "WorkspaceService",
    "aggregate",
    "has_scope",
]
