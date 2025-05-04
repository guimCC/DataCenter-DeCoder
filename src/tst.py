"""
High-Performance Clustered Module Placement Algorithm

Optimized for speed while creating aesthetically pleasing layouts with
modules of the same type grouped together.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import time
import math
import random
from tqdm import tqdm
from collections import defaultdict

# Resource categories
INPUT_RESOURCES = ['grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']

class FastClusteredPlacement:
    """Optimized solution for clustered module placement with focus on performance."""
    
    def __init__(self, module_data, selected_modules, datacenter_width, datacenter_height, locked_regions=None):
        """
        Initialize the fast clustered placement engine.
        
        Args:
            module_data: Dictionary with module specifications
            selected_modules: Dictionary with module_id -> count mapping
            datacenter_width: Width of the datacenter grid
            datacenter_height: Height of the datacenter grid
            locked_regions: Optional boolean mask where True indicates locked cells
        """
        self.width = datacenter_width
        self.height = datacenter_height
        self.module_data = module_data
        
        # Create a spatial grid for fast collision detection
        self.grid = np.zeros((datacenter_height, datacenter_width), dtype=int)
        if locked_regions is not None:
            self.grid[locked_regions] = -1  # Mark locked regions
        
        # Process module data
        self.modules = []
        self.clusters_by_type = defaultdict(list)
        
        # Group modules by type and calculate centroids for faster access
        for module_id, count in selected_modules.items():
            if module_id not in module_data:
                continue
                
            module_info = module_data[module_id]
            
            # Create module instances
            for i in range(count):
                module = {
                    'id': module_id,
                    'name': module_info['name'],
                    'width': module_info['width'],
                    'height': module_info['height'],
                    'inputs': module_info['inputs'],
                    'outputs': module_info['outputs'],
                    'x': -1,  # Will be set during placement
                    'y': -1   # Will be set during placement
                }
                self.modules.append(module)
                self.clusters_by_type[module_id].append(module)
        
        # Final placement results
        self.placed_modules = []
        self.placement_score = 0
    
    def run(self):
        """Run the optimized placement algorithm."""
        print(f"Starting fast clustered placement for {len(self.modules)} modules of {len(self.clusters_by_type)} types")
        start_time = time.time()
        
        # Process modules in batches by type for better organization
        placed_count = 0
        
        # First, create super-modules (clusters) by combining modules of the same type
        super_modules = self._create_super_modules()
        
        # Sort super modules by area (largest first)
        super_modules.sort(key=lambda m: m['width'] * m['height'], reverse=True)
        
        # Place super modules one by one
        with tqdm(total=len(super_modules), desc="Placing clusters") as pbar:
            for super_module in super_modules:
                if self._place_super_module(super_module):
                    placed_count += len(super_module['modules'])
                    pbar.update(1)
                else:
                    # If placement failed, try splitting and placing individually
                    print(f"Failed to place super module with {len(super_module['modules'])} modules of type {super_module['name']}")
                    # Try to place individual modules
                    individual_success = 0
                    for module in super_module['modules']:
                        if self._place_individual_module(module):
                            individual_success += 1
                            placed_count += 1
                    
                    print(f"Placed {individual_success}/{len(super_module['modules'])} modules individually")
                    pbar.update(1)
        
        # Calculate final score
        self._calculate_score()
        
        end_time = time.time()
        print(f"Placement completed in {end_time - start_time:.2f} seconds")
        print(f"Successfully placed {placed_count}/{len(self.modules)} modules")
        print(f"Final placement score: {self.placement_score:.4f}")
        
        return self.placed_modules, self.grid
    
    def _create_super_modules(self):
        """
        Create super modules by combining modules of the same type.
        Uses an approximation algorithm to create near-square shapes.
        """
        super_modules = []
        
        for module_type, modules in self.clusters_by_type.items():
            if not modules:
                continue
                
            # Sample module to get dimensions
            sample = modules[0]
            module_width = sample['width']
            module_height = sample['height']
            
            # Calculate how many modules we need to arrange
            count = len(modules)
            
            # Compute grid dimensions for this super module
            # Try to create a roughly square arrangement
            aspect_ratio = module_height / module_width
            cols = max(1, int(math.sqrt(count / aspect_ratio)))
            rows = math.ceil(count / cols)
            
            # Ensure we have enough cells
            while rows * cols < count:
                cols += 1
            
            # Create super module
            super_module = {
                'id': f"super_{module_type}",
                'name': sample['name'],
                'width': cols * module_width,
                'height': rows * module_height,
                'modules': modules,
                'rows': rows,
                'cols': cols,
                'module_width': module_width,
                'module_height': module_height
            }
            
            super_modules.append(super_module)
        
        return super_modules
    
    def _place_super_module(self, super_module):
        """Place a super module (cluster) on the grid."""
        width = super_module['width']
        height = super_module['height']
        
        # Can't place if it's too big for the datacenter
        if width > self.width or height > self.height:
            return False
        
        # Check a reduced set of positions for speed
        # First try corners and center
        priority_positions = [
            (0, 0),  # Top-left
            (0, self.height - height),  # Bottom-left
            (self.width - width, 0),  # Top-right
            (self.width - width, self.height - height),  # Bottom-right
            (self.width//2 - width//2, self.height//2 - height//2)  # Center
        ]
        
        # Filter valid positions
        priority_positions = [(x, y) for x, y in priority_positions 
                              if 0 <= x <= self.width - width and 
                                 0 <= y <= self.height - height]
        
        # Try priority positions first
        for x, y in priority_positions:
            if self._can_place_at(x, y, width, height):
                return self._commit_super_module_placement(super_module, x, y)
        
        # If priority positions don't work, sample grid with larger steps for speed
        step = max(1, min(width, height) // 3)
        
        # Create a list of positions to sample
        positions = []
        for y in range(0, self.height - height + 1, step):
            for x in range(0, self.width - width + 1, step):
                positions.append((x, y))
        
        # Shuffle positions for randomness with fixed seed for reproducibility
        random.seed(42)
        random.shuffle(positions)
        
        # Only check a reasonable number of positions for speed
        max_positions = min(200, len(positions))
        
        for x, y in positions[:max_positions]:
            if self._can_place_at(x, y, width, height):
                return self._commit_super_module_placement(super_module, x, y)
        
        # More positions didn't work, try stricter limits for last attempt
        if max_positions < len(positions):
            for x, y in positions[max_positions:]:
                if self._can_place_at(x, y, width, height):
                    return self._commit_super_module_placement(super_module, x, y)
        
        return False
    
    def _can_place_at(self, x, y, width, height):
        """Check if we can place a module at the given position."""
        # Check bounds
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            return False
        
        # Check for collision using efficient array operations
        region = self.grid[y:y+height, x:x+width]
        return np.all(region == 0)
    
    def _commit_super_module_placement(self, super_module, x, y):
        """Place the super module and its constituent modules."""
        modules = super_module['modules']
        rows = super_module['rows']
        cols = super_module['cols']
        module_width = super_module['module_width']
        module_height = super_module['module_height']
        
        # Mark the grid as occupied - use the module_id as the grid value
        module_id = int(modules[0]['id'])
        
        # Place individual modules within the super module grid
        placed_count = 0
        for i, module in enumerate(modules):
            if placed_count >= rows * cols:
                break
                
            # Calculate position within the super module
            row = i // cols
            col = i % cols
            
            module_x = x + col * module_width
            module_y = y + row * module_height
            
            # Update module position
            module['x'] = module_x
            module['y'] = module_y
            
            # Mark grid as occupied
            self.grid[module_y:module_y+module_height, module_x:module_x+module_width] = module_id
            
            # Add to placed modules list
            self.placed_modules.append(module)
            placed_count += 1
        
        return True
    
    def _place_individual_module(self, module):
        """Place a single module as fallback if super module placement fails."""
        width = module['width']
        height = module['height']
        
        # Sample positions randomly for speed
        positions = []
        step = max(1, min(width, height))
        
        for y in range(0, self.height - height + 1, step):
            for x in range(0, self.width - width + 1, step):
                positions.append((x, y))
        
        # Shuffle positions
        random.shuffle(positions)
        
        # Try to place at available positions
        for x, y in positions:
            if self._can_place_at(x, y, width, height):
                # Update module position
                module['x'] = x
                module['y'] = y
                
                # Mark grid as occupied
                self.grid[y:y+height, x:x+width] = int(module['id'])
                
                # Add to placed modules list
                self.placed_modules.append(module)
                return True
        
        return False
    
    def _calculate_score(self):
        """Calculate a score for the placement."""
        if not self.placed_modules:
            self.placement_score = 0
            return
        
        # Calculate bounding box
        min_x = min(m['x'] for m in self.placed_modules)
        min_y = min(m['y'] for m in self.placed_modules)
        max_x = max(m['x'] + m['width'] for m in self.placed_modules)
        max_y = max(m['y'] + m['height'] for m in self.placed_modules)
        
        # Calculate metrics
        bounding_area = (max_x - min_x) * (max_y - min_y)
        used_area = sum(m['width'] * m['height'] for m in self.placed_modules)
        
        # Compactness - higher is better
        compactness = used_area / bounding_area if bounding_area > 0 else 0
        
        # Clustering metric - higher is better
        clusters = defaultdict(list)
        for module in self.placed_modules:
            clusters[module['id']].append(module)
        
        clustering_score = 0
        module_count = len(self.placed_modules)
        
        for module_id, cluster_modules in clusters.items():
            if len(cluster_modules) <= 1:
                continue
                
            # Calculate centroid
            centroid_x = sum(m['x'] + m['width']/2 for m in cluster_modules) / len(cluster_modules)
            centroid_y = sum(m['y'] + m['height']/2 for m in cluster_modules) / len(cluster_modules)
            
            # Average Manhattan distance to centroid
            avg_distance = sum(abs(m['x'] + m['width']/2 - centroid_x) + 
                              abs(m['y'] + m['height']/2 - centroid_y) 
                              for m in cluster_modules) / len(cluster_modules)
            
            # Normalize by grid dimensions
            max_distance = self.width + self.height
            normalized_distance = avg_distance / max_distance
            
            # Higher score for closer clustering
            type_score = 1 - normalized_distance
            
            # Weight by cluster size
            clustering_score += type_score * len(cluster_modules) / module_count
        
        # Combined score
        self.placement_score = 0.4 * compactness + 0.6 * clustering_score
        print(f"Compactness: {compactness:.4f}, Clustering: {clustering_score:.4f}")

    def visualize(self, save_path=None, show_grid=True):
        """
        Visualize the module placement with a focus on performance.
        """
        if not self.placed_modules:
            print("No modules placed yet. Run the placement algorithm first.")
            return
            
        print("Generating visualization...")
        plt.figure(figsize=(12, 10))
        ax = plt.gca()
        
        # Generate optimized colormapping for module types with a fixed color palette
        module_types = sorted(set(m['id'] for m in self.placed_modules))
        cmap = plt.cm.tab20
        colors = cmap(np.linspace(0, 1, min(20, len(module_types))))
        id_to_color = {id: colors[i % len(colors)] for i, id in enumerate(module_types)}
        
        # Progress tracking for visualization
        with tqdm(total=3, desc="Rendering visualization") as viz_pbar:
            # Step 1: Draw modules by type
            # Group modules by type for efficiency
            modules_by_type = defaultdict(list)
            for module in self.placed_modules:
                modules_by_type[module['id']].append(module)
            
            # First pass: outline clusters
            for module_id, modules in modules_by_type.items():
                if len(modules) <= 1:
                    continue
                    
                # Calculate bounding box for this type
                min_x = min(m['x'] for m in modules)
                min_y = min(m['y'] for m in modules)
                max_x = max(m['x'] + m['width'] for m in modules)
                max_y = max(m['y'] + m['height'] for m in modules)
                
                # Draw cluster outline if modules are clustered
                cluster_width = max_x - min_x
                cluster_height = max_y - min_y
                total_module_area = sum(m['width'] * m['height'] for m in modules)
                cluster_area = cluster_width * cluster_height
                
                # Only draw outline if reasonable density (not scattered)
                if total_module_area / cluster_area > 0.6:
                    rect = Rectangle(
                        (min_x, min_y),
                        cluster_width,
                        cluster_height,
                        fill=False,
                        edgecolor=id_to_color[module_id],
                        linestyle='--',
                        linewidth=2,
                        alpha=0.8
                    )
                    ax.add_patch(rect)
                    
                    # Add cluster label
                    plt.text(
                        min_x + cluster_width/2,
                        min_y - 0.5,  # Just above the cluster
                        f"{modules[0]['name']} Cluster ({len(modules)})",
                        ha='center',
                        va='center',
                        fontsize=8,
                        color=id_to_color[module_id],
                        bbox=dict(facecolor='white', alpha=0.7, boxstyle='round,pad=0.3')
                    )
            
            # Second pass: draw individual modules
            for module_id, modules in modules_by_type.items():
                color = id_to_color[module_id]
                
                # Batch draw modules of the same type (more efficient)
                for module in modules:
                    rect = Rectangle(
                        (module['x'], module['y']),
                        module['width'], module['height'],
                        facecolor=color,
                        edgecolor='black',
                        alpha=0.7
                    )
                    ax.add_patch(rect)
                    
                    # Add module label if large enough
                    if module['width'] >= 3 and module['height'] >= 3:
                        plt.text(
                            module['x'] + module['width']/2,
                            module['y'] + module['height']/2,
                            f"{module['name']}\n(ID:{module['id']})",
                            ha='center', va='center',
                            fontsize=8
                        )
            
            viz_pbar.update(1)
            
            # Step 2: Draw locked regions
            locked_mask = self.grid == -1
            if np.any(locked_mask):
                y_indices, x_indices = np.where(locked_mask)
                for y, x in zip(y_indices, x_indices):
                    rect = Rectangle(
                        (x, y), 1, 1,
                        facecolor='red',
                        edgecolor='none',
                        alpha=0.3
                    )
                    ax.add_patch(rect)
            
            viz_pbar.update(1)
            
            # Step 3: Draw resource connections (limited for performance)
            # Get modules with resource dependencies
            dependent_modules = {}
            for i, module in enumerate(self.placed_modules):
                for resource in INTERNAL_RESOURCES:
                    if resource in module.get('inputs', {}) or resource in module.get('outputs', {}):
                        dependent_modules[i] = module
                        break
            
            # Draw connections only between dependent modules (limited for performance)
            max_connections = 200  # Limit for performance
            connection_count = 0
            
            for resource in INTERNAL_RESOURCES:
                # Find sources and sinks
                sources = [(i, m, m['outputs'].get(resource, 0)) 
                          for i, m in dependent_modules.items() 
                          if resource in m.get('outputs', {})]
                
                sinks = [(i, m, m['inputs'].get(resource, 0)) 
                        for i, m in dependent_modules.items() 
                        if resource in m.get('inputs', {})]
                
                # Filter for non-zero flow
                sources = [(i, m, flow) for i, m, flow in sources if flow > 0]
                sinks = [(i, m, flow) for i, m, flow in sinks if flow > 0]
                
                # Map connections using a greedy approach
                for source_idx, source, source_flow in sources:
                    remaining_flow = source_flow
                    
                    for sink_idx, sink, sink_flow in sinks:
                        if source_idx == sink_idx or remaining_flow <= 0 or connection_count >= max_connections:
                            continue
                            
                        flow = min(remaining_flow, sink_flow)
                        
                        # Calculate centers
                        source_x = source['x'] + source['width'] / 2
                        source_y = source['y'] + source['height'] / 2
                        sink_x = sink['x'] + sink['width'] / 2
                        sink_y = sink['y'] + sink['height'] / 2
                        
                        # Get line color based on resource type
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
                        
                        # Draw the connection line
                        plt.plot(
                            [source_x, sink_x],
                            [source_y, sink_y],
                            '-',
                            color=color,
                            linewidth=0.5 + min(3, flow / 50),
                            alpha=0.5
                        )
                        
                        connection_count += 1
                        remaining_flow -= flow
                        
                        if connection_count >= max_connections:
                            break
            
            viz_pbar.update(1)
        
        # Set plot limits and grid
        plt.xlim(-1, self.width + 1)
        plt.ylim(-1, self.height + 1)
        
        if show_grid:
            plt.grid(True, linestyle='--', alpha=0.3)
        
        # Add legend
        legend_elements = [
            Line2D([0], [0], color='red', lw=2, label='Power'),
            Line2D([0], [0], color='blue', lw=2, label='Fresh Water'),
            Line2D([0], [0], color='cyan', lw=2, label='Distilled Water'),
            Line2D([0], [0], color='lightblue', lw=2, label='Chilled Water'),
            Line2D([0], [0], color='green', lw=2, label='Network'),
            Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.3, label='Locked Region'),
            Rectangle((0, 0), 1, 1, fill=False, edgecolor='black', linestyle='--', label='Module Cluster')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title('Datacenter Module Placement (Clustered Approach)')
        plt.xlabel('X coordinate')
        plt.ylabel('Y coordinate')
        
        if save_path:
            print(f"Saving visualization to {save_path}...")
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved successfully")
        
        plt.show()

# Example usage:
def run_fast_clustered_placement(module_data, selected_modules, width, height, locked_regions=None, save_path="fast_clustered_placement.png"):
    """
    Run the high-performance module placement algorithm.
    
    Args:
        module_data: Dictionary with module specifications
        selected_modules: Dictionary with module_id -> count mapping
        width: Width of the datacenter
        height: Height of the datacenter
        locked_regions: Optional boolean mask of locked regions
        save_path: Path to save the visualization image (default: "fast_clustered_placement.png")
    
    Returns:
        Tuple of (placed_modules, grid)
    """
    placement = FastClusteredPlacement(
        module_data, selected_modules, width, height, locked_regions
    )
    
    placed_modules, grid = placement.run()
    
    # Visualize the result with the custom save path
    placement.visualize(save_path=save_path)
    
    return placed_modules, grid

if __name__ == "__main__":
    from resource_optimization_no_placement import load_data, run_datacenter_resource_optimization
    from resource_optimization_no_placement import MODULES_CSV_PATH, SPEC_CSV_PATH
    import numpy as np
    
    def run_batch_processing():
        """Process all specifications automatically using the fast clustered approach."""
        print("=== Starting Fast Clustered Placement for All Specifications ===\n")
        
        # Load data from optimizer
        module_data, all_specs_df, module_ids, unique_spec_names = load_data(
            MODULES_CSV_PATH, SPEC_CSV_PATH
        )
        
        # Run resource optimization to get module selections
        optimization_results = run_datacenter_resource_optimization(
            MODULES_CSV_PATH, SPEC_CSV_PATH
        )
        
        # Process each specification
        for result in optimization_results:
            spec_name = result['spec_name']
            status = result['status']
            
            if status not in ["Optimal", "Feasible"]:
                print(f"Skipping placement for {spec_name} - Status: {status}")
                continue
            
            print(f"\n====== Running Fast Clustered Placement for: {spec_name} ======\n")
            
            try:
                # Extract total width and height from spec
                width_rows = all_specs_df[
                    (all_specs_df['Name'] == spec_name) &
                    (all_specs_df['Unit'] == 'space_x') & 
                    (all_specs_df['Below_Amount'] == 1)
                ]['Amount']
                
                height_rows = all_specs_df[
                    (all_specs_df['Name'] == spec_name) & 
                    (all_specs_df['Unit'] == 'space_y') & 
                    (all_specs_df['Below_Amount'] == 1)
                ]['Amount']
                
                total_width = int(width_rows.iloc[0])
                total_height = int(height_rows.iloc[0])
                
                # Run the placement without locked regions
                run_fast_clustered_placement(
                    module_data,
                    result['selected_modules_counts'],
                    total_width,
                    total_height,
                    save_path=f"{spec_name}_fast_clustered.png"
                )
                
            except Exception as e:
                print(f"Error during placement for {spec_name}: {e}")
                import traceback
                traceback.print_exc()
    
    def run_interactive_mode():
        """Run placement with interactive specification selection and region locking."""
        print("=== Starting Interactive Fast Clustered Placement ===\n")
        
        # Load data
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
            width_rows = all_specs_df[
                (all_specs_df['Name'] == spec_name) &
                (all_specs_df['Unit'] == 'space_x') & 
                (all_specs_df['Below_Amount'] == 1)
            ]['Amount']
            
            height_rows = all_specs_df[
                (all_specs_df['Name'] == spec_name) & 
                (all_specs_df['Unit'] == 'space_y') & 
                (all_specs_df['Below_Amount'] == 1)
            ]['Amount']
            
            total_width = int(width_rows.iloc[0])
            total_height = int(height_rows.iloc[0])
            
            # Handle locked regions
            from module_placement_interactive import RegionLocker
            
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
            
            # Run the placement
            run_fast_clustered_placement(
                module_data,
                selected_result['selected_modules_counts'],
                total_width,
                total_height,
                locked_regions=(region_locker.grid == -1),
                save_path=f"{spec_name}_fast_clustered_interactive.png"
            )
            
        except Exception as e:
            print(f"Error during placement for {spec_name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Main menu
    print("Fast Clustered Module Placement Options:")
    print("1. Batch process all specifications")
    print("2. Interactive mode (select specification and lock regions)")
    print("Enter your choice:")
    
    choice = input().strip()
    
    if choice == '1':
        run_batch_processing()
    elif choice == '2':
        run_interactive_mode()
    else:
        print("Invalid choice. Exiting.")