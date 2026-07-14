from pathlib import Path

from caelus_terminal.cli import default_connection_args, main


def test_default_connection_args_use_only_the_isolated_caelus_runtime(tmp_path):
    runtime_home = tmp_path / "runtime"
    runtime_home.mkdir()
    (runtime_home / ".env").write_text(
        "API_SERVER_HOST=127.0.0.1\nAPI_SERVER_PORT=9123\nAPI_SERVER_KEY=private-local-key\n"
    )

    assert default_connection_args(runtime_home) == [
        "--endpoint",
        "http://127.0.0.1:9123/v1",
        "--api-key",
        "private-local-key",
        "--interactive",
    ]


def test_demo_command_prints_matrix_terminal_dashboard(capsys):
    exit_code = main(["--demo", "--expanded-tools"])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "CAELUS AGENT" in output
    assert "• Reading runtime capabilities" in output
