from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel

# MongoDB
from mongo_utils import insert_modules, get_all_modules, get_database


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
    return get_all_modules()

# POST: add a new module
@app.post("/modules")
def add_module(module: Module):
    insert_modules([module.model_dump()])
    return {"message": "Module added"}

# POST: add many modules
@app.post("/modules/upload-many")
def upload_many(modules: List[Module]):
    insert_modules([m.model_dump() for m in modules])
    return {"message": "Modules uploaded"}

# POST: solve dummy layout
@app.post("/solve-dummy")
async def solve_dummy():
    dummy_modules = [
        {
            "id": 1,
            "name": "Transformer_100",
            "io_fields": [
                {"is_input": True, "is_output": False, "unit": "Space_X", "amount": 40},
                {"is_input": True, "is_output": False, "unit": "Space_Y", "amount": 40},
                {"is_input": True, "is_output": False, "unit": "Price", "amount": 1000},
                {"is_input": False, "is_output": True, "unit": "Power", "amount": 100}
            ]
        },
        {
            "id": 2,
            "name": "Cooling_Unit",
            "io_fields": [
                {"is_input": True, "is_output": False, "unit": "Space_X", "amount": 30},
                {"is_input": True, "is_output": False, "unit": "Space_Y", "amount": 30},
                {"is_input": True, "is_output": False, "unit": "Price", "amount": 500},
                {"is_input": False, "is_output": True, "unit": "Cooling", "amount": 100}
            ]
        },
        {
            "id": 3,
            "name": "Processor_X",
            "io_fields": [
                {"is_input": True, "is_output": False, "unit": "Space_X", "amount": 50},
                {"is_input": True, "is_output": False, "unit": "Space_Y", "amount": 25},
                {"is_input": True, "is_output": False, "unit": "Price", "amount": 3000},
                {"is_input": False, "is_output": True, "unit": "Processing", "amount": 500}
            ]
        },
    ]

    # Fake layout logic: place modules left to right
    positioned = []
    for i, mod in enumerate(dummy_modules):
        mod["gridColumn"] = 1 #+ 10*i  # Space each 3 cells apart
        mod["gridRow"] = 1 + 5 * i
        positioned.append(mod)

    return {"modules": positioned}

# DELETE: delete a module
@app.delete("/modules/{module_id}")
def delete_module(module_id: int):
    db = get_database()
    result = db.modules.delete_one({"id": module_id})
    return {"success": result.deleted_count > 0}

# PUT: update a module
@app.put("/modules/{module_id}")
def update_module(module_id: int, updated: Module):
    db = get_database()
    db.modules.update_one({"id": module_id}, {"$set": updated.dict()})
    return {"message": "Updated"}
