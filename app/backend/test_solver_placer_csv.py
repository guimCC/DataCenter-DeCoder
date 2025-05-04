import csv
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from collections import defaultdict

from solver_utils_list import _solve_module_list
from solver_utils_placement import _solve_module_placement
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
    fig, ax = plt.subplots(figsize=(14, 10))
    
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
    id_to_color = {module_id: colors[i % 10] for i, module_id in enumerate(unique_ids)}
    
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

# --- Define file paths relative to this script ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), '../data') # Go up one level to 'app' then into 'data'
MODULES_CSV_PATH = os.path.join(DATA_DIR, 'Modules.csv')
SPECS_CSV_PATH = os.path.join(DATA_DIR, 'Data_Center_Spec.csv')

# Create output directory if it doesn't exist
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- 1. Load Modules from CSV ---
print(f"Loading modules from: {MODULES_CSV_PATH}")
modules_raw_data = defaultdict(lambda: {'name': None, 'io_fields': []})
try:
    with open(MODULES_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                mod_id = int(row['ID'])
                if modules_raw_data[mod_id]['name'] is None:
                    modules_raw_data[mod_id]['name'] = row['Name']

                modules_raw_data[mod_id]['io_fields'].append(
                    IOField(
                        is_input=bool(int(row['Is_Input'])),
                        is_output=bool(int(row['Is_Output'])),
                        unit=str(row['Unit']),
                        amount=float(row['Amount'])
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                print(f"Warning: Skipping row due to error ({e}): {row}")
                continue # Skip malformed rows

except FileNotFoundError:
    print(f"Error: Modules CSV file not found at {MODULES_CSV_PATH}")
    exit()
except Exception as e:
    print(f"Error reading Modules CSV: {e}")
    exit()

available_modules = [
    Module(id=mod_id, name=data['name'], io_fields=data['io_fields'])
    for mod_id, data in modules_raw_data.items()
]
print(f"Loaded {len(available_modules)} module types.")

# Function to test different specs
def test_spec_placement(spec_id):
    print(f"\n{'='*50}")
    print(f"Testing Datacenter Spec ID: {spec_id}")
    print(f"{'='*50}")
    
    # --- 2. Load Specs from CSV ---
    print(f"Loading specs for ID {spec_id} from: {SPECS_CSV_PATH}")
    specs = []
    try:
        with open(SPECS_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                try:
                    if int(row['ID']) == spec_id:
                        # Handle potential None/empty string for Amount
                        amount_str = row.get('Amount', '').strip()
                        amount_val = float(amount_str) if amount_str and amount_str != '-1' else None # Treat -1 or empty as None

                        specs.append({
                            "Unit": str(row['Unit']),
                            "Below_Amount": int(row['Below_Amount']),
                            "Above_Amount": int(row['Above_Amount']),
                            "Minimize": int(row['Minimize']),
                            "Maximize": int(row['Maximize']),
                            "Unconstrained": int(row['Unconstrained']),
                            "Amount": amount_val
                        })
                except (ValueError, KeyError, TypeError) as e:
                    print(f"Warning: Skipping spec row due to error ({e}): {row}")
                    continue # Skip malformed rows

    except FileNotFoundError:
        print(f"Error: Specs CSV file not found at {SPECS_CSV_PATH}")
        return
    except Exception as e:
        print(f"Error reading Specs CSV: {e}")
        return

    print(f"Loaded {len(specs)} spec rules for ID {spec_id}.")

    # --- 3. Define weights based on spec objectives ---
    weights = {}
    for spec in specs:
        unit = spec["Unit"].lower().replace(' ', '_')
        if spec["Maximize"] == 1:
            weights[unit] = 1.0  # Default weight
        elif spec["Minimize"] == 1:
            weights[unit] = 1.0  # Default weight
    
    # Make sure we have weights for common objectives
    if "price" not in weights and any(spec["Unit"].lower() == "price" for spec in specs):
        weights["price"] = 1.0
    if "total_area" not in weights:
        weights["total_area"] = 0.1  # Small weight for area minimization
    
    print(f"Using weights: {weights}")

    # --- 4. Run Module Selection ---
    print("\n--- Running Module Selection ---")
    selected_counts, net_resources = _solve_module_list(available_modules, specs, weights)

    if not selected_counts:
        print("Module selection failed or returned empty solution.")
        return

    print("\nSelected Module Counts:")
    for mod_id, count in selected_counts.items():
        mod_name = next((m.name for m in available_modules if m.id == mod_id), "Unknown")
        print(f"  Module ID {mod_id} ({mod_name}): {count}")

    # --- 5. Run Module Placement ---
    print("\n--- Running Module Placement ---")
    placement_result = _solve_module_placement(available_modules, specs, weights, selected_counts)

    if "error" in placement_result:
        print(f"Placement error: {placement_result['error']}")
        return

    print(f"Datacenter Dimensions: {placement_result['width']} x {placement_result['height']}")
    print(f"Total Modules Placed: {len(placement_result['placed_modules'])} / {sum(selected_counts.values())}")
    print(f"Placement Score: {placement_result['placement_score']:.4f}")
    
    # --- 6. Check for placement issues ---
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
    # Save visualization
    save_path = os.path.join(OUTPUT_DIR, f'datacenter_spec_{spec_id}_placement.png')
    visualize_placement(placement_result, available_modules, save_path)
    
    return placement_result

# --- Run tests for multiple spec IDs ---
if __name__ == "__main__":
    # Test multiple specs (you can adjust this list based on available spec IDs)
    spec_ids_to_test = [1, 2, 3]
    
    # Create a summary table
    print("\n\n=== SUMMARY OF PLACEMENT TESTS ===")
    print(f"{'Spec ID':<10} {'Modules Selected':<20} {'Modules Placed':<20} {'Placement Score':<20}")
    print("-" * 70)
    
    for spec_id in spec_ids_to_test:
        try:
            result = test_spec_placement(spec_id)
            if result and "placed_modules" in result:
                modules_placed = len(result['placed_modules'])
                score = result['placement_score']
                print(f"{spec_id:<10} {'N/A':<20} {modules_placed:<20} {score:<20.4f}")
            else:
                print(f"{spec_id:<10} {'Failed':<20} {'Failed':<20} {'N/A':<20}")
        except Exception as e:
            print(f"{spec_id:<10} {'Error':<20} {'Error':<20} {'Error':<20}")
            print(f"Error testing spec {spec_id}: {e}")
    
    print("\nAll tests completed. Visualizations saved to:", OUTPUT_DIR)