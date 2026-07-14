from unittest.mock import patch

from caelus_terminal.cli import main
from caelus_terminal.client import RuntimeDetails


def test_interactive_mode_uses_persistent_session_and_streams_tool_activity(capsys):
    with patch("caelus_terminal.cli.HermesClient") as client_class, patch(
        "builtins.input", side_effect=["Hello", "/quit"]
    ):
        client = client_class.return_value
        client.discover.return_value = RuntimeDetails(
            model_name="gpt-test",
            skills=["research"],
            mcp_servers=["mcp-github"],
            tools=["web_search"],
        )
        client.create_session.return_value = {"id": "session-1"}
        client.start_run.return_value = "run-1"
        client.stream_run.return_value = iter(
            [
                {"event": "tool.started", "tool": "web_search", "preview": "Caelus docs"},
                {"event": "run.completed", "output": "Connected reply"},
            ]
        )
        exit_code = main(
            [
                "--endpoint", "http://127.0.0.1:8642/v1", "--api-key", "test-key", "--interactive"
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert client.create_session.call_count == 1
    assert client.start_run.call_args.kwargs == {"session_id": "session-1"}
    assert client.stream_run.call_args.args == ("run-1",)
    assert "[tool] web_search: Caelus docs" in output
    assert "Connected reply" in output


def test_interactive_mode_resumes_persisted_session_messages(capsys):
    with patch("caelus_terminal.cli.HermesClient") as client_class, patch(
        "builtins.input", side_effect=["/quit"]
    ):
        client = client_class.return_value
        client.discover.return_value = RuntimeDetails("gpt-test", [], [], [])
        client.session_messages.return_value = [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ]
        exit_code = main(
            [
                "--endpoint", "http://127.0.0.1:8642/v1", "--api-key", "test-key",
                "--session-id", "session-1", "--interactive",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    client.create_session.assert_not_called()
    client.session_messages.assert_called_once_with("session-1")
    assert "You: Earlier question" in output
    assert "default: Earlier answer" in output
