from typing import Dict
from .models import GameState, ResourceType, PRODUCIBLE_RESOURCES
from .board import BoardGraph, VertexCoord, PIP_PROBABILITIES

DICE_ROLL_PROBABILITIES = {
    roll: pips / 36
    for roll, pips in {
        2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
        8: 5, 9: 4, 10: 3, 11: 2, 12: 1,
    }.items()
}

def parse_vertex(vertex_str: str) -> VertexCoord:
    """
    Parses a string representation of a vertex into a canonical VertexCoord.
    Expected format: "q1,r1|q2,r2|q3,r3"
    """
    parts = vertex_str.split('|')
    if len(parts) != 3:
        raise ValueError(f"A vertex must contain exactly 3 hex coordinates: {vertex_str!r}")

    coords = []
    for part in parts:
        values = part.split(',')
        if len(values) != 2:
            raise ValueError(f"Invalid hex coordinate in vertex: {part!r}")
        try:
            coords.append((int(values[0]), int(values[1])))
        except ValueError as exc:
            raise ValueError(f"Invalid integer coordinate in vertex: {part!r}") from exc

    if len(set(coords)) != 3:
        raise ValueError(f"A vertex cannot repeat a hex coordinate: {vertex_str!r}")
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
            player_income = {res: 0.0 for res in PRODUCIBLE_RESOURCES}
            
            # Settlements count as 1x
            for settlement in player.settlements:
                vertex = parse_vertex(settlement.vertex)
                for resource, pips in self.get_vertex_pips(vertex).items():
                    player_income[resource] += pips
                            
            # Cities count as 2x
            for city in player.cities:
                vertex = parse_vertex(city.vertex)
                for resource, pips in self.get_vertex_pips(vertex).items():
                    player_income[resource] += pips * 2
                            
            income[player.id] = player_income
            
        return income

    def get_vertex_pips(self, vertex: VertexCoord) -> Dict[ResourceType, int]:
        """
        Returns the expected pip yield per resource type if a settlement were built here.
        Useful for the Build Evaluation Engine.
        """
        yields = {res: 0 for res in PRODUCIBLE_RESOURCES}
        tiles = self.board.get_tiles_for_vertex(vertex)
        for tile in tiles:
            if tile.resource == "desert" or tile.number is None:
                continue
            if (tile.q, tile.r) == self.board.robber_pos:
                continue
            yields[tile.resource] += PIP_PROBABILITIES.get(tile.number, 0)
        return yields

    def get_roll_income(self, player_id: str, roll: int) -> Dict[ResourceType, int]:
        """Return the cards a player receives for one dice roll."""
        if roll not in DICE_ROLL_PROBABILITIES:
            return {resource: 0 for resource in PRODUCIBLE_RESOURCES}

        player = next((p for p in self.state.players if p.id == player_id), None)
        if player is None:
            return {resource: 0 for resource in PRODUCIBLE_RESOURCES}

        income = {resource: 0 for resource in PRODUCIBLE_RESOURCES}
        pieces = [(settlement.vertex, 1) for settlement in player.settlements]
        pieces.extend((city.vertex, 2) for city in player.cities)
        for vertex_string, multiplier in pieces:
            vertex = parse_vertex(vertex_string)
            for tile in self.board.get_tiles_for_vertex(vertex):
                if tile.number != roll or tile.resource == "desert":
                    continue
                if (tile.q, tile.r) == self.board.robber_pos:
                    continue
                income[tile.resource] += multiplier
        return income
