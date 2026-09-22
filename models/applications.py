from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, conint
from enum import Enum, IntEnum
from uuid import UUID
from companies import Company
from positions import Position, PositionStage
import Comp

class ApplicationStatusEnum(IntEnum):
    APPLIED = 0
    INTERVIEWING = 1
    REJECTED = 2
    NO_ANSWER = 3

class Application(BaseModel):
    date: datetime
    broker_link: str
    website: str
    description: str
    position: Position
    position_stage: PositionStage
    company: Company
