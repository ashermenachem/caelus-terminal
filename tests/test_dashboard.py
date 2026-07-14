from caelus_terminal.dashboard import DashboardState, render_dashboard


def test_dashboard_renders_agent_capabilities_and_runtime_status():
    state = DashboardState(
        agent_name="Nova",
        model_name="gpt-test",
        context_percent=42,
        runtime_seconds=125,
        skills=["Research", "Files"],
        mcp_servers=["GitHub"],
        tools=["Web", "Terminal"],
    )

    output = render_dashboard(state, width=100)

    assert "CAELUS AGENT" in output
    assert "Nova  •  gpt-test  •  ready" in output
    assert "context 42%" in output
    assert "session 02:05" in output
    assert "skills Research, Files" in output


def test_dashboard_collapses_tool_activity_until_expanded():
    state = DashboardState(tool_activity=["Reading docs", "Running tests"])

    collapsed = render_dashboard(state, width=100)
    expanded = render_dashboard(state, width=100, show_tool_activity=True)

    assert "▸ 2 tool actions" in collapsed
    assert "Reading docs" not in collapsed
    assert "▾ 2 tool actions" in expanded
    assert "• Reading docs" in expanded
    assert "• Running tests" in expanded


def test_dashboard_separates_wrapped_messages_from_the_composer():
    state = DashboardState(
        agent_name="Caelus",
        model_name="terra",
        transcript=[
            ("You", "Please summarize this long document carefully."),
            ("Caelus", "I can do that. I will keep the result organized."),
        ],
    )

    output = render_dashboard(state, width=60)

    assert "CAELUS AGENT" in output
    assert "YOU" in output
    assert "CAELUS" in output
    assert "Please summarize this long document" in output
    assert "Message Caelus" in output


def test_dashboard_can_hide_the_static_composer_while_live_input_is_open():
    output = render_dashboard(DashboardState(), width=60, show_composer=False)

    assert "Message Caelus" not in output
    assert "/help for controls" not in output
