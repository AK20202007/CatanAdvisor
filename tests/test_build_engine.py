import pytest
from src.models import GameState, Board, Tile, Coordinate, Player, Resources, DevCards, UnrevealedDevCards, Settlement, Port
from src.board import BoardGraph
from src.production_engine import ProductionEngine
from src.build_engine import BuildEngine

@pytest.fixture
def base_state():
    return GameState(
        board=Board(
            tiles=[
                Tile(q=0, r=0, resource="ore", number=10), # 3 pips
                Tile(q=1, r=0, resource="brick", number=8), # 5 pips
                Tile(q=0, r=1, resource="lumber", number=6), # 5 pips
            ],
            ports=[],
            robber=Coordinate(q=2, r=0)
        ),
        players=[
            Player(
                id="P1",
                victoryPoints=2,
                resources=Resources(),
                devCards=DevCards(unrevealed=UnrevealedDevCards(count=0)),
                settlements=[],
                cities=[],
                roads=[]
            )
        ],
        activePlayer="P1"
    )

def test_evaluate_settlement(base_state):
    board = BoardGraph(base_state.board)
    prod = ProductionEngine(base_state, board)
    engine = BuildEngine(base_state, board, prod)
    
    player = base_state.players[0]
    option = engine.evaluate_settlement(player, "0,0|1,0|0,1")
    
    assert option.type == "settlement"
    assert option.location == "0,0|1,0|0,1"
    # Expected score: 1.0 (w1) * (3 + 5 + 5) = 13.0
    assert option.score == 13.0

def test_get_best_builds(base_state):
    board = BoardGraph(base_state.board)
    prod = ProductionEngine(base_state, board)
    engine = BuildEngine(base_state, board, prod)
    
    # "0,0|1,0|0,1" -> 13 pips
    # "0,0|1,0|-1,0" -> only has 0,0 and 1,0 -> 8 pips (assuming -1,0 is empty water)
    options = engine.get_best_builds("P1", ["0,0|1,0|-1,0", "0,0|1,0|0,1"])
    
    assert len(options) == 2
    assert options[0].location == "0,0|1,0|0,1"
    assert options[0].score == 13.0
    assert options[1].location == "0,0|1,0|-1,0"
    assert options[1].score == 8.0

def test_build_costs_and_affordable_builds(base_state):
    board = BoardGraph(base_state.board)
    prod = ProductionEngine(base_state, board)
    engine = BuildEngine(base_state, board, prod)
    player = base_state.players[0]

    assert engine.can_afford(player, "settlement") is False
    assert engine.get_missing_resources(player, {"ore": 3, "grain": 2}) == {"ore": 3, "grain": 2}
    assert engine.get_affordable_builds("P1") == []

def test_affordable_city_ranks_above_road(base_state):
    board = BoardGraph(base_state.board)
    prod = ProductionEngine(base_state, board)
    engine = BuildEngine(base_state, board, prod)
    player = base_state.players[0]
    player.resources = Resources(brick=1, lumber=1, grain=2, ore=3)
    player.settlements = [Settlement(vertex="0,0|1,0|0,1")]

    options = engine.get_affordable_builds("P1")

    assert [option.type for option in options] == ["city", "road"]

def test_port_synergy_increases_settlement_score(base_state):
    base_state.board.ports = [Port(edge="0,0|1,0|0,1", type="2:1_ore")]
    board = BoardGraph(base_state.board)
    prod = ProductionEngine(base_state, board)
    engine = BuildEngine(base_state, board, prod)

    option = engine.evaluate_settlement(base_state.players[0], "0,0|1,0|0,1")

    assert option.score > 13.0
    assert "2:1 ore port synergy" in option.reasoning
