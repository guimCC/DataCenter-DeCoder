from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel


app = FastAPI()

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run the app with: uvicorn main:app --reload
@app.get("/")
def home():
    return {"message": "API is running!"}

MODULES = [
    {
        "id": 1,
        "name": "Transformer_100",
        "io_fields": [
            {"is_input": True, "is_output": False, "unit": "Grid_Connection", "amount": 1},
            {"is_input": True, "is_output": False, "unit": "Space_X", "amount": 40},
            {"is_input": True, "is_output": False, "unit": "Space_Y", "amount": 45},
            {"is_input": True, "is_output": False, "unit": "Price", "amount": 1000},
            {"is_input": False, "is_output": True, "unit": "Usable_Power", "amount": 100}
        ]
    }
]

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


# GET: return all modules
@app.get("/modules")
def get_modules():
    return MODULES

# POST: add a new module
@app.post("/modules")
def add_module(module: Module):
    MODULES.append(module)
    return {"message": "Module added"}