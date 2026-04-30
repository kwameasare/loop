"""Per-service Dockerfile renderer for the deploy pipeline (S262).

The deploy controller (S266) hands the build step a
:class:`DockerfileSpec` and gets back a string Dockerfile. In
production the BuildKit / kaniko backend writes the rendered file to
a build context; for tests we simply assert the string contents.

Why a renderer instead of static Dockerfiles per service? Two
reasons:

1. **Pinned bases.** ``base_image`` and ``runtime_image`` come from
   ``loop_implementation/architecture/`` and must be uniform across
   cp-api, dp-runtime, dp-tool-host, dp-kb-engine, etc. A
   centralised renderer enforces the pin.
2. **Distroless contract.** The runtime image is always
   ``gcr.io/distroless/python3-debian12`` (or a workspace-pinned
   override). The renderer rejects non-distroless runtime bases.

The renderer is intentionally string-based. We don't depend on
``jinja2``: the Dockerfile is small enough that a few f-strings make
the contract clearer and easier to audit.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "DEFAULT_BASE_IMAGE",
    "DEFAULT_RUNTIME_IMAGE",
    "DockerfileError",
    "DockerfileSpec",
    "render_dockerfile",
]


DEFAULT_BASE_IMAGE: str = "python:3.14-slim-bookworm"
DEFAULT_RUNTIME_IMAGE: str = "gcr.io/distroless/python3-debian12:nonroot"

# A "distroless"-style image must be either gcr.io/distroless or a
# pinned chainguard variant. Anything that ships /bin/sh fails the
# CIS-bench rule we wrote in security/SECURITY.md.
_DISTROLESS_PATTERN: re.Pattern[str] = re.compile(
    r"^(gcr\.io/distroless/|cgr\.dev/chainguard/python|registry\.loop\.test/distroless/)"
)


class DockerfileError(ValueError):
    """Raised when a spec violates the deploy-image contract."""


class DockerfileSpec(BaseModel):
    """Frozen spec the renderer accepts."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    service: str = Field(min_length=1, max_length=64)
    package_dir: str = Field(min_length=1, max_length=128)
    entrypoint_module: str = Field(min_length=1, max_length=128)
    base_image: str = Field(default=DEFAULT_BASE_IMAGE, min_length=1)
    runtime_image: str = Field(default=DEFAULT_RUNTIME_IMAGE, min_length=1)
    extra_apt_packages: tuple[str, ...] = ()
    expose_port: int | None = Field(default=None, ge=1, le=65535)

    @field_validator("service")
    @classmethod
    def _service_slug(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", v):
            raise ValueError(
                "service must be lowercase, start with a letter, "
                "and contain only [a-z0-9-]"
            )
        return v

    @field_validator("runtime_image")
    @classmethod
    def _distroless_runtime(cls, v: str) -> str:
        if not _DISTROLESS_PATTERN.match(v):
            raise ValueError(
                f"runtime_image {v!r} must be a pinned distroless variant"
            )
        return v

    @field_validator("extra_apt_packages")
    @classmethod
    def _no_dangerous_apt(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for pkg in v:
            if not re.fullmatch(r"[a-z0-9.+-]+", pkg):
                raise ValueError(f"apt package {pkg!r} fails strict regex")
        return v


def render_dockerfile(spec: DockerfileSpec) -> str:
    """Return the rendered Dockerfile as a single string."""
    apt_block = _render_apt(spec.extra_apt_packages)
    expose = (
        f"EXPOSE {spec.expose_port}\n" if spec.expose_port is not None else ""
    )
    if "/" in spec.entrypoint_module or " " in spec.entrypoint_module:
        raise DockerfileError(
            f"entrypoint_module must be a python module path, "
            f"got {spec.entrypoint_module!r}"
        )
    return (
        f"# Dockerfile for {spec.service} (rendered by render_dockerfile).\n"
        f"# DO NOT EDIT by hand; regenerate via the deploy pipeline.\n"
        f"FROM {spec.base_image} AS builder\n"
        f"WORKDIR /build\n"
        f"COPY pyproject.toml uv.lock* ./\n"
        f"COPY {spec.package_dir} ./{spec.package_dir}\n"
        f"{apt_block}"
        f"RUN pip install --no-cache-dir --target /opt/python ./{spec.package_dir}\n"
        f"\n"
        f"FROM {spec.runtime_image}\n"
        f"WORKDIR /app\n"
        f"COPY --from=builder /opt/python /opt/python\n"
        f"ENV PYTHONPATH=/opt/python\n"
        f"ENV PYTHONUNBUFFERED=1\n"
        f"USER nonroot\n"
        f"{expose}"
        f'ENTRYPOINT ["python", "-m", "{spec.entrypoint_module}"]\n'
    )


def _render_apt(packages: Iterable[str]) -> str:
    pkg_list = sorted(packages)
    if not pkg_list:
        return ""
    joined = " ".join(pkg_list)
    return (
        "RUN apt-get update \\\n"
        f"    && apt-get install -y --no-install-recommends {joined} \\\n"
        "    && rm -rf /var/lib/apt/lists/*\n"
    )
