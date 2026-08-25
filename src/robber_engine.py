from typing import List

from pydantic import BaseModel

from .board import BoardGraph
from .models import GameState
from .production_engine import PIP_PROBABILITIES, parse_vertex


class RobberOption(BaseModel):
    tile: str
    score: float
    blockedPlayers: List[str]
    reasoning: str


class RobberEngine:
    """Rank robber placements by opponent production blocked."""

    def __init__(self, game_state: GameState, board_graph: BoardGraph):
        self.state = game_state
        self.board = board_graph

    def get_best_placements(self, active_player_id: str) -> List[RobberOption]:
        active = next((player for player in self.state.players if player.id == active_player_id), None)
        if active is None:
            return []

        leaders = sorted(self.state.players, key=lambda player: player.victoryPoints, reverse=True)
        leader_id = leaders[0].id if leaders else None
        active_vertices = {
            parse_vertex(piece.vertex)
            for piece in [*active.settlements, *active.cities]
        }
        options = []
        for tile in self.state.board.tiles:
            if tile.number is None or tile.resource == "desert":
                continue
            tile_coord = (tile.q, tile.r)
            if tile_coord == self.board.robber_pos:
                continue
            if any(tile_coord in vertex for vertex in active_vertices):
                continue

            pips = PIP_PROBABILITIES.get(tile.number, 0)
            blocked = []
            score = 0.0
            for player in self.state.players:
                if player.id == active_player_id:
                    continue
                player_pieces = [(piece.vertex, 1) for piece in player.settlements]
                player_pieces.extend((piece.vertex, 2) for piece in player.cities)
                multiplier = sum(
                    piece_multiplier
                    for vertex_string, piece_multiplier in player_pieces
                    if tile_coord in parse_vertex(vertex_string)
                )
                if multiplier:
                    blocked.append(player.id)
                    leader_weight = 2.0 if player.id == leader_id else 1.0
                    score += pips * multiplier * leader_weight

            if score:
                names = ", ".join(blocked)
                options.append(RobberOption(
                    tile=f"{tile.q},{tile.r}",
                    score=score,
                    blockedPlayers=blocked,
                    reasoning=f"Blocks {pips} pips from {names}; the leading player is weighted more heavily.",
                ))
        return sorted(options, key=lambda option: (-option.score, option.tile))

    def recommend(self, active_player_id: str) -> RobberOption | None:
        options = self.get_best_placements(active_player_id)
        return options[0] if options else None
