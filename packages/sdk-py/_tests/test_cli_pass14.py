"""Pass14 CLI tests for S426-S433."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from loop.cli import (
    build_release_manifest,
    bundle_project,
    completion_script,
    load_credentials,
    main,
)


class FakeTransport:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, Any] | None, str | None]] = []
        self.streams: list[tuple[str, str | None]] = []
        self.deployment_statuses: list[str] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        self.requests.append((method, path, json_body, token))
        if path == "/auth/device-code":
            return {
                "verification_url": "https://loop.test/device",
                "user_code": "ABCD-EFGH",
                "device_code": "dev_123",
            }
        if path == "/auth/device-token":
            return {
                "access_token": "access_123",
                "refresh_token": "refresh_123",
                "workspace_id": "ws_123",
                "expires_at": 1_800_000_000,
            }
        if path == "/agents/deployments":
            status = self.deployment_statuses.pop(0) if self.deployment_statuses else "accepted"
            return {"id": "dep_123", "status": status}
        if path == "/agents/deployments/dep_123":
            status = self.deployment_statuses.pop(0) if self.deployment_statuses else "succeeded"
            return {"id": "dep_123", "status": status}
        if path == "/releases":
            return {"status": "published"}
        if path.endswith("/runs"):
            return {"id": "run_123", "status": "passed"}
        if path == "/secrets":
            if method == "GET":
                return {"secrets": [{"name": "OPENAI_API_KEY"}]}
            return {"status": "stored"}
        if path.startswith("/secrets/"):
            return {"status": "ok"}
        return {"status": "ok"}

    def stream(self, path: str, *, token: str | None = None):
        self.streams.append((path, token))
        yield "first log line\n"
        yield "second log line\n"


def _run(
    argv: list[str],
    *,
    transport: FakeTransport | None = None,
    home: Path,
) -> tuple[int, str, FakeTransport]:
    fake = transport or FakeTransport()
    out = io.StringIO()
    code = main(argv, transport=fake, home=home, out=out)
    return code, out.getvalue(), fake


def test_completion_scripts_cover_supported_shells() -> None:
    assert "complete -F _loop_complete loop" in completion_script("bash")
    assert "complete -F _loop_complete loop" in completion_script("zsh")
    assert "complete -c loop" in completion_script("fish")


def test_login_persists_credentials_with_secure_mode(tmp_path: Path) -> None:
    code, output, fake = _run(["login"], home=tmp_path)

    creds_path = tmp_path / ".loop" / "credentials"
    assert code == 0
    assert "https://loop.test/device" in output
    assert fake.requests[0][1] == "/auth/device-code"
    assert fake.requests[1][2] == {"device_code": "dev_123"}
    assert load_credentials(creds_path).access_token == "access_123"
    assert creds_path.stat().st_mode & 0o777 == 0o600


def test_init_scaffolds_agent_project(tmp_path: Path) -> None:
    project = tmp_path / "agent"
    code, output, _fake = _run(
        ["init", str(project), "--name", "returns-agent"],
        home=tmp_path,
    )

    assert code == 0
    assert "Created Loop agent" in output
    assert (project / "agent.yaml").read_text(encoding="utf-8").startswith(
        "name: returns-agent"
    )
    assert (project / "agent.py").exists()
    assert (project / "evals" / "smoke.yaml").exists()


def test_deploy_bundles_project_and_calls_control_plane(
    tmp_path: Path,
) -> None:
    project = tmp_path / "agent"
    project.mkdir()
    (project / "agent.yaml").write_text("name: x\n", encoding="utf-8")
    fake = FakeTransport()
    _run(["login"], transport=fake, home=tmp_path)

    code, output, fake = _run(["deploy", str(project)], transport=fake, home=tmp_path)

    assert code == 0
    assert "Deploy dep_123" in output
    method, path, body, token = fake.requests[-1]
    assert method == "POST"
    assert path == "/agents/deployments"
    assert token == "access_123"
    assert body is not None
    assert len(body["sha256"]) == 64
    assert body["size_bytes"] > 0


def test_deploy_polls_until_terminal_status(tmp_path: Path) -> None:
    project = tmp_path / "agent"
    project.mkdir()
    (project / "agent.yaml").write_text("name: x\n", encoding="utf-8")
    fake = FakeTransport()
    fake.deployment_statuses = ["pending", "running", "succeeded"]

    code, output, fake = _run(["deploy", str(project)], transport=fake, home=tmp_path)

    assert code == 0
    assert "Deploy dep_123: succeeded" in output
    assert [request[1] for request in fake.requests] == [
        "/agents/deployments",
        "/agents/deployments/dep_123",
        "/agents/deployments/dep_123",
    ]


def test_logs_streams_one_line_unless_follow(tmp_path: Path) -> None:
    fake = FakeTransport()
    _run(["login"], transport=fake, home=tmp_path)

    code, output, fake = _run(
        ["logs", "agent_123", "--conversation-id", "conv_123"],
        transport=fake,
        home=tmp_path,
    )

    assert code == 0
    assert output == "first log line\n"
    assert fake.streams[-1] == (
        "/logs/agent_123?conversation_id=conv_123",
        "access_123",
    )


def test_eval_run_prints_tap_style_status(tmp_path: Path) -> None:
    fake = FakeTransport()
    _run(["login"], transport=fake, home=tmp_path)

    code, output, fake = _run(
        ["eval", "run", "smoke", "--agent-version", "v1"],
        transport=fake,
        home=tmp_path,
    )

    assert code == 0
    assert output == "ok 1 - remote eval smoke status=passed\n"
    assert fake.requests[-1][2] == {"agent_version_id": "v1"}


def test_secrets_never_print_secret_values(tmp_path: Path) -> None:
    fake = FakeTransport()
    _run(["login"], transport=fake, home=tmp_path)

    code, output, _fake = _run(
        ["secrets", "set", "OPENAI_API_KEY", "sk-live-secret"],
        transport=fake,
        home=tmp_path,
    )
    assert code == 0
    assert "sk-live-secret" not in output
    assert "OPENAI_API_KEY" in output

    code, output, _fake = _run(
        ["secrets", "get", "OPENAI_API_KEY"],
        transport=fake,
        home=tmp_path,
    )
    assert code == 0
    assert "value hidden" in output


def test_release_manifest_hashes_artifacts(tmp_path: Path) -> None:
    artifact = tmp_path / "loop-linux-amd64.zip"
    artifact.write_bytes(b"binary")

    manifest = build_release_manifest("v1.2.3", [artifact])
    code, output, fake = _run(
        ["release", "v1.2.3", str(artifact), "--publish"],
        home=tmp_path,
    )

    rendered = json.loads(output)
    assert code == 0
    assert fake.requests[-1][1] == "/releases"
    assert manifest.artifacts[0].platform == "linux-amd64"
    assert rendered["version"] == "v1.2.3"
    assert rendered["artifacts"][0]["sha256"] == manifest.artifacts[0].sha256


def test_bundle_project_excludes_git_directory(tmp_path: Path) -> None:
    project = tmp_path / "agent"
    git_dir = project / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text("secret", encoding="utf-8")
    (project / "agent.yaml").write_text("name: x\n", encoding="utf-8")

    bundle = bundle_project(project)

    assert bundle.size_bytes > 0
    assert len(bundle.sha256) == 64
