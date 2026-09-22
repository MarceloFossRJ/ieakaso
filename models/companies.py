from pydantic import BaseModel, Field, ValidationError

class Company(BaseModel):
    name: str
    website: str
    description: str
