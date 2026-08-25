from typing import List, Dict
from pydantic import BaseModel, Field
from .models import GameState, Player, ResourceType
from .board import BoardGraph, VertexCoord
from .production_engine import ProductionEngine, parse_vertex

class BuildOption(BaseModel):
    type: str  # "settlement", "city", "road", "dev_card"
    location: str = "" # vertex or edge string
    score: float = 0.0
    reasoning: str = ""
    cost: Dict[ResourceType, int] = Field(default_factory=dict)
    missing: Dict[ResourceType, int] = Field(default_factory=dict)


BUILD_COSTS: Dict[str, Dict[ResourceType, int]] = {
    "road": {"brick": 1, "lumber": 1},
    "settlement": {"brick": 1, "lumber": 1, "wool": 1, "grain": 1},
    "city": {"grain": 2, "ore": 3},
    "dev_card": {"wool": 1, "grain": 1, "ore": 1},
}

class BuildEngine:
    def __init__(self, game_state: GameState, board_graph: BoardGraph, production_engine: ProductionEngine):
        self.state = game_state
        self.board = board_graph
        self.production = production_engine
        
        # Tunable weights
        self.w1 = 1.0  # ΔExpectedProduction
        self.w2 = 0.5  # ExpansionValue (not fully implemented in v1)
        self.w3 = 1.5  # PortAccessValue
        self.w4 = 0.8  # DiversificationBonus
        
    def evaluate_settlement(self, player: Player, vertex_str: str) -> BuildOption:
        vertex = parse_vertex(vertex_str)
        pips = self.production.get_vertex_pips(vertex)
        total_pips = sum(pips.values())
        
        score = self.w1 * total_pips
        
        # Simple diversification bonus: favor resources the player currently lacks in production
        # In a full implementation, we'd compare this to their existing income.
        
        reasoning = f"Adds {total_pips} expected pips per turn."

        port_bonus, port_reasoning = self._port_synergy(player, vertex, pips)
        score += port_bonus
        if port_reasoning:
            reasoning += " " + port_reasoning
        
        cost = BUILD_COSTS["settlement"]
        missing = self.get_missing_resources(player, cost)
        missing_text = (
            " Missing: " + ", ".join(f"{amount} {resource}" for resource, amount in missing.items()) + "."
            if missing else ""
        )

        return BuildOption(
            type="settlement",
            location=vertex_str,
            score=score,
            reasoning=reasoning + missing_text,
            cost=cost,
            missing=missing,
        )

    def _port_synergy(self, player: Player, vertex: VertexCoord, pips: Dict[ResourceType, int]) -> tuple[float, str]:
        ports = self.board.get_ports_for_vertex(vertex)
        if not ports:
            return 0.0, ""

        income = self.production.calculate_expected_income().get(player.id, {})
        details = []
        bonus = 0.0
        for port in ports:
            if port.type == "3:1_generic":
                port_bonus = self.w3
                details.append("generic 3:1 port access")
            else:
                resource = port.type.removeprefix("2:1_")
                existing = income.get(resource, 0.0)
                local = pips.get(resource, 0)
                port_bonus = self.w3 * (1.0 + existing / 5.0 + local / 5.0)
                details.append(f"2:1 {resource} port synergy")
            bonus += port_bonus
        return bonus, "Also gains " + " and ".join(details) + "."

    @staticmethod
    def get_missing_resources(player: Player, cost: Dict[ResourceType, int]) -> Dict[ResourceType, int]:
        resources = player.resources.model_dump()
        return {
            resource: amount - resources.get(resource, 0)
            for resource, amount in cost.items()
            if resources.get(resource, 0) < amount
        }

    @staticmethod
    def can_afford(player: Player, build_type: str) -> bool:
        cost = BUILD_COSTS.get(build_type)
        return cost is not None and not BuildEngine.get_missing_resources(player, cost)

    def get_affordable_builds(self, player_id: str) -> List[BuildOption]:
        """Return affordable build types ranked by their immediate utility."""
        player = next((p for p in self.state.players if p.id == player_id), None)
        if not player:
            return []

        income = self.production.calculate_expected_income().get(player.id, {})
        total_income = sum(income.values())
        utility = {
            "city": total_income * 1.5,
            "settlement": total_income * 0.75,
            "road": 0.5,
            "dev_card": 0.25,
        }
        options = [
            BuildOption(
                type=build_type,
                score=utility[build_type],
                cost=cost,
                reasoning="Affordable this turn.",
            )
            for build_type, cost in BUILD_COSTS.items()
            if self.can_afford(player, build_type)
        ]
        return sorted(options, key=lambda option: (-option.score, option.type))
        
    def get_best_builds(self, player_id: str, possible_settlements: List[str]) -> List[BuildOption]:
        """
        Evaluates a list of possible builds and returns them ranked by score.
        In a full engine, `possible_settlements` would be generated by finding all legal placements.
        """
        player = next((p for p in self.state.players if p.id == player_id), None)
        if not player:
            return []
            
        options = []
        for v_str in possible_settlements:
            try:
                options.append(self.evaluate_settlement(player, v_str))
            except ValueError:
                continue
            
        # Sort by highest score
        options.sort(key=lambda x: x.score, reverse=True)
        return options
