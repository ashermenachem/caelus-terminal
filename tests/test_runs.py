import json
from unittest.mock import patch

from caelus_terminal.client import HermesClient


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode()


class _StreamResponse:
    def __init__(self, lines):
        self.lines = iter(lines)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def readline(self):
        return next(self.lines, b"")


def test_client_creates_persistent_hermes_session():
    client = HermesClient("http://127.0.0.1:8642/v1", "test-key")
    response = _Response({"session": {"id": "caelus-session", "title": "Caelus"}})

    with patch("caelus_terminal.client.urlopen", return_value=response) as urlopen:
        session = client.create_session("Caelus")

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8642/api/sessions"
    assert json.loads(request.data) == {"title": "Caelus"}
    assert request.get_header("Authorization") == "Bearer test-key"
    assert session["id"] == "caelus-session"




def test_client_loads_persistent_session_messages():
    client = HermesClient("http://127.0.0.1:8642/v1", "test-key")
    response = _Response({"session_id": "session-1", "data": [{"role": "user", "content": "Hello"}]})

    with patch("caelus_terminal.client.urlopen", return_value=response) as urlopen:
        messages = client.session_messages("session-1")

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8642/api/sessions/session-1/messages"
    assert messages == [{"role": "user", "content": "Hello"}]


def test_client_starts_streamable_run_and_stops_it():
    client = HermesClient("http://127.0.0.1:8642/v1", "test-key")
    with patch(
        "caelus_terminal.client.urlopen",
        side_effect=[_Response({"run_id": "run-1", "status": "started"}), _Response({"status": "stopping"})],
    ) as urlopen:
        run_id = client.start_run("Hello", session_id="session-1")
        client.stop_run(run_id)

    start, stop = [call.args[0] for call in urlopen.call_args_list]
    assert start.full_url == "http://127.0.0.1:8642/v1/runs"
    assert json.loads(start.data) == {"input": "Hello", "session_id": "session-1"}
    assert stop.full_url == "http://127.0.0.1:8642/v1/runs/run-1/stop"
    assert stop.data == b"{}"


def test_client_yields_sse_tool_and_completion_events():
    client = HermesClient("http://127.0.0.1:8642/v1", "test-key")
    stream = _StreamResponse(
        [
            b": keepalive\n",
            b'data: {"event":"tool.started","tool":"terminal","preview":"pytest"}\n',
            b"\n",
            b'data: {"event":"message.delta","delta":"Hello"}\n',
            b'data: {"event":"run.completed","output":"Hello"}\n',
            b"\n",
        ]
    )

    with patch("caelus_terminal.client.urlopen", return_value=stream) as urlopen:
        events = list(client.stream_run("run-1"))

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://127.0.0.1:8642/v1/runs/run-1/events"
    assert [event["event"] for event in events] == [
        "tool.started",
        "message.delta",
        "run.completed",
    ]
