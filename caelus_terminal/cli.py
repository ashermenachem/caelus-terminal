from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .client import HermesClient
from .dashboard import DashboardState, render_dashboard
from .helptext import runtime_help
from .runtime import (
    api_is_healthy,
    bootstrap_runtime,
    runtime_endpoint,
    runtime_is_running,
    start_runtime,
    stop_runtime,
)


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
        default=Path.home() / ".caelus" / "runtime",
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
        default=Path.home() / ".caelus" / "runtime",
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


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    if argv and argv[:2] == ["runtime", "init"]:
        return runtime_init(argv[2:])
    if argv and argv[:2] == ["runtime", "start"]:
        return runtime_control(argv[2:], action="start")
    if argv and argv[:2] == ["runtime", "status"]:
        return runtime_control(argv[2:], action="status")
    if argv and argv[:2] == ["runtime", "stop"]:
        return runtime_control(argv[2:], action="stop")
    parser = argparse.ArgumentParser(description="Caelus Terminal")
    parser.add_argument("--demo", action="store_true", help="render the local UI demo")
    parser.add_argument(
        "--expanded-tools", action="store_true", help="show collapsed tool activity"
    )
    parser.add_argument("--endpoint", help="local Hermes API endpoint ending in /v1")
    parser.add_argument("--api-key", help="local Hermes API server key")
    parser.add_argument("--agent", default="default", help="Caelus agent conversation name")
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
        print(render_dashboard(state))
        if args.session_id:
            session_id = args.session_id
            for message in client.session_messages(session_id):
                role = message.get("role")
                if role in {"user", "assistant"} and message.get("content"):
                    state.transcript.append(("You" if role == "user" else args.agent, message["content"]))
            print(render_dashboard(state))
        else:
            session_id = client.create_session(args.agent)["id"]
        print("Type /quit to end the Caelus chat session. Press Ctrl-C to stop an active run.")
        while True:
            message = input("\n> ").strip()
            if message in {"/quit", "/exit"}:
                return 0
            if message == "/help":
                print("\n" + runtime_help())
                continue
            if not message:
                continue
            state.transcript.append(("You", message))
            run_id = client.start_run(message, session_id=session_id)
            try:
                for event in client.stream_run(run_id):
                    event_type = event.get("event")
                    if event_type in {"tool.started", "tool.completed", "tool.failed"}:
                        tool = event.get("tool", "tool")
                        detail = event.get("preview") or event.get("error") or ""
                        state.tool_activity.append(f"{tool}: {detail}".rstrip(": "))
                    if event_type == "run.completed":
                        state.transcript.append((args.agent, event.get("output", "")))
                    if event_type in {"run.failed", "run.cancelled"}:
                        state.transcript.append((args.agent, event_type.replace("run.", "").title()))
            except KeyboardInterrupt:
                client.stop_run(run_id)
                state.transcript.append((args.agent, "Cancellation requested."))
            print("\n" + render_dashboard(state, show_tool_activity=True))

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
