import json
import requests

# Load modules from JSON
with open("../data/datacenter_1.json", "r") as f:
    datacenter = json.load(f)

# Transform modules to match PositionedModule format
transformed_modules = []
for module in datacenter["modules"]:
    # Convert x,y coordinates to grid coordinates
    # Using simple formula:
    grid_column = module["x"] 
    grid_row = module["y"]
    
    # Create properly formatted module object
    positioned_module = {
        "id": module["id"],
        "name": module["name"],
        "io_fields": [],  # This field is required by the Module model; empty list as placeholder
        "gridColumn": grid_column,
        "gridRow": grid_row
    }
    
    transformed_modules.append(positioned_module)

# Replace the modules in the datacenter
datacenter["modules"] = transformed_modules

# URL of your FastAPI backend
base_url = "http://localhost:8000/datacenters"

# Send POST request
print("Sending datacenter:", json.dumps(datacenter, indent=2))
response = requests.post(base_url, json=datacenter)
print(f"✅ Datacenter ID: {datacenter.get('id', 'unknown')}, Status code: {response.status_code}")
if response.status_code == 200:
    print("📦 Response:", response.json())
else:
    print("❌ Error:", response.text)