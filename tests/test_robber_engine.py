from pathlib import Path

from src.models import GameState
from src.robber_engine import RobberEngine
from src.board import BoardGraph


def test_robber_avoids_active_player_tiles_and_targets_opponent():
    state = GameState.model_validate_json(Path("sample_state.json").read_text())
    engine = RobberEngine(state, BoardGraph(state.board))

    recommendation = engine.recommend("P1")

    assert recommendation is not None
    assert recommendation.tile == "1,1"
    assert recommendation.blockedPlayers == ["P2"]
