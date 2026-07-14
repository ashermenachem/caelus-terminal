import json
from unittest.mock import patch

import pytest

from caelus_terminal.cli import main
from caelus_terminal.replay import ReplayValidationError, create_recipe, load_recipe


def test_guided_teach_creates_a_browser_recipe_with_required_verification(tmp_path):
    recipes = tmp_path / "replays"

    recipe = create_recipe(
        recipes,
        name="daily-assignments",
        domains=["portal.example.edu"],
        steps=["Open the assignments page", "Read assignments due this week"],
        verification="The page shows the current assignment list.",
    )

    saved = json.loads((recipes / "daily-assignments.json").read_text())
    assert recipe.name == "daily-assignments"
    assert saved["domains"] == ["portal.example.edu"]
    assert saved["side_effect_policy"] == "read-only"
    assert saved["verification"] == "The page shows the current assignment list."


def test_guided_teach_rejects_credential_like_steps(tmp_path):
    with pytest.raises(ReplayValidationError, match="credential-like"):
        create_recipe(
            tmp_path,
            name="bad-recipe",
            domains=["portal.example.edu"],
            steps=["Paste password: hunter2"],
            verification="Done",
        )


def test_replay_teach_and_preview_commands_use_a_private_recipe_directory(tmp_path, capsys):
    recipes = tmp_path / "replays"
    command = [
        "replay",
        "teach",
        "daily-assignments",
        "--recipes-dir",
        str(recipes),
        "--domain",
        "portal.example.edu",
        "--step",
        "Open assignments",
        "--verify",
        "Current assignments are visible",
    ]

    assert main(command) == 0
    assert "Taught replay: daily-assignments" in capsys.readouterr().out
    assert main(["replay", "preview", "daily-assignments", "--recipes-dir", str(recipes)]) == 0
    preview = capsys.readouterr().out
    assert "PREVIEW — daily-assignments" in preview
    assert "Read-only policy" in preview
    assert "portal.example.edu" in preview


def test_replay_run_sends_a_guarded_instruction_and_writes_a_receipt(tmp_path, capsys):
    recipes = tmp_path / "replays"
    create_recipe(
        recipes,
        name="daily-assignments",
        domains=["portal.example.edu"],
        steps=["Open assignments", "Read due dates"],
        verification="Current assignments are visible",
    )

    class FakeClient:
        def create_session(self, title):
            assert title == "Replay: daily-assignments"
            return {"id": "session-1"}

        def start_run(self, message, *, session_id):
            assert session_id == "session-1"
            assert "portal.example.edu" in message
            assert "Do not enter, request, reveal, or store passwords" in message
            assert "Do not submit forms" in message
            return "run-1"

        def stream_run(self, run_id):
            assert run_id == "run-1"
            yield {"event": "tool.completed", "tool": "browser", "preview": "Assignments visible"}
            yield {"event": "run.completed", "output": "Found two assignments."}

    with patch("caelus_terminal.cli.HermesClient", return_value=FakeClient()):
        assert main(
            [
                "replay",
                "run",
                "daily-assignments",
                "--recipes-dir",
                str(recipes),
                "--endpoint",
                "http://127.0.0.1:8642/v1",
                "--api-key",
                "test-key",
            ]
        ) == 0

    output = capsys.readouterr().out
    assert "REPLAY COMPLETE — daily-assignments" in output
    receipt = json.loads((recipes / "receipts" / "daily-assignments-run-1.json").read_text())
    assert receipt["status"] == "completed"
    assert receipt["verification"] == "Current assignments are visible"
    assert receipt["tool_events"] == ["browser: Assignments visible"]
    assert receipt["output"] == "Found two assignments."


def test_replay_run_uses_the_private_runtime_connection_by_default(tmp_path):
    recipes = tmp_path / "replays"
    create_recipe(
        recipes,
        name="daily-assignments",
        domains=["portal.example.edu"],
        steps=["Read assignments"],
        verification="Assignments are visible",
    )

    class FakeClient:
        def __init__(self, endpoint, api_key):
            assert endpoint == "http://127.0.0.1:8642/v1"
            assert api_key == "private-key"

        def create_session(self, title):
            return {"id": "session-1"}

        def start_run(self, message, *, session_id):
            return "run-1"

        def stream_run(self, run_id):
            yield {"event": "run.completed", "output": "Assignments are visible"}

    with patch("caelus_terminal.cli.runtime_endpoint", return_value="http://127.0.0.1:8642/v1"), patch(
        "caelus_terminal.cli.runtime_api_key", return_value="private-key"
    ), patch("caelus_terminal.cli.HermesClient", FakeClient):
        assert main(["replay", "run", "daily-assignments", "--recipes-dir", str(recipes)]) == 0


def test_load_recipe_rejects_path_traversal_names(tmp_path):
    with pytest.raises(ReplayValidationError, match="lowercase letters"):
        load_recipe(tmp_path, "../outside")
