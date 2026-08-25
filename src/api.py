import hmac
import os
from pathlib import Path
from typing import Any, Dict

from .session import GameSession

try:
    from fastapi import Depends, FastAPI, Header, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
except ModuleNotFoundError as exc:  # pragma: no cover - exercised by deployment setup
    raise RuntimeError("Install fastapi and uvicorn to run the web API.") from exc


def create_app(state_path: str | Path = "sample_state.json") -> FastAPI:
    resolved_state_path = Path(state_path)
    if not resolved_state_path.is_absolute() and not resolved_state_path.exists():
        resolved_state_path = Path(__file__).resolve().parent.parent / resolved_state_path
    session = GameSession.from_file(resolved_state_path)
    api_token = os.getenv("CATAN_API_TOKEN")
    app = FastAPI(title="Catan Advisor API", version="1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Catan-Token"],
    )

    def require_token(x_catan_token: str | None = Header(default=None)) -> None:
        if not api_token:
            raise HTTPException(status_code=503, detail="Set CATAN_API_TOKEN before starting the API.")
        if not x_catan_token or not hmac.compare_digest(x_catan_token, api_token):
            raise HTTPException(status_code=401, detail="Valid X-Catan-Token header required.")

    @app.get("/api/state", dependencies=[Depends(require_token)])
    def get_state() -> Dict[str, Any]:
        return session.state.model_dump()

    @app.get("/api/recommendations", dependencies=[Depends(require_token)])
    def get_recommendations(player_id: str | None = None) -> Dict[str, Any]:
        return session.recommendations(player_id)

    @app.post("/api/roll", dependencies=[Depends(require_token)])
    def apply_roll(payload: Dict[str, int]) -> Dict[str, Any]:
        try:
            return {"income": session.roll(int(payload["roll"])), "recommendations": session.recommendations()}
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/robber", dependencies=[Depends(require_token)])
    def apply_robber(payload: Dict[str, int]) -> Dict[str, Any]:
        try:
            session.place_robber(int(payload["q"]), int(payload["r"]))
            return session.recommendations()
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/board/tile", dependencies=[Depends(require_token)])
    def update_tile(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            number = payload.get("number")
            session.update_tile(
                int(payload["q"]),
                int(payload["r"]),
                payload["resource"],
                None if number in (None, "") else int(number),
            )
            return {"state": session.state.model_dump(), "recommendations": session.recommendations()}
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/trade", dependencies=[Depends(require_token)])
    def apply_trade(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            event = session.trade(payload["fromPlayer"], payload["toPlayer"], payload["give"], payload["receive"])
            return {"event": event.model_dump(), "recommendations": session.recommendations()}
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/build", dependencies=[Depends(require_token)])
    def apply_build(payload: Dict[str, str]) -> Dict[str, Any]:
        try:
            session.build(payload.get("playerId", session.state.activePlayer), payload["type"], payload.get("location", ""))
            return session.recommendations()
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")
    return app


app = create_app(os.getenv("CATAN_STATE", "sample_state.json"))
