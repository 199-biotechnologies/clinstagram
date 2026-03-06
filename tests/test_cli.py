from typer.testing import CliRunner
from clinstagram.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "instagram" in result.stdout.lower() or "clinstagram" in result.stdout.lower()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_auth_status_json(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0


def test_config_show_json(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0


def test_config_mode_set(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "mode", "official-only"])
    assert result.exit_code == 0
