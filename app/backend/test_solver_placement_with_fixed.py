import json
import numpy as np
from models import Module, IOField
from solver_utils_placement import _solve_module_placement, solve_modules_placement_with_fixed, validate_placement_output
from solver_utils_list import standardize_unit_name # Needed if used within tests, though not directly in the provided snippets

# --- Constants (copy if needed by tests, or import if defined elsewhere) ---
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']

def test_placement_output():
    """Tests the basic _solve_module_placement function."""
    print("\n--- Testing Basic Placement ---")
    # Create test modules
    test_modules = [
        Module(
            id=1,
            name="Test Module",
            io_fields=[
                IOField(is_input=True, is_output=False, unit="space_x", amount=2),
                IOField(is_input=True, is_output=False, unit="space_y", amount=2),
                IOField(is_input=False, is_output=True, unit="processing", amount=100),
                IOField(is_input=True, is_output=False, unit="price", amount=50)
            ]
        ),
        Module(
            id=2,
            name="Network Module",
            io_fields=[
                IOField(is_input=True, is_output=False, unit="space_x", amount=1),
                IOField(is_input=True, is_output=False, unit="space_y", amount=1),
                IOField(is_input=False, is_output=True, unit="external_network", amount=50),
                IOField(is_input=True, is_output=False, unit="price", amount=20)
            ]
        )
    ]


    # Create specs
    test_specs = [
        {"Unit": "space_x", "Below_Amount": 1, "Amount": 10}, # Smaller grid for testing
        {"Unit": "space_y", "Below_Amount": 1, "Amount": 8},
        {"Unit": "price", "Below_Amount": 1, "Amount": 1000}, # Example budget
        {"Unit": "processing", "Above_Amount": 1, "Amount": 300}, # Example requirement
        {"Unit": "external_network", "Above_Amount": 1, "Amount": 80}
    ]

    # Selected modules
    test_selected = {1: 3, 2: 2} # 3 instances of module ID 1, 2 instances of module ID 2

    # Call the placement function (Note: _solve_module_placement doesn't use weights directly)
    result = _solve_module_placement(test_modules, test_specs, test_selected)

    # Validate the output
    is_valid, message = validate_placement_output(result)
    print(f"Validation result: {is_valid}")
    print(f"Message: {message}")

    # Print the complete output as formatted JSON
    print("\n=== BASIC PLACEMENT OUTPUT ===")
    print(json.dumps(result, indent=2))

    return result

def test_fixed_placement():
    """Tests the solve_modules_placement_with_fixed function."""
    print("\n--- Testing Fixed Placement ---")
    # Create test modules
    test_modules = [
        Module(id=1, name="Compute A", io_fields=[IOField(is_input=True, is_output=False, unit="space_x", amount=2), IOField(is_input=True, is_output=False, unit="space_y", amount=2), IOField(is_input=False, is_output=True, unit="processing", amount=100), IOField(is_input=True, is_output=False, unit="price", amount=50)]),
        Module(id=2, name="Network B", io_fields=[IOField(is_input=True, is_output=False, unit="space_x", amount=1), IOField(is_input=True, is_output=False, unit="space_y", amount=1), IOField(is_input=False, is_output=True, unit="external_network", amount=50), IOField(is_input=True, is_output=False, unit="price", amount=20)]),
        Module(id=3, name="Storage C", io_fields=[IOField(is_input=True, is_output=False, unit="space_x", amount=3), IOField(is_input=True, is_output=False, unit="space_y", amount=2), IOField(is_input=False, is_output=True, unit="data_storage", amount=200), IOField(is_input=True, is_output=False, unit="price", amount=80)])
    ]
    test_specs = [
        {"Unit": "space_x", "Below_Amount": 1, "Amount": 8},
        {"Unit": "space_y", "Below_Amount": 1, "Amount": 7},
        {"Unit": "price", "Below_Amount": 1, "Amount": 2000},
        {"Unit": "processing", "Above_Amount": 1, "Amount": 400},
        {"Unit": "external_network", "Above_Amount": 1, "Amount": 80},
        {"Unit": "data_storage", "Above_Amount": 1, "Amount": 300}
    ]
    # Total counts needed
    test_selected_total = {1: 5, 2: 3, 3: 2} # 5xA, 3xB, 2xC TOTAL

    # Define fixed modules (1xA, 1xC are fixed)
    fixed_modules = [
        {"id": 1, "name": "Compute A", "gridColumn": 0, "gridRow": 0, "width": 2, "height": 2},
        {"id": 3, "name": "Storage C", "gridColumn": 5, "gridRow": 5, "width": 3, "height": 2}
        # We expect the solver to place the remaining 4xA, 3xB, 1xC
    ]

    # Call the new function
    result = solve_modules_placement_with_fixed(
        test_modules,
        test_specs,
        test_selected_total,
        fixed_modules
    )

    # Validate and print
    is_valid, message = validate_placement_output(result)
    print(f"Validation result: {is_valid}")
    print(f"Message: {message}")
    print("\n=== FIXED PLACEMENT OUTPUT ===")
    print(json.dumps(result, indent=2))

    # Add specific assertions if using a test framework like pytest
    assert is_valid, f"Validation failed: {message}"
    assert len(result.get("modules", [])) == sum(test_selected_total.values()), "Incorrect total number of modules in output"
    # Check if fixed modules are present at correct locations
    fixed_found_count = 0
    for fm in fixed_modules:
        found = False
        for rm in result.get("modules", []):
            if (rm['id'] == fm['id'] and
                rm['gridColumn'] == fm['gridColumn'] and
                rm['gridRow'] == fm['gridRow']):
                found = True
                fixed_found_count += 1
                break
        assert found, f"Fixed module {fm['id']} not found at expected location ({fm['gridColumn']}, {fm['gridRow']})"
    assert fixed_found_count == len(fixed_modules), "Not all fixed modules were found"


    return result

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


# Add this function after test_fixed_placement but before the __main__ block
def plot_placement_result(result, fixed_modules=None, save_path=None):
    """
    Creates a visualization of the module placement, highlighting fixed modules.
    
    Args:
        result: The datacenter configuration result from the placement function
        fixed_modules: List of dictionaries with fixed module information
        save_path: Optional path to save the figure, if None it will be displayed
    """
    # Extract datacenter dimensions from placed modules
    if not result.get("modules"):
        print("No modules to plot.")
        return
    
    # Find the dimensions by getting max x and y
    max_x = max(m["gridColumn"] + m["width"] for m in result["modules"])
    max_y = max(m["gridRow"] + m["height"] for m in result["modules"])
    
    # Create a figure with a grid
    fig, ax = plt.subplots(figsize=(max(12, max_x), max(8, max_y)))
    
    # Draw grid lines
    for i in range(max_x + 1):
        ax.axvline(i, color='gray', linestyle='-', linewidth=0.5)
    for i in range(max_y + 1):
        ax.axhline(i, color='gray', linestyle='-', linewidth=0.5)
    
    # Map from module ID to a color
    unique_ids = sorted(set(m["id"] for m in result["modules"]))
    color_map = plt.cm.get_cmap('tab10', len(unique_ids))
    id_to_color = {mod_id: color_map(i) for i, mod_id in enumerate(unique_ids)}
    
    # Create a set of fixed module positions for quick lookup
    fixed_positions = set()
    if fixed_modules:
        for fm in fixed_modules:
            x, y = fm["gridColumn"], fm["gridRow"]
            fixed_positions.add((x, y))
    
    # Draw modules as rectangles
    for m in result["modules"]:
        mod_id = m["id"]
        x, y = m["gridColumn"], m["gridRow"]
        w, h = m["width"], m["height"]
        
        # Check if this is a fixed module
        is_fixed = (x, y) in fixed_positions
        
        # Get basic color for module type
        color = id_to_color[mod_id]
        
        # Create rectangle
        rect = patches.Rectangle(
            (x, y), w, h, 
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.7 if is_fixed else 0.3,  # Fixed modules are more opaque
            hatch='///' if is_fixed else None  # Add hatching to fixed modules
        )
        ax.add_patch(rect)
        
        # Add text label
        plt.text(
            x + w/2, y + h/2, 
            f"ID:{mod_id}\n{m['name'][:8]}", 
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=8,
            fontweight='bold' if is_fixed else 'normal'
        )
    
    # Create legend for module types
    legend_elements = [
        patches.Patch(color=id_to_color[mod_id], alpha=0.3, 
                     label=f"ID {mod_id}: {next((m['name'] for m in result['modules'] if m['id'] == mod_id), '')}")
        for mod_id in unique_ids
    ]
    
    # Add fixed module indicator to legend
    legend_elements.append(
        patches.Patch(facecolor='gray', alpha=0.7, hatch='///', 
                     label='Fixed Module')
    )
    
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Set axis labels and title
    ax.set_xlabel('X (grid columns)')
    ax.set_ylabel('Y (grid rows)')
    ax.set_title('Datacenter Module Placement (Fixed modules are hatched)')
    
    # Invert y-axis to match grid coordinates (0,0 at top left)
    ax.invert_yaxis()
    
    # Adjust plot limits
    ax.set_xlim(-0.5, max_x + 0.5)
    ax.set_ylim(max_y + 0.5, -0.5)  # Inverted y-axis
    
    # Customize ticks to show grid coordinates
    ax.set_xticks(range(max_x + 1))
    ax.set_yticks(range(max_y + 1))
    
    plt.tight_layout()
    
    # Save or show plot
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()

# Update the __main__ block to use the plotting function
if __name__ == "__main__":
    # basic_output = test_placement_output()
    fixed_output = test_fixed_placement()
    
    # Define fixed modules (same as in test_fixed_placement)
    fixed_modules = [
        {"id": 1, "name": "Compute A", "gridColumn": 0, "gridRow": 0, "width": 2, "height": 2},
        {"id": 3, "name": "Storage C", "gridColumn": 5, "gridRow": 5, "width": 3, "height": 2}
    ]
    
    # Plot the result
    plot_placement_result(fixed_output, fixed_modules)



# Run the tests
if __name__ == "__main__":
    # basic_output = test_placement_output()
    fixed_output = test_fixed_placement()
    plot_placement_result(fixed_output, fixed_modules)


