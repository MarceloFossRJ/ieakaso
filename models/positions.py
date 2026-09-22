from pydantic import BaseModel, Field, ValidationError, conint
from companies import Company

class PositionStage(BaseModel):
    name: str
    order: int
    is_initial: bool
    is_final: bool
    description: str
    position: Position

class Position(BaseModel):
    description: str
    location: str
    company: Company
    stages: dict[]