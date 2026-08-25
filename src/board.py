from typing import List, Tuple, Dict, Set
from .models import Board as BoardModel, Tile, GameState

HexCoord = Tuple[int, int]
VertexCoord = Tuple[HexCoord, HexCoord, HexCoord]
EdgeCoord = Tuple[HexCoord, HexCoord]

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
        # This will be used by the production engine
        pass
