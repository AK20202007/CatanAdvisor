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

### Interactive shell

Keep a game state in memory and update it as the game progresses:

```bash
PYTHONPATH=. python -m src.cli --interactive sample_state.json
```

Useful commands include `roll 6`, `robber 1,1`, `build settlement 0,1|0,2|1,1`,
and `trade P1 1 lumber for 1 brick with P2`. The shell recalculates builds,
trades, robber placement, and lookahead suggestions after each change.

### Web UI and API

The optional FastAPI surface exposes the same live session to a small browser UI.
Set a token before starting it; all API requests require the `X-Catan-Token`
header and the browser keeps the token in memory only.

```bash
CATAN_API_TOKEN=choose-a-local-token uvicorn src.api:app --reload
```

Open `http://127.0.0.1:8000` and enter the same token. The board workspace lets
you click a tile to change its resource or number, move the robber to the
selected tile, click a board point to place a settlement or upgrade a city,
apply dice rolls, and inspect the updated recommendations. The API supports
the same state, recommendations, rolls, robber placement, trades, builds, and
tile editing actions.

### Optional board-photo ingestion

The calibrated OpenCV/OCR adapter is kept separate from the core dependencies:

```bash
pip install -r requirements-vision.txt
```

Call `src.cv_ingest.extract_board_from_image` with image regions mapped to axial
coordinates and a color palette for the physical board edition. Number-token OCR
is best-effort; unreadable numbers remain `None` for manual correction.

## Core Components

- **`models.py`**: Pydantic models mapping to the JSON schema.
- **`board.py`**: Axial coordinate graph logic (vertices, edges).
- **`production_engine.py`**: Calculates probability-based expected resource income per turn for each player based on the board graph.
- **`build_engine.py`**: Scores various build options (settlements, cities) using heuristics and the production probabilities.
- **`trade_engine.py`**: Suggests bank/port trades and player-to-player trade recommendations by looking at players' resource surplus and income.
- **`cli.py`**: Ingests JSON files, runs engines, and outputs trade/build recommendations.
- **`session.py`**: Applies rolls, builds, robber moves, and trades to a live in-memory game.
- **`robber_engine.py`**: Ranks robber placements by opponent production blocked while avoiding the active player's tiles.
- **`lookahead_engine.py`**: Scores settlement candidates across a shallow dice-probability horizon.
- **`api.py` / `web/`**: Token-protected FastAPI and browser UI for live sessions.
- **`cv_ingest.py`**: Optional calibrated OpenCV/OCR board-photo adapter.
