"""
Optimized Datacenter Module Placement Algorithm

This script takes the resource optimization results and creates an efficient grid layout placement
for the selected modules using a greedy approach.

The improved placement algorithm prioritizes:
1. Minimizing total used space (compactness)
2. Placing modules with resource dependencies closer together
3. Reducing computation time by using a pure greedy approach
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import time
from matplotlib.lines import Line2D
from resource_optimization_no_placement import load_data, run_datacenter_resource_optimization
from resource_optimization_no_placement import MODULES_CSV_PATH, SPEC_CSV_PATH

# Resource flow categories (for positioning related modules)
INPUT_RESOURCES = ['grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']


class GreedyModulePlacement:
    """Handles the greedy placement of modules on a grid."""
    
    def __init__(self, module_data, selected_modules_counts, total_width, total_height):
        """
        Initialize placement algorithm with module data and selection.
        
        Args:
            module_data: Dictionary with module specifications
            selected_modules_counts: Dictionary of selected module IDs and counts
            total_width: Width constraint of the datacenter
            total_height: Height constraint of the datacenter
        """
        self.module_data = module_data
        self.selected_modules = []
        
        # Create individual module instances based on counts
        for mod_id, count in selected_modules_counts.items():
            for i in range(count):
                mod_info = module_data[mod_id]
                module = {
                    'id': mod_id,
                    'name': mod_info['name'],
                    'width': mod_info['width'],
                    'height': mod_info['height'],
                    'inputs': mod_info['inputs'].copy(),
                    'outputs': mod_info['outputs'].copy(),
                    'instance': i,  # Instance counter for multiple of same type
                    'x': -1,  # To be determined by placement algorithm
                    'y': -1   # To be determined by placement algorithm
                }
                self.selected_modules.append(module)
        
        self.total_width = total_width
        self.total_height = total_height
        self.grid = None
        self.best_placement = None
        self.best_score = float('-inf')
        
        print(f"Initialized placement for {len(self.selected_modules)} module instances")
        print(f"Datacenter dimensions: {total_width} x {total_height}")
    
    def create_empty_grid(self):
        """Create an empty grid representation of the datacenter area."""
        return np.zeros((self.total_height, self.total_width), dtype=int)
    
    def can_place_module(self, grid, module, x, y):
        """Check if a module can be placed at the given position without overlapping."""
        if x < 0 or y < 0 or x + module['width'] > self.total_width or y + module['height'] > self.total_height:
            return False
        
        # Check if the area is empty (all zeros)
        area = grid[y:y+module['height'], x:x+module['width']]
        return np.all(area == 0)
    
    def place_module(self, grid, module, x, y):
        """Place a module on the grid and return the updated grid."""
        new_grid = grid.copy()
        module_id = int(module['id'])
        new_grid[y:y+module['height'], x:x+module['width']] = module_id
        return new_grid
    
    def analyze_resource_connections(self):
        """
        Analyze all modules to find the resource dependencies between them.
        Returns a connectivity graph showing which modules should be placed near each other.
        """
        # Create a connectivity matrix where each cell [i,j] represents the 
        # strength of the connection between module i and j
        n = len(self.selected_modules)
        connectivity = np.zeros((n, n))
        
        # For each resource type
        for resource in INTERNAL_RESOURCES:
            # Find producers and consumers
            producers = [(i, mod, mod['outputs'].get(resource, 0)) 
                         for i, mod in enumerate(self.selected_modules) 
                         if resource in mod['outputs']]
            
            consumers = [(i, mod, mod['inputs'].get(resource, 0)) 
                         for i, mod in enumerate(self.selected_modules) 
                         if resource in mod['inputs']]
            
            # Connect producers to consumers
            for p_idx, p_mod, p_amount in producers:
                for c_idx, c_mod, c_amount in consumers:
                    if p_idx != c_idx:  # Don't connect module to itself
                        flow = min(p_amount, c_amount)
                        connectivity[p_idx, c_idx] += flow
                        connectivity[c_idx, p_idx] += flow  # Make it symmetric
        
        return connectivity

    def enhanced_greedy_placement(self):
        """
        Enhanced greedy placement algorithm that considers both module size and connectivity.
        
        Steps:
        1. Sort modules by size (largest first)
        2. Pre-calculate module connectivity
        3. Place modules one by one, prioritizing placement near connected modules
        4. Use a more efficient grid packing approach
        """
        print("Starting enhanced greedy placement...")
        start_time = time.time()
        
        # Pre-calculate connectivity
        connectivity = self.analyze_resource_connections()
        
        # Sort modules by area (largest first)
        module_indices = list(range(len(self.selected_modules)))
        module_indices.sort(key=lambda i: self.selected_modules[i]['width'] * 
                                        self.selected_modules[i]['height'], 
                            reverse=True)
        
        # Create empty grid and placement list
        grid = self.create_empty_grid()
        placement = []
        
        # First, place the largest module at the origin
        first_idx = module_indices[0]
        first_module = self.selected_modules[first_idx]
        
        grid = self.place_module(grid, first_module, 0, 0)
        
        first_module_placed = first_module.copy()
        first_module_placed['x'] = 0
        first_module_placed['y'] = 0
        placement.append(first_module_placed)
        placed_indices = {first_idx}
        
        # Place remaining modules
        while len(placed_indices) < len(self.selected_modules):
            best_position = None
            best_module_idx = None
            best_distance = float('inf')
            
            # Find the next module to place based on connectivity
            for i in module_indices:
                if i in placed_indices:
                    continue
                
                candidate = self.selected_modules[i]
                
                # Calculate connectivity score to already placed modules
                total_connectivity = sum(connectivity[i, j] for j in placed_indices)
                
                # If connected, prioritize this module
                if total_connectivity > 0:
                    # Find best position for this module
                    min_dist = float('inf')
                    best_pos = None
                    
                    # Try to place near connected modules
                    for placed_idx in placed_indices:
                        placed_mod = placement[list(placed_indices).index(placed_idx)]
                        
                        # Try positions around this module
                        positions_to_try = []
                        
                        # Try right of the module
                        positions_to_try.append((
                            placed_mod['x'] + placed_mod['width'], 
                            placed_mod['y']
                        ))
                        
                        # Try below the module
                        positions_to_try.append((
                            placed_mod['x'], 
                            placed_mod['y'] + placed_mod['height']
                        ))
                        
                        # Try left of the module
                        positions_to_try.append((
                            placed_mod['x'] - candidate['width'], 
                            placed_mod['y']
                        ))
                        
                        # Try above the module
                        positions_to_try.append((
                            placed_mod['x'], 
                            placed_mod['y'] - candidate['height']
                        ))
                        
                        for x, y in positions_to_try:
                            if self.can_place_module(grid, candidate, x, y):
                                # Calculate manhattan distance to all connected modules
                                total_dist = 0
                                candidate_center_x = x + candidate['width'] / 2
                                candidate_center_y = y + candidate['height'] / 2
                                
                                for other_idx in placed_indices:
                                    other_mod = placement[list(placed_indices).index(other_idx)]
                                    other_center_x = other_mod['x'] + other_mod['width'] / 2
                                    other_center_y = other_mod['y'] + other_mod['height'] / 2
                                    
                                    manhattan_dist = (abs(candidate_center_x - other_center_x) + 
                                                     abs(candidate_center_y - other_center_y))
                                    
                                    # Weight by connectivity
                                    weighted_dist = manhattan_dist / (connectivity[i, other_idx] + 0.1)
                                    total_dist += weighted_dist
                                
                                if total_dist < min_dist:
                                    min_dist = total_dist
                                    best_pos = (x, y)
                    
                    if best_pos and min_dist < best_distance:
                        best_distance = min_dist
                        best_position = best_pos
                        best_module_idx = i
            
            # If no connected module found, take the next largest module
            if best_module_idx is None:
                for i in module_indices:
                    if i not in placed_indices:
                        best_module_idx = i
                        break
                
                # If we found an unplaced module, find the best compact position
                if best_module_idx is not None:
                    candidate = self.selected_modules[best_module_idx]
                    
                    # Try to place in a compact way
                    min_outer_area = float('inf')
                    
                    # Try all possible positions
                    for y in range(0, self.total_height - candidate['height'] + 1):
                        for x in range(0, self.total_width - candidate['width'] + 1):
                            if self.can_place_module(grid, candidate, x, y):
                                # Calculate new bounding box if this module is placed here
                                temp_placement = placement + [{
                                    'x': x, 
                                    'y': y, 
                                    'width': candidate['width'], 
                                    'height': candidate['height']
                                }]
                                
                                min_x = min(mod['x'] for mod in temp_placement)
                                min_y = min(mod['y'] for mod in temp_placement)
                                max_x = max(mod['x'] + mod['width'] for mod in temp_placement)
                                max_y = max(mod['y'] + mod['height'] for mod in temp_placement)
                                
                                outer_area = (max_x - min_x) * (max_y - min_y)
                                
                                if outer_area < min_outer_area:
                                    min_outer_area = outer_area
                                    best_position = (x, y)
            
            # Place the chosen module
            if best_module_idx is not None and best_position is not None:
                module = self.selected_modules[best_module_idx]
                x, y = best_position
                
                grid = self.place_module(grid, module, x, y)
                
                module_placed = module.copy()
                module_placed['x'] = x
                module_placed['y'] = y
                placement.append(module_placed)
                placed_indices.add(best_module_idx)
                
                print(f"Placed module {module['name']} (ID:{module['id']}) at position ({x},{y})")
            else:
                print("Warning: Could not place all modules!")
                break
        
        # Calculate final score
        self.best_placement = placement
        self.grid = grid
        self.calculate_placement_score()
        
        elapsed_time = time.time() - start_time
        print(f"Placement completed in {elapsed_time:.2f} seconds")
        
        return placement, grid
    
    def calculate_placement_score(self):
        """Calculate the score for the final placement."""
        if not self.best_placement:
            return 0
            
        # Find min/max coordinates of placed modules
        min_x = min(mod['x'] for mod in self.best_placement)
        min_y = min(mod['y'] for mod in self.best_placement)
        max_x = max(mod['x'] + mod['width'] for mod in self.best_placement)
        max_y = max(mod['y'] + mod['height'] for mod in self.best_placement)
        
        # Calculate bounding box area and used area
        bbox_area = (max_x - min_x) * (max_y - min_y)
        used_area = sum(mod['width'] * mod['height'] for mod in self.best_placement)
        
        # Density within bounding box (compactness)
        if bbox_area == 0:
            compactness = 0
        else:
            compactness = used_area / bbox_area
            
        # Calculate connectivity score
        connectivity = self.analyze_resource_connections()
        connectivity_score = 0
        total_connections = 0
        
        for i, mod_i in enumerate(self.best_placement):
            for j, mod_j in enumerate(self.best_placement):
                if i != j and connectivity[i, j] > 0:
                    # Calculate distance between centers
                    center_i_x = mod_i['x'] + mod_i['width'] / 2
                    center_i_y = mod_i['y'] + mod_i['height'] / 2
                    center_j_x = mod_j['x'] + mod_j['width'] / 2
                    center_j_y = mod_j['y'] + mod_j['height'] / 2
                    
                    manhattan_dist = abs(center_i_x - center_j_x) + abs(center_i_y - center_j_y)
                    max_dist = self.total_width + self.total_height
                    
                    # Higher connectivity and lower distance = better score
                    connection_score = connectivity[i, j] * (1 - manhattan_dist / max_dist)
                    connectivity_score += connection_score
                    total_connections += connectivity[i, j]
        
        # Normalize connectivity score
        if total_connections > 0:
            connectivity_score /= total_connections
            
        # Final score (weighted average)
        final_score = 0.6 * compactness + 0.4 * connectivity_score
        self.best_score = final_score
        
        print(f"Final placement score: {final_score:.4f}")
        print(f"Compactness: {compactness:.4f}")
        print(f"Connectivity: {connectivity_score:.4f}")
        
        return final_score
    
    def get_resource_connections(self):
        """
        Map the resource flows between modules.
        Returns dict of connections where each key is a resource type
        and values are lists of (producer_idx, consumer_idx, flow) tuples.
        """
        connections = {res: [] for res in INTERNAL_RESOURCES}
        
        for resource in INTERNAL_RESOURCES:
            # Find producers of this resource
            producers = []
            for i, mod in enumerate(self.best_placement):
                if resource in mod['outputs']:
                    producers.append((i, mod['outputs'][resource]))
            
            # Find consumers of this resource
            consumers = []
            for i, mod in enumerate(self.best_placement):
                if resource in mod['inputs']:
                    consumers.append((i, mod['inputs'][resource]))
            
            # Create connections between producers and consumers
            remaining_production = {i: amount for i, amount in producers}
            remaining_consumption = {i: amount for i, amount in consumers}
            
            for p_idx, _ in producers:
                for c_idx, _ in consumers:
                    if p_idx != c_idx and remaining_production.get(p_idx, 0) > 0 and remaining_consumption.get(c_idx, 0) > 0:
                        flow = min(remaining_production[p_idx], remaining_consumption[c_idx])
                        connections[resource].append((p_idx, c_idx, flow))
                        remaining_production[p_idx] -= flow
                        remaining_consumption[c_idx] -= flow
        
        return connections
    
    def run_placement(self):
        """Run the greedy placement and return the results."""
        return self.enhanced_greedy_placement()
    
    def visualize_placement(self, save_path=None):
        """
        Visualize the module placement with a color-coded grid.
        """
        if self.best_placement is None:
            print("No placement to visualize. Run placement algorithm first.")
            return
            
        plt.figure(figsize=(12, 10))
        ax = plt.gca()
        
        # Generate colors for module types (same type = same color)
        unique_ids = set(m['id'] for m in self.best_placement)
        colors = plt.cm.tab20(np.linspace(0, 1, len(unique_ids)))
        id_to_color = {id: colors[i] for i, id in enumerate(unique_ids)}
        
        # Plot each module as a rectangle
        for module in self.best_placement:
            rect = Rectangle((module['x'], module['y']), 
                            module['width'], module['height'],
                            facecolor=id_to_color[module['id']],
                            edgecolor='black',
                            alpha=0.7)
            ax.add_patch(rect)
            
            # Add module name and ID text
            label = f"{module['name']}\n(ID:{module['id']})"
            plt.text(module['x'] + module['width']/2, 
                    module['y'] + module['height']/2,
                    label,
                    ha='center', va='center',
                    fontsize=8)
        
        # Add resource flow lines
        connections = self.get_resource_connections()
        for resource, flows in connections.items():
            for p_idx, c_idx, flow in flows:
                if p_idx >= len(self.best_placement) or c_idx >= len(self.best_placement):
                    continue
                    
                p_mod = self.best_placement[p_idx]
                c_mod = self.best_placement[c_idx]
                
                p_center_x = p_mod['x'] + p_mod['width'] // 2
                p_center_y = p_mod['y'] + p_mod['height'] // 2
                c_center_x = c_mod['x'] + c_mod['width'] // 2
                c_center_y = c_mod['y'] + c_mod['height'] // 2
                
                # Line width based on flow amount
                line_width = 0.5 + (flow / 100)
                
                # Different colors for different resource types
                if resource == 'usable_power':
                    color = 'red'
                elif resource == 'fresh_water':
                    color = 'blue'
                elif resource == 'distilled_water':
                    color = 'cyan'
                elif resource == 'chilled_water':
                    color = 'lightblue'
                elif resource == 'internal_network':
                    color = 'green'
                else:
                    color = 'gray'
                
                plt.plot([p_center_x, c_center_x], [p_center_y, c_center_y], 
                        '-', color=color, linewidth=line_width, alpha=0.5)
        
        # Draw grid outline
        plt.xlim(0, self.total_width)
        plt.ylim(0, self.total_height)
        plt.grid(True, linestyle='--', alpha=0.3)
        
        # Add legend for resource flow lines
        legend_elements = [
            Line2D([0], [0], color='red', lw=2, label='Usable Power'),
            Line2D([0], [0], color='blue', lw=2, label='Fresh Water'),
            Line2D([0], [0], color='cyan', lw=2, label='Distilled Water'),
            Line2D([0], [0], color='lightblue', lw=2, label='Chilled Water'),
            Line2D([0], [0], color='green', lw=2, label='Internal Network')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title('Datacenter Module Placement')
        plt.xlabel('X coordinate')
        plt.ylabel('Y coordinate')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Placement visualization saved to {save_path}")
        
        plt.show()
    
    def generate_placement_report(self):
        """Generate a text report of the placement results."""
        if not self.best_placement:
            return "No placement results available."
            
        report = []
        report.append("=== Module Placement Report ===\n")
        report.append(f"Total modules placed: {len(self.best_placement)}")
        
        # Find actual used area
        min_x = min(mod['x'] for mod in self.best_placement)
        min_y = min(mod['y'] for mod in self.best_placement)
        max_x = max(mod['x'] + mod['width'] for mod in self.best_placement)
        max_y = max(mod['y'] + mod['height'] for mod in self.best_placement)
        
        used_width = max_x - min_x
        used_height = max_y - min_y
        theoretical_area = sum(mod['width'] * mod['height'] for mod in self.best_placement)
        actual_area = used_width * used_height
        
        report.append(f"Area utilization: {theoretical_area}/{actual_area} = {theoretical_area/actual_area:.2%}")
        report.append(f"Used dimensions: {used_width} x {used_height}")
        report.append(f"Placement score: {self.best_score:.4f}")
        
        report.append("\nModule placement coordinates:")
        
        # Sort by module type for readability
        sorted_placement = sorted(self.best_placement, key=lambda m: (m['id'], m['instance']))
        
        for module in sorted_placement:
            report.append(f"  - {module['name']} (ID: {module['id']}, Instance: {module['instance']}): "
                         f"Position=({module['x']},{module['y']}), "
                         f"Size={module['width']}x{module['height']}")
        
        return "\n".join(report)


def extract_space_constraints(spec_df, spec_name):
    """Extract space constraints (total width and height) from spec."""
    width_rows = spec_df[
        (spec_df['Name'] == spec_name) &
        (spec_df['Unit'] == 'space_x') & 
        (spec_df['Below_Amount'] == 1)
    ]['Amount']
    
    height_rows = spec_df[
        (spec_df['Name'] == spec_name) & 
        (spec_df['Unit'] == 'space_y') & 
        (spec_df['Below_Amount'] == 1)
    ]['Amount']
    
    if width_rows.empty or height_rows.empty:
        raise ValueError(f"Missing space constraints for spec {spec_name}")
        
    total_width = int(width_rows.iloc[0])
    total_height = int(height_rows.iloc[0])
    
    return total_width, total_height


def run_greedy_module_placement():
    """Run the module placement process using the greedy algorithm."""
    print("=== Starting Greedy Datacenter Module Placement ===\n")
    
    # Load the same data as used by resource optimization
    module_data, all_specs_df, module_ids, unique_spec_names = load_data(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )
    
    # Run resource optimization to get the selected modules
    optimization_results = run_datacenter_resource_optimization(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )
    
    # Process each specification result
    for result in optimization_results:
        spec_name = result['spec_name']
        status = result['status']
        
        if status not in ["Optimal", "Feasible"]:
            print(f"Skipping placement for {spec_name} - Status: {status}")
            continue
        
        print(f"\n====== Running Greedy Placement for Specification: {spec_name} ======\n")
        
        try:
            # Extract total width and height from spec
            total_width, total_height = extract_space_constraints(all_specs_df, spec_name)
            
            # Create placement object
            placement_engine = GreedyModulePlacement(
                module_data,
                result['selected_modules_counts'],
                total_width,
                total_height
            )
            
            # Run greedy placement
            placement_engine.run_placement()
            
            # Output report and visualization
            print("\n" + placement_engine.generate_placement_report())
            
            # Save visualization to file
            placement_engine.visualize_placement(f"{spec_name}_greedy_placement.png")
            
        except Exception as e:
            print(f"Error during placement for {spec_name}: {e}")


if __name__ == "__main__":
    run_greedy_module_placement()