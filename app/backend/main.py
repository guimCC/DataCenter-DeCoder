from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from pydantic import BaseModel

# MongoDB
from mongo_utils import insert_modules, get_all_modules, get_database

from solver_utils import solve_module_list, solve_module_placement

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
    Amount: float

class DataCenter(BaseModel):
    id: int
    name: str
    specs: List[SpecRule]
    details: Dict[str, float]
    modules: List[PositionedModule]


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
            "name": "Water_Supply_100",
            "io_fields": [
                {"is_input": True, "is_output": False, "unit": "Space_X", "amount": 30},
                {"is_input": True, "is_output": False, "unit": "Space_Y", "amount": 30},
                {"is_input": True, "is_output": False, "unit": "Price", "amount": 500},
                {"is_input": False, "is_output": True, "unit": "Cooling", "amount": 100}
            ]
        },
        {
            "id": 3,
            "name": "Server_Rack_500",
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


# POST: solve layout
@app.post("/solve-dummy")
async def solve(specs: json, weights) -> json:
    modules = get_modules()
    # solve for the list of modules
    module_list = solve_module_list(modules, specs, weights)
    
    # solve for the location given the list of modules
    return solve_module_placement(modules, specs, weights, module_list)






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

######################### DATACENTER #########################
# GET: return all datacenters
@app.get("/datacenters")
def get_all_datacenters():
    db = get_database()
    return list(db.datacenters.find({}, {"_id": 0}))

# GET: a single datacenter
@app.get("/datacenters/{id}")
def get_datacenter(id: int):
    db = get_database()
    result = db.datacenters.find_one({"id": id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Not found")
    return result

# POST: add a new datacenter
@app.post("/datacenters")
def create_datacenter(dc: DataCenter):
    db = get_database()
    if db.datacenters.find_one({"id": dc.id}):
        raise HTTPException(status_code=400, detail="ID already exists")
    db.datacenters.insert_one(dc.model_dump())
    return {"message": "Datacenter saved"}

# PUT: update a datacenter
@app.put("/datacenters/{id}")
def update_datacenter(id: int, dc: DataCenter):
    db = get_database()
    db.datacenters.update_one({"id": id}, {"$set": dc.model_dump()})
    return {"message": "Datacenter updated"}

# DELETE: delete a datacenter
@app.delete("/datacenters/{id}")
def delete_datacenter(id: int):
    db = get_database()
    db.datacenters.delete_one({"id": id})
    return {"message": "Datacenter deleted"}