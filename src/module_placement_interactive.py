"""
Optimized Datacenter Module Placement Algorithm with Region Locking

This script takes the resource optimization results and creates an efficient grid layout placement
for the selected modules using a greedy approach, with the ability to lock regions by selecting them with the mouse.

The improved placement algorithm prioritizes:
1. Minimizing total used space (compactness)
2. Placing modules with resource dependencies closer together
3. Reducing computation time by using a pure greedy approach
4. Respecting user-defined locked regions that are off-limits for module placement
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import time
from matplotlib.lines import Line2D
from resource_optimization_no_placement import load_data, run_datacenter_resource_optimization
from resource_optimization_no_placement import MODULES_CSV_PATH, SPEC_CSV_PATH
from matplotlib.widgets import RectangleSelector

# Resource flow categories (for positioning related modules)
INPUT_RESOURCES = ['grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']


class RegionLocker:
    """Handles user-defined locked regions in the datacenter grid."""
    
    def __init__(self, total_width, total_height):
        """
        Initialize the region locker.
        
        Args:
            total_width: Width of the datacenter grid
            total_height: Height of the datacenter grid
        """
        self.total_width = total_width
        self.total_height = total_height
        self.locked_regions = []
        self.fig = None
        self.ax = None
        self.rs = None
        self.grid = np.zeros((total_height, total_width), dtype=int)
        
    def start_region_selection(self):
        """Start the interactive region selection process."""
        print("Starting locked region selection mode")
        print("Instructions:")
        print("- Click and drag to select regions you want to lock")
        print("- Press Enter to complete selection")
        print("- Press Escape to cancel selection")
        
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        plt.title('Select Regions to Lock (Click & Drag, press Enter when done)')
        
        # Display the grid
        self.ax.set_xlim(0, self.total_width)
        self.ax.set_ylim(0, self.total_height)
        self.ax.grid(True, linestyle='--', alpha=0.3)
        
        # Show existing locked regions
        for region in self.locked_regions:
            x, y, width, height = region
            rect = Rectangle((x, y), width, height, 
                            facecolor='red', edgecolor='black', alpha=0.3)
            self.ax.add_patch(rect)
            
        def onselect(eclick, erelease):
            """Callback for region selection."""
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            
            # Ensure coordinates are within bounds
            x1 = max(0, min(x1, self.total_width))
            y1 = max(0, min(y1, self.total_height))
            x2 = max(0, min(x2, self.total_width))
            y2 = max(0, min(y2, self.total_height))
            
            # Calculate rectangle properties
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            # Add to locked regions
            if width > 0 and height > 0:
                self.locked_regions.append((x, y, width, height))
                print(f"Added locked region: x={x}, y={y}, width={width}, height={height}")
                
                # Update the grid
                for i in range(y, min(y + height, self.total_height)):
                    for j in range(x, min(x + width, self.total_width)):
                        self.grid[i, j] = -1  # -1 indicates locked cell
                
                # Redraw
                self.ax.clear()
                self.ax.set_xlim(0, self.total_width)
                self.ax.set_ylim(0, self.total_height)
                self.ax.grid(True, linestyle='--', alpha=0.3)
                
                for region in self.locked_regions:
                    rx, ry, rw, rh = region
                    rect = Rectangle((rx, ry), rw, rh, 
                                    facecolor='red', edgecolor='black', alpha=0.3)
                    self.ax.add_patch(rect)
                
                plt.title('Select Regions to Lock (Click & Drag, press Enter when done)')
                plt.draw()
        
        def on_key(event):
            """Handle keyboard events."""
            if event.key == 'enter':
                plt.close(self.fig)
                print(f"Selection completed. {len(self.locked_regions)} regions locked.")
            elif event.key == 'escape':
                self.locked_regions = []
                self.grid = np.zeros((self.total_height, self.total_width), dtype=int)
                plt.close(self.fig)
                print("Selection canceled.")
        
        # Set up the RectangleSelector
        self.rs = RectangleSelector(
            self.ax, onselect, useblit=True,
            button=[1], minspanx=1, minspany=1,
            spancoords='pixels', interactive=True
        )
        
        # Connect keyboard event
        self.fig.canvas.mpl_connect('key_press_event', on_key)
        
        plt.xlabel('X coordinate')
        plt.ylabel('Y coordinate')
        plt.show()
        
        return self.grid
    
    def clear_locked_regions(self):
        """Clear all locked regions."""
        self.locked_regions = []
        self.grid = np.zeros((self.total_height, self.total_width), dtype=int)
        print("All locked regions cleared.")

class GreedyModulePlacement:
    """Handles the greedy placement of modules on a grid."""
    
    def __init__(self, module_data, selected_modules_counts, total_width, total_height, locked_grid=None):
        """
        Initialize placement algorithm with module data and selection.
        
        Args:
            module_data: Dictionary with module specifications
            selected_modules_counts: Dictionary of selected module IDs and counts
            total_width: Width constraint of the datacenter
            total_height: Height constraint of the datacenter
            locked_grid: Grid with locked regions (cells with value -1 are locked)
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
        
        # Initialize grid with locked regions if provided
        if locked_grid is not None:
            self.initial_grid = locked_grid.copy()
        else:
            self.initial_grid = np.zeros((self.total_height, self.total_width), dtype=int)
        
        print(f"Initialized placement for {len(self.selected_modules)} module instances")
        print(f"Datacenter dimensions: {total_width} x {total_height}")
        if np.any(self.initial_grid == -1):
            locked_cells = np.sum(self.initial_grid == -1)
            total_cells = total_width * total_height
            print(f"Locked regions: {locked_cells} cells ({locked_cells/total_cells:.2%} of total area)")
    
    def create_empty_grid(self):
        """Create a grid with locked regions marked."""
        return self.initial_grid.copy()
    
    def can_place_module(self, grid, module, x, y):
        """Check if a module can be placed at the given position without overlapping."""
        if x < 0 or y < 0 or x + module['width'] > self.total_width or y + module['height'] > self.total_height:
            return False
        
        # Check if the area is empty (no modules and no locked regions)
        area = grid[y:y+module['height'], x:x+module['width']]
        return np.all(area == 0)  # 0 = empty, -1 = locked, >0 = module ID
    
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
        
        # First, place the largest module at the first available position
        first_placed = False
        first_idx = module_indices[0]
        first_module = self.selected_modules[first_idx]
        
        # Try to find a valid placement for the first module
        for y in range(self.total_height - first_module['height'] + 1):
            for x in range(self.total_width - first_module['width'] + 1):
                if self.can_place_module(grid, first_module, x, y):
                    grid = self.place_module(grid, first_module, x, y)
                    
                    first_module_placed = first_module.copy()
                    first_module_placed['x'] = x
                    first_module_placed['y'] = y
                    placement.append(first_module_placed)
                    placed_indices = {first_idx}
                    first_placed = True
                    break
            if first_placed:
                break
        
        if not first_placed:
            print("Error: Could not place the first module due to locked regions!")
            return [], grid
        
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
        
        # First visualize locked regions
        for y in range(self.total_height):
            for x in range(self.total_width):
                if self.initial_grid[y, x] == -1:
                    rect = Rectangle((x, y), 1, 1,
                                    facecolor='red', edgecolor='none',
                                    alpha=0.3)
                    ax.add_patch(rect)
        
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
        
        # Add legend for resource flow lines and locked regions
        legend_elements = [
            Line2D([0], [0], color='red', lw=2, label='Usable Power'),
            Line2D([0], [0], color='blue', lw=2, label='Fresh Water'),
            Line2D([0], [0], color='cyan', lw=2, label='Distilled Water'),
            Line2D([0], [0], color='lightblue', lw=2, label='Chilled Water'),
            Line2D([0], [0], color='green', lw=2, label='Internal Network'),
            Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.3, label='Locked Region')
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
        
        # Calculate locked area stats
        locked_cells = np.sum(self.initial_grid == -1)
        total_cells = self.total_width * self.total_height
        report.append(f"Locked area: {locked_cells}/{total_cells} cells = {locked_cells/total_cells:.2%}")
        
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
    print("=== Starting Greedy Datacenter Module Placement with Region Locking ===\n")
    
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
            
            # Initialize region locker
            region_locker = RegionLocker(total_width, total_height)
            
            # Allow user to interactively lock regions
            print("Do you want to lock any regions? (y/n)")
            user_input = input().strip().lower()
            
            if user_input == 'y':
                locked_grid = region_locker.start_region_selection()
            else:
                locked_grid = region_locker.grid
            
            # Create placement object
            placement_engine = GreedyModulePlacement(
                module_data,
                result['selected_modules_counts'],
                total_width,
                total_height,
                locked_grid
            )
            
            # Run greedy placement
            placement_engine.run_placement()
            
            # Output report and visualization
            print("\n" + placement_engine.generate_placement_report())
            
            # Save visualization to file
            placement_engine.visualize_placement(f"{spec_name}_greedy_placement.png")
            
        except Exception as e:
            print(f"Error during placement for {spec_name}: {e}")


def run_interactive_module_placement():
    """Run the module placement process in a fully interactive mode."""
    print("=== Starting Interactive Datacenter Module Placement with Region Locking ===\n")
    
    # Load the same data as used by resource optimization
    module_data, all_specs_df, module_ids, unique_spec_names = load_data(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )
    
    # Select a specification
    print("Available specifications:")
    for i, spec_name in enumerate(unique_spec_names):
        print(f"  {i+1}. {spec_name}")
    
    print("\nSelect a specification (enter number):")
    try:
        spec_idx = int(input()) - 1
        spec_name = unique_spec_names[spec_idx]
    except (ValueError, IndexError):
        print("Invalid selection. Using the first specification.")
        spec_name = unique_spec_names[0]
    
    print(f"\nSelected specification: {spec_name}")
    
    # Run resource optimization
    optimization_results = run_datacenter_resource_optimization(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )
    
    # Find the selected spec result
    selected_result = None
    for result in optimization_results:
        if result['spec_name'] == spec_name:
            selected_result = result
            break
    
    if not selected_result or selected_result['status'] not in ["Optimal", "Feasible"]:
        print(f"Error: No valid optimization result for {spec_name}")
        return
    
    try:
        # Extract total width and height from spec
        total_width, total_height = extract_space_constraints(all_specs_df, spec_name)
        
        # Initialize region locker
        region_locker = RegionLocker(total_width, total_height)
        
        # Interactive region locking loop
        while True:
            print("\nRegion Locking Options:")
            print("1. Add locked regions")
            print("2. Clear all locked regions")
            print("3. Continue to module placement")
            print("Enter your choice:")
            
            choice = input().strip()
            
            if choice == '1':
                locked_grid = region_locker.start_region_selection()
            elif choice == '2':
                region_locker.clear_locked_regions()
            elif choice == '3':
                break
            else:
                print("Invalid choice. Please try again.")
        
        # Create placement object
        placement_engine = GreedyModulePlacement(
            module_data,
            selected_result['selected_modules_counts'],
            total_width,
            total_height,
            region_locker.grid
        )
        
        # Run greedy placement
        placement_engine.run_placement()
        
        # Output report and visualization
        print("\n" + placement_engine.generate_placement_report())
        
        # Save visualization to file
        placement_engine.visualize_placement(f"{spec_name}_interactive_placement.png")
        
    except Exception as e:
        print(f"Error during placement for {spec_name}: {e}")


if __name__ == "__main__":
    print("Datacenter Module Placement Options:")
    print("1. Batch process all specifications")
    print("2. Interactive mode (select specification and lock regions)")
    print("Enter your choice:")
    
    choice = input().strip()
    
    if choice == '1':
        run_greedy_module_placement()
    elif choice == '2':
        run_interactive_module_placement()
    else:
        print("Invalid choice. Exiting.")