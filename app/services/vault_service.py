from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

from dotenv import dotenv_values

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CacheEntry:
    data: dict[str, str]
    fetched_at: float


class VaultService:
    def __init__(self) -> None:
        env_file = os.getenv("INFISICAL_ENV_FILE", ".env")
        self._file_env = dotenv_values(env_file)
        self.project_id = self._get_config("INFISICAL_PROJECT_ID")
        self.environment = self._get_config("INFISICAL_ENV", "dev") or "dev"
        self.token = self._get_config("INFISICAL_TOKEN")
        self.client_id = self._get_config("INFISICAL_CLIENT_ID")
        self.client_secret = self._get_config("INFISICAL_CLIENT_SECRET")
        self.api_url = self._get_config("INFISICAL_API_URL")
        self.cache_ttl_seconds = int(self._get_config("INFISICAL_CACHE_TTL_SECONDS", "1800"))
        self.refresh_interval_seconds = int(self._get_config("INFISICAL_REFRESH_INTERVAL_SECONDS", "1800"))
        self.renew_interval_seconds = int(self._get_config("INFISICAL_TOKEN_REFRESH_INTERVAL_SECONDS", "600"))
        self.max_retries = max(1, int(self._get_config("INFISICAL_MAX_RETRIES", "3")))
        self.retry_backoff_seconds = max(0.25, float(self._get_config("INFISICAL_RETRY_BACKOFF_SECONDS", "1.0")))
        self._lock = threading.RLock()
        self._cache: dict[str, _CacheEntry] = {}
        self._known_paths: set[str] = set()
        self._binary = shutil.which("infisical")
        self._enabled = bool(self._binary and self.project_id and (self.token or (self.client_id and self.client_secret)))
        self._started = False

        if not self._enabled:
            logger.info(
                "infisical_disabled binary=%s project_id=%s token=%s client_id=%s client_secret=%s",
                bool(self._binary),
                bool(self.project_id),
                bool(self.token),
                bool(self.client_id),
                bool(self.client_secret),
            )
            return
        self.authenticate()
        self._start_background_loops()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def authenticate(self) -> bool:
        if not self._enabled:
            return False
        if self.token:
            return True
        if not self.client_id or not self.client_secret:
            return False
        for attempt in range(1, self.max_retries + 1):
            try:
                token = self._run_cli(
                    [
                        "login",
                        "--method",
                        "universal-auth",
                        "--client-id",
                        self.client_id,
                        "--client-secret",
                        self.client_secret,
                        "--silent",
                        "--plain",
                    ],
                    token=None,
                ).strip()
                if not token:
                    raise RuntimeError("empty infisical token")
                self.token = token
                logger.info("infisical_auth_success attempt=%s", attempt)
                return True
            except Exception as exc:
                logger.warning("infisical_auth_failed attempt=%s error=%s", attempt, exc.__class__.__name__)
                time.sleep(self.retry_backoff_seconds * attempt)
        return False

    def get_secret(self, path: str, force_refresh: bool = False) -> dict[str, str]:
        normalized = self._normalize_path(path)
        with self._lock:
            self._known_paths.add(normalized)
            cached = self._cache.get(normalized)
            if cached and not force_refresh and (time.monotonic() - cached.fetched_at) < self.cache_ttl_seconds:
                return dict(cached.data)

        data = self._fetch_secret_with_retry(normalized)
        if data is not None:
            with self._lock:
                self._cache[normalized] = _CacheEntry(data=data, fetched_at=time.monotonic())
            return dict(data)

        with self._lock:
            cached = self._cache.get(normalized)
            if cached:
                return dict(cached.data)
        return {}

    def invalidate_secret(self, path: str) -> None:
        normalized = self._normalize_path(path)
        with self._lock:
            self._cache.pop(normalized, None)

    def refresh_all_cached(self) -> None:
        with self._lock:
            paths = list(self._known_paths)
        for path in paths:
            self.get_secret(path, force_refresh=True)
        if paths:
            logger.info("infisical_secret_cache_refresh paths=%s", len(paths))

    def _fetch_secret_with_retry(self, path: str) -> dict[str, str] | None:
        if not self._enabled:
            return None
        for attempt in range(1, self.max_retries + 1):
            try:
                output: dict[str, str] = {}
                for key in self._path_keys(path):
                    value = self._get_secret_value(path=path, key=key)
                    if value:
                        output[key] = value
                return output
            except Exception as exc:
                logger.warning(
                    "infisical_secret_read_failed path=%s attempt=%s error=%s",
                    path,
                    attempt,
                    exc.__class__.__name__,
                )
                if not self._try_recover_auth():
                    time.sleep(self.retry_backoff_seconds * attempt)
        return None

    def renew_token(self) -> bool:
        if not self._enabled:
            return False
        if self.token and not self.client_id:
            return True
        try:
            self.token = ""
            ok = self.authenticate()
            if ok:
                logger.info("infisical_token_renewed")
            return ok
        except Exception as exc:
            logger.warning("infisical_token_renew_failed error=%s", exc.__class__.__name__)
            return self.authenticate()

    def _try_recover_auth(self) -> bool:
        if not self._enabled:
            return False
        return self.authenticate()

    def _start_background_loops(self) -> None:
        if self._started:
            return
        self._started = True

        def renew_loop() -> None:
            while True:
                time.sleep(self.renew_interval_seconds)
                self.renew_token()

        def refresh_loop() -> None:
            while True:
                time.sleep(self.refresh_interval_seconds)
                self.refresh_all_cached()

        threading.Thread(target=renew_loop, daemon=True).start()
        threading.Thread(target=refresh_loop, daemon=True).start()

    def _normalize_path(self, path: str) -> str:
        return path.strip().strip("/") or "ai"

    def _path_keys(self, path: str) -> list[str]:
        mapping: dict[str, list[str]] = {
            "ai": [
                "OPENAI_API_KEY",
                "GEMINI_API_KEY",
                "NEWSAPI_KEY",
                "ANTHROPIC_API_KEY",
            ],
            "database": [
                "POSTGRES_USER",
                "POSTGRES_PASSWORD",
                "POSTGRES_HOST",
                "POSTGRES_DB",
            ],
            "email": [
                "SENDGRID_API_KEY",
                "RESEND_API_KEY",
            ],
            "auth": [
                "AUTH0_SECRET",
                "JWT_SECRET",
                "TWILIO_ACCOUNT_SID",
                "TWILIO_AUTH_TOKEN",
                "TWILIO_WHATSAPP_NUMBER",
                "WHATSAPP_META_ACCESS_TOKEN",
                "WHATSAPP_META_PHONE_NUMBER_ID",
            ],
        }
        return mapping.get(path, [])

    def _get_secret_value(self, path: str, key: str) -> str | None:
        path_arg = path if path.startswith("/") else f"/{path}"
        output = self._run_cli(
            [
                "secrets",
                "get",
                key,
                "--projectId",
                self.project_id,
                "--env",
                self.environment,
                "--path",
                path_arg,
                "--plain",
                "--silent",
            ],
            token=self.token or None,
            allow_failure=True,
        )
        value = output.strip()
        return value or None

    def _run_cli(self, args: list[str], token: str | None, allow_failure: bool = False) -> str:
        if not self._binary:
            raise RuntimeError("infisical cli not found")

        env = os.environ.copy()
        env["INFISICAL_DISABLE_UPDATE_CHECK"] = "true"
        # Avoid passing empty values from process env; the CLI treats some as invalid config.
        env.pop("INFISICAL_API_URL", None)
        env.pop("INFISICAL_TOKEN", None)
        if self.api_url:
            env["INFISICAL_API_URL"] = self.api_url
        if token:
            env["INFISICAL_TOKEN"] = token

        proc = subprocess.run(
            [self._binary, *args],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip().lower()
            if "unauthorized" in stderr or "expired" in stderr:
                self.token = ""
            if allow_failure and self._is_secret_not_found_error(stderr):
                return ""
            short_err = " ".join(stderr.splitlines()[:2])[:240]
            raise RuntimeError(f"infisical cli failed: {proc.returncode} ({short_err})")
        return (proc.stdout or "").strip()

    def _get_config(self, key: str, default: str = "") -> str:
        value = os.getenv(key)
        if value is not None:
            return value.strip()
        file_value = self._file_env.get(key)
        if isinstance(file_value, str):
            return file_value.strip()
        return default

    @staticmethod
    def _is_secret_not_found_error(stderr: str) -> bool:
        markers = (
            "secret with name",
            "secret not found",
            "no secret found",
            "secret does not exist",
        )
        return any(marker in stderr for marker in markers)
