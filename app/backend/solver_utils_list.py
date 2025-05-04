from models import Module
import pulp
import time
import math # For checking NaN

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


def solve_module_list(modules: list[Module], specs: list[dict], weights: dict, initial_resources: dict = None) -> tuple[dict, dict]:
    """
    Solves the resource optimization problem to select the best module counts.

    Args:
        modules (list[Module]): List of available Module objects.
        specs (list[dict]): A list of dictionaries defining the constraints and objectives.
                             Each dict should have keys like 'Unit', 'Below_Amount', 'Above_Amount',
                             'Minimize', 'Maximize', 'Amount', 'Unconstrained'.
        weights (dict): Dictionary specifying the relative importance for objective terms.
                        Example: {'data_storage': 2.0, 'total_area': 1.0}
        initial_resources (dict, optional): A dictionary representing the initial state of resources
                                            before adding any modules. Defaults to None (treated as empty).
                                            Example: {'data_storage': 100, 'price': -50}

    Returns:
        tuple[dict, dict]: A tuple containing:
            - selected_modules_counts (dict): {module_id: count}
            - net_resources (dict): {resource_unit: net_value} for all involved resources,
                                    including the initial state.
            Returns ({}, {}) if optimization fails or is infeasible.
    """
    start_time = time.time()
    print(f"--- Starting Module List Optimization ---")
    print(f"Received {len(modules)} module types, {len(specs)} spec rules.")

    # Initialize initial_resources if None
    if initial_resources is None:
        initial_resources = {}
    else:
        # Standardize keys in initial_resources
        initial_resources = {standardize_unit_name(k): v for k, v in initial_resources.items() if standardize_unit_name(k)}
        print(f"Using Initial Resources: {initial_resources}")


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
            # Calculate net contribution from modules for this unit
            unit_net_contrib_expr = pulp.lpSum(
                float(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts
            )
            # Add the initial resource value for this unit to the objective expression
            initial_value = float(initial_resources.get(unit, 0))
            objective_expr += weight * (unit_net_contrib_expr + initial_value) # Add initial value here
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
        safe_area_limit = 0.9 * total_area_limit
        prob += area_expr <= safe_area_limit, "TotalAreaConstraint"
        print(f"Constraint Added: Total Area <= {safe_area_limit:.2f} (90% of {total_area_limit})")

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
        initial_value = float(initial_resources.get(unit, 0)) # Get initial value for the unit

        # --- Define expressions (consider moving this down if computationally heavy) ---
        input_expr = pulp.lpSum(
            float(module_data[mod_id]['inputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )
        output_expr = pulp.lpSum(
            float(module_data[mod_id]['outputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )
        # Net expression including initial value
        net_expr_with_initial = output_expr - input_expr + initial_value

        constraint_added_for_unit = False
        constraint_str = ""
        # --- Apply constraints using limit_float and initial_value ---
        if unit in INPUT_RESOURCES:
            if is_below:
                prob += input_expr + initial_value <= limit_float, f"InputLimit_Below_{unit}"
                constraint_str = f"INPUT (Below): {unit} + {initial_value} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above:
                prob += input_expr + initial_value >= limit_float, f"InputLimit_Above_{unit}"
                constraint_str = f"INPUT (Above): {unit} + {initial_value} >= {limit_float}"
                constraint_added_for_unit = True
        elif unit in OUTPUT_RESOURCES:
            # Output constraints apply to the total output (module outputs + initial)
            if is_below:
                prob += output_expr + initial_value <= limit_float, f"OutputReq_Below_{unit}"
                constraint_str = f"OUTPUT (Below): {unit} + {initial_value} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above:
                prob += output_expr + initial_value >= limit_float, f"OutputReq_Above_{unit}"
                constraint_str = f"OUTPUT (Above): {unit} + {initial_value} >= {limit_float}"
                constraint_added_for_unit = True
        elif unit in INTERNAL_RESOURCES:
             # Below/Above constraints are currently ignored for internal resources
             # If needed later, they would likely apply to the net value: net_expr_with_initial
             print(f"Warning: Ignoring Below/Above constraint for internal resource '{unit}'.")
        else: # Unknown resource type
            # Apply constraints to the net value for unknown types
            print(f"Warning: Applying spec constraint to unknown resource type '{unit}' (using net value).")
            if is_below:
                prob += net_expr_with_initial <= limit_float, f"UnknownLimit_Below_{unit}"
                constraint_str = f"UNKNOWN (Below): Net {unit} + {initial_value} <= {limit_float}"
                constraint_added_for_unit = True
            elif is_above:
                prob += net_expr_with_initial >= limit_float, f"UnknownReq_Above_{unit}"
                constraint_str = f"UNKNOWN (Above): Net {unit} + {initial_value} >= {limit_float}"
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
        # Check if the unit is involved in modules OR initial resources
        if unit in all_defined_units or unit in initial_resources:
            initial_value = float(initial_resources.get(unit, 0))
            net_expr = pulp.lpSum(
                float(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts
            )
            # Add initial value to the net expression for the constraint
            prob += net_expr + initial_value >= 0, f"InternalNet_{unit}"
            print(f"Constraint Added: INTERNAL Net {unit} + {initial_value} >= 0")
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

    if prob.status == pulp.LpStatusOptimal: # Corrected status check
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()

        # Calculate totals from selected modules
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

        # Calculate Net Resources for all involved units (including internal and initial)
        spec_units = {rule['Unit'] for rule in valid_specs if rule['Unit']}
        initial_units = set(initial_resources.keys())
        relevant_units = sorted(list(all_units_in_solution | spec_units | set(INTERNAL_RESOURCES) | initial_units))

        for unit in relevant_units:
            if unit in DIMENSION_RESOURCES: continue # Exclude dimensions from net resource dict
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            initial_val = initial_resources.get(unit, 0)
            # Final net is (output from modules + initial output) - (input from modules + initial input)
            # Assuming initial_resources represents the net starting value:
            net = (outp - inp) + initial_val
            net_resources[unit] = net # Store the final net value including initial state

        print(f"Selected Modules: {selected_modules_counts}")
        print(f"Initial Resources: {initial_resources}")
        print(f"Final Net Resources (incl. initial): {net_resources}")

    else:
        print("Optimization did not find an optimal or feasible solution.")
        # Return empty dicts as per function description
        return {}, {}

    return selected_modules_counts, net_resources


def solve_module_list_with_fixed_modules(modules: list[Module], specs: list[dict], weights: dict, fixed_modules: list[Module]) -> tuple[dict, dict]:
    """
    Calculates initial resources based on a list of fixed modules and then solves
    the optimization problem for the remaining selectable modules.

    Args:
        modules (list[Module]): List of available Module objects to select from.
        specs (list[dict]): List of constraints and objectives.
        weights (dict): Dictionary of objective weights.
        fixed_modules (list[Module]): List of Module objects that are pre-selected
                                      and contribute to the initial resource state.

    Returns:
        tuple[dict, dict]: Result from solve_module_list:
            - selected_modules_counts (dict): {module_id: count} for the non-fixed modules.
            - net_resources (dict): {resource_unit: net_value} for all resources,
                                    including contributions from fixed modules.
    """
    print(f"--- Calculating Initial Resources from {len(fixed_modules)} Fixed Modules ---")
    initial_resources_from_fixed = {}

    if not fixed_modules:
        print("No fixed modules provided. Proceeding without initial resources from fixed set.")
    else:
        for fixed_mod in fixed_modules:
            print(f"Processing fixed module: {fixed_mod.name} (ID: {fixed_mod.id})")
            for field in fixed_mod.io_fields:
                unit = standardize_unit_name(field.unit)
                if not unit or unit in DIMENSION_RESOURCES: # Skip dimensions and invalid units
                    continue

                try:
                    amount = float(field.amount) if field.amount is not None else 0.0
                except (ValueError, TypeError):
                    print(f"Warning: Invalid amount '{field.amount}' for unit '{unit}' in fixed module ID {fixed_mod.id}. Skipping field.")
                    continue

                # Calculate net contribution: output is positive, input is negative
                net_contribution = 0
                if field.is_output:
                    net_contribution = amount
                elif field.is_input:
                    net_contribution = -amount

                # Update the initial resources dictionary
                initial_resources_from_fixed[unit] = initial_resources_from_fixed.get(unit, 0) + net_contribution
                # print(f"  - Unit: {unit}, Amount: {field.amount}, IsInput: {field.is_input}, IsOutput: {field.is_output}, Net: {net_contribution}, Cumulative: {initial_resources_from_fixed[unit]}")


        print(f"Calculated Initial Resources from Fixed Modules: {initial_resources_from_fixed}")

    # Call the main solver function with the calculated initial resources
    return solve_module_list(modules, specs, weights, initial_resources=initial_resources_from_fixed)
