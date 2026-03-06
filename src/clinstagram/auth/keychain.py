from __future__ import annotations

from typing import Optional

SERVICE_PREFIX = "clinstagram"

BACKEND_TOKEN_MAP = {
    "graph_ig": "graph_ig_token",
    "graph_fb": "graph_fb_token",
    "private": "private_session",
}


class SecretsStore:
    """Abstraction over secret storage. Supports 'memory' (testing), 'keyring' (production)."""

    def __init__(self, backend: str = "keyring"):
        self.backend = backend
        self._memory: dict[str, str] = {}

    def _key(self, account: str, name: str) -> str:
        return f"{SERVICE_PREFIX}/{account}/{name}"

    def set(self, account: str, name: str, value: str) -> None:
        key = self._key(account, name)
        if self.backend == "memory":
            self._memory[key] = value
        elif self.backend == "keyring":
            import keyring as kr

            kr.set_password(SERVICE_PREFIX, key, value)
        else:
            raise ValueError(f"Unknown secrets backend: {self.backend}")

    def get(self, account: str, name: str) -> Optional[str]:
        key = self._key(account, name)
        if self.backend == "memory":
            return self._memory.get(key)
        elif self.backend == "keyring":
            import keyring as kr

            return kr.get_password(SERVICE_PREFIX, key)
        return None

    def delete(self, account: str, name: str) -> None:
        key = self._key(account, name)
        if self.backend == "memory":
            self._memory.pop(key, None)
        elif self.backend == "keyring":
            import keyring as kr

            try:
                kr.delete_password(SERVICE_PREFIX, key)
            except kr.errors.PasswordDeleteError:
                pass

    def list_keys(self, account: str) -> list[str]:
        prefix = self._key(account, "")
        if self.backend == "memory":
            return [k.removeprefix(prefix) for k in self._memory if k.startswith(prefix)]
        return [
            name
            for name in ["graph_ig_token", "graph_fb_token", "private_session"]
            if self.get(account, name) is not None
        ]

    def has_backend(self, account: str, backend_name: str) -> bool:
        token_key = BACKEND_TOKEN_MAP.get(backend_name)
        if not token_key:
            return False
        return self.get(account, token_key) is not None
