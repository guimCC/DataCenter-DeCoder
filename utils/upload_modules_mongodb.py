import json
import requests

# Load modules from JSON
with open("../data/modules.json", "r") as f:
    modules = json.load(f)

# URL of your FastAPI backend
url = "http://localhost:8000/modules/upload-many"

# Send POST request
response = requests.post(url, json=modules)

# Print result
print("✅ Status code:", response.status_code)
print("📦 Response:", response.json())
