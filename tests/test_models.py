import json
from clinstagram.models import CLIResponse, CLIError, ExitCode


def test_success_response():
    r = CLIResponse(data={"thread_id": "123"}, backend_used="graph_fb")
    assert r.exit_code == ExitCode.SUCCESS
    d = json.loads(r.to_json())
    assert d["data"]["thread_id"] == "123"
    assert d["backend_used"] == "graph_fb"


def test_error_response():
    e = CLIError(
        exit_code=ExitCode.AUTH_ERROR,
        error="session_expired",
        remediation="Run: clinstagram auth login",
    )
    d = json.loads(e.to_json())
    assert d["exit_code"] == 2
    assert d["remediation"] == "Run: clinstagram auth login"


def test_all_exit_codes():
    assert ExitCode.SUCCESS == 0
    assert ExitCode.USER_ERROR == 1
    assert ExitCode.AUTH_ERROR == 2
    assert ExitCode.RATE_LIMITED == 3
    assert ExitCode.API_ERROR == 4
    assert ExitCode.CHALLENGE_REQUIRED == 5
    assert ExitCode.POLICY_BLOCKED == 6
    assert ExitCode.CAPABILITY_UNAVAILABLE == 7
