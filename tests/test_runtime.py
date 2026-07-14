import os
from pathlib import Path

from caelus_terminal.runtime import (
    bootstrap_runtime,
    build_runtime_env,
    default_caelus_home,
    default_runtime_home,
    runtime_api_key,
    runtime_endpoint,
)


def test_default_caelus_paths_follow_the_launcher_environment(tmp_path, monkeypatch):
    home = tmp_path / "custom-caelus"
    monkeypatch.setenv("CAELUS_HOME", str(home))

    assert default_caelus_home() == home
    assert default_runtime_home() == home / "runtime"


def test_runtime_adapter_uses_a_separate_caelus_test_home(tmp_path):
    env = build_runtime_env(tmp_path)

    assert env["HERMES_HOME"] == str(tmp_path / "runtime")
    assert Path(env["HERMES_HOME"]).name == "runtime"
    assert ".hermes" not in env["HERMES_HOME"]


def test_bootstrap_creates_an_isolated_loopback_api_runtime(tmp_path):
    runtime_home = tmp_path / "caelus" / "runtime"

    details = bootstrap_runtime(runtime_home, port=8765, token_factory=lambda: "test-key")

    assert details.home == runtime_home
    assert runtime_endpoint(runtime_home) == "http://127.0.0.1:8765/v1"
    assert runtime_api_key(runtime_home) == "test-key"
    assert (runtime_home / ".env").read_text() == (
        "API_SERVER_ENABLED=true\n"
        "API_SERVER_HOST=127.0.0.1\n"
        "API_SERVER_PORT=8765\n"
        "API_SERVER_KEY=test-key\n"
        "API_SERVER_MODEL_NAME=caelus\n"
    )
    assert os.stat(runtime_home / ".env").st_mode & 0o777 == 0o600
    assert runtime_home.parent.stat().st_mode & 0o777 == 0o700


def test_bootstrap_reuses_existing_api_key_without_replacing_private_state(tmp_path):
    runtime_home = tmp_path / "caelus" / "runtime"
    bootstrap_runtime(runtime_home, token_factory=lambda: "first-key")
    (runtime_home / "state.db").write_text("private session state")

    bootstrap_runtime(runtime_home, token_factory=lambda: "replacement-key")

    assert runtime_api_key(runtime_home) == "first-key"
    assert (runtime_home / "state.db").read_text() == "private session state"


def test_bootstrap_never_changes_permissions_of_an_existing_parent_directory(tmp_path):
    existing_parent = tmp_path / "shared-parent"
    existing_parent.mkdir(mode=0o755)
    os.chmod(existing_parent, 0o755)

    bootstrap_runtime(existing_parent / "runtime", token_factory=lambda: "test-key")

    assert existing_parent.stat().st_mode & 0o777 == 0o755
