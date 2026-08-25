import json
import sys

from src.cli import main


def test_cli_uses_board_derived_candidates(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["catan-advisor", "sample_state.json"])

    main()

    output = capsys.readouterr().out
    payload = json.loads(output[output.index("{"):])
    build = payload["recommendedBuild"]

    assert build is not None
    assert build["location"] not in {
        "0,0|1,0|0,1",
        "1,0|2,0|1,1",
        "-1,0|0,-1|0,0",
    }
    assert payload["fallback"] is None
