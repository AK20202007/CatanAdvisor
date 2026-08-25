import pytest
from src.board import (
    hex_add, 
    get_hex_neighbors, 
    canonical_vertex, 
    canonical_edge,
    get_hex_vertices,
    get_hex_edges,
    BoardGraph
)
from src.models import Board, Tile, Coordinate

def test_hex_add():
    assert hex_add((0, 0), (1, 1)) == (1, 1)
    assert hex_add((2, -1), (-1, 3)) == (1, 2)

def test_get_hex_neighbors():
    neighbors = get_hex_neighbors((0, 0))
    assert len(neighbors) == 6
    assert (1, 0) in neighbors
    assert (-1, 0) in neighbors

def test_canonical_vertex():
    # Should sort coordinates
    v = canonical_vertex((0, 1), (-1, 0), (0, 0))
    assert v == ((-1, 0), (0, 0), (0, 1))
    
    # Same vertex with different order of inputs
    v2 = canonical_vertex((0, 0), (0, 1), (-1, 0))
    assert v == v2

def test_canonical_edge():
    e = canonical_edge((1, -1), (0, 0))
    assert e == ((0, 0), (1, -1))

def test_get_hex_vertices():
    vertices = get_hex_vertices((0, 0))
    assert len(vertices) == 6
    # Check one specific vertex
    expected_v = canonical_vertex((0, 0), (1, 0), (1, -1))
    assert expected_v in vertices

def test_get_hex_edges():
    edges = get_hex_edges((0, 0))
    assert len(edges) == 6
    expected_e = canonical_edge((0, 0), (1, 0))
    assert expected_e in edges

def test_board_graph_initialization():
    board_model = Board(
        tiles=[
            Tile(q=0, r=0, resource="ore", number=10),
            Tile(q=1, r=0, resource="brick", number=8)
        ],
        ports=[],
        robber=Coordinate(q=0, r=0)
    )
    
    graph = BoardGraph(board_model)
    
    assert len(graph.tiles) == 2
    assert (0, 0) in graph.tiles
    assert (1, 0) in graph.tiles
    
    # 6 vertices from first hex, 6 from second, 2 shared -> 10 unique
    assert len(graph.vertices) == 10
    
    # 6 edges from first hex, 6 from second, 1 shared -> 11 unique
    assert len(graph.edges) == 11
    
def test_board_graph_get_tiles_for_vertex():
    board_model = Board(
        tiles=[
            Tile(q=0, r=0, resource="ore", number=10),
            Tile(q=1, r=0, resource="brick", number=8),
            Tile(q=0, r=1, resource="lumber", number=6)
        ],
        ports=[],
        robber=Coordinate(q=2, r=0)
    )
    graph = BoardGraph(board_model)
    
    v = canonical_vertex((0, 0), (1, 0), (0, 1))
    tiles = graph.get_tiles_for_vertex(v)
    assert len(tiles) == 3
    resources = {t.resource for t in tiles}
    assert resources == {"ore", "brick", "lumber"}
