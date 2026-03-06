from __future__ import annotations

from enum import IntEnum
from typing import Any, Optional

from pydantic import BaseModel


class ExitCode(IntEnum):
    SUCCESS = 0
    USER_ERROR = 1
    AUTH_ERROR = 2
    RATE_LIMITED = 3
    API_ERROR = 4
    CHALLENGE_REQUIRED = 5
    POLICY_BLOCKED = 6
    CAPABILITY_UNAVAILABLE = 7


class CLIResponse(BaseModel):
    exit_code: ExitCode = ExitCode.SUCCESS
    data: Any = None
    backend_used: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()


class CLIError(BaseModel):
    exit_code: ExitCode
    error: str
    remediation: Optional[str] = None
    retry_after: Optional[int] = None
    challenge_type: Optional[str] = None
    challenge_url: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)
