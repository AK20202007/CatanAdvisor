from typing import List, Dict, Optional
from pydantic import BaseModel
from .models import GameState, Player, ResourceType
from .board import BoardGraph
from .production_engine import ProductionEngine
from .build_engine import BuildOption

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
        
    def get_player_income(self, player_id: str) -> Dict[ResourceType, float]:
        incomes = self.production.calculate_expected_income()
        return incomes.get(player_id, {res: 0.0 for res in ["brick", "lumber", "wool", "grain", "ore"]})
        
    def evaluate_bank_trades(self, active_player: Player, needed: ResourceType) -> List[TradeOffer]:
        """
        Suggests 4:1 bank trades to obtain the needed resource.
        (In a full implementation, it would check for 3:1 and 2:1 port ownership).
        """
        offers = []
        resources = active_player.resources.model_dump()
        for res, amount in resources.items():
            if res != needed and amount >= 4:
                offers.append(TradeOffer(
                    give={res: 4},
                    receive={needed: 1},
                    offerTo="bank",
                    score=2.0,
                    acceptanceLikelihood="high",
                    reasoning=f"Convert surplus 4 {res} to 1 {needed} via bank."
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
                active_surplus.append(res)
                
        if not active_surplus:
            return offers
            
        for opponent in self.state.players:
            if opponent.id == active_player.id:
                continue
                
            opp_income = self.get_player_income(opponent.id)
            
            # If opponent has high expected income of the needed resource
            if opp_income.get(needed, 0.0) > 2.0:
                # Offer our biggest surplus
                offer_res = active_surplus[0]
                offers.append(TradeOffer(
                    give={offer_res: 1},
                    receive={needed: 1},
                    offerTo=opponent.id,
                    score=3.5,
                    acceptanceLikelihood="moderate",
                    reasoning=f"{opponent.id} has high {needed} production; they might trade it for {offer_res}."
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
            
        # In a real engine, we'd calculate exactly what is missing for `best_build`
        needed_resource = "ore" 
        
        trades = []
        trades.extend(self.evaluate_bank_trades(player, needed_resource))
        trades.extend(self.evaluate_player_trades(player, needed_resource))
        
        # Rank trades
        trades.sort(key=lambda t: t.score, reverse=True)
        return trades
