from __future__ import annotations

import subprocess

from app.services.vault_service import VaultService


def test_infisical_service_caches_and_force_refresh(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, env, check, capture_output, text):
        calls.append(cmd)
        if cmd[1] == "secrets" and cmd[2] == "get":
            key = cmd[3]
            if key == "OPENROUTER_API_KEY":
                return subprocess.CompletedProcess(cmd, 0, "k1\n", "")
            return subprocess.CompletedProcess(cmd, 1, "", "secret not found")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr("app.services.vault_service.shutil.which", lambda _: "/usr/local/bin/infisical")
    monkeypatch.setattr("app.services.vault_service.subprocess.run", fake_run)
    monkeypatch.setattr(VaultService, "_start_background_loops", lambda self: None)
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "p1")
    monkeypatch.setenv("INFISICAL_ENV", "dev")
    monkeypatch.setenv("INFISICAL_TOKEN", "tok")

    service = VaultService()

    first = service.get_secret("ai")
    second = service.get_secret("ai")
    refreshed = service.get_secret("ai", force_refresh=True)

    assert first["OPENROUTER_API_KEY"] == "k1"
    assert second["OPENROUTER_API_KEY"] == "k1"
    assert refreshed["OPENROUTER_API_KEY"] == "k1"
    assert sum(1 for c in calls if len(c) > 3 and c[1:4] == ["secrets", "get", "OPENROUTER_API_KEY"]) == 2


def test_infisical_service_reauth_on_renew(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(cmd, env, check, capture_output, text):
        calls.append(cmd)
        if cmd[1] == "login":
            return subprocess.CompletedProcess(cmd, 0, "new-token\n", "")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr("app.services.vault_service.shutil.which", lambda _: "/usr/local/bin/infisical")
    monkeypatch.setattr("app.services.vault_service.subprocess.run", fake_run)
    monkeypatch.setattr(VaultService, "_start_background_loops", lambda self: None)
    monkeypatch.setenv("INFISICAL_PROJECT_ID", "p1")
    monkeypatch.setenv("INFISICAL_ENV", "dev")
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    monkeypatch.setenv("INFISICAL_CLIENT_ID", "cid")
    monkeypatch.setenv("INFISICAL_CLIENT_SECRET", "csecret")

    service = VaultService()
    assert service.token == "new-token"
    assert service.renew_token() is True
    assert service.token == "new-token"


def test_infisical_service_disabled_without_required_env(monkeypatch):
    monkeypatch.setattr("app.services.vault_service.shutil.which", lambda _: "/usr/local/bin/infisical")
    monkeypatch.setenv("INFISICAL_ENV_FILE", "/tmp/non-existent-infisical.env")
    monkeypatch.delenv("INFISICAL_PROJECT_ID", raising=False)
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    monkeypatch.delenv("INFISICAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("INFISICAL_CLIENT_SECRET", raising=False)

    service = VaultService()
    assert service.enabled is False
    assert service.get_secret("ai") == {}


def test_infisical_service_reads_from_dotenv_when_shell_env_missing(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "INFISICAL_PROJECT_ID=p1",
                "INFISICAL_ENV=dev",
                "INFISICAL_TOKEN=tok",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("INFISICAL_ENV_FILE", str(env_file))
    monkeypatch.delenv("INFISICAL_PROJECT_ID", raising=False)
    monkeypatch.delenv("INFISICAL_TOKEN", raising=False)
    monkeypatch.delenv("INFISICAL_CLIENT_ID", raising=False)
    monkeypatch.delenv("INFISICAL_CLIENT_SECRET", raising=False)
    monkeypatch.setattr("app.services.vault_service.shutil.which", lambda _: "/usr/local/bin/infisical")
    monkeypatch.setattr(VaultService, "_start_background_loops", lambda self: None)

    service = VaultService()
    assert service.enabled is True
