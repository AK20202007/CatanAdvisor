from typing import Dict
from .models import GameState, ResourceType
from .board import BoardGraph, VertexCoord

PIP_PROBABILITIES = {
    2: 1, 12: 1,
    3: 2, 11: 2,
    4: 3, 10: 3,
    5: 4, 9: 4,
    6: 5, 8: 5
}

def parse_vertex(vertex_str: str) -> VertexCoord:
    """
    Parses a string representation of a vertex into a canonical VertexCoord.
    Expected format: "q1,r1|q2,r2|q3,r3"
    """
    parts = vertex_str.split('|')
    coords = []
    for p in parts:
        q, r = p.split(',')
        coords.append((int(q), int(r)))
    return tuple(sorted(coords))

class ProductionEngine:
    def __init__(self, game_state: GameState, board_graph: BoardGraph):
        self.state = game_state
        self.board = board_graph
        
    def calculate_expected_income(self) -> Dict[str, Dict[ResourceType, float]]:
        """
        Calculates expected resource income per turn (in pips / 36) for each player.
        """
        income = {}
        for player in self.state.players:
            player_income = {res: 0.0 for res in ["brick", "lumber", "wool", "grain", "ore"]}
            
            # Settlements count as 1x
            for settlement in player.settlements:
                vertex = parse_vertex(settlement.vertex)
                tiles = self.board.get_tiles_for_vertex(vertex)
                for tile in tiles:
                    if tile.number and tile.resource != "desert":
                        if (tile.q, tile.r) != self.board.robber_pos:
                            pips = PIP_PROBABILITIES.get(tile.number, 0)
                            player_income[tile.resource] += pips
                            
            # Cities count as 2x
            for city in player.cities:
                vertex = parse_vertex(city.vertex)
                tiles = self.board.get_tiles_for_vertex(vertex)
                for tile in tiles:
                    if tile.number and tile.resource != "desert":
                        if (tile.q, tile.r) != self.board.robber_pos:
                            pips = PIP_PROBABILITIES.get(tile.number, 0)
                            player_income[tile.resource] += (pips * 2)
                            
            income[player.id] = player_income
            
        return income

    def get_vertex_pips(self, vertex: VertexCoord) -> Dict[ResourceType, int]:
        """
        Returns the expected pip yield per resource type if a settlement were built here.
        Useful for the Build Evaluation Engine.
        """
        yields = {res: 0 for res in ["brick", "lumber", "wool", "grain", "ore"]}
        tiles = self.board.get_tiles_for_vertex(vertex)
        for tile in tiles:
            if tile.number and tile.resource != "desert":
                if (tile.q, tile.r) != self.board.robber_pos:
                    pips = PIP_PROBABILITIES.get(tile.number, 0)
                    yields[tile.resource] += pips
        return yields
