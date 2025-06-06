from models import Module
import time
import numpy as np
import math
from collections import defaultdict
import random
from solver_utils_list import standardize_unit_name

# --- Constants ---
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']


def _solve_module_placement(modules: list[Module], specs: list[dict], selected_modules_counts: dict, unavailable_area: np.ndarray | None = None) -> dict:
    """
    Places modules in a datacenter grid using a clustered approach.

    Args:
        modules (list[Module]): List of available Module objects
        specs (list[dict]): List of specifications for the datacenter
        selected_modules_counts (dict): Dictionary with module_id -> count mapping
        unavailable_area (np.ndarray | None): Optional boolean NumPy array indicating locked cells (True means unavailable).

    Returns:
        dict: A dictionary containing datacenter configuration including placed modules
    """
    print(f"--- Starting Module Placement ---")
    start_time = time.time()

    # Extract datacenter dimensions from specs
    datacenter_width = None
    datacenter_height = None
    datacenter_id = 1  # Default ID if not specified
    datacenter_name = "Datacenter Configuration"  # Default name

    # Extract dimensions from specs
    for rule in specs:
        unit = standardize_unit_name(rule.get('Unit'))
        if unit == 'space_x' and rule.get('Below_Amount') == 1:
            try:
                datacenter_width = int(rule.get('Amount'))
            except (ValueError, TypeError):
                pass
        elif unit == 'space_y' and rule.get('Below_Amount') == 1:
            try:
                datacenter_height = int(rule.get('Amount'))
            except (ValueError, TypeError):
                pass

    if not datacenter_width or not datacenter_height:
        print("Error: Could not determine datacenter dimensions from specs")
        return {"error": "Invalid datacenter dimensions"}

    print(f"Datacenter dimensions: {datacenter_width} x {datacenter_height}")

    # Process module data
    module_data = {}
    for mod in modules:
        mod_id = mod["id"]
        inputs = {}
        outputs = {}
        mod_width = 0
        mod_height = 0

        # Process IO fields to extract needed information
        for field in mod["io_fields"]:
            unit = standardize_unit_name(field["unit"])
            amount = field["amount"]

            if unit == 'space_x' and field["is_input"]:
                try:
                    mod_width = int(amount) if amount else 0
                except (ValueError, TypeError):
                    mod_width = 0
            elif unit == 'space_y' and field["is_input"]:
                try:
                    mod_height = int(amount) if amount else 0
                except (ValueError, TypeError):
                    mod_height = 0

            if field["is_input"]:
                inputs[unit] = amount
            if field["is_output"]:
                outputs[unit] = amount

        module_data[mod_id] = {
            "name": mod["name"],
            "inputs": inputs,
            "outputs": outputs,
            "width": mod_width,
            "height": mod_height
        }

    # Initialize and run the placement algorithm
    placement = FastClusteredPlacement(
        module_data, selected_modules_counts, datacenter_width, datacenter_height,
        locked_regions=unavailable_area # Pass the unavailable area
    )

    placed_modules, grid = placement.run()

    # Calculate total resources (only for the modules placed by this function)
    # The wrapper function will handle combining details if needed
    details = {}

    # Initialize with any initial resources from specs
    for spec in specs:
        unit = standardize_unit_name(spec.get('Unit'))
        if unit not in DIMENSION_RESOURCES:  # Skip dimensions
            # Initialize resource values based on constraints
            if spec.get('Above_Amount') == 1 and spec.get('Amount') is not None:
                details[unit] = spec.get('Amount')

    # Add module contributions to resources
    for module in placed_modules:
        # Add inputs (consumed resources)
        for unit, amount in module.get('inputs', {}).items():
            if unit not in DIMENSION_RESOURCES:  # Skip dimensions
                if unit not in details:
                    details[unit] = 0
                # For inputs like price, we subtract from the total
                if unit in INPUT_RESOURCES:
                    details[unit] -= float(amount) if amount is not None else 0

        # Add outputs (produced resources)
        for unit, amount in module.get('outputs', {}).items():
            if unit not in details:
                details[unit] = 0
            details[unit] += float(amount) if amount is not None else 0

    # Make sure all resource values are positive for inputs
    for unit in INPUT_RESOURCES:
        if unit in details:
            details[unit] = abs(details[unit])

    # Format modules for return
    formatted_modules = []
    for module in placed_modules:
        # Find the original Module object to get io_fields if needed, or keep empty
        original_module = next((m for m in modules if m["id"] == module['id']), None)
        io_fields_data = original_module["io_fields"] if original_module else [] # Or format io_fields if required

        formatted_modules.append({
            "id": module['id'],
            "name": module['name'],
            "io_fields": [], # Keep empty as per original requirement, adjust if needed
            "gridColumn": module['x'],
            "gridRow": module['y'],
            "width": module['width'],
            "height": module['height']
        })

    # Build the final response object
    result = {
        "id": datacenter_id,
        "name": datacenter_name,
        "specs": specs,
        "details": details, # Details only for modules placed here
        "modules": formatted_modules # Modules placed by this function
    }

    print(f"Placement completed in {time.time() - start_time:.2f} seconds")
    print(f"Successfully placed {len(placed_modules)} modules (excluding fixed ones)")
    print(f"Placement score: {placement.placement_score:.4f}")

    return result


class FastClusteredPlacement:
    """Optimized solution for clustered module placement with focus on performance."""

    def __init__(self, module_data, selected_modules, datacenter_width, datacenter_height, locked_regions: np.ndarray | None = None):
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
        # 0: empty, -1: locked/unavailable, >0: module_id
        self.grid = np.zeros((datacenter_height, datacenter_width), dtype=int)
        if locked_regions is not None:
            if locked_regions.shape == (datacenter_height, datacenter_width):
                self.grid[locked_regions] = -1  # Mark locked regions
            else:
                print(f"Warning: locked_regions shape mismatch. Expected ({datacenter_height}, {datacenter_width}), got {locked_regions.shape}. Ignoring.")


        # Process module data
        self.modules = []
        self.clusters_by_type = defaultdict(list)

        # Group modules by type and calculate centroids for faster access
        
        print("SSSSSSSSSSS", selected_modules)
        for module_id, count in selected_modules.items():
            module_id = int(module_id)
            if module_id not in module_data:
                print(f"Warning: Module ID {module_id} not found in module_data. Skipping.")
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
        for super_module in super_modules:
            if self._place_super_module(super_module):
                placed_count += len(super_module['modules'])
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
            aspect_ratio = module_height / module_width if module_width > 0 else 1
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
        try:
            module_id = int(modules[0]['id'])
        except (ValueError, TypeError):
            module_id = 1  # Default if ID can't be converted to int
        
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
                try:
                    module_id = int(module['id'])
                except (ValueError, TypeError):
                    module_id = 1  # Default if ID can't be converted to int
                
                self.grid[y:y+height, x:x+width] = module_id
                
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
    

    def _can_place_at(self, x, y, width, height):
        """Check if we can place a module at the given position."""
        # Check bounds
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            return False

        # Check for collision using efficient array operations
        # Any non-zero value indicates occupied or locked
        region = self.grid[y:y+height, x:x+width]
        return np.all(region == 0)


def validate_placement_output(result):
    """
    Validates that the placement output matches the expected format.
    Returns a tuple of (is_valid, error_message).
    """
    # Check top-level structure
    required_keys = ["id", "name", "specs", "details", "modules"]
    missing_keys = [key for key in required_keys if key not in result]
    if missing_keys:
        return False, f"Missing required top-level keys: {missing_keys}"
    
    # Check module structure
    if not isinstance(result["modules"], list):
        return False, "Modules should be a list"
    
    if not result["modules"]:
        return True, "Warning: No modules were placed"
    
    # Check first module structure
    required_module_keys = ["id", "name", "io_fields", "gridColumn", "gridRow", "width", "height"]
    first_module = result["modules"][0]
    missing_module_keys = [key for key in required_module_keys if key not in first_module]
    if missing_module_keys:
        return False, f"Module is missing required keys: {missing_module_keys}"
    
    # Check details structure
    if not isinstance(result["details"], dict):
        return False, "Details should be a dictionary"
    
    # All checks passed
    return True, "Output format is valid"


def solve_modules_placement_with_fixed(modules: list[Module], specs: list[dict], selected_modules_counts: dict, modules_with_position: list[dict] = []):
    """
    Places modules, respecting pre-defined positions for some modules.

    Args:
        modules (list[Module]): List of *all* available Module objects.
        specs (list[dict]): List of specifications for the datacenter.
        selected_modules_counts (dict): Dictionary with module_id -> total count mapping (including fixed ones).
        modules_with_position (list[dict]): List of modules with fixed positions.
            Each dict should have: 'id', 'name', 'gridColumn', 'gridRow', 'width', 'height'.
            'io_fields' can be included if needed for detail calculation.

    Returns:
        dict: A dictionary containing the final datacenter configuration,
              including both fixed and newly placed modules, in the standard format.
    """
    if not modules_with_position:
        print("--- No fixed modules provided, running standard placement ---")
        return _solve_module_placement(modules, specs, selected_modules_counts, unavailable_area=None)

    print("--- Starting Placement with Fixed Modules ---")
    start_time_fixed = time.time()

    # 1. Extract Datacenter Dimensions
    datacenter_width = None
    datacenter_height = None
    for rule in specs:
        unit = standardize_unit_name(rule.get('Unit'))
        if unit == 'space_x' and rule.get('Below_Amount') == 1:
            try: datacenter_width = int(rule.get('Amount'))
            except (ValueError, TypeError): pass
        elif unit == 'space_y' and rule.get('Below_Amount') == 1:
            try: datacenter_height = int(rule.get('Amount'))
            except (ValueError, TypeError): pass

    if not datacenter_width or not datacenter_height:
        print("Error: Could not determine datacenter dimensions from specs")
        return {"error": "Invalid datacenter dimensions for fixed placement"}

    # 2. Create Unavailable Area Grid
    unavailable_grid = np.zeros((datacenter_height, datacenter_width), dtype=bool)
    formatted_fixed_modules = []
    fixed_module_ids = defaultdict(int)

    # Store original io_fields for detail calculation later
    module_io_map = {m["id"]: m["io_fields"] for m in modules}

    for fixed_mod in modules_with_position:
        try:
            mod_id = fixed_mod['id']
            x = int(fixed_mod['gridColumn'])
            y = int(fixed_mod['gridRow'])
            w = int(fixed_mod['width'])
            h = int(fixed_mod['height'])
            name = fixed_mod['name']
        except (KeyError, ValueError, TypeError) as e:
            print(f"Error: Invalid data for fixed module: {fixed_mod}. Skipping. Error: {e}")
            continue

        # Basic validation
        if x < 0 or y < 0 or x + w > datacenter_width or y + h > datacenter_height:
            print(f"Error: Fixed module '{name}' (ID: {mod_id}) at ({x},{y}) with size ({w}x{h}) is out of bounds ({datacenter_width}x{datacenter_height}). Skipping.")
            continue

        # Check for overlaps with already marked areas
        if np.any(unavailable_grid[y:y+h, x:x+w]):
            print(f"Error: Fixed module '{name}' (ID: {mod_id}) at ({x},{y}) overlaps with another fixed module or locked area. Skipping.")
            continue

        # Mark area as unavailable
        unavailable_grid[y:y+h, x:x+w] = True
        fixed_module_ids[mod_id] += 1

        # Format for final output
        formatted_fixed_modules.append({
            "id": mod_id,
            "name": name,
            "io_fields": [], # Keep empty as per original requirement
            "gridColumn": x,
            "gridRow": y,
            "width": w,
            "height": h
        })

    print(f"Reserved space for {len(formatted_fixed_modules)} fixed modules.")

    # 3. Adjust Selected Module Counts
    remaining_modules_counts = selected_modules_counts.copy()
    for mod_id, count in fixed_module_ids.items():
        if mod_id in remaining_modules_counts:
            remaining_modules_counts[mod_id] -= count
            if remaining_modules_counts[mod_id] <= 0:
                del remaining_modules_counts[mod_id]
        else:
            print(f"Warning: Fixed module ID {mod_id} was not found in selected_modules_counts.")

    # Filter out modules with zero count
    remaining_modules_counts = {k: v for k, v in remaining_modules_counts.items() if v > 0}
    print(f"Modules remaining to be placed: {remaining_modules_counts}")

    # 4. Call Core Placement Function
    placement_result = _solve_module_placement(
        modules,
        specs,
        remaining_modules_counts,
        unavailable_area=unavailable_grid
    )

    if "error" in placement_result:
        # If core placement failed, return the error but maybe still include fixed modules?
        # For now, just return the error. Consider adding fixed modules even on error if needed.
        return placement_result

    # 5. Combine Results
    # Add the formatted fixed modules to the list of placed modules
    final_modules = formatted_fixed_modules + placement_result.get("modules", [])
    placement_result["modules"] = final_modules

    # 6. Recalculate Details (including fixed modules)
    print("Recalculating details including fixed modules...")
    final_details = {}
    # Initialize from specs
    for spec in specs:
        unit = standardize_unit_name(spec.get('Unit'))
        if unit not in DIMENSION_RESOURCES:
            if spec.get('Above_Amount') == 1 and spec.get('Amount') is not None:
                final_details[unit] = spec.get('Amount')

    # Add contributions from ALL modules (fixed + placed)
    all_placed_modules_data = []
    # Get data for fixed modules
    for fixed_mod in modules_with_position:
         # Fetch IO fields using the map created earlier
        io_fields = module_io_map.get(fixed_mod['id'], [])
        inputs = {}
        outputs = {}
        for field in io_fields:
            unit = standardize_unit_name(field["unit"])
            if field["is_input"]: inputs[unit] = field["amount"]
            if field["is_output"]: outputs[unit] = field["amount"]
        all_placed_modules_data.append({'id': fixed_mod['id'], 'inputs': inputs, 'outputs': outputs})

    # Get data for dynamically placed modules (already processed in _solve_module_placement)
    # We need the internal representation used there, or re-process io_fields
    module_data_map = {m["id"]: m for m in modules}
    for placed_mod in placement_result.get("modules", [])[len(formatted_fixed_modules):]: # Only iterate dynamically placed ones
        original_module = module_data_map.get(placed_mod['id'])
        if original_module:
            inputs = {}
            outputs = {}
            for field in original_module["io_fields"]:
                unit = standardize_unit_name(field["unit"])
                if field["is_input"]: inputs[unit] = field["amount"]
                if field["is_output"]: outputs[unit] = field["amount"]
            all_placed_modules_data.append({'id': placed_mod['id'], 'inputs': inputs, 'outputs': outputs})


    # Calculate final details
    for module_info in all_placed_modules_data:
        # Inputs
        for unit, amount in module_info.get('inputs', {}).items():
            if unit not in DIMENSION_RESOURCES:
                if unit not in final_details: final_details[unit] = 0
                if unit in INPUT_RESOURCES:
                    final_details[unit] -= float(amount) if amount is not None else 0
        # Outputs
        for unit, amount in module_info.get('outputs', {}).items():
             if unit not in DIMENSION_RESOURCES:
                if unit not in final_details: final_details[unit] = 0
                final_details[unit] += float(amount) if amount is not None else 0

    # Ensure positive inputs
    for unit in INPUT_RESOURCES:
        if unit in final_details:
            final_details[unit] = abs(final_details[unit])

    placement_result["details"] = final_details

    print(f"Fixed placement process completed in {time.time() - start_time_fixed:.2f} seconds")
    print(f"Total modules in final layout: {len(final_modules)}")

    return placement_result











# import json
# from solver_utils_placement import _solve_module_placement, validate_placement_output
# from models import Module, IOField

# def test_placement_output():
#     # Create test modules
#     test_modules = [
#         Module(
#             id=1,
#             name="Test Module",
#             io_fields=[
#                 IOField(is_input=True, is_output=False, unit="space_x", amount=2),
#                 IOField(is_input=True, is_output=False, unit="space_y", amount=2),
#                 IOField(is_input=False, is_output=True, unit="processing", amount=100)
#             ]
#         ),
#         Module(
#             id=2,
#             name="Network Module",
#             io_fields=[
#                 IOField(is_input=True, is_output=False, unit="space_x", amount=1),
#                 IOField(is_input=True, is_output=False, unit="space_y", amount=1),
#                 IOField(is_input=False, is_output=True, unit="external_network", amount=50)
#             ]
#         )
#     ]
    
#     # Create specs similar to your example
#     test_specs = [
#         {"Unit": "space_x", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 100},
#         {"Unit": "space_y", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 50},
#         {"Unit": "price", "Below_Amount": 1, "Above_Amount": 0, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 1000000},
#         {"Unit": "data_storage", "Below_Amount": 0, "Above_Amount": 1, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 1000},
#         {"Unit": "processing", "Below_Amount": 0, "Above_Amount": 1, "Minimize": 0, "Maximize": 0, "Unconstrained": 0, "Amount": 1000},
#         {"Unit": "external_network", "Below_Amount": 0, "Above_Amount": 0, "Minimize": 0, "Maximize": 1, "Unconstrained": 0, "Amount": -1}
#     ]
    
#     # Weights
#     test_weights = {"processing": 1.0, "external_network": 1.5, "data_storage": 0.8}
    
#     # Selected modules - add more to better match your example
#     test_selected = {1: 5, 2: 3}  # 5 instances of module ID 1, 3 instances of module ID 2
    
#     # Call the placement function
#     result = _solve_module_placement(test_modules, test_specs, test_weights, test_selected)
    
#     # Validate the output
#     is_valid, message = validate_placement_output(result)
#     print(f"Validation result: {is_valid}")
#     print(f"Message: {message}")
    
#     # Print the complete output as formatted JSON
#     print("\n=== COMPLETE OUTPUT ===")
#     print(json.dumps(result, indent=2))
    
#     return result

# # Run the test
# if __name__ == "__main__":
#     output = test_placement_output()


