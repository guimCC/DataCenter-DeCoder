import sys
import os

# Add the backend directory to the Python path to find models and solver utils
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Attempt to import necessary components
try:
    from solver_utils_list import solve_module_list_with_fixed_modules, standardize_unit_name
    from models import Module, IOField
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Ensure 'models.py' and 'solver_utils_list.py' are in the same directory or accessible via PYTHONPATH.")
    sys.exit(1)

def create_test_module(id, name, io_data):
    """Helper function to create Module objects for testing."""
    fields = []
    for unit, amount, is_input, is_output in io_data:
        # Ensure amount is treated as float for consistency, handle None
        try:
            numeric_amount = float(amount) if amount is not None else 0.0
        except (ValueError, TypeError):
            print(f"Warning: Invalid amount '{amount}' for unit '{unit}' in module '{id}'. Using 0.0.")
            numeric_amount = 0.0
        fields.append(IOField(unit=unit, amount=numeric_amount, is_input=is_input, is_output=is_output))
    # Add dummy dimensions if not provided, as Module might require them
    if not any(f.unit == 'space_x' for f in fields):
        fields.append(IOField(unit='space_x', amount=1.0, is_input=True, is_output=False))
    if not any(f.unit == 'space_y' for f in fields):
         fields.append(IOField(unit='space_y', amount=1.0, is_input=True, is_output=False))
    return Module(id=id, name=name, io_fields=fields)

def run_fixed_module_test():
    """Tests the solver with a predefined set of fixed and selectable modules."""
    print("\n--- Running Test: solve_module_list_with_fixed_modules (Feasible Scenario) ---")

    # --- Define Fixed Modules ---
    fixed_power = create_test_module(
        id=1, name="Fixed Power Supply Unit",
        io_data=[
            ("price", 1200, True, False),
            ("grid_connection", 60, True, False),
            ("usable_power", 75, False, True), # Increased usable power from 55 to 75
        ]
    )
    fixed_rack = create_test_module(
        id=2, name="Fixed Basic Server Rack",
        io_data=[
            ("price", 600, True, False),
            ("usable_power", 5, True, False),
            ("data_storage", 50, False, True),
        ]
    )
    fixed_modules_list = [fixed_power, fixed_rack]

    # --- Define Selectable Modules ---
    compute_module = create_test_module(
        id=101, name="Compute Server A",
        io_data=[
            ("price", 400, True, False),
            ("usable_power", 15, True, False),
            ("processing", 100, False, True),
            ("internal_network", 20, False, True),
        ]
    )
    storage_module = create_test_module(
        id=102, name="Storage Array B",
        io_data=[
            ("price", 300, True, False),
            ("usable_power", 5, True, False),
            ("data_storage", 500, False, True),
            ("internal_network", 10, False, True),
        ]
    )
    network_switch = create_test_module(
        id=103, name="Network Switch C",
        io_data=[
            ("price", 500, True, False),
            ("usable_power", 10, True, False),
            ("internal_network", 50, True, False), # Reduced internal network consumption from 100 to 50
            ("external_network", 200, False, True),
        ]
    )
    selectable_modules_list = [compute_module, storage_module, network_switch]

    # --- Define Specs (Constraints and Objectives) ---
    problem_specs = [
        # Objectives
        {"Unit": "processing", "Maximize": 1},
        {"Unit": "data_storage", "Maximize": 1},
        {"Unit": "price", "Minimize": 1},
        # Constraints
        {"Unit": "grid_connection", "Below_Amount": 1, "Amount": 150}, # Max total grid power
        {"Unit": "external_network", "Above_Amount": 1, "Amount": 150}, # Min required external network
        # Implicit: usable_power >= 0, internal_network >= 0
    ]

    # --- Define Weights ---
    objective_weights = {
        "processing": 1.0,
        "data_storage": 1.2, # Slightly prefer storage
        "price": 0.5         # Cost is less critical than performance
    }

    # --- Execute the Solver ---
    print("Calling solve_module_list_with_fixed_modules...")
    selected_counts, final_net_resources = solve_module_list_with_fixed_modules(
        modules=selectable_modules_list,
        specs=problem_specs,
        weights=objective_weights,
        fixed_modules=fixed_modules_list
    )

    # --- Display Results ---
    print("\n--- Solver Results ---")
    if selected_counts or final_net_resources:
        print(f"Selected Module Counts (excluding fixed): {selected_counts}")
        print(f"Final Net Resources (including fixed modules):")
        # Print sorted net resources for clarity
        for unit, value in sorted(final_net_resources.items()):
             # Only print non-zero values for brevity, unless it's a constrained/objective unit
            is_relevant = unit in objective_weights or any(s.get('Unit') == unit for s in problem_specs)
            if value != 0 or is_relevant:
                print(f"  - {unit}: {value:.2f}")

        # Verification (Optional)
        print("\n--- Verification ---")
        initial_power = sum(f.amount for m in fixed_modules_list for f in m.io_fields if f.unit == 'usable_power' and f.is_output) - \
                        sum(f.amount for m in fixed_modules_list for f in m.io_fields if f.unit == 'usable_power' and f.is_input)
        selected_power_input = sum(selected_counts.get(m.id, 0) * next((f.amount for f in m.io_fields if f.unit == 'usable_power' and f.is_input), 0) for m in selectable_modules_list)
        selected_power_output = sum(selected_counts.get(m.id, 0) * next((f.amount for f in m.io_fields if f.unit == 'usable_power' and f.is_output), 0) for m in selectable_modules_list)
        net_power = initial_power + selected_power_output - selected_power_input
        print(f"Calculated Net Usable Power: {net_power:.2f} (Should match result above and be >= 0)")

        initial_ext_net = sum(f.amount for m in fixed_modules_list for f in m.io_fields if f.unit == 'external_network' and f.is_output) - \
                          sum(f.amount for m in fixed_modules_list for f in m.io_fields if f.unit == 'external_network' and f.is_input)
        selected_ext_net_input = sum(selected_counts.get(m.id, 0) * next((f.amount for f in m.io_fields if f.unit == 'external_network' and f.is_input), 0) for m in selectable_modules_list)
        selected_ext_net_output = sum(selected_counts.get(m.id, 0) * next((f.amount for f in m.io_fields if f.unit == 'external_network' and f.is_output), 0) for m in selectable_modules_list)
        net_ext_net = initial_ext_net + selected_ext_net_output - selected_ext_net_input
        ext_net_req = next((s['Amount'] for s in problem_specs if s.get('Unit') == 'external_network' and s.get('Above_Amount')), 0)
        print(f"Calculated Net External Network: {net_ext_net:.2f} (Should match result above and be >= {ext_net_req})")

    else:
        print("Solver did not find an optimal or feasible solution.") # Should not happen in this scenario


if __name__ == "__main__":
    run_fixed_module_test()
