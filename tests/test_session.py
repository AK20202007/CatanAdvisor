from src.session import GameSession
from src.interactive import execute_command


def test_roll_updates_all_hands_and_turn():
    session = GameSession.from_file("sample_state.json")
    before = session.state.players[0].resources.brick

    income = session.roll(8)

    assert income["P1"]["brick"] == 1
    assert session.state.players[0].resources.brick == before + 1
    assert session.state.turn == 1


def test_bank_trade_updates_state_and_history():
    session = GameSession.from_file("sample_state.json")
    player = session.state.players[0]
    player.resources.lumber = 4
    before_brick = player.resources.brick

    event = session.trade("P1", "bank", {"lumber": 4}, {"brick": 1})

    assert player.resources.lumber == 0
    assert player.resources.brick == before_brick + 1
    assert event.toPlayer == "bank"
    assert session.state.history[-1].receive == {"brick": 1}


def test_bank_trade_rejects_invalid_ratio():
    session = GameSession.from_file("sample_state.json")
    player = session.state.players[0]
    player.resources.lumber = 4
    before = player.resources.model_dump()

    try:
        session.trade("P1", "bank", {"lumber": 3}, {"brick": 1})
    except ValueError as exc:
        assert "4:1" in str(exc)
    else:
        raise AssertionError("Expected invalid bank ratio to be rejected")
    assert player.resources.model_dump() == before


def test_recommendations_include_robber_and_lookahead():
    session = GameSession.from_file("sample_state.json")

    recommendations = session.recommendations()

    assert recommendations["robber"]["tile"] in {"1,0", "1,1"}
    assert recommendations["lookahead"]


def test_interactive_commands_accept_game_vocabulary():
    session = GameSession.from_file("sample_state.json")
    session.state.players[0].resources.lumber = 4
    session.state.players[1].resources.brick = 1

    event = execute_command(session, "trade P1 1 wood for 1 brick with P2")

    assert event["give"] == {"lumber": 1}
    assert event["receive"] == {"brick": 1}
