# Import necessary components
from app.backend.solver_utils_list import solve_module_list
from models import Module, IOField # Changed import source

# --- 1. Define Sample Modules ---
# Using the Module and IOField classes from main.py
module1 = Module(
    id=1,
    name="PowerGen_100",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="Space_X", amount=10),
        IOField(is_input=True, is_output=False, unit="Space_Y", amount=10),
        IOField(is_input=True, is_output=False, unit="Price", amount=500),
        IOField(is_input=False, is_output=True, unit="Usable_Power", amount=100) # Internal
    ]
)

module2 = Module(
    id=2,
    name="ServerRack_50",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="Space_X", amount=5),
        IOField(is_input=True, is_output=False, unit="Space_Y", amount=20),
        IOField(is_input=True, is_output=False, unit="Price", amount=1000),
        IOField(is_input=True, is_output=False, unit="Usable_Power", amount=50), # Internal
        IOField(is_input=False, is_output=True, unit="Processing", amount=50) # Output
    ]
)

module3 = Module(
    id=3,
    name="Cooler_Large",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="Space_X", amount=15),
        IOField(is_input=True, is_output=False, unit="Space_Y", amount=15),
        IOField(is_input=True, is_output=False, unit="Price", amount=800),
        IOField(is_input=True, is_output=False, unit="Usable_Power", amount=20), # Internal
        IOField(is_input=False, is_output=True, unit="Chilled_Water", amount=200) # Internal
    ]
)

available_modules = [module1, module2, module3]

# --- 2. Define Sample Specs ---
# List of dictionaries, similar to how it's received from the frontend/DB
specs = [
    # Objective: Maximize Processing
    {"Unit": "Processing", "Below_Amount": 0, "Above_Amount": 0, "Minimize": 0, "Maximize": 1, "Unconstrained": 0, "Amount": None},
    # Objective: Minimize Price
    {"Unit": "Price", "Below_Amount": 0, "Above_Amount": 0, "Minimize": 1, "Maximize": 0, "Unconstrained": 0, "Amount": None},
    # Constraint: Total Area Limit (Implicit via Space_X and Space_Y)
    {"Unit": "Space_X", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 50},
    {"Unit": "Space_Y", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 50},
    # Constraint: Require at least 80 Processing
    # {"Unit": "Processing", "Below_Amount": 0, "Above_Amount": 1, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 80},
]

# --- 3. Define Sample Weights ---
# Relative importance of objectives
weights = {
    "processing": 2.0, # Make processing twice as important as minimizing price
    "price": 1.0,
    "total_area": 0.1 # Optional: Add weight if minimizing area instead of constraining
}

# --- 4. Call the Function ---
print("--- Running Test ---")
selected_counts, net_resources = solve_module_list(available_modules, specs, weights)

# --- 5. Print Results ---
print("\n--- Test Results ---")
if selected_counts:
    print("Selected Module Counts:")
    for mod_id, count in selected_counts.items():
        # Find module name for better readability
        mod_name = next((m.name for m in available_modules if m.id == mod_id), "Unknown")
        print(f"  Module ID {mod_id} ({mod_name}): {count}")

    print("\nNet Resources:")
    for resource, value in net_resources.items():
        print(f"  {resource}: {value:.2f}")

    # Example Assertion (Optional - for automated testing)
    # You would calculate the expected outcome manually or based on a known good run
    # expected_counts = {2: 2} # Example: Expect 2 Server Racks
    # assert selected_counts == expected_counts, f"Expected {expected_counts}, but got {selected_counts}"
    # print("\nAssertion Passed (Example)")

else:
    print("Solver did not find a feasible/optimal solution or returned empty.")

print("\n--- Test Complete ---")