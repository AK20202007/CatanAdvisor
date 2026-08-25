from typing import Dict, List

from pydantic import BaseModel

from .board import BoardGraph
from .models import GameState, PRODUCIBLE_RESOURCES
from .production_engine import DICE_ROLL_PROBABILITIES, ProductionEngine, parse_vertex


class LookaheadOption(BaseModel):
    location: str
    score: float
    immediateScore: float
    expectedFutureScore: float
    reasoning: str


class LookaheadEngine:
    """A shallow chance-node lookahead over dice rolls and future upgrades."""

    def __init__(self, state: GameState, board: BoardGraph, production: ProductionEngine):
        self.state = state
        self.board = board
        self.production = production

    def rank_settlements(self, player_id: str, candidates: List[str], depth: int = 2) -> List[LookaheadOption]:
        if depth < 1:
            raise ValueError("Lookahead depth must be at least 1.")
        if not any(player.id == player_id for player in self.state.players):
            return []

        results = []
        for location in candidates:
            vertex = parse_vertex(location)
            pips = self.production.get_vertex_pips(vertex)
            immediate = float(sum(pips.values()))
            future = self._expect_future(player_id, vertex, depth)
            results.append(LookaheadOption(
                location=location,
                score=immediate + future,
                immediateScore=immediate,
                expectedFutureScore=future,
                reasoning=(
                    f"Immediate gain is {int(immediate)} pips; expected future value is "
                    f"{future:.2f} across the next {depth} roll horizon."
                ),
            ))
        return sorted(results, key=lambda result: (-result.score, result.location))

    def _expect_future(self, player_id: str, vertex, depth: int) -> float:
        if depth <= 0:
            return 0.0

        expected = 0.0
        for roll, probability in DICE_ROLL_PROBABILITIES.items():
            existing = self.production.get_roll_income(player_id, roll)
            hypothetical = self._vertex_roll_income(vertex, roll)
            projected = {resource: existing[resource] + hypothetical[resource] for resource in PRODUCIBLE_RESOURCES}
            upgrade_value = self._best_upgrade_value(player_id, projected)
            branch_value = sum(hypothetical.values()) * 0.5 + upgrade_value
            expected += probability * branch_value
        return expected + (0.5 * self._expect_future(player_id, vertex, depth - 1) if depth > 1 else 0.0)

    def _vertex_roll_income(self, vertex, roll: int) -> Dict[str, int]:
        income = {resource: 0 for resource in PRODUCIBLE_RESOURCES}
        for tile in self.board.get_tiles_for_vertex(vertex):
            if tile.number == roll and tile.resource != "desert" and (tile.q, tile.r) != self.board.robber_pos:
                income[tile.resource] += 1
        return income

    def _best_upgrade_value(self, player_id: str, projected: Dict[str, int]) -> float:
        player = next(player for player in self.state.players if player.id == player_id)
        current_resources = player.resources.model_dump()
        possible = {
            resource: current_resources.get(resource, 0) + projected.get(resource, 0)
            for resource in PRODUCIBLE_RESOURCES
        }
        if possible["grain"] < 2 or possible["ore"] < 3:
            return 0.0

        best = 0
        for settlement in player.settlements:
            best = max(best, self.board.get_pips_for_vertex(parse_vertex(settlement.vertex)))
        return best * 1.5
