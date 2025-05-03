from models import Module, IOField # Changed import source
import json
import pulp
import time
import math # For checking NaN
import numpy as np # Added for placement grid

# --- Constants ---
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
DIMENSION_RESOURCES = ['space_x', 'space_y']

SOLVER_TIME_LIMIT_SECONDS = 60.0

# --- Helper Function ---
def standardize_unit_name(name):
    """Converts unit name to standard format: lowercase_with_underscores."""
    if name is None or (isinstance(name, float) and math.isnan(name)):
        return None
    return str(name).strip().lower().replace(' ', '_')

def solve_module_list(modules: list[Module], specs: list[dict], weights: dict) -> tuple[dict, dict]:
    """
    Solves the resource optimization problem to select the best module counts.

    Args:
        modules (list[Module]): List of available Module objects.
        specs (list[dict]): A list of dictionaries defining the constraints and objectives.
                             Each dict should have keys like 'Unit', 'Below_Amount', 'Above_Amount',
                             'Minimize', 'Maximize', 'Amount', 'Unconstrained'.
        weights (dict): Dictionary specifying the relative importance for objective terms.
                        Example: {'data_storage': 2.0, 'total_area': 1.0}

    Returns:
        tuple[dict, dict]: A tuple containing:
            - selected_modules_counts (dict): {module_id: count}
            - net_resources (dict): {resource_unit: net_value} for all involved resources.
            Returns ({}, {}) if optimization fails or is infeasible.
    """
    start_time = time.time()
    print(f"--- Starting Module List Optimization ---")
    print(f"Received {len(modules)} module types, {len(specs)} spec rules.")

    # --- 1. Process Modules ---
    module_data = {}
    module_ids = []
    if not modules:
        print("Error: No modules provided.")
        return {}, {}

    for mod in modules:
        mod_id = mod.id # Correct: Module class has 'id'
        module_ids.append(mod_id)
        inputs = {}
        outputs = {}
        mod_width = 0
        mod_height = 0

        # Process io_fields to populate inputs, outputs, width, height
        for field in mod.io_fields: # Iterate through io_fields list
            unit = standardize_unit_name(field.unit)
            amount = field.amount

            if unit == 'space_x' and field.is_input:
                try:
                    mod_width = int(amount) if amount else 0
                except (ValueError, TypeError):
                    print(f"Warning: Module ID {mod_id} has invalid width value ('{amount}'). Width set to 0.")
                    mod_width = 0
                continue # Don't add space_x to standard inputs dict
            elif unit == 'space_y' and field.is_input:
                try:
                    mod_height = int(amount) if amount else 0
                except (ValueError, TypeError):
                    print(f"Warning: Module ID {mod_id} has invalid height value ('{amount}'). Height set to 0.")
                    mod_height = 0
                continue # Don't add space_y to standard inputs dict

            if field.is_input:
                inputs[unit] = amount
            if field.is_output:
                outputs[unit] = amount

        # Calculate Area
        mod_area = 0
        if mod_width > 0 and mod_height > 0:
            mod_area = mod_width * mod_height
        elif mod_width <= 0 or mod_height <= 0:
             # Add warning if area is zero due to missing/invalid dimensions
             if any(f.unit.lower() == 'space_x' for f in mod.io_fields if f.is_input) or \
                any(f.unit.lower() == 'space_y' for f in mod.io_fields if f.is_input):
                 print(f"Warning: Module ID {mod_id} has zero area due to non-positive dimensions (W={mod_width}, H={mod_height}).")


        module_data[mod_id] = {
            "name": mod.name, # Correct: Module class has 'name'
            "inputs": inputs, # Now correctly populated
            "outputs": outputs, # Now correctly populated
            "width": mod_width,
            "height": mod_height,
            "area": mod_area
        }
    module_ids = sorted(list(set(module_ids))) # Ensure unique and sorted IDs

    # --- 2. Process Specs ---
    # Standardize unit names in specs and filter invalid rules
    valid_specs = []
    total_area_limit = 0
    minimize_area = False
    spec_total_width = None
    spec_total_height = None

    for rule in specs:
        unit = standardize_unit_name(rule.get('Unit'))
        if not unit:
            continue # Skip rules without a unit

        rule['Unit'] = unit # Update rule with standardized name
        # Convert flags/amounts to numeric, handle potential errors/missing keys
        try:
            rule['Below_Amount'] = int(rule.get('Below_Amount', 0) or 0)
            rule['Above_Amount'] = int(rule.get('Above_Amount', 0) or 0)
            rule['Minimize'] = int(rule.get('Minimize', 0) or 0)
            rule['Maximize'] = int(rule.get('Maximize', 0) or 0)
            rule['Unconstrained'] = int(rule.get('Unconstrained', 0) or 0)
            # Amount can be float/int, handle None/NaN for limits
            amount_val = rule.get('Amount')
            rule['Amount'] = float(amount_val) if amount_val is not None else None
        except (ValueError, TypeError):
             print(f"Warning: Invalid non-numeric flag/amount for unit '{unit}'. Skipping rule: {rule}")
             continue

        # Check for area minimization objective
        if unit in DIMENSION_RESOURCES and rule['Minimize'] == 1:
            minimize_area = True

        # Check for area limit constraint (Below_Amount on space_x/y)
        if unit == 'space_x' and rule['Below_Amount'] == 1 and rule['Amount'] is not None:
            spec_total_width = rule['Amount']
        if unit == 'space_y' and rule['Below_Amount'] == 1 and rule['Amount'] is not None:
            spec_total_height = rule['Amount']

        valid_specs.append(rule)

    # Calculate total area limit if both dimensions are constrained
    if not minimize_area and spec_total_width is not None and spec_total_height is not None:
        try:
            w = int(spec_total_width)
            h = int(spec_total_height)
            if w > 0 and h > 0:
                total_area_limit = w * h
                print(f"Area Constraint Detected: Total Area Limit = {total_area_limit} (W={w}, H={h})")
            else:
                print("Warning: Non-positive dimensions found in Space_X/Y Below_Amount constraints. Area limit ignored.")
        except (ValueError, TypeError):
            print("Warning: Invalid numeric value in Space_X/Y Below_Amount constraints. Area limit ignored.")
    elif minimize_area:
         print("Area Minimization Detected: Treating total area as part of the objective.")
    else:
         print("Area Handling: No area limit constraint or minimization objective found in specs.")


    # --- 3. Create PuLP Problem ---
    prob = pulp.LpProblem("Module_Selection", pulp.LpMaximize)

    # --- 4. Define Decision Variables ---
    module_counts = pulp.LpVariable.dicts(
        "Count", module_ids, lowBound=0, cat='Integer'
    )

    # --- 5. Define Objective Function ---
    objective_expr = pulp.LpAffineExpression()
    objective_terms_added = 0
    maximized_units = []
    minimized_units = []

    # Add standard resource objectives
    for rule in valid_specs:
        unit = rule['Unit']
        if unit is None or unit in DIMENSION_RESOURCES: continue # Handle area separately

        weight = 0
        base_sign = 0
        is_minimize = rule['Minimize'] == 1
        is_maximize = rule['Maximize'] == 1

        # Validate objective based on resource type
        if unit in INPUT_RESOURCES:
            if is_maximize: continue # Cannot Maximize input
            if is_minimize: base_sign = -1
        elif unit in OUTPUT_RESOURCES:
            if is_minimize: continue # Cannot Minimize output
            if is_maximize: base_sign = 1
        elif unit in INTERNAL_RESOURCES:
            if is_minimize or is_maximize: continue # Cannot Min/Max internal
        else: # Unknown resource type
            if is_minimize: base_sign = -1
            if is_maximize: base_sign = 1

        # Apply user-defined weight
        if base_sign != 0:
            relative_weight = weights.get(unit, 1.0) # Use provided weights dict
            weight = base_sign * relative_weight

        if weight != 0:
            unit_net_contrib_expr = pulp.lpSum(
                float(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts
            )
            objective_expr += weight * unit_net_contrib_expr
            objective_terms_added += 1
            term_desc = f"{unit} (W={weight:.2f})"
            if weight > 0: maximized_units.append(term_desc)
            else: minimized_units.append(term_desc)

    # Add Area to Objective if Minimizing Area
    area_expr = pulp.lpSum(
        float(module_data[mod_id]['area']) * module_counts[mod_id]
        for mod_id in module_ids if mod_id in module_counts and module_data[mod_id]['area'] > 0
    )

    if minimize_area:
        relative_area_weight = weights.get('total_area', 1.0) # Use provided weights dict
        final_area_weight = -1.0 * relative_area_weight
        objective_expr += final_area_weight * area_expr
        objective_terms_added += 1
        term_desc = f"total_area (W={final_area_weight:.2f})"
        minimized_units.append(term_desc)

    if objective_terms_added == 0:
        print("Warning: No valid terms added to the objective function! Setting dummy objective (maximize 0).")
        prob += 0
    else:
        prob += objective_expr
        if maximized_units: print(f"Objective Maximizing: {', '.join(maximized_units)}")
        if minimized_units: print(f"Objective Minimizing: {', '.join(minimized_units)}")


    # --- 6. Define Constraints ---
    # Area Constraint (if not minimizing and limit > 0)
    if not minimize_area and total_area_limit > 0:
        prob += area_expr <= total_area_limit, "TotalAreaConstraint"
        print(f"Constraint Added: Total Area <= {total_area_limit}")

    # Resource Constraints from Specs
    constraints_added = 0
    for rule in valid_specs:
        unit = rule['Unit']
        limit = rule['Amount']
        is_below = rule['Below_Amount'] == 1
        is_above = rule['Above_Amount'] == 1
        is_unconstrained = rule['Unconstrained'] == 1

        # Skip rules that are not Below/Above constraints or are for dimensions/unconstrained
        if unit is None or unit in DIMENSION_RESOURCES or is_unconstrained:
            continue
        if not is_below and not is_above: # Skip if it's not a limit constraint (e.g., objective rule)
             continue

        # Check for missing/invalid limit *only* for Below/Above constraints
        if limit is None or (isinstance(limit, float) and math.isnan(limit)):
            print(f"Warning: Skipping constraint for '{unit}' due to missing/invalid limit amount.")
            continue

        # --- Convert limit to float only now that we know it's needed and valid ---
        limit_float = float(limit)

        # --- Define expressions (consider moving this down if computationally heavy) ---
        input_expr = pulp.lpSum(
            float(module_data[mod_id]['inputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )
        output_expr = pulp.lpSum(
            float(module_data[mod_id]['outputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )

        constraint_added_for_unit = False
        constraint_str = ""
        # --- Apply constraints using limit_float ---
        if unit in INPUT_RESOURCES:
            if is_below:
                prob += input_expr <= limit_float, f"InputLimit_Below_{unit}"
                constraint_str = f"INPUT (Below): {unit} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above: # 'elif' is fine since is_below and is_above shouldn't both be true for the same rule
                prob += input_expr >= limit_float, f"InputLimit_Above_{unit}"
                constraint_str = f"INPUT (Above): {unit} >= {limit_float}"
                constraint_added_for_unit = True
        elif unit in OUTPUT_RESOURCES:
            if is_below:
                prob += output_expr <= limit_float, f"OutputReq_Below_{unit}"
                constraint_str = f"OUTPUT (Below): {unit} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above:
                prob += output_expr >= limit_float, f"OutputReq_Above_{unit}"
                constraint_str = f"OUTPUT (Above): {unit} >= {limit_float}"
                constraint_added_for_unit = True
        elif unit in INTERNAL_RESOURCES:
             # Below/Above constraints are currently ignored for internal resources
             print(f"Warning: Ignoring Below/Above constraint for internal resource '{unit}'.")
        else: # Unknown resource type
            print(f"Warning: Applying spec constraint to unknown resource type '{unit}'.")
            if is_below:
                # Assume below applies to input-like aspect for unknown
                prob += input_expr <= limit_float, f"UnknownLimit_Below_{unit}"
                constraint_str = f"UNKNOWN (Below): {unit} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above:
                 # Assume above applies to output-like aspect for unknown
                prob += output_expr >= limit_float, f"UnknownReq_Above_{unit}"
                constraint_str = f"UNKNOWN (Above): {unit} >= {limit_float}"
                constraint_added_for_unit = True

        if constraint_added_for_unit:
            constraints_added += 1
            print(f"Constraint Added: {constraint_str}")

    # Implicit Constraints for Internal Resources (Net >= 0)
    all_defined_units = set()
    for mod_id in module_ids:
        all_defined_units.update(module_data[mod_id]['inputs'].keys())
        all_defined_units.update(module_data[mod_id]['outputs'].keys())

    internal_constraints_added = 0
    for unit in INTERNAL_RESOURCES:
        if unit in all_defined_units:
            net_expr = pulp.lpSum(
                float(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts
            )
            prob += net_expr >= 0, f"InternalNet_{unit}"
            print(f"Constraint Added: INTERNAL Net {unit} >= 0")
            internal_constraints_added += 1

    # --- 7. Solve the Problem ---
    print(f"\nSolving the MIP problem (Time Limit: {SOLVER_TIME_LIMIT_SECONDS}s)...")
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT_SECONDS)
    prob.solve(solver)
    solve_time = time.time() - start_time
    print(f"Solve Time: {solve_time:.2f} seconds")
    print(f"Solver Status: {pulp.LpStatus[prob.status]}")

    # --- 8. Process Results ---
    selected_modules_counts = {}
    net_resources = {}

    if prob.status == pulp.LpStatusOptimal or prob.status == pulp.LpStatusFeasible:
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()

        for mod_id in module_ids:
            if mod_id in module_counts:
                count_val = module_counts[mod_id].varValue
                if count_val is not None and count_val > 0.5: # Use tolerance
                    count = int(round(count_val))
                    selected_modules_counts[mod_id] = count
                    mod_details = module_data[mod_id]
                    for unit, amount in mod_details['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_details['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)

        # Calculate Net Resources for all involved units (including internal)
        # Also include units mentioned in specs, even if not produced/consumed
        spec_units = {rule['Unit'] for rule in valid_specs if rule['Unit']}
        relevant_units = sorted(list(all_units_in_solution | spec_units | set(INTERNAL_RESOURCES)))

        for unit in relevant_units:
            if unit in DIMENSION_RESOURCES: continue # Exclude dimensions from net resource dict
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            net_resources[unit] = net # Store only the net value

        print(f"Selected Modules: {selected_modules_counts}")
        print(f"Net Resources: {net_resources}")

    else:
        print("Optimization did not find an optimal or feasible solution.")
        # Return empty dicts as per function description
        return {}, {}

    return selected_modules_counts, net_resources


def solve_module_placement(modules: list[Module], specs: list[dict], weights: dict, selected_modules_counts: dict) -> dict:
    """
    Implements the module placement algorithm based on the GreedyModulePlacement class.
    
    Args:
        modules (list[Module]): List of available Module objects.
        specs (list[dict]): A list of dictionaries defining the constraints and objectives.
        weights (dict): Dictionary specifying the relative importance for objective terms.
        selected_modules_counts (dict): Dictionary of selected module IDs and counts from solve_module_list.
        
    Returns:
        dict: A dictionary containing placement information:
            - 'status': Status of the placement ('Success', 'Failed', etc.).
            - 'placement': List of dictionaries with module placement details.
            - 'grid': 2D numpy array representation of the placement.
            - 'score': Placement score metrics.
            
    If placement fails, returns a dictionary with status 'Failed' and empty values.
    """
    if not selected_modules_counts:
        return {
            'status': 'Failed',
            'message': 'No modules selected for placement',
            'placement': [],
            'grid': None,
            'score': 0.0
        }
    
    print(f"--- Starting Module Placement ---")
    
    # --- 1. Process Modules ---
    module_data = {}
    for mod in modules:
        mod_id = mod.id
        inputs = {}
        outputs = {}
        mod_width = 0
        mod_height = 0
        
        # Process io_fields to populate inputs, outputs, width, height
        for field in mod.io_fields:
            unit = standardize_unit_name(field.unit)
            amount = field.amount
            
            if unit == 'space_x' and field.is_input:
                try:
                    mod_width = int(amount) if amount else 0
                except (ValueError, TypeError):
                    mod_width = 0
            elif unit == 'space_y' and field.is_input:
                try:
                    mod_height = int(amount) if amount else 0
                except (ValueError, TypeError):
                    mod_height = 0
            
            if field.is_input:
                inputs[unit] = amount
            if field.is_output:
                outputs[unit] = amount
        
        # Calculate Area
        mod_area = 0
        if mod_width > 0 and mod_height > 0:
            mod_area = mod_width * mod_height
        
        module_data[mod_id] = {
            "name": mod.name,
            "inputs": inputs,
            "outputs": outputs,
            "width": mod_width,
            "height": mod_height,
            "area": mod_area
        }
    
    # --- 2. Extract space constraints from specs ---
    total_width = None
    total_height = None
    
    for rule in specs:
        unit = standardize_unit_name(rule.get('Unit'))
        if not unit:
            continue
        
        # Check for space constraints (Below_Amount on space_x/y)
        if unit == 'space_x' and rule.get('Below_Amount') == 1 and rule.get('Amount') is not None:
            try:
                total_width = int(rule.get('Amount'))
            except (ValueError, TypeError):
                print(f"Warning: Invalid space_x constraint: {rule.get('Amount')}")
                
        if unit == 'space_y' and rule.get('Below_Amount') == 1 and rule.get('Amount') is not None:
            try:
                total_height = int(rule.get('Amount'))
            except (ValueError, TypeError):
                print(f"Warning: Invalid space_y constraint: {rule.get('Amount')}")
    
    if total_width is None or total_height is None or total_width <= 0 or total_height <= 0:
        return {
            'status': 'Failed',
            'message': f'Invalid space constraints: width={total_width}, height={total_height}',
            'placement': [],
            'grid': None,
            'score': 0.0
        }
    
    print(f"Space constraints: {total_width} x {total_height}")
    
    # --- 3. Create the placement grid (locked regions are not supported in this version) ---
    initial_grid = np.zeros((total_height, total_width), dtype=int)
    
    # --- 4. Implement placement algorithm ---
    class GreedyModulePlacement:
        """Handles the greedy placement of modules on a grid."""
        
        def __init__(self, module_data, selected_modules_counts, total_width, total_height, locked_grid=None):
            """Initialize placement algorithm with module data and selection."""
            self.module_data = module_data
            self.selected_modules = []
            
            # Create individual module instances based on counts
            for mod_id, count in selected_modules_counts.items():
                for i in range(count):
                    if mod_id not in module_data:
                        continue  # Skip if module doesn't exist in data
                        
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
            Returns a connectivity matrix showing which modules should be placed near each other.
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
                print("Error: Could not place the first module!")
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
                    
                    # Increase the influence of connectivity by squaring it
                    total_connectivity = total_connectivity ** 2
                    
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
                                        weighted_dist = manhattan_dist / (connectivity[i, other_idx] ** 2 + 0.1)
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
                        
                        # Try to place in a compact way (minimize total bounding box)
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
            
            return {
                'total_score': final_score,
                'compactness': compactness,
                'connectivity': connectivity_score,
                'used_area': used_area,
                'bbox_area': bbox_area,
                'bbox_width': max_x - min_x,
                'bbox_height': max_y - min_y
            }
        
        def get_resource_connections(self):
            """Map the resource flows between modules."""
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
    
    # --- 5. Run the placement algorithm ---
    placement_engine = GreedyModulePlacement(
        module_data,
        selected_modules_counts,
        total_width,
        total_height
    )
    
    placement, grid = placement_engine.run_placement()
    
    if not placement:
        return {
            'status': 'Failed',
            'message': 'Placement algorithm failed to place modules',
            'placement': [],
            'grid': None,
            'score': 0.0
        }
    
    # Calculate score details
    score_details = placement_engine.calculate_placement_score()
    
    # Prepare connections data for frontend visualization
    resource_connections = placement_engine.get_resource_connections()
    connections_list = []
    
    for resource, flows in resource_connections.items():
        for producer_idx, consumer_idx, flow_amount in flows:
            if producer_idx < len(placement) and consumer_idx < len(placement):
                connections_list.append({
                    'resource': resource,
                    'producer_id': placement[producer_idx]['id'],
                    'producer_instance': placement[producer_idx]['instance'],
                    'consumer_id': placement[consumer_idx]['id'],
                    'consumer_instance': placement[consumer_idx]['instance'],
                    'flow_amount': flow_amount
                })
    
    # Prepare result
    result = {
        'status': 'Success',
        'placement': placement,
        'grid': grid.tolist() if grid is not None else None,
        'score': score_details,
        'connections': connections_list,
        'dimensions': {
            'width': total_width,
            'height': total_height
        }
    }
    
    return result