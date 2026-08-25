import sys
import json
from pathlib import Path

from pydantic import ValidationError
from .models import GameState
from .board import BoardGraph
from .production_engine import ProductionEngine, parse_vertex
from .build_engine import BuildEngine
from .trade_engine import TradeEngine

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli <game_state.json>")
        sys.exit(1)
        
    state_file = Path(sys.argv[1])
    if not state_file.exists():
        print(f"File not found: {state_file}")
        sys.exit(1)
        
    try:
        with open(state_file, 'r') as f:
            data = json.load(f)
        state = GameState.model_validate(data)
    except ValidationError as e:
        print("Invalid game state JSON:")
        print(e)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("JSON Decode Error:")
        print(e)
        sys.exit(1)

    print(f"Loaded game state for active player: {state.activePlayer}")
    
    # 1. Initialization
    board_graph = BoardGraph(state.board)
    production_engine = ProductionEngine(state, board_graph)
    build_engine = BuildEngine(state, board_graph, production_engine)
    trade_engine = TradeEngine(state, board_graph, production_engine)
    
    # 2. Find best builds from board-derived, non-adjacent vertices instead of
    # relying on a fixed list that may not exist on the current board.
    occupied = {
        parse_vertex(piece.vertex)
        for player in state.players
        for piece in [*player.settlements, *player.cities]
    }
    possible_settlements = [
        "|".join(f"{q},{r}" for q, r in vertex)
        for vertex in board_graph.get_available_settlements(occupied)
    ]
    best_builds = build_engine.get_best_builds(state.activePlayer, possible_settlements)
    
    recommended_build = best_builds[0] if best_builds else None
    
    # 3. Find recommended trades
    recommended_trades = []
    if recommended_build:
        recommended_trades = trade_engine.get_recommended_trades(state.activePlayer, recommended_build)
        
    # 4. Output summary
    fallback = None
    if not recommended_build:
        fallback = {
            "type": "dev_card",
            "reasoning": "No board placement could be evaluated from the current state.",
        }
    elif not recommended_trades and recommended_build.missing:
        fallback = {
            "type": "hold",
            "reasoning": "The recommended build is missing resources and no useful trade was found.",
        }

    output = {
        "recommendedBuild": recommended_build.model_dump() if recommended_build else None,
        "recommendedTrades": [t.model_dump() for t in recommended_trades],
        "fallback": fallback,
    }
    
    print("\n--- Catan Advisor Engine Output ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
