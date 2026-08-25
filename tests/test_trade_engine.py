import pytest
from src.models import GameState, Board, Tile, Coordinate, Player, Resources, DevCards, UnrevealedDevCards, Settlement
from src.board import BoardGraph
from src.production_engine import ProductionEngine
from src.build_engine import BuildOption
from src.trade_engine import TradeEngine

@pytest.fixture
def trade_state():
    return GameState(
        board=Board(
            tiles=[
                Tile(q=0, r=0, resource="ore", number=10),
                Tile(q=1, r=0, resource="brick", number=8)
            ],
            ports=[],
            robber=Coordinate(q=2, r=0)
        ),
        players=[
            Player(
                id="P1",
                victoryPoints=2,
                resources=Resources(lumber=4, grain=1, wool=0, brick=0, ore=0),
                devCards=DevCards(unrevealed=UnrevealedDevCards(count=0)),
                settlements=[],
                cities=[],
                roads=[]
            ),
            Player(
                id="P2",
                victoryPoints=2,
                resources=Resources(brick=1, lumber=0, wool=0, grain=0, ore=0),
                devCards=DevCards(unrevealed=UnrevealedDevCards(count=0)),
                settlements=[Settlement(vertex="0,0|1,0|0,1")],
                cities=[],
                roads=[]
            )
        ],
        activePlayer="P1"
    )

def test_evaluate_bank_trades(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    
    player = trade_state.players[0]
    # P1 has 4 lumber. They want ore.
    offers = engine.evaluate_bank_trades(player, needed="ore")
    
    assert len(offers) == 1
    assert offers[0].give == {"lumber": 4}
    assert offers[0].receive == {"ore": 1}
    assert offers[0].offerTo == "bank"

def test_evaluate_player_trades(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    
    player = trade_state.players[0]
    
    # P1 wants brick. P2 has one brick in hand and a settlement on brick
    # (1,0 -> 8 -> 5 pips).
    # Expected income for P2 for brick is 5, which > 2.0.
    # P1 has lumber (4) and grain (1) surplus.
    
    offers = engine.evaluate_player_trades(player, needed="brick")
    
    assert len(offers) >= 1
    assert offers[0].offerTo == "P2"
    assert offers[0].receive == {"brick": 1}
    # It will offer the first surplus it finds, maybe lumber or grain
    assert "lumber" in offers[0].give or "grain" in offers[0].give
    assert list(offers[0].give.values())[0] == 1

def test_get_recommended_trades(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    
    best_build = BuildOption(type="settlement", location="0,0|1,0|0,1", score=10.0, reasoning="")
    
    trades = engine.get_recommended_trades("P1", best_build)
    
    # A settlement needs brick, lumber, wool, and grain. P1 is missing brick
    # and wool; the engine should derive that instead of hard-coding ore.
    assert len(trades) > 0
    assert trades[0].receive == {"brick": 1}

def test_bank_trade_caps_output_to_requested_amount(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    player = trade_state.players[0]
    player.resources.lumber = 12

    offers = engine.evaluate_bank_trades(player, needed="ore", amount_needed=2)

    assert offers[0].give == {"lumber": 8}
    assert offers[0].receive == {"ore": 2}

def test_player_trade_requires_opponent_to_have_resource(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    player = trade_state.players[0]
    trade_state.players[1].resources.brick = 0

    assert engine.evaluate_player_trades(player, needed="brick") == []

def test_city_recommendations_use_city_cost(trade_state):
    board = BoardGraph(trade_state.board)
    prod = ProductionEngine(trade_state, board)
    engine = TradeEngine(trade_state, board, prod)
    player = trade_state.players[0]
    player.resources.lumber = 12
    player.resources.grain = 2

    trades = engine.get_recommended_trades(
        player.id,
        BuildOption(type="city", location="0,0|1,0|0,1", score=10.0),
    )

    assert trades[0].receive == {"ore": 3}
    assert trades[0].give == {"lumber": 12}
