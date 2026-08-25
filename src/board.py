from typing import List, Tuple, Dict, Set
from .models import Board as BoardModel, Tile

HexCoord = Tuple[int, int]
VertexCoord = Tuple[HexCoord, HexCoord, HexCoord]
EdgeCoord = Tuple[HexCoord, HexCoord]

PIP_PROBABILITIES = {
    2: 1, 12: 1,
    3: 2, 11: 2,
    4: 3, 10: 3,
    5: 4, 9: 4,
    6: 5, 8: 5,
}

# Axial coordinate directions for a pointy-topped or flat-topped hex grid.
# Assuming standard axial directions.
HEX_DIRECTIONS = [
    (1, 0), (1, -1), (0, -1), 
    (-1, 0), (-1, 1), (0, 1)
]

def hex_add(a: HexCoord, b: HexCoord) -> HexCoord:
    return (a[0] + b[0], a[1] + b[1])

def get_hex_neighbors(coord: HexCoord) -> List[HexCoord]:
    return [hex_add(coord, d) for d in HEX_DIRECTIONS]

def canonical_vertex(h1: HexCoord, h2: HexCoord, h3: HexCoord) -> VertexCoord:
    """Returns a uniquely identifiable vertex representation by sorting the 3 adjacent hex coordinates."""
    return tuple(sorted([h1, h2, h3]))

def canonical_edge(h1: HexCoord, h2: HexCoord) -> EdgeCoord:
    """Returns a uniquely identifiable edge representation by sorting the 2 adjacent hex coordinates."""
    return tuple(sorted([h1, h2]))

def get_hex_vertices(coord: HexCoord) -> List[VertexCoord]:
    """
    Returns the 6 vertices of a hex.
    In a hex grid, a vertex is shared by 3 hexes. 
    If we consider the 6 neighbors of a hex (in order), adjacent pairs of neighbors 
    along with the center hex form the 3 hexes sharing a vertex.
    """
    neighbors = get_hex_neighbors(coord)
    vertices = []
    for i in range(6):
        n1 = neighbors[i]
        n2 = neighbors[(i + 1) % 6]
        vertices.append(canonical_vertex(coord, n1, n2))
    return vertices

def get_hex_edges(coord: HexCoord) -> List[EdgeCoord]:
    """Returns the 6 edges of a hex."""
    return [canonical_edge(coord, n) for n in get_hex_neighbors(coord)]

class BoardGraph:
    def __init__(self, board_model: BoardModel):
        self.model = board_model
        
        # Maps HexCoord to Tile model
        self.tiles: Dict[HexCoord, Tile] = {}
        for t in board_model.tiles:
            self.tiles[(t.q, t.r)] = t
            
        self.robber_pos: HexCoord = (board_model.robber.q, board_model.robber.r)
        
        # Build vertex and edge sets based on tiles present
        self.vertices: Set[VertexCoord] = set()
        self.edges: Set[EdgeCoord] = set()
        
        for coord in self.tiles.keys():
            self.vertices.update(get_hex_vertices(coord))
            self.edges.update(get_hex_edges(coord))
            
    def get_tiles_for_vertex(self, vertex: VertexCoord) -> List[Tile]:
        """Returns the actual land tiles adjacent to a vertex."""
        return [self.tiles[h] for h in vertex if h in self.tiles]

    def get_pips_for_vertex(self, vertex: VertexCoord) -> int:
        """Returns the total pip value of tiles adjacent to this vertex."""
        return sum(
            PIP_PROBABILITIES.get(tile.number, 0)
            for tile in self.get_tiles_for_vertex(vertex)
            if tile.resource != "desert"
            and tile.number is not None
            and (tile.q, tile.r) != self.robber_pos
        )

    def get_available_settlements(self, occupied: Set[VertexCoord] | None = None) -> List[VertexCoord]:
        """Return vertices that satisfy Catan's distance rule.

        Road connectivity is left to the caller because setup turns and normal
        turns use different connectivity rules.
        """
        occupied = occupied or set()
        available = []
        for vertex in sorted(self.vertices):
            if vertex in occupied:
                continue
            if any(len(set(vertex).intersection(other)) >= 2 for other in occupied):
                continue
            available.append(vertex)
        return available
