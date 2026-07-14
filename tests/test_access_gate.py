import json
import stat
from unittest.mock import patch

from caelus_terminal.access_gate import configure_gate, require_access
from caelus_terminal.cli import main


def test_access_gate_uses_three_hidden_attempts_and_never_stores_password(tmp_path):
    gate_path = tmp_path / "access-gate.json"
    configure_gate(gate_path, "test-only-password", salt_factory=lambda _size: b"a" * 16)

    saved = json.loads(gate_path.read_text())
    assert set(saved) == {"algorithm", "salt", "password_hash"}
    assert "test-only-password" not in gate_path.read_text()
    assert stat.S_IMODE(gate_path.stat().st_mode) == 0o600

    messages = []
    attempts = iter(["wrong", "still-wrong", "nope"])
    assert not require_access(gate_path, prompt=lambda _prompt: next(attempts), notify=messages.append)
    assert messages[-1] == "Access denied after 3 attempts."

    assert require_access(gate_path, prompt=lambda _prompt: "test-only-password", notify=messages.append)


def test_cli_blocks_normal_commands_after_three_wrong_gate_attempts(tmp_path, capsys):
    gate_path = tmp_path / "access-gate.json"
    configure_gate(gate_path, "test-only-password")

    with patch("caelus_terminal.cli.default_gate_path", return_value=gate_path), patch(
        "caelus_terminal.cli.getpass", side_effect=["wrong", "wrong", "wrong"]
    ):
        assert main(["--demo"]) == 1

    output = capsys.readouterr().out
    assert "Access denied after 3 attempts." in output
    assert "CAELUS // ACTIVE AGENT" not in output

    with patch("caelus_terminal.cli.default_gate_path", return_value=gate_path), patch(
        "caelus_terminal.cli.getpass", return_value="test-only-password"
    ):
        assert main(["--demo"]) == 0


def test_gate_set_command_uses_hidden_confirmation_and_is_exempt_from_gate(tmp_path, capsys):
    gate_path = tmp_path / "access-gate.json"

    with patch("caelus_terminal.cli.default_gate_path", return_value=gate_path), patch(
        "caelus_terminal.cli.getpass", side_effect=["test-only-password", "test-only-password"]
    ):
        assert main(["gate", "set"]) == 0

    assert gate_path.is_file()
    assert "test-only-password" not in gate_path.read_text()
    assert "Access gate configured." in capsys.readouterr().out
