from caelus_terminal.dashboard import DashboardState, render_dashboard


def test_dashboard_renders_a_short_chat_transcript():
    state = DashboardState(
        agent_name="Nova",
        transcript=[("You", "Hello there"), ("Nova", "Hi, what can I help with?")],
    )

    output = render_dashboard(state, width=100)

    assert "YOU" in output
    assert "Hello there" in output
    assert "NOVA" in output
    assert "Hi, what can I help with?" in output
