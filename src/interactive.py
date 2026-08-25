import re

from .session import GameSession


TRADE_RE = re.compile(
    r"^trade\s+(?P<from>\S+)\s+(?P<give_amount>\d+)\s+(?P<give_resource>\w+)\s+"
    r"for\s+(?P<receive_amount>\d+)\s+(?P<receive_resource>\w+)\s+with\s+(?P<to>\S+)$",
    re.IGNORECASE,
)
BUILD_RE = re.compile(r"^(?P<player>\S+)\s+builds?\s+(?P<type>\w+)(?:\s+(?P<location>.+))?$", re.IGNORECASE)
RESOURCE_ALIASES = {"wood": "lumber", "wheat": "grain", "sheep": "wool", "clay": "brick"}


def help_text() -> str:
    return """Commands:
  recommend
  roll <2-12>
  robber <q>,<r>
  build <settlement|city|road|dev_card> [location]
  P2 builds settlement <location>
  trade <player> <amount> <resource> for <amount> <resource> with <player|bank>
    resource aliases: wood/lumber, wheat/grain, sheep/wool, clay/brick
  help
  quit
"""


def run_interactive(session: GameSession) -> None:
    print("Catan Advisor interactive shell. Type 'help' for commands.")
    while True:
        try:
            raw = input("catan> ").strip()
        except EOFError:
            print()
            return
        if not raw:
            continue
        if raw.lower() in {"quit", "exit"}:
            return
        if raw.lower() == "help":
            print(help_text())
            continue
        try:
            result = execute_command(session, raw)
            if result is not None:
                print(result)
        except (ValueError, IndexError) as exc:
            print(f"Error: {exc}")


def execute_command(session: GameSession, raw: str):
    parts = raw.split()
    command = parts[0].lower()
    if command == "recommend":
        return session.recommendations()
    if command == "roll" and len(parts) == 2:
        return session.roll(int(parts[1]))
    if command == "robber" and len(parts) == 2:
        q, r = (int(value) for value in parts[1].split(","))
        session.place_robber(q, r)
        return {"robber": f"{q},{r}"}
    if command == "build" and len(parts) >= 2:
        return session.build(session.state.activePlayer, parts[1], " ".join(parts[2:])).model_dump()
    build_match = BUILD_RE.match(raw)
    if build_match:
        data = build_match.groupdict()
        return session.build(data["player"], data["type"], data.get("location") or "").model_dump()
    match = TRADE_RE.match(raw)
    if match:
        data = match.groupdict()
        give_resource = RESOURCE_ALIASES.get(data["give_resource"].lower(), data["give_resource"].lower())
        receive_resource = RESOURCE_ALIASES.get(data["receive_resource"].lower(), data["receive_resource"].lower())
        return session.trade(
            data["from"],
            data["to"],
            {give_resource: int(data["give_amount"])},
            {receive_resource: int(data["receive_amount"])},
        ).model_dump()
    raise ValueError("Unknown command. Type 'help' to see available commands.")
