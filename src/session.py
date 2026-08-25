import json
from pathlib import Path
from typing import Dict, List

from .board import BoardGraph
from .build_engine import BUILD_COSTS, BuildEngine, BuildOption
from .hand_tracker import HandTracker
from .lookahead_engine import LookaheadEngine
from .models import City, GameState, PRODUCIBLE_RESOURCES, Resources, Road, Settlement, TradeEvent
from .models import ResourceType
from .production_engine import ProductionEngine, parse_vertex
from .robber_engine import RobberEngine
from .trade_engine import TradeEngine, TradeOffer


class GameSession:
    """Mutable game façade shared by the interactive CLI and web API."""

    def __init__(self, state: GameState):
        self.state = state
        self.board = BoardGraph(state.board)
        self.production = ProductionEngine(state, self.board)
        self.builds = BuildEngine(state, self.board, self.production)
        self.trades = TradeEngine(state, self.board, self.production)
        self.robber = RobberEngine(state, self.board)
        self.hands = HandTracker(state)
        self.lookahead = LookaheadEngine(state, self.board, self.production)

    @classmethod
    def from_file(cls, path: str | Path) -> "GameSession":
        data = json.loads(Path(path).read_text())
        return cls(GameState.model_validate(data))

    def roll(self, roll: int) -> Dict[str, Dict[str, int]]:
        if roll < 2 or roll > 12:
            raise ValueError("A dice roll must be between 2 and 12.")
        result = {}
        for player in self.state.players:
            income = self.production.get_roll_income(player.id, roll)
            self._add_resources(player.resources, income)
            result[player.id] = income
        self.state.turn += 1
        return result

    def place_robber(self, q: int, r: int) -> None:
        if (q, r) not in self.board.tiles:
            raise ValueError("The robber must be placed on a tile that exists on the board.")
        self.state.board.robber.q = q
        self.state.board.robber.r = r
        self.board.robber_pos = (q, r)

    def update_tile(self, q: int, r: int, resource: ResourceType, number: int | None = None) -> None:
        """Update a tile from the visual board editor."""
        tile = next((tile for tile in self.state.board.tiles if tile.q == q and tile.r == r), None)
        if tile is None:
            raise ValueError("That tile does not exist on the board.")
        if resource not in (*PRODUCIBLE_RESOURCES, "desert"):
            raise ValueError(f"Unknown tile resource: {resource}")
        if number is not None and number not in range(2, 13):
            raise ValueError("Tile numbers must be between 2 and 12.")
        if resource == "desert":
            number = None
        tile.resource = resource
        tile.number = number

    def build(self, player_id: str, build_type: str, location: str = "") -> BuildOption:
        player = self._player(player_id)
        cost = BUILD_COSTS.get(build_type)
        if cost is None:
            raise ValueError(f"Unknown build type: {build_type}")
        missing = self.builds.get_missing_resources(player, cost)
        if missing:
            raise ValueError(f"Missing resources: {missing}")

        if build_type == "settlement":
            vertex = parse_vertex(location)
            if vertex not in self.board.vertices:
                raise ValueError("That settlement location is not on the board.")
            occupied = {
                parse_vertex(piece.vertex)
                for other in self.state.players
                for piece in [*other.settlements, *other.cities]
            }
            if vertex in occupied or any(len(set(vertex) & set(other)) >= 2 for other in occupied):
                raise ValueError("Settlements must be unoccupied and one vertex away from another building.")
            self._subtract_resources(player.resources, cost)
            player.settlements.append(Settlement(vertex=location))
        elif build_type == "city":
            vertex = parse_vertex(location)
            if not any(parse_vertex(settlement.vertex) == vertex for settlement in player.settlements):
                raise ValueError("A city must upgrade one of your settlements.")
            self._subtract_resources(player.resources, cost)
            player.settlements = [s for s in player.settlements if parse_vertex(s.vertex) != vertex]
            player.cities.append(City(vertex=location))
        elif build_type == "road":
            self._subtract_resources(player.resources, cost)
            player.roads.append(Road(edge=location))
        else:
            self._subtract_resources(player.resources, cost)
            player.devCards.unrevealed.count += 1
        return BuildOption(type=build_type, location=location, cost=cost, reasoning="Build applied to the live game state.")

    def trade(self, from_player: str, to_player: str, give: Dict[str, int], receive: Dict[str, int]) -> TradeEvent:
        giver = self._player(from_player)
        recipient = None if to_player == "bank" else self._player(to_player)
        if to_player == "bank" and sum(give.values()) != 4 * sum(receive.values()):
            raise ValueError("Bank trades must use the 4:1 ratio until port ownership is modeled.")
        self._validate_resource_names(receive)
        self._validate_resources(giver.resources, give)
        if recipient:
            self._validate_resources(recipient.resources, receive)
        self._subtract_resources(giver.resources, give)
        self._add_resources(giver.resources, receive)
        if recipient:
            self._subtract_resources(recipient.resources, receive)
            self._add_resources(recipient.resources, give)
        event = TradeEvent(turn=self.state.turn, fromPlayer=from_player, toPlayer=to_player, give=give, receive=receive)
        self.state.history.append(event)
        return event

    def recommendations(self, player_id: str | None = None) -> Dict[str, object]:
        player_id = player_id or self.state.activePlayer
        occupied = {
            parse_vertex(piece.vertex)
            for player in self.state.players
            for piece in [*player.settlements, *player.cities]
        }
        candidates = ["|".join(f"{q},{r}" for q, r in vertex) for vertex in self.board.get_available_settlements(occupied)]
        builds = self.builds.get_best_builds(player_id, candidates)
        best = builds[0] if builds else None
        trades: List[TradeOffer] = self.trades.get_recommended_trades(player_id, best) if best else []
        robber = self.robber.recommend(player_id)
        return {
            "recommendedBuild": best.model_dump() if best else None,
            "recommendedTrades": [trade.model_dump() for trade in trades],
            "robber": robber.model_dump() if robber else None,
            "lookahead": [option.model_dump() for option in self.lookahead.rank_settlements(player_id, candidates[:12])],
        }

    def _player(self, player_id: str):
        player = next((player for player in self.state.players if player.id == player_id), None)
        if player is None:
            raise ValueError(f"Unknown player: {player_id}")
        return player

    @staticmethod
    def _validate_resource_names(amounts: Dict[str, int]) -> None:
        unknown = set(amounts) - set(PRODUCIBLE_RESOURCES)
        if unknown:
            raise ValueError(f"Unknown resource(s): {', '.join(sorted(unknown))}")

    @staticmethod
    def _validate_resources(resources: Resources, amounts: Dict[str, int]) -> None:
        GameSession._validate_resource_names(amounts)
        if any(amount <= 0 for amount in amounts.values()):
            raise ValueError("Resource amounts must be positive.")
        current = resources.model_dump()
        missing = {resource: amount for resource, amount in amounts.items() if current.get(resource, 0) < amount}
        if missing:
            raise ValueError(f"Insufficient resources: {missing}")

    @staticmethod
    def _subtract_resources(resources: Resources, amounts: Dict[str, int]) -> None:
        for resource, amount in amounts.items():
            setattr(resources, resource, getattr(resources, resource) - amount)

    @staticmethod
    def _add_resources(resources: Resources, amounts: Dict[str, int]) -> None:
        for resource, amount in amounts.items():
            setattr(resources, resource, getattr(resources, resource) + amount)
