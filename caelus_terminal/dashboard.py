from __future__ import annotations

from dataclasses import dataclass, field
import textwrap


@dataclass
class DashboardState:
    agent_name: str = "Caelus"
    model_name: str = "not configured"
    context_percent: int = 0
    runtime_seconds: int = 0
    skills: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    transcript: list[tuple[str, str]] = field(default_factory=list)
    tool_activity: list[str] = field(default_factory=list)


def _format_runtime(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"
    return f"{minutes:02}:{remaining_seconds:02}"


def _display(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _line(content: str, width: int) -> str:
    return f"│ {content[: width - 4]:<{width - 4}} │"


def _wrapped_lines(content: str, width: int, *, prefix: str = "") -> list[str]:
    usable_width = max(20, width - 4 - len(prefix))
    paragraphs = content.splitlines() or [""]
    lines: list[str] = []
    for paragraph in paragraphs:
        wrapped = textwrap.wrap(paragraph, width=usable_width, break_long_words=False) or [""]
        lines.extend(f"{prefix}{line}" for line in wrapped)
    return lines


def _message_lines(speaker: str, message: str, width: int) -> list[str]:
    label = "YOU" if speaker.lower() == "you" else speaker.upper()
    lines = [f"{label}"]
    lines.extend(_wrapped_lines(message, width, prefix="  "))
    return lines


def render_dashboard(
    state: DashboardState,
    *,
    width: int = 100,
    show_tool_activity: bool = False,
    busy: bool = False,
    show_composer: bool = True,
) -> str:
    """Render one stable chat screen; the caller clears/redraws it between turns."""
    width = max(width, 60)
    border = "─" * (width - 2)
    title = " CAELUS AGENT "
    model = state.model_name or "not configured"
    status = "working" if busy else "ready"
    lines = [
        "┌" + title.center(width - 2, "─") + "┐",
        _line(f"{state.agent_name}  •  {model}  •  {status}", width),
        "├" + border + "┤",
    ]

    if state.transcript:
        for index, (speaker, message) in enumerate(state.transcript[-10:]):
            if index:
                lines.append(_line("", width))
            lines.extend(_line(content, width) for content in _message_lines(speaker, message, width))
    elif busy:
        lines.append(_line("CAELUS", width))
        lines.append(_line("  Thinking…", width))
    else:
        lines.append(_line("Start a conversation with Caelus.", width))

    activity_count = len(state.tool_activity)
    if activity_count:
        lines.append("├" + border + "┤")
        marker = "▾" if show_tool_activity else "▸"
        lines.append(_line(f"{marker} {activity_count} tool actions", width))
        if show_tool_activity:
            for activity in state.tool_activity[-6:]:
                lines.extend(_line(content, width) for content in _wrapped_lines(activity, width, prefix="  • "))

    lines.append("├" + border + "┤")
    if show_composer:
        lines.extend(
            [
                _line("Message Caelus  ›", width),
                _line("/help for controls  •  /quit to exit", width),
            ]
        )
    lines.extend(
        [
            _line(
                f"context {state.context_percent}%  •  session {_format_runtime(state.runtime_seconds)}  •  skills {_display(state.skills[:3])}",
                width,
            ),
            "└" + border + "┘",
        ]
    )
    return "\n".join(lines)
