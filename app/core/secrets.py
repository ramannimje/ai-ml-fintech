from __future__ import annotations
from collections.abc import Iterator, Mapping

from app.services.vault_service import VaultService

vault = VaultService()

_SECRET_PATHS = {
    "ai": "ai",
    "database": "database",
    "email": "email",
    "auth": "auth",
}


class SecretNamespace(Mapping[str, str]):
    def __init__(self, namespace: str):
        if namespace not in _SECRET_PATHS:
            raise ValueError(f"Unsupported namespace: {namespace}")
        self.namespace = namespace

    def read(self, force_refresh: bool = False) -> dict[str, str]:
        return vault.get_secret(_SECRET_PATHS[self.namespace], force_refresh=force_refresh)

    def invalidate(self) -> None:
        vault.invalidate_secret(_SECRET_PATHS[self.namespace])

    def __getitem__(self, key: str) -> str:
        data = self.read()
        if key not in data:
            raise KeyError(key)
        return data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.read())

    def __len__(self) -> int:
        return len(self.read())


AI_SECRETS = SecretNamespace("ai")
DB_SECRETS = SecretNamespace("database")
EMAIL_SECRETS = SecretNamespace("email")
AUTH_SECRETS = SecretNamespace("auth")


def get_secret_value(
    namespace: SecretNamespace,
    key: str,
    env_fallback: str | None = None,
    default: str | None = None,
    force_refresh: bool = False,
) -> str | None:
    fallback_keys: list[str] = []
    if env_fallback:
        fallback_keys.append(env_fallback)
    return vault.get_value(
        path=_SECRET_PATHS[namespace.namespace],
        key=key,
        env_fallbacks=fallback_keys,
        default=default,
        force_refresh=force_refresh,
    )
