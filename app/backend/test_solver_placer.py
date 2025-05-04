# Import necessary components
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
from solver_utils_placement import solve_module_placement
from models import Module, IOField

# --- Visualization Function ---
def visualize_placement(placement_result, available_modules, save_path=None):
    """
    Visualize the module placement in the datacenter.
    
    Args:
        placement_result: Dictionary with placement results
        available_modules: List of Module objects for name lookup
        save_path: Optional path to save the visualization image
    """
    if "error" in placement_result:
        print(f"Cannot visualize placement due to error: {placement_result['error']}")
        return
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Set datacenter boundaries
    width = placement_result['width']
    height = placement_result['height']
    
    # Draw datacenter outline
    datacenter = patches.Rectangle((0, 0), width, height, linewidth=2, 
                                 edgecolor='black', facecolor='none')
    ax.add_patch(datacenter)
    
    # Create a mapping of module types to colors
    module_types = {m.id: m.name for m in available_modules}
    unique_ids = sorted(list(set(module_types.keys())))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_ids)))
    id_to_color = {module_id: colors[i] for i, module_id in enumerate(unique_ids)}
    
    # Draw each placed module
    legend_handles = []
    legend_names = []
    
    for module in placement_result['placed_modules']:
        module_id = module['id']
        x, y = module['x'], module['y']
        w, h = module['width'], module['height']
        
        color = id_to_color.get(module_id, 'gray')
        rect = patches.Rectangle((x, y), w, h, linewidth=1, 
                               edgecolor='black', facecolor=color, alpha=0.7)
        ax.add_patch(rect)
        
        # Add module ID text
        ax.text(x + w/2, y + h/2, str(module_id), 
                ha='center', va='center', fontsize=8, color='black')
        
        # Add to legend if not already added
        module_name = module_types.get(module_id, f"Unknown Module {module_id}")
        if module_name not in legend_names:
            legend_patch = patches.Patch(color=color, label=f"{module_name} (ID: {module_id})")
            legend_handles.append(legend_patch)
            legend_names.append(module_name)
    
    # Draw grid lines (optional)
    for i in range(0, width + 1, 5):
        ax.axvline(x=i, color='gray', linestyle='--', alpha=0.3)
    for i in range(0, height + 1, 5):
        ax.axhline(y=i, color='gray', linestyle='--', alpha=0.3)
    
    # Set up the plot
    ax.set_xlim(-1, width + 1)
    ax.set_ylim(-1, height + 1)
    ax.set_xticks(range(0, width + 1, 5))
    ax.set_yticks(range(0, height + 1, 5))
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # Add legend outside the plot
    plt.legend(handles=legend_handles, bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Add title and labels
    plt.title(f"Datacenter Module Placement ({width}x{height})\nScore: {placement_result['placement_score']:.4f}")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    
    # Adjust layout to make room for legend
    plt.tight_layout()
    plt.subplots_adjust(right=0.75)
    
    # Save or show the figure
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Visualization saved to: {save_path}")
    else:
        plt.show()
    
    return fig, ax

# --- 1. Define Sample Modules ---
# Create modules with dimensions and resource requirements
power_module = Module(
    id=1,
    name="Power Generator",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="space_x", amount=3),
        IOField(is_input=True, is_output=False, unit="space_y", amount=4),
        IOField(is_input=True, is_output=False, unit="price", amount=800),
        IOField(is_input=False, is_output=True, unit="usable_power", amount=200)
    ]
)

server_rack = Module(
    id=2,
    name="Server Rack",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="space_x", amount=2),
        IOField(is_input=True, is_output=False, unit="space_y", amount=5),
        IOField(is_input=True, is_output=False, unit="price", amount=1200),
        IOField(is_input=True, is_output=False, unit="usable_power", amount=60),
        IOField(is_input=False, is_output=True, unit="processing", amount=100),
        IOField(is_input=False, is_output=True, unit="data_storage", amount=50)
    ]
)

cooling_unit = Module(
    id=3,
    name="Cooling Unit",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="space_x", amount=3),
        IOField(is_input=True, is_output=False, unit="space_y", amount=3),
        IOField(is_input=True, is_output=False, unit="price", amount=600),
        IOField(is_input=True, is_output=False, unit="usable_power", amount=40),
        IOField(is_input=False, is_output=True, unit="chilled_water", amount=150)
    ]
)

network_switch = Module(
    id=4,
    name="Network Switch",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="space_x", amount=1),
        IOField(is_input=True, is_output=False, unit="space_y", amount=2),
        IOField(is_input=True, is_output=False, unit="price", amount=350),
        IOField(is_input=True, is_output=False, unit="usable_power", amount=15),
        IOField(is_input=False, is_output=True, unit="external_network", amount=100),
        IOField(is_input=False, is_output=True, unit="internal_network", amount=200)
    ]
)

storage_array = Module(
    id=5,
    name="Storage Array",
    io_fields=[
        IOField(is_input=True, is_output=False, unit="space_x", amount=2),
        IOField(is_input=True, is_output=False, unit="space_y", amount=2),
        IOField(is_input=True, is_output=False, unit="price", amount=900),
        IOField(is_input=True, is_output=False, unit="usable_power", amount=30),
        IOField(is_input=False, is_output=True, unit="data_storage", amount=500)
    ]
)

available_modules = [power_module, server_rack, cooling_unit, network_switch, storage_array]

# --- 2. Define Datacenter Specs ---
specs = [
    # Datacenter dimensions
    {"Unit": "space_x", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 30},
    {"Unit": "space_y", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 20},
    
    # Resource objectives
    {"Unit": "processing", "Below_Amount": 0, "Above_Amount": 0, "Minimize": 0, "Maximize": 1, "Unconstrained": 0, "Amount": None},
    {"Unit": "data_storage", "Below_Amount": 0, "Above_Amount": 0, "Minimize": 0, "Maximize": 1, "Unconstrained": 0, "Amount": None},
    {"Unit": "external_network", "Below_Amount": 0, "Above_Amount": 1, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 100}
]

# --- 3. Define Objective Weights ---
weights = {
    "processing": 1.5,
    "data_storage": 2.0,
    "external_network": 1.0
}

# --- 4. Define Selected Module Counts ---
# This is the output we would get from solve_module_list
selected_modules_counts = {
    1: 3,  # 3 Power Generators
    2: 7,  # 7 Server Racks
    3: 2,  # 2 Cooling Units
    4: 4,  # 4 Network Switches
    5: 3   # 3 Storage Arrays
}

# --- 5. Run the Placement Algorithm ---
print("--- Running Module Placement Test ---")
placement_result = solve_module_placement(available_modules, specs, weights, selected_modules_counts)

# --- 6. Print Results ---
print("\n--- Placement Results ---")
if "error" in placement_result:
    print(f"Error: {placement_result['error']}")
else:
    print(f"Datacenter Dimensions: {placement_result['width']} x {placement_result['height']}")
    print(f"Total Modules Placed: {len(placement_result['placed_modules'])}")
    print(f"Placement Score: {placement_result['placement_score']:.4f}")
    
    # Print modules count by type
    module_counts = {}
    for module in placement_result['placed_modules']:
        module_id = module['id']
        if module_id not in module_counts:
            module_counts[module_id] = 0
        module_counts[module_id] += 1
    
    print("\nPlaced Module Counts by Type:")
    for module_id, count in module_counts.items():
        module_name = next((m.name for m in available_modules if m.id == module_id), f"Unknown Module {module_id}")
        print(f"  {module_name}: {count}")
    
    # Verify no overlaps
    overlaps = 0
    for i, module1 in enumerate(placement_result['placed_modules']):
        for j, module2 in enumerate(placement_result['placed_modules']):
            if i != j:  # Don't compare a module with itself
                # Calculate module boundaries
                m1_x1, m1_y1 = module1['x'], module1['y']
                m1_x2, m1_y2 = m1_x1 + module1['width'], m1_y1 + module1['height']
                
                m2_x1, m2_y1 = module2['x'], module2['y']
                m2_x2, m2_y2 = m2_x1 + module2['width'], m2_y1 + module2['height']
                
                # Check for overlap
                if (m1_x1 < m2_x2 and m1_x2 > m2_x1 and
                    m1_y1 < m2_y2 and m1_y2 > m2_y1):
                    overlaps += 1
    
    if overlaps > 0:
        print(f"\nWARNING: Found {overlaps // 2} overlapping module pairs!")  # Divide by 2 because each overlap is counted twice
    else:
        print("\nNo module overlaps detected - valid placement!")
    
    # Check all modules are within datacenter boundaries
    out_of_bounds = 0
    for module in placement_result['placed_modules']:
        if (module['x'] < 0 or module['y'] < 0 or
            module['x'] + module['width'] > placement_result['width'] or
            module['y'] + module['height'] > placement_result['height']):
            out_of_bounds += 1
    
    if out_of_bounds > 0:
        print(f"\nWARNING: Found {out_of_bounds} modules outside datacenter boundaries!")
    else:
        print("All modules within datacenter boundaries!")
    
    # --- 7. Visualize the Placement ---
    print("\n--- Creating Visualization ---")
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Save visualization
    save_path = os.path.join(output_dir, 'datacenter_placement.png')
    visualize_placement(placement_result, available_modules, save_path)

print("\n--- Test Complete ---")

# --- Additional Test for Different Scenarios ---
def test_different_scenarios():
    """Run additional tests with different module configurations"""
    print("\n=== Testing Different Placement Scenarios ===")
    
    # Scenario 1: Dense placement with many small modules
    print("\n--- Scenario 1: Dense placement with many small modules ---")
    dense_specs = [
        {"Unit": "space_x", "Below_Amount": 1, "Amount": 20},
        {"Unit": "space_y", "Below_Amount": 1, "Amount": 15}
    ]
    
    dense_modules = {
        4: 12,  # 12 Network Switches (small)
        5: 8    # 8 Storage Arrays (medium)
    }
    
    dense_result = solve_module_placement(available_modules, dense_specs, weights, dense_modules)
    
    if "error" not in dense_result:
        print(f"Placed {len(dense_result['placed_modules'])} modules")
        print(f"Score: {dense_result['placement_score']:.4f}")
        
        save_path = os.path.join(output_dir, 'dense_placement.png')
        visualize_placement(dense_result, available_modules, save_path)
    
    # Scenario 2: Mixed module sizes
    print("\n--- Scenario 2: Mixed module sizes ---")
    mixed_specs = [
        {"Unit": "space_x", "Below_Amount": 1, "Amount": 25},
        {"Unit": "space_y", "Below_Amount": 1, "Amount": 25}
    ]
    
    mixed_modules = {
        1: 2,  # 2 Power Generators (large)
        2: 4,  # 4 Server Racks (tall)
        3: 3,  # 3 Cooling Units (medium)
        4: 5,  # 5 Network Switches (small)
        5: 3   # 3 Storage Arrays (medium)
    }
    
    mixed_result = solve_module_placement(available_modules, mixed_specs, weights, mixed_modules)
    
    if "error" not in mixed_result:
        print(f"Placed {len(mixed_result['placed_modules'])} modules")
        print(f"Score: {mixed_result['placement_score']:.4f}")
        
        save_path = os.path.join(output_dir, 'mixed_placement.png')
        visualize_placement(mixed_result, available_modules, save_path)
    
    # Scenario 3: Edge case - datacenter too small
    print("\n--- Scenario 3: Edge case - datacenter too small ---")
    small_specs = [
        {"Unit": "space_x", "Below_Amount": 1, "Amount": 8},
        {"Unit": "space_y", "Below_Amount": 1, "Amount": 8}
    ]
    
    small_modules = {
        1: 3,  # 3 Power Generators (too large to all fit)
    }
    
    small_result = solve_module_placement(available_modules, small_specs, weights, small_modules)
    
    if "error" not in small_result:
        print(f"Placed {len(small_result['placed_modules'])}/{sum(small_modules.values())} modules")
        print(f"Score: {small_result['placement_score']:.4f}")
        
        save_path = os.path.join(output_dir, 'small_placement.png')
        visualize_placement(small_result, available_modules, save_path)
    
    print("\n=== Additional Tests Complete ===")

# Run additional tests
if __name__ == "__main__":
    # Create output directory if needed
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Run additional scenarios
    test_different_scenarios()