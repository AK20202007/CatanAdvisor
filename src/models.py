from typing import List, Literal, Dict, Optional, Any, Union
from pydantic import BaseModel, Field

# Common Types
ResourceType = Literal["brick", "lumber", "wool", "grain", "ore", "desert"]
DevCardType = Literal["knight", "road_building", "year_of_plenty", "monopoly", "victory_point"]
PortType = Literal["3:1_generic", "2:1_brick", "2:1_lumber", "2:1_wool", "2:1_grain", "2:1_ore"]

class Coordinate(BaseModel):
    q: int
    r: int

class Tile(BaseModel):
    q: int
    r: int
    resource: ResourceType
    number: Optional[int] = None # None for desert

class Port(BaseModel):
    # Depending on representation, an edge could be defined by two adjacent tiles
    # or by a tile and a direction. Let's accept a string or a list of coordinates for flexibility in ingestion.
    edge: Any
    type: PortType

class Board(BaseModel):
    tiles: List[Tile]
    ports: List[Port]
    robber: Coordinate

class Resources(BaseModel):
    brick: int = 0
    lumber: int = 0
    wool: int = 0
    grain: int = 0
    ore: int = 0

class UnrevealedDevCards(BaseModel):
    count: int

class DevCards(BaseModel):
    unrevealed: UnrevealedDevCards
    revealed: List[DevCardType] = Field(default_factory=list)

class Settlement(BaseModel):
    vertex: str

class City(BaseModel):
    vertex: str

class Road(BaseModel):
    edge: Any

class Player(BaseModel):
    id: str
    victoryPoints: int
    resources: Resources
    devCards: DevCards
    settlements: List[Settlement] = Field(default_factory=list)
    cities: List[City] = Field(default_factory=list)
    roads: List[Road] = Field(default_factory=list)
    longestRoad: bool = False
    largestArmy: bool = False

class GameState(BaseModel):
    board: Board
    players: List[Player]
    activePlayer: str
