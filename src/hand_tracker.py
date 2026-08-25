from typing import Dict

from .models import GameState, ResourceType


class HandTracker:
    """Use current hands plus recent transaction history for trade context."""

    def __init__(self, state: GameState):
        self.state = state

    def known_hand(self, player_id: str) -> Dict[ResourceType, int]:
        player = next((player for player in self.state.players if player.id == player_id), None)
        if player is None:
            return {}
        return player.resources.model_dump()

    def received_recently(self, player_id: str, resource: ResourceType, lookback: int = 3) -> int:
        """Return how many units of a resource appeared in recent trades."""
        minimum_turn = max(0, self.state.turn - lookback)
        return sum(
            event.receive.get(resource, 0)
            for event in self.state.history
            if event.toPlayer == player_id and event.turn >= minimum_turn
        )

    def context_for_trade(self, player_id: str, resource: ResourceType) -> str:
        recent = self.received_recently(player_id, resource)
        if recent:
            return f"{player_id} recently received {recent} {resource}; verify they are willing to trade it."
        return f"{player_id} has {self.known_hand(player_id).get(resource, 0)} {resource} in the known hand."
