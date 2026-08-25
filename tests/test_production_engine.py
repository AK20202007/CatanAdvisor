import pytest
from src.models import GameState, Board, Tile, Coordinate, Player, Resources, DevCards, UnrevealedDevCards, Settlement, City
from src.board import BoardGraph
from src.production_engine import ProductionEngine, parse_vertex

@pytest.fixture
def sample_state():
    return GameState(
        board=Board(
            tiles=[
                Tile(q=0, r=0, resource="ore", number=10), # 3 pips
                Tile(q=1, r=0, resource="brick", number=8), # 5 pips
                Tile(q=0, r=1, resource="lumber", number=6), # 5 pips
                Tile(q=2, r=0, resource="desert", number=None) # 0 pips
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
                settlements=[Settlement(vertex="0,0|1,0|0,1")],
                cities=[],
                roads=[]
            ),
            Player(
                id="P2",
                victoryPoints=2,
                resources=Resources(),
                devCards=DevCards(unrevealed=UnrevealedDevCards(count=0)),
                settlements=[],
                cities=[City(vertex="0,0|1,0|0,1")],
                roads=[]
            )
        ],
        activePlayer="P1"
    )

def test_parse_vertex():
    v = parse_vertex("0,0|1,0|0,1")
    assert v == ((0, 0), (0, 1), (1, 0))

def test_parse_vertex_rejects_malformed_values():
    with pytest.raises(ValueError):
        parse_vertex("0,0|1,0")
    with pytest.raises(ValueError):
        parse_vertex("0,0|0,0|1,0")

def test_calculate_expected_income(sample_state):
    board = BoardGraph(sample_state.board)
    engine = ProductionEngine(sample_state, board)
    
    incomes = engine.calculate_expected_income()
    
    # P1 has a settlement on 0,0 (ore 10 -> 3 pips), 1,0 (brick 8 -> 5 pips), 0,1 (lumber 6 -> 5 pips)
    p1_income = incomes["P1"]
    assert p1_income["ore"] == 3
    assert p1_income["brick"] == 5
    assert p1_income["lumber"] == 5
    assert p1_income["wool"] == 0
    
    # P2 has a city on the same vertex (2x production)
    p2_income = incomes["P2"]
    assert p2_income["ore"] == 6
    assert p2_income["brick"] == 10
    assert p2_income["lumber"] == 10

def test_robber_blocks_production(sample_state):
    # Move robber to (1, 0) blocking brick
    sample_state.board.robber = Coordinate(q=1, r=0)
    board = BoardGraph(sample_state.board)
    engine = ProductionEngine(sample_state, board)
    
    incomes = engine.calculate_expected_income()
    
    p1_income = incomes["P1"]
    assert p1_income["brick"] == 0 # blocked
    assert p1_income["ore"] == 3 # not blocked
    assert p1_income["lumber"] == 5 # not blocked

def test_get_vertex_pips(sample_state):
    board = BoardGraph(sample_state.board)
    engine = ProductionEngine(sample_state, board)
    
    v = parse_vertex("0,0|1,0|0,1")
    yields = engine.get_vertex_pips(v)
    
    assert yields["ore"] == 3
    assert yields["brick"] == 5
    assert yields["lumber"] == 5
    assert yields["wool"] == 0
