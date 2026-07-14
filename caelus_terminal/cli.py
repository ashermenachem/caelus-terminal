from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import shutil
import sys
import time

from .access_gate import (
    AccessGateError,
    configure_gate,
    default_gate_path,
    gate_is_configured,
    require_access,
)
from .client import HermesClient
from .dashboard import DashboardState, render_dashboard
from .helptext import runtime_help
from .runtime import (
    api_is_healthy,
    bootstrap_runtime,
    default_runtime_home,
    runtime_endpoint,
    runtime_api_key,
    runtime_is_running,
    start_runtime,
    stop_runtime,
)
from .replay import (
    ReplayValidationError,
    build_run_instruction,
    create_recipe,
    default_recipes_dir,
    load_recipe,
    render_preview,
    write_receipt,
)
from .templates import TemplateValidationError, export_template, import_template
from .trajectory import TrajectoryDriver, TrajectoryError, recording_path


def _redraw_chat(state: DashboardState, *, busy: bool = False) -> int:
    width = max(60, shutil.get_terminal_size(fallback=(100, 30)).columns)
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    print(render_dashboard(state, width=width, show_tool_activity=True, busy=busy, show_composer=False))
    return width


def _read_composer(width: int) -> str:
    border = "─" * (width - 2)
    print("┌" + " MESSAGE CAELUS ".center(width - 2, "─") + "┐")
    print(f"│ {'Type your message. /help for controls, /quit to exit.':<{width - 4}} │")
    print("├" + border + "┤")
    try:
        return input("│ You › ").strip()
    finally:
        print("└" + border + "┘")


def demo_state() -> DashboardState:
    return DashboardState(
        agent_name="Nova",
        model_name="runtime not connected",
        context_percent=0,
        runtime_seconds=0,
        skills=["Research", "Files", "Memory"],
        mcp_servers=["none configured"],
        tools=["Web", "Terminal", "Browser"],
        tool_activity=["Reading runtime capabilities", "Waiting for an agent connection"],
    )


def runtime_init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create an isolated Caelus runtime")
    parser.add_argument(
        "--runtime-home",
        type=Path,
        default=default_runtime_home(),
        help="dedicated HERMES_HOME for Caelus",
    )
    parser.add_argument("--runtime-port", type=int, default=8642)
    args = parser.parse_args(argv)
    details = bootstrap_runtime(args.runtime_home, port=args.runtime_port)
    print(f"Created isolated Caelus runtime at {details.home}")
    print(f"HERMES_HOME={details.home}")
    print(f"API endpoint: {runtime_endpoint(details.home)}")
    print("No provider credentials or personal Hermes state were copied.")
    print(f"Next: HERMES_HOME={details.home} hermes setup")
    return 0


def runtime_control(argv: list[str], *, action: str) -> int:
    parser = argparse.ArgumentParser(description=f"{action.title()} the isolated Caelus runtime")
    parser.add_argument(
        "--runtime-home",
        type=Path,
        default=default_runtime_home(),
        help="dedicated HERMES_HOME for Caelus",
    )
    args = parser.parse_args(argv)
    if action == "start":
        pid = start_runtime(args.runtime_home)
        print(f"Started isolated Caelus runtime (PID {pid}).")
        return 0
    if action == "status":
        process = "running" if runtime_is_running(args.runtime_home) else "stopped"
        api = "healthy" if api_is_healthy(args.runtime_home) else "unreachable"
        print(f"process: {process}")
        print(f"api: {api}")
        return 0
    if stop_runtime(args.runtime_home):
        print("Stopped isolated Caelus runtime.")
    else:
        print("Caelus runtime was not running.")
    return 0


def template_control(argv: list[str], *, action: str) -> int:
    parser = argparse.ArgumentParser(description=f"{action.title()} a safe Caelus agent template")
    if action == "export":
        parser.add_argument("--source", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
    else:
        parser.add_argument("--input", type=Path, required=True)
        parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if action == "export":
            export_template(args.source, args.output)
            print(f"Exported safe Caelus agent template to {args.output}")
        else:
            import_template(args.input, args.destination)
            print(f"Imported safe Caelus agent template to {args.destination}")
    except TemplateValidationError as exc:
        parser.error(str(exc))
    return 0


def gate_control(argv: list[str], *, gate_path: Path) -> int:
    parser = argparse.ArgumentParser(description="Configure the local Caelus access gate")
    parser.add_argument("action", choices=["set", "status"])
    args = parser.parse_args(argv)
    if args.action == "status":
        print("Access gate: configured" if gate_is_configured(gate_path) else "Access gate: not configured")
        return 0
    try:
        if gate_is_configured(gate_path) and not require_access(gate_path, prompt=getpass, notify=print):
            return 1
        password = getpass("Set Caelus access password: ")
        confirmation = getpass("Confirm Caelus access password: ")
        if password != confirmation:
            print("Passwords did not match; access gate was not changed.")
            return 1
        configure_gate(gate_path, password)
    except AccessGateError as exc:
        print(f"Caelus access gate was not changed: {exc}")
        return 1
    print("Access gate configured.")
    return 0


def default_connection_args(runtime_home: Path | None = None) -> list[str]:
    """Build the private, local connection used by a plain ``caelus`` launch."""
    home = runtime_home or default_runtime_home()
    return [
        "--endpoint",
        runtime_endpoint(home),
        "--api-key",
        runtime_api_key(home),
        "--interactive",
    ]


def replay_control(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Teach, preview, and safely run Caelus Replay recipes")
    subcommands = parser.add_subparsers(dest="action", required=True)

    teach = subcommands.add_parser("teach", help="save a guided, read-only browser replay")
    teach.add_argument("name", help="lowercase replay name, such as daily-assignments")
    teach.add_argument("--recipes-dir", type=Path, default=default_recipes_dir())
    teach.add_argument("--domain", action="append", required=True, help="allowed hostname; repeatable")
    teach.add_argument("--step", action="append", required=True, help="read-only workflow step; repeatable")
    teach.add_argument("--verify", required=True, help="observable success condition")

    for action in ("preview", "run"):
        command = subcommands.add_parser(action)
        command.add_argument("name")
        command.add_argument("--recipes-dir", type=Path, default=default_recipes_dir())
        if action == "run":
            command.add_argument("--endpoint", help="local Hermes API endpoint ending in /v1")
            command.add_argument("--api-key", help="local Hermes API server key")

    record = subcommands.add_parser("record", help="record or replay concrete browser actions with Cua Driver")
    record.add_argument("record_action", choices=["start", "stop", "play"])
    record.add_argument("name")
    record.add_argument("--recordings-dir", type=Path, default=Path.home() / ".caelus" / "replays" / "recordings")

    args = parser.parse_args(argv)
    try:
        if args.action == "record":
            output_dir = recording_path(args.recordings_dir, args.name)
            driver = TrajectoryDriver()
            if args.record_action == "start":
                driver.start(output_dir)
                print(f"Recording started: {args.name}")
                print("Perform only read-only browser actions with Caelus/Hermes, then run `caelus replay record stop <name>`.")
                return 0
            if args.record_action == "stop":
                driver.stop()
                print(f"Recording stopped: {args.name}")
                return 0
            result = driver.replay(output_dir)
            count = result.get("replayed", result.get("count", "recorded"))
            print(f"Replay executed: {args.name} ({count} recorded actions)")
            return 0
        if args.action == "teach":
            recipe = create_recipe(
                args.recipes_dir,
                name=args.name,
                domains=args.domain,
                steps=args.step,
                verification=args.verify,
            )
            print(f"Taught replay: {recipe.name}")
            print(f"Saved: {args.recipes_dir / (recipe.name + '.json')}")
            print("Policy: read-only. Replay will never submit, message, purchase, delete, publish, or enter secrets.")
            return 0

        recipe = load_recipe(args.recipes_dir, args.name)
        if args.action == "preview":
            print(render_preview(recipe))
            return 0

        if not args.endpoint and not args.api_key:
            runtime_home = default_runtime_home()
            args.endpoint = runtime_endpoint(runtime_home)
            args.api_key = runtime_api_key(runtime_home)
        elif not args.endpoint or not args.api_key:
            parser.error("replay run requires both --endpoint and --api-key together")
        client = HermesClient(args.endpoint, args.api_key)
        session_id = client.create_session(f"Replay: {recipe.name}")["id"]
        run_id = client.start_run(build_run_instruction(recipe), session_id=session_id)
        tool_events: list[str] = []
        output = ""
        status = "failed"
        try:
            for event in client.stream_run(run_id):
                event_type = event.get("event")
                if event_type in {"tool.started", "tool.completed", "tool.failed"}:
                    tool = event.get("tool", "tool")
                    detail = event.get("preview") or event.get("error") or ""
                    tool_events.append(f"{tool}: {detail}".rstrip(": "))
                if event_type == "run.completed":
                    status = "completed"
                    output = event.get("output", "")
                if event_type == "run.cancelled":
                    status = "cancelled"
                if event_type == "run.failed":
                    output = event.get("error", "")
        except KeyboardInterrupt:
            client.stop_run(run_id)
            status = "cancelled"
            output = "Cancellation requested."
        receipt = write_receipt(
            args.recipes_dir,
            recipe,
            run_id=run_id,
            status=status,
            tool_events=tool_events,
            output=output,
        )
        status_label = {"completed": "COMPLETE", "failed": "FAILED", "cancelled": "CANCELLED"}[status]
        print(f"REPLAY {status_label} — {recipe.name}")
        print(f"Verification required: {recipe.verification}")
        print(f"Receipt: {receipt}")
        if output:
            print(output)
        return 0 if status == "completed" else 1
    except (ReplayValidationError, TrajectoryError) as exc:
        parser.error(str(exc))
    return 2


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if not argv:
        try:
            argv = default_connection_args()
        except RuntimeError as exc:
            print(f"Caelus is not ready: {exc}", file=sys.stderr)
            print("Run `caelus runtime init` first.", file=sys.stderr)
            return 1
    gate_path = default_gate_path()
    if argv[:1] != ["gate"] and gate_is_configured(gate_path):
        try:
            if not require_access(gate_path, prompt=getpass, notify=print):
                return 1
        except AccessGateError as exc:
            print(f"Caelus access gate is invalid: {exc}")
            return 1
    if argv[:1] == ["gate"]:
        return gate_control(argv[1:], gate_path=gate_path)
    if argv[:1] == ["replay"]:
        return replay_control(argv[1:])
    if argv and argv[:2] == ["runtime", "init"]:
        return runtime_init(argv[2:])
    if argv and argv[:2] == ["runtime", "start"]:
        return runtime_control(argv[2:], action="start")
    if argv and argv[:2] == ["runtime", "status"]:
        return runtime_control(argv[2:], action="status")
    if argv and argv[:2] == ["runtime", "stop"]:
        return runtime_control(argv[2:], action="stop")
    if argv and argv[:2] == ["template", "export"]:
        return template_control(argv[2:], action="export")
    if argv and argv[:2] == ["template", "import"]:
        return template_control(argv[2:], action="import")
    parser = argparse.ArgumentParser(description="Caelus Agent")
    parser.add_argument("--demo", action="store_true", help="render the local UI demo")
    parser.add_argument(
        "--expanded-tools", action="store_true", help="show collapsed tool activity"
    )
    parser.add_argument("--endpoint", help="local Hermes API endpoint ending in /v1")
    parser.add_argument("--api-key", help="local Hermes API server key")
    parser.add_argument("--agent", default="Caelus", help="Caelus agent conversation name")
    parser.add_argument("--session-id", help="resume an existing Hermes session")
    parser.add_argument("--chat", help="send one message through the configured runtime")
    parser.add_argument("--interactive", action="store_true", help="start an interactive terminal chat")
    args = parser.parse_args(argv)

    if args.demo:
        print(render_dashboard(demo_state(), show_tool_activity=args.expanded_tools))
        return 0

    if args.interactive:
        if not args.endpoint or not args.api_key:
            parser.error("--interactive requires --endpoint and --api-key")
        client = HermesClient(args.endpoint, args.api_key)
        runtime = client.discover()
        state = DashboardState(
            agent_name=args.agent,
            model_name=runtime.model_name,
            skills=runtime.skills,
            mcp_servers=runtime.mcp_servers,
            tools=runtime.tools,
        )
        started_at = time.monotonic()
        if args.session_id:
            session_id = args.session_id
            for message in client.session_messages(session_id):
                role = message.get("role")
                if role in {"user", "assistant"} and message.get("content"):
                    state.transcript.append(("You" if role == "user" else args.agent, message["content"]))
        else:
            session_id = client.create_session(args.agent)["id"]
        while True:
            state.runtime_seconds = int(time.monotonic() - started_at)
            try:
                message = _read_composer(_redraw_chat(state))
            except EOFError:
                return 0
            if message in {"/quit", "/exit"}:
                return 0
            if message == "/help":
                state.transcript.append((args.agent, runtime_help()))
                continue
            if not message:
                continue
            state.transcript.append(("You", message))
            _redraw_chat(state, busy=True)
            run_id = client.start_run(message, session_id=session_id)
            try:
                for event in client.stream_run(run_id):
                    event_type = event.get("event")
                    if event_type in {"tool.started", "tool.completed", "tool.failed"}:
                        tool = event.get("tool", "tool")
                        detail = event.get("preview") or event.get("error") or ""
                        state.tool_activity.append(f"{tool}: {detail}".rstrip(": "))
                        _redraw_chat(state, busy=True)
                    if event_type == "run.completed":
                        state.transcript.append((args.agent, event.get("output", "")))
                    if event_type in {"run.failed", "run.cancelled"}:
                        state.transcript.append((args.agent, event_type.replace("run.", "").title()))
            except KeyboardInterrupt:
                client.stop_run(run_id)
                state.transcript.append((args.agent, "Cancellation requested."))

    if args.chat:
        if not args.endpoint or not args.api_key:
            parser.error("--chat requires --endpoint and --api-key")
        reply = HermesClient(args.endpoint, args.api_key).chat(
            args.chat, conversation=args.agent
        )
        print(f"{args.agent}: {reply}")
        return 0

    parser.print_help()
    return 0
