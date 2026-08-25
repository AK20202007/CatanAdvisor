import sys
import json
from pathlib import Path

from pydantic import ValidationError
from .models import GameState
from .board import BoardGraph
from .production_engine import ProductionEngine
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
    
    # 2. Find best build
    # In a full game, we would generate all legal placements. Here we simulate a few choices.
    possible_settlements = ["0,0|1,0|0,1", "1,0|2,0|1,1", "-1,0|0,-1|0,0"]
    best_builds = build_engine.get_best_builds(state.activePlayer, possible_settlements)
    
    recommended_build = best_builds[0] if best_builds else None
    
    # 3. Find recommended trades
    recommended_trades = []
    if recommended_build:
        recommended_trades = trade_engine.get_recommended_trades(state.activePlayer, recommended_build)
        
    # 4. Output summary
    output = {
        "recommendedBuild": recommended_build.model_dump() if recommended_build else None,
        "recommendedTrades": [t.model_dump() for t in recommended_trades],
        "fallback": {
            "type": "dev_card",
            "reasoning": "No affordable build or high-likelihood trade this turn; dev card keeps VP progress live."
        }
    }
    
    print("\n--- Catan Advisor Engine Output ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
