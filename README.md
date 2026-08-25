# Catan Advisor Engine

A decision-support tool that ingests the current state of a Settlers of Catan game (board layout, player count, each player's resources, victory points, and development cards) and outputs the highest-value build and trade recommendations for the active player, with reasoning attached to each suggestion.

## Setup

1. Make sure you have python 3 installed.
2. Initialize virtualenv and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Engine

A sample game state is provided in `sample_state.json`. Run the engine via CLI:

```bash
PYTHONPATH=. python -m src.cli sample_state.json
```

## Core Components

- **`models.py`**: Pydantic models mapping to the JSON schema.
- **`board.py`**: Axial coordinate graph logic (vertices, edges).
- **`production_engine.py`**: Calculates probability-based expected resource income per turn for each player based on the board graph.
- **`build_engine.py`**: Scores various build options (settlements, cities) using heuristics and the production probabilities.
- **`trade_engine.py`**: Suggests bank/port trades and player-to-player trade recommendations by looking at players' resource surplus and income.
- **`cli.py`**: Ingests JSON files, runs engines, and outputs trade/build recommendations.
