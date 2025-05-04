from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import  json
# Remove Pydantic import if no longer needed directly here
# from pydantic import BaseModel # Keep if needed for other things, remove if not

# Import models from the new file
from models import Module, IOField, PositionedModule, SpecRule, DataCenter

# MongoDB
from mongo_utils import insert_modules, get_all_modules, get_database

from solver_utils_list import _solve_module_list, solve_module_list_with_fixed_modules
from solver_utils_placement import _solve_module_placement, solve_modules_placement_with_fixed
import ast

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


@app.post('/solve-components')
async def solve_components_with_fixed_modules(specs, weights, fixed_modules: list[Module] = []):
    # Get all modules and convert weights to Python object
    modules = get_modules()
    weights = ast.literal_eval(weights)
    
    # Get solution from solver
    sol_modules, sol_states = solve_module_list_with_fixed_modules(modules, specs, weights, fixed_modules)
    print(sol_modules)
    
    
    # Create module lookup dictionary for faster access
    modules_by_id = {mod['id']: mod for mod in modules}
    
    # Generate result list with all module instances
    result_modules = []
    
    # For each module ID in the solution
    for module_id, quantity in sol_modules.items():
        module_id = int(module_id) if isinstance(module_id, str) else module_id
        
        if module_id not in modules_by_id:
            print(f"Warning: Module ID {module_id} not found in database")
            continue
            
        # Get the module data
        module = modules_by_id[module_id]
        
        # Get width and height from io_fields
        width = next((io['amount'] for io in module['io_fields'] if io['unit'] == 'Space_X'), 1)
        height = next((io['amount'] for io in module['io_fields'] if io['unit'] == 'Space_Y'), 1)
        
        # Create the specified number of copies
        for i in range(quantity):
            result_modules.append({
                "id": module_id,
                "name": module['name'],
                "width": width,
                "height": height,
                "instanceId": f"{module_id}_{i}",  # Create unique instance ID
                "gridColumn": 1,  # Default position
                "gridRow": 1,     # Default position
                "io_fields": module['io_fields']
            })
    
    # Return properly formatted result
    return {"modules": result_modules,
            "raw_solution":{
                "modules": sol_modules,
                "states": sol_states,
                "specs": json.loads(specs),
            }}


# POST: solve problem for the placements of the modules of module_list, possibly with fixed_modules
@app.post('/solve-placements')
def solve_placements(data: Dict):
    # No need to use json.loads on data - FastAPI already deserializes it
    # Extract the required data from the request
    modules = get_modules() 
    specs = data.get('specs', [])
    module_quantities = data.get('module_quantities', {})
    print("Module Quantities: ", module_quantities)
    grid_dimensions = data.get('grid_dimensions', {})
    current_modules = data.get('modules', {})
    
    
    # Call the placement solver with the correct parameters
    print("Modules: ", modules)
    print("Curr. Mod: ", current_modules)
    result = solve_modules_placement_with_fixed(
        modules,
        specs,
        module_quantities,
        current_modules
    )
    
    return result


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