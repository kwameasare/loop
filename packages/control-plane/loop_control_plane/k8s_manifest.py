"""Kubernetes manifest renderer (S264).

Produces a `Deployment + Service + HorizontalPodAutoscaler` triple from a
small, type-checked input. The output is a single multi-document YAML
string that ``kubectl apply -f`` (or ``kubeval``) can consume.

We render YAML by hand rather than pulling in jinja or k8s python clients:

* we only ever emit a tiny known schema, so the implementation is ~120
  lines and depends on stdlib + PyYAML (already in the workspace);
* a generated YAML with no comments and sorted keys is easier to diff in
  PR review and easier to checksum in deploy provenance.

The renderer rejects inputs that would produce manifests rejected by the
API server (zero replicas, non-DNS names, env-var keys with whitespace).
This catches real misconfigurations early without depending on a live
``kubectl`` to validate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

_DNS1123 = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


class ManifestError(ValueError):
    """Raised when the input cannot be rendered into valid manifests."""


def _validate_name(name: str, *, kind: str) -> None:
    if not _DNS1123.match(name) or len(name) > 63:
        raise ManifestError(
            f"{kind} name must match DNS-1123 (lowercase, <=63 chars): {name!r}"
        )


@dataclass(frozen=True)
class ManifestSpec:
    """Inputs for the deployment trio."""

    name: str
    namespace: str
    image: str
    replicas: int = 1
    container_port: int = 8080
    service_port: int = 80
    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "128Mi"
    memory_limit: str = "512Mi"
    env: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    min_replicas: int = 1
    max_replicas: int = 5
    target_cpu_utilisation_pct: int = 70

    def __post_init__(self) -> None:
        _validate_name(self.name, kind="deployment")
        _validate_name(self.namespace, kind="namespace")
        if not self.image or ":" not in self.image:
            raise ManifestError(
                "image must be a fully-qualified ref including a tag"
            )
        if self.replicas < 1:
            raise ManifestError("replicas must be >= 1")
        if not (1 <= self.container_port <= 65535):
            raise ManifestError("container_port must be 1..65535")
        if not (1 <= self.service_port <= 65535):
            raise ManifestError("service_port must be 1..65535")
        if self.min_replicas < 1 or self.max_replicas < self.min_replicas:
            raise ManifestError(
                "min_replicas must be >=1 and <= max_replicas"
            )
        if not (1 <= self.target_cpu_utilisation_pct <= 100):
            raise ManifestError(
                "target_cpu_utilisation_pct must be 1..100"
            )
        for key in self.env:
            if not key or any(ch.isspace() for ch in key):
                raise ManifestError(f"env key invalid: {key!r}")


def _common_labels(spec: ManifestSpec) -> dict[str, str]:
    base = {
        "app.kubernetes.io/name": spec.name,
        "app.kubernetes.io/managed-by": "loop",
    }
    base.update(spec.labels)
    return base


def _deployment(spec: ManifestSpec) -> dict[str, object]:
    labels = _common_labels(spec)
    env_list = [
        {"name": k, "value": v} for k, v in sorted(spec.env.items())
    ]
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": spec.name,
            "namespace": spec.namespace,
            "labels": labels,
        },
        "spec": {
            "replicas": spec.replicas,
            "selector": {"matchLabels": labels},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "containers": [
                        {
                            "name": spec.name,
                            "image": spec.image,
                            "ports": [
                                {"containerPort": spec.container_port}
                            ],
                            "env": env_list,
                            "resources": {
                                "requests": {
                                    "cpu": spec.cpu_request,
                                    "memory": spec.memory_request,
                                },
                                "limits": {
                                    "cpu": spec.cpu_limit,
                                    "memory": spec.memory_limit,
                                },
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/healthz",
                                    "port": spec.container_port,
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 10,
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/healthz",
                                    "port": spec.container_port,
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 30,
                            },
                        }
                    ]
                },
            },
        },
    }


def _service(spec: ManifestSpec) -> dict[str, object]:
    labels = _common_labels(spec)
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": spec.name,
            "namespace": spec.namespace,
            "labels": labels,
        },
        "spec": {
            "type": "ClusterIP",
            "selector": labels,
            "ports": [
                {
                    "name": "http",
                    "port": spec.service_port,
                    "targetPort": spec.container_port,
                    "protocol": "TCP",
                }
            ],
        },
    }


def _hpa(spec: ManifestSpec) -> dict[str, object]:
    labels = _common_labels(spec)
    return {
        "apiVersion": "autoscaling/v2",
        "kind": "HorizontalPodAutoscaler",
        "metadata": {
            "name": spec.name,
            "namespace": spec.namespace,
            "labels": labels,
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": spec.name,
            },
            "minReplicas": spec.min_replicas,
            "maxReplicas": spec.max_replicas,
            "metrics": [
                {
                    "type": "Resource",
                    "resource": {
                        "name": "cpu",
                        "target": {
                            "type": "Utilization",
                            "averageUtilization": spec.target_cpu_utilisation_pct,
                        },
                    },
                }
            ],
        },
    }


def render(spec: ManifestSpec) -> str:
    """Render the Deployment+Service+HPA triple as YAML."""

    docs = [_deployment(spec), _service(spec), _hpa(spec)]
    return yaml.safe_dump_all(docs, sort_keys=True, default_flow_style=False)


def render_documents(spec: ManifestSpec) -> tuple[dict[str, object], ...]:
    """Return the parsed dicts (for tests / programmatic use)."""

    return (_deployment(spec), _service(spec), _hpa(spec))


__all__ = [
    "ManifestError",
    "ManifestSpec",
    "render",
    "render_documents",
]
