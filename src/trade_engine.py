from typing import List, Dict, Optional
from pydantic import BaseModel
from .models import GameState, Player, ResourceType, PRODUCIBLE_RESOURCES
from .board import BoardGraph
from .production_engine import ProductionEngine
from .build_engine import BuildOption, BUILD_COSTS
from .hand_tracker import HandTracker

class TradeOffer(BaseModel):
    give: Dict[ResourceType, int]
    receive: Dict[ResourceType, int]
    offerTo: Optional[str] = "bank" # "bank" or player id
    score: float = 0.0
    acceptanceLikelihood: str = "high" # "high", "moderate", "low"
    reasoning: str = ""

class TradeEngine:
    def __init__(self, game_state: GameState, board_graph: BoardGraph, production_engine: ProductionEngine):
        self.state = game_state
        self.board = board_graph
        self.production = production_engine
        self.hands = HandTracker(game_state)
        
    def get_player_income(self, player_id: str) -> Dict[ResourceType, float]:
        incomes = self.production.calculate_expected_income()
        return incomes.get(player_id, {res: 0.0 for res in PRODUCIBLE_RESOURCES})
        
    def evaluate_bank_trades(self, active_player: Player, needed: ResourceType, amount_needed: int = 1) -> List[TradeOffer]:
        """
        Suggests 4:1 bank trades to obtain the needed resource.
        (In a full implementation, it would check for 3:1 and 2:1 port ownership).
        """
        offers = []
        if needed == "desert" or amount_needed <= 0:
            return offers

        resources = active_player.resources.model_dump()
        for res, amount in resources.items():
            if res != needed and amount >= 4:
                units = min(amount // 4, amount_needed)
                offers.append(TradeOffer(
                    give={res: units * 4},
                    receive={needed: units},
                    offerTo="bank",
                    score=2.0 + units * 0.1,
                    acceptanceLikelihood="high",
                    reasoning=f"Convert {units * 4} {res} to {units} {needed} via the 4:1 bank rate."
                ))
        return offers
        
    def evaluate_player_trades(self, active_player: Player, needed: ResourceType) -> List[TradeOffer]:
        """
        Suggests player-to-player trades.
        Looks for opponents who have a surplus of the 'needed' resource and might want 
        something the active player has a surplus of.
        """
        offers = []
        active_surplus = []
        resources = active_player.resources.model_dump()
        for res, amount in resources.items():
            if res != needed and amount >= 1:
                active_surplus.append((amount, res))
                
        if not active_surplus or needed == "desert":
            return offers

        active_surplus.sort(reverse=True)
            
        for opponent in self.state.players:
            if opponent.id == active_player.id:
                continue
                
            opp_income = self.get_player_income(opponent.id)
            
            # A player can only trade a resource they currently hold. Production
            # is still used as a signal that they may be willing to part with it.
            opponent_stock = opponent.resources.model_dump().get(needed, 0)
            if opponent_stock >= 1 and opp_income.get(needed, 0.0) > 2.0:
                offer_res = active_surplus[0][1]
                offers.append(TradeOffer(
                    give={offer_res: 1},
                    receive={needed: 1},
                    offerTo=opponent.id,
                    score=3.5 + min(opponent_stock, 3) * 0.1,
                    acceptanceLikelihood="moderate",
                    reasoning=(
                        f"{opponent.id} has high {needed} production and it is in their hand; "
                        f"they might trade it for {offer_res}. {self.hands.context_for_trade(opponent.id, needed)}"
                    )
                ))
                
        return offers

    def get_recommended_trades(self, active_player_id: str, best_build: BuildOption) -> List[TradeOffer]:
        """
        Returns a list of trade suggestions to enable the best build.
        (Simplified logic: assume we are trying to get 'ore' just to show the structure).
        """
        player = next((p for p in self.state.players if p.id == active_player_id), None)
        if not player:
            return []
            
        trades = []
        cost = best_build.cost or BUILD_COSTS.get(best_build.type, {})
        player_resources = player.resources.model_dump()
        missing = best_build.missing or {
            resource: amount - player_resources.get(resource, 0)
            for resource, amount in cost.items()
            if player_resources.get(resource, 0) < amount
        }

        for needed, amount in missing.items():
            trades.extend(self.evaluate_bank_trades(player, needed, amount))
            trades.extend(self.evaluate_player_trades(player, needed))
        
        # Rank trades
        trades.sort(key=lambda t: t.score, reverse=True)
        return trades
