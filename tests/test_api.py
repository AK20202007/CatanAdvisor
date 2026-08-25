from fastapi.testclient import TestClient

from src.api import create_app


def test_api_requires_token_and_supports_state_updates(monkeypatch):
    monkeypatch.setenv("CATAN_API_TOKEN", "test-token")
    client = TestClient(create_app("sample_state.json"))

    assert client.get("/api/state").status_code == 401
    headers = {"X-Catan-Token": "test-token"}
    state_response = client.get("/api/state", headers=headers)
    assert state_response.status_code == 200
    assert state_response.json()["activePlayer"] == "P1"

    roll_response = client.post("/api/roll", json={"roll": 8}, headers=headers)
    assert roll_response.status_code == 200
    assert roll_response.json()["income"]["P1"]["brick"] == 1

    tile_response = client.post(
        "/api/board/tile",
        json={"q": 0, "r": 0, "resource": "brick", "number": 5},
        headers=headers,
    )
    assert tile_response.status_code == 200
    assert tile_response.json()["state"]["board"]["tiles"][0]["resource"] == "brick"
