from pydantic import BaseModel
from typing import List, Dict

# Pydantic models
class IOField(BaseModel):
    is_input: bool
    is_output: bool
    unit: str
    amount: float

class Module(BaseModel):
    id: int
    name: str
    io_fields: List[IOField]

class PositionedModule(Module):
    gridColumn: int
    gridRow: int
    width: int
    height: int

class SpecRule(BaseModel):
    Below_Amount: int
    Above_Amount: int
    Minimize: int
    Maximize: int
    Unconstrained: int
    Unit: str
    Amount: float | None # Allow None for Amount

class DataCenter(BaseModel):
    id: int
    name: str
    specs: List[SpecRule]
    details: Dict[str, float]
    modules: List[PositionedModule]

