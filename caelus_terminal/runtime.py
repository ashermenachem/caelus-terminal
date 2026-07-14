from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
from urllib.request import Request, urlopen


DEFAULT_PORT = 8642


def default_caelus_home() -> Path:
    return Path(os.environ.get("CAELUS_HOME", Path.home() / ".caelus")).expanduser()


def default_runtime_home() -> Path:
    return default_caelus_home() / "runtime"


@dataclass(frozen=True)
class RuntimeDetails:
    home: Path
    port: int


def build_runtime_env(caelus_home: Path) -> dict[str, str]:
    """Return an isolated runtime environment without changing the active Hermes home."""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(caelus_home / "runtime")
    return env


def _env_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    return values


def runtime_api_key(runtime_home: Path) -> str:
    key = _env_values(runtime_home / ".env").get("API_SERVER_KEY")
    if not key:
        raise RuntimeError(f"No Caelus API key configured in {runtime_home / '.env'}")
    return key


def runtime_endpoint(runtime_home: Path) -> str:
    values = _env_values(runtime_home / ".env")
    host = values.get("API_SERVER_HOST", "127.0.0.1")
    port = values.get("API_SERVER_PORT", str(DEFAULT_PORT))
    return f"http://{host}:{port}/v1"


def api_is_healthy(runtime_home: Path) -> bool:
    """Return whether the isolated local API server reports itself healthy."""
    health_url = runtime_endpoint(runtime_home).removesuffix("/v1") + "/health"
    request = Request(health_url, method="GET")
    try:
        with urlopen(request, timeout=2) as response:  # nosec B310: fixed loopback URL from runtime config
            return json.loads(response.read()).get("status") == "ok"
    except OSError:
        return False


def runtime_launch_command(
    runtime_home: Path, *, hermes_executable: str | None = None
) -> tuple[list[str], dict[str, str]]:
    """Return a gateway launch command bound to an isolated Caelus home."""
    executable = hermes_executable or shutil.which("hermes")
    if not executable:
        raise RuntimeError("Hermes Agent is required; install it before starting Caelus.")
    env = os.environ.copy()
    env["HERMES_HOME"] = str(runtime_home.expanduser())
    env.pop("API_SERVER_KEY", None)
    return [executable, "gateway", "run", "--force"], env


def _pid_path(runtime_home: Path) -> Path:
    return runtime_home / "caelus-api.pid"


def runtime_is_running(runtime_home: Path) -> bool:
    """Check only the PID recorded for this isolated Caelus runtime."""
    pid_path = _pid_path(runtime_home.expanduser())
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
        os.kill(pid, 0)
    except (ProcessLookupError, ValueError):
        return False
    return True


def start_runtime(runtime_home: Path, *, hermes_executable: str | None = None) -> int:
    """Start the isolated local Hermes API gateway and record only its PID."""
    runtime_home = runtime_home.expanduser()
    pid_path = _pid_path(runtime_home)
    if pid_path.exists():
        try:
            existing_pid = int(pid_path.read_text().strip())
            os.kill(existing_pid, 0)
        except (ProcessLookupError, ValueError):
            pid_path.unlink()
        else:
            raise RuntimeError(
                "Caelus runtime is already running; use `caelus runtime stop` first."
            )
    command, env = runtime_launch_command(runtime_home, hermes_executable=hermes_executable)
    log_dir = runtime_home / "logs"
    log_dir.mkdir(mode=0o700, exist_ok=True)
    log_path = log_dir / "api-server.log"
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(  # nosec B603: fixed executable + argv, no shell
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_path.write_text(f"{process.pid}\n")
    os.chmod(pid_path, 0o600)
    return process.pid


def stop_runtime(runtime_home: Path) -> bool:
    """Request graceful shutdown of the recorded isolated gateway process."""
    pid_path = _pid_path(runtime_home.expanduser())
    if not pid_path.exists():
        return False
    try:
        pid = int(pid_path.read_text().strip())
    except ValueError as error:
        raise RuntimeError(f"Invalid Caelus runtime PID file: {pid_path}") from error
    os.kill(pid, signal.SIGTERM)
    pid_path.unlink()
    return True


def bootstrap_runtime(
    runtime_home: Path,
    *,
    port: int = DEFAULT_PORT,
    token_factory=secrets.token_hex,
) -> RuntimeDetails:
    """Create an isolated Caelus runtime without reading or copying ~/.hermes."""
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    runtime_home = runtime_home.expanduser()
    caelus_home = runtime_home.parent
    created_caelus_home = not caelus_home.exists()
    caelus_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    if created_caelus_home:
        os.chmod(caelus_home, 0o700)
    runtime_home.mkdir(mode=0o700, exist_ok=True)
    os.chmod(runtime_home, 0o700)

    env_path = runtime_home / ".env"
    values = _env_values(env_path)
    key = values.get("API_SERVER_KEY") or token_factory()
    env_path.write_text(
        "API_SERVER_ENABLED=true\n"
        "API_SERVER_HOST=127.0.0.1\n"
        f"API_SERVER_PORT={port}\n"
        f"API_SERVER_KEY={key}\n"
        "API_SERVER_MODEL_NAME=caelus\n"
    )
    os.chmod(env_path, 0o600)
    return RuntimeDetails(home=runtime_home, port=port)
