# filepath: resource_optimization_no_placement.py
"""
Solves the datacenter module resource optimization problem using PuLP.

This script reads module specifications (including area derived from Space_X/Y inputs)
and datacenter requirements (including total area from Space_X/Y constraints)
from CSV files. It formulates a Mixed Integer Linear Programming problem for each spec,
aiming to select the optimal number of each module type to maximize/minimize
resource objectives, satisfy resource constraints (including total area),
and respect resource type rules. It handles area either as a constraint or
as a minimization objective based on the spec. It does NOT consider module placement/layout.
"""
import pandas as pd
import pulp
import sys
import time # To measure solve time

# --- Configuration ---
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"
# Solver time limit in seconds
SOLVER_TIME_LIMIT_SECONDS = 600.0
# Weight for area minimization in the objective function
# Make it negative because the default problem sense is Maximization
# AREA_MINIMIZATION_WEIGHT = -1.0 # <<< REMOVED: Replaced by OBJECTIVE_WEIGHTS

# --- User-Defined Objective Weights ---
# Specify relative importance. Units/area not listed default to 1.0.
# Positive values indicate importance magnitude. Sign is determined by Maximize/Minimize rule.
# Example: {'data_storage': 2.0, 'total_area': 1.0, 'price': 0.5} means data_storage is twice
# as important as total_area minimization, which is twice as important as price minimization.
OBJECTIVE_WEIGHTS = {
    'data_storage': 1.0,
    'processing': 1.0,
    'external_network': 1.0,
    'price': 1.0,
    'total_area': 0.1 # Weight for area minimization if active
    # Add other units and their weights here if needed
}


# Define Resource Categories
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
# Add space dimensions here so they are ignored in standard resource constraint logic
# but used for area calculation and constraint/objective.
DIMENSION_RESOURCES = ['space_x', 'space_y']


# --- Helper Function to Load and Process Data ---
def standardize_unit_name(name):
    """Converts unit name to standard format: lowercase_with_underscores."""
    if pd.isna(name):
        return None
    # Convert to string first to handle potential non-string types
    return str(name).strip().lower().replace(' ', '_')


def load_data(modules_path, spec_path):
    """
    Loads module and specification data, extracting module area and total area.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        tuple: module_data (dict), all_specs_df (pd.DataFrame),
               module_ids (list), unique_spec_names (list)
    Raises:
        SystemExit: On file loading errors or missing essential data.
    """
    try:
        modules_df = pd.read_csv(modules_path, sep=';', quotechar='"', skipinitialspace=True)
        specs_df = pd.read_csv(spec_path, sep=';', quotechar='"', skipinitialspace=True)
    except FileNotFoundError as e:
        print(f"Error loading CSV: {e}. Make sure files exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        sys.exit(1)

    # Standardize Unit names consistently
    modules_df['Unit'] = modules_df['Unit'].apply(standardize_unit_name)
    specs_df['Unit'] = specs_df['Unit'].apply(standardize_unit_name)
    modules_df.dropna(subset=['Unit'], inplace=True)
    # Don't dropna for specs yet, need Name column first
    # specs_df.dropna(subset=['Unit'], inplace=True) # Moved after Name check

    # --- Process Modules Data ---
    module_data = {}
    module_ids = sorted(list(modules_df['ID'].unique())) # Use sorted list
    module_names = modules_df.drop_duplicates('ID').set_index('ID')['Name'].to_dict()

    print("Processing Module Dimensions and Area:")
    for mod_id in module_ids:
        df_mod = modules_df[modules_df['ID'] == mod_id]
        inputs_series = df_mod[df_mod['Is_Input'] == 1].set_index('Unit')['Amount']
        outputs_series = df_mod[df_mod['Is_Output'] == 1].set_index('Unit')['Amount']

        inputs = {k: v for k, v in inputs_series.items() if pd.notna(v)}
        outputs = {k: v for k, v in outputs_series.items() if pd.notna(v)}

        # *** Extract Dimensions and Calculate Area ***
        width = inputs.get('space_x', 0)
        height = inputs.get('space_y', 0)
        mod_area = 0

        try:
            mod_width = int(width)
            mod_height = int(height)
            if mod_width <= 0 or mod_height <= 0:
                 print(f"  - Warning: Module ID {mod_id} ({module_names.get(mod_id)}) has non-positive dimensions "
                       f"(W={mod_width}, H={mod_height}). Area set to 0, cannot contribute to area constraint/objective.")
                 mod_width = 0
                 mod_height = 0
                 mod_area = 0
            else:
                 mod_area = mod_width * mod_height

        except (ValueError, TypeError):
             print(f"  - Warning: Module ID {mod_id} ({module_names.get(mod_id)}) has invalid dimension values "
                   f"(W='{width}', H='{height}'). Area set to 0.")
             mod_width = 0
             mod_height = 0
             mod_area = 0

        # Remove Space_X/Y from standard inputs if they represent dimensions
        inputs.pop('space_x', None)
        inputs.pop('space_y', None)

        module_data[mod_id] = {
            "name": module_names.get(mod_id, f"Unknown_{mod_id}"),
            "inputs": inputs,
            "outputs": outputs,
            "width": mod_width, # Keep for info if needed
            "height": mod_height, # Keep for info if needed
            "area": mod_area
        }


    # --- Process Spec Data ---
    # Drop rows where Name is missing first
    specs_df.dropna(subset=['Name'], inplace=True)
    unique_spec_names = sorted(list(specs_df['Name'].unique())) # Use sorted list
    if len(unique_spec_names) == 0:
        print(f"Error: No specifications found (or missing 'Name') in {spec_path}")
        sys.exit(1)

    # Now drop rows where Unit is missing, as they are unusable rules
    specs_df.dropna(subset=['Unit'], inplace=True)

    # Convert relevant columns to numeric
    num_cols_spec = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained', 'Amount']
    for col in num_cols_spec:
         if col in specs_df.columns:
              specs_df[col] = pd.to_numeric(specs_df[col], errors='coerce')
         else:
              print(f"Warning: Column '{col}' not found in {spec_path}")
              specs_df[col] = 0 # Add the column with default 0

    # Fill NaN in flags with 0
    flag_cols = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained']
    for col in flag_cols:
        if col in specs_df.columns:
             specs_df[col] = specs_df[col].fillna(0).astype(int)


    print(f"\n--- Loaded Data ---")
    print(f"- {len(module_data)} module types.")
    print(f"- {len(unique_spec_names)} specifications found: {', '.join(unique_spec_names)}")

    return module_data, specs_df, module_ids, unique_spec_names


# --- PuLP Optimization Function ---
def solve_resource_optimization_no_placement(module_data, target_spec_df, module_ids,
                                             target_spec_name, total_area_limit):
    """
    Creates and solves the PuLP problem for module count selection and resource optimization.
    Handles area either as a constraint or a minimization objective.

    Args:
        module_data (dict): Module info including area.
        target_spec_df (pd.DataFrame): Specification rules for the current target.
        module_ids (list): List of unique module IDs.
        target_spec_name (str): Name of the specification being solved.
        total_area_limit (int): The total available area from the spec (used only if area is constrained).

    Returns:
        dict: Results including status, objective value, selected module counts,
              resource summary, and constraint verification.
    """
    print(f"\n##### Solving Resource Optimization for Specification: {target_spec_name} #####")
    print("-" * 30)

    start_time = time.time()

    # --- Determine if Area should be Minimized ---
    minimize_area = False
    if 'Minimize' in target_spec_df.columns:
        if target_spec_df[
            (target_spec_df['Unit'].isin(DIMENSION_RESOURCES)) &
            (target_spec_df['Minimize'] == 1)
        ].any().any(): # Check if any row matches
            minimize_area = True
            print("Area Minimization Detected: Treating total area as part of the objective.")
    if not minimize_area:
        print(f"Area Constraint Active: Total Available Area Limit = {total_area_limit}")


    # --- Create PuLP Problem ---
    # Default to Maximization, can be adjusted if only minimization objectives exist
    prob = pulp.LpProblem(f"ResourceOpt_{target_spec_name}", pulp.LpMaximize)

    # --- Define Decision Variables ---
    # Integer count for each module type
    module_counts = pulp.LpVariable.dicts(
        "Count", module_ids, lowBound=0, cat='Integer'
    )

    # --- Define Objective Function (respecting resource types) ---
    print("Building Objective Function:")
    objective_expr = pulp.LpAffineExpression() # Start with an empty expression
    objective_terms_added = 0
    maximized_units = []
    minimized_units = []

    # Add standard resource objectives first
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        # Skip dimensions here, handle area objective/constraint separately
        if unit is None or unit in DIMENSION_RESOURCES: continue

        weight = 0
        base_sign = 0 # +1 for maximize, -1 for minimize
        is_minimize = row['Minimize'] == 1
        is_maximize = row['Maximize'] == 1

        # Validate objective based on resource type
        if unit in INPUT_RESOURCES:
            if is_maximize:
                print(f"  - Warning: Cannot Maximize input resource '{unit}'. Ignoring objective term.")
                continue
            if is_minimize:
                base_sign = -1 # Minimization is maximizing the negative
        elif unit in OUTPUT_RESOURCES:
            if is_minimize:
                print(f"  - Warning: Cannot Minimize output resource '{unit}'. Ignoring objective term.")
                continue
            if is_maximize:
                base_sign = 1
        elif unit in INTERNAL_RESOURCES:
            if is_minimize or is_maximize:
                print(f"  - Warning: Cannot Minimize/Maximize internal resource '{unit}'. Ignoring objective term.")
                continue
        else: # Unknown resource type
            if is_minimize: base_sign = -1
            if is_maximize: base_sign = 1
            if base_sign != 0:
                 print(f"  - Warning: Applying objective to unknown resource type '{unit}'.")

        # Apply user-defined weight if applicable
        if base_sign != 0:
            relative_weight = OBJECTIVE_WEIGHTS.get(unit, 1.0) # Default to 1.0 if not specified
            weight = base_sign * relative_weight


        if weight != 0:
            # Calculate net contribution expression for this unit
            unit_net_contrib_expr = pulp.lpSum(
                # Cast amounts to float for potentially non-integer weights
                float(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts # Ensure var exists
            )

            # Add term to objective - PuLP handles zero expressions gracefully
            objective_expr += weight * unit_net_contrib_expr
            objective_terms_added += 1
            term_desc = f"{unit} (W={weight:.2f})"
            if weight > 0:
                maximized_units.append(term_desc)
            elif weight < 0:
                minimized_units.append(term_desc)
            print(f"  - Adding Objective Term: {term_desc}")


    # --- Add Area to Objective if Minimizing Area ---
    # Calculate area expression regardless (needed for constraint or objective)
    area_expr = pulp.lpSum(
        # Cast area to float for potentially non-integer weights
        float(module_data[mod_id]['area']) * module_counts[mod_id]
        for mod_id in module_ids if mod_id in module_counts and module_data[mod_id]['area'] > 0
    )

    if minimize_area:
        # Get relative weight for area, default to 1.0
        relative_area_weight = OBJECTIVE_WEIGHTS.get('total_area', 1.0)
        # Final weight is negative because we minimize area (in a maximization problem)
        final_area_weight = -1.0 * relative_area_weight
        objective_expr += final_area_weight * area_expr
        objective_terms_added += 1
        term_desc = f"total_area (W={final_area_weight:.2f})"
        minimized_units.append(term_desc) # Add to list for clarity
        print(f"  - Adding Objective Term: {term_desc}")


    if objective_terms_added == 0:
        print("  - Warning: No valid terms added to the objective function! Setting dummy objective (maximize 0).")
        prob += 0 # Define a dummy objective
    else:
        prob += objective_expr # Add the combined objective expression
        if maximized_units: print(f"  - Maximizing: {', '.join(maximized_units)}")
        if minimized_units: print(f"  - Minimizing: {', '.join(minimized_units)}")


    # --- Define Constraints ---

    # 1. Total Area Constraint (ONLY if not minimizing area)
    print("Building Constraints:")
    if not minimize_area:
        if total_area_limit > 0:
            # Add constraint - PuLP handles zero expressions gracefully
            prob += area_expr <= total_area_limit, "TotalAreaConstraint"
            print(f"  - Constraint Added: Total Area <= {total_area_limit}")


    # 2. Resource Constraints from Spec (respecting resource types)
    constraints_added = 0
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']
        is_below = row['Below_Amount'] == 1
        is_above = row['Above_Amount'] == 1
        is_unconstrained = row['Unconstrained'] == 1

        # Skip dimensions (handled above), unconstrained, or invalid rows
        if unit is None or unit in DIMENSION_RESOURCES: continue
        if is_unconstrained:
            continue
        if pd.isna(limit) and (is_below or is_above):
            print(f"  - Warning: Skipping constraint for '{unit}' due to missing limit amount.")
            continue

        # Ensure limit is integer for comparison/constraint RHS
        try:
            limit_int = int(limit)
        except (ValueError, TypeError):
             print(f"  - Warning: Skipping constraint for '{unit}' due to non-integer limit amount '{limit}'.")
             continue


        # Calculate total input and output expressions for the unit
        input_expr = pulp.lpSum(
            int(module_data[mod_id]['inputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )
        output_expr = pulp.lpSum(
            int(module_data[mod_id]['outputs'].get(unit, 0)) * module_counts[mod_id]
            for mod_id in module_ids if mod_id in module_counts
        )

        # Apply constraints based on resource type
        constraint_added_for_unit = False
        constraint_str = ""
        if unit in INPUT_RESOURCES:
            # Allow both Below and Above constraints for Input resources
            if is_below:
                prob += input_expr <= limit_int, f"InputLimit_Below_{unit}"
                constraint_str = f"INPUT (Below): {unit} <= {limit_int}"
                constraint_added_for_unit = True
            elif is_above:
                prob += input_expr >= limit_int, f"InputLimit_Above_{unit}"
                constraint_str = f"INPUT (Above): {unit} >= {limit_int}"
                constraint_added_for_unit = True

        elif unit in OUTPUT_RESOURCES:
            # Allow both Below and Above constraints for Output resources
            if is_below:
                prob += output_expr <= limit_int, f"OutputReq_Below_{unit}"
                constraint_str = f"OUTPUT (Below): {unit} <= {limit_int}"
                constraint_added_for_unit = True
            elif is_above:
                prob += output_expr >= limit_int, f"OutputReq_Above_{unit}"
                constraint_str = f"OUTPUT (Above): {unit} >= {limit_int}"
                constraint_added_for_unit = True

        elif unit in INTERNAL_RESOURCES:
            if is_below or is_above:
                print(f"  - Warning: Cannot apply 'Below/Above_Amount' constraint to internal resource '{unit}'. Internal resources must always be >= 0 net (handled separately). Ignoring spec constraint.")

        else: # Unknown resource type - apply constraints as specified but warn
            print(f"  - Warning: Applying spec constraint to unknown resource type '{unit}'.")
            if is_below:
                prob += input_expr <= limit_int, f"UnknownLimit_Below_{unit}"
                constraint_str = f"UNKNOWN (Below): {unit} <= {limit_int}"
                constraint_added_for_unit = True
            elif is_above:
                prob += output_expr >= limit_int, f"UnknownReq_Above_{unit}"
                constraint_str = f"UNKNOWN (Above): {unit} >= {limit_int}"
                constraint_added_for_unit = True

        if constraint_added_for_unit:
            constraints_added += 1
            print(f"  - Constraint Added: {constraint_str}")


    # 3. Implicit Constraints for Internal Resources (Net >= 0)
    internal_constraints_added = 0
    all_defined_units = set()
    for mod_id in module_ids:
        all_defined_units.update(module_data[mod_id]['inputs'].keys())
        all_defined_units.update(module_data[mod_id]['outputs'].keys())

    for unit in INTERNAL_RESOURCES:
        # Only add constraint if the resource is actually used by any module
        if unit in all_defined_units:
            net_expr = pulp.lpSum(
                int(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts
            )
            # Add constraint - PuLP handles zero expressions gracefully
            prob += net_expr >= 0, f"InternalNet_{unit}"
            print(f"  - Constraint Added: INTERNAL Net {unit} >= 0")
            internal_constraints_added += 1


    # Check if any constraints were added at all (excluding internal >= 0)
    area_constraint_active = (not minimize_area and total_area_limit > 0) # Simplified check
    if constraints_added == 0 and not area_constraint_active and internal_constraints_added == 0:
         print("\n  - Warning: No constraints were added! Check spec file.")


    # --- Solve the Problem ---
    print(f"\nSolving the MIP problem for {target_spec_name} (Time Limit: {SOLVER_TIME_LIMIT_SECONDS}s)...")
    # Use default CBC solver, suppress excessive messages, set time limit
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT_SECONDS)
    prob.solve(solver)
    solve_time = time.time() - start_time
    print(f"Solve Time: {solve_time:.2f} seconds")

    # --- Process Results ---
    status_name = pulp.LpStatus[prob.status]
    results = {
        "spec_name": target_spec_name,
        "status": status_name,
        "objective_value": None,
        "selected_modules_counts": {},
        "total_area_used": 0,
        "resource_summary": {},
        "constraint_verification": [],
        "solve_time_seconds": solve_time,
        "area_minimized": minimize_area # Store how area was handled
    }

    if prob.status == pulp.LpStatusOptimal:
        results["objective_value"] = pulp.value(prob.objective)
        selected_counts = {}
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()
        total_area_used_calc = 0

        # Get selected module counts and calculate totals
        for mod_id in module_ids:
            if mod_id in module_counts:
                count_val = module_counts[mod_id].varValue
                # Use a small tolerance for floating point issues with integer vars
                if count_val is not None and count_val > 0.5:
                    count = int(round(count_val)) # Round to nearest integer
                    selected_counts[mod_id] = count
                    mod_details = module_data[mod_id]
                    # Calculate area used based on selected modules
                    total_area_used_calc += mod_details['area'] * count
                    for unit, amount in mod_details['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_details['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)

        results["selected_modules_counts"] = selected_counts
        # Store the calculated area used
        results["total_area_used"] = total_area_used_calc

        # --- Calculate Resource Summary ---
        resource_summary_dict = {}
        spec_units = set(target_spec_df['Unit'].dropna())
        relevant_units = sorted(list(all_units_in_solution | spec_units | set(INTERNAL_RESOURCES)))

        for unit in relevant_units:
            # Skip dimension resources in this summary section
            if unit in DIMENSION_RESOURCES: continue
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
        tolerance = 1e-6 # Tolerance for floating point comparisons

        # Verify Area Constraint (only if it was active)
        if not minimize_area and total_area_limit > 0:
            area_ok = total_area_used_calc <= total_area_limit + tolerance
            area_status = "OK" if area_ok else "VIOLATED"
            verification_str = f"Area Constraint : Actual={total_area_used_calc:10.2f} <= Limit={total_area_limit:10.2f} ({area_status})"
            constraint_verification_list.append(verification_str)
        elif minimize_area:
            verification_str = f"Area Objective  : Actual={total_area_used_calc:10.2f} (Minimized in Objective)"
            constraint_verification_list.append(verification_str)
        else: # No area constraint applied
             verification_str = f"Area Info       : Actual={total_area_used_calc:10.2f} (No Constraint Applied)"
             constraint_verification_list.append(verification_str)


        # Verify Spec Constraints
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            is_below = row['Below_Amount'] == 1
            is_above = row['Above_Amount'] == 1
            is_unconstrained = row['Unconstrained'] == 1

            # Skip dimensions, unconstrained, or invalid rows
            if unit is None or unit in DIMENSION_RESOURCES or is_unconstrained: continue
            if pd.isna(limit) and (is_below or is_above): continue # Skip invalid

            # Ensure limit is numeric for comparison
            try:
                limit_float = float(limit)
            except (ValueError, TypeError):
                 continue # Skip if limit wasn't valid earlier

            actual_input = total_inputs.get(unit, 0)
            actual_output = total_outputs.get(unit, 0)
            status_ok = True
            violation_type = ""
            verification_str = ""

            if unit in INPUT_RESOURCES:
                if is_below:
                    status_ok = actual_input <= limit_float + tolerance
                    violation_type = "Below Input"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                elif is_above: # Now check Above for Inputs
                    status_ok = actual_input >= limit_float - tolerance
                    violation_type = "Above Input"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} >= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

            elif unit in OUTPUT_RESOURCES:
                if is_below: # Now check Below for Outputs
                    status_ok = actual_output <= limit_float + tolerance
                    violation_type = "Below Output"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} <= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                elif is_above:
                    status_ok = actual_output >= limit_float - tolerance
                    violation_type = "Above Output"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

            elif unit in INTERNAL_RESOURCES:
                 # Spec constraints are ignored, only implicit >= 0 matters (verified next)
                 pass

            else: # Unknown resource type - verify as specified
                 if is_below:
                    # Assuming Below applies to the 'input-like' aspect
                    status_ok = actual_input <= limit_float + tolerance
                    violation_type = "Below Input (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                 elif is_above:
                    # Assuming Above applies to the 'output-like' aspect
                    status_ok = actual_output >= limit_float - tolerance
                    violation_type = "Above Output (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit_float:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

            if verification_str: # Add if a check was performed
                constraint_verification_list.append(verification_str)


        # Verify Implicit Internal Resource Constraints
        for unit in INTERNAL_RESOURCES:
             if unit in resource_summary_dict: # Only verify if present in solution/modules
                actual_net = resource_summary_dict[unit]['net']
                status_ok = actual_net >= -tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Internal Net    {unit:<15}: Actual={actual_net:10.2f} >= Limit=   0.00 ({status_str})"
                constraint_verification_list.append(verification_str)

        results["constraint_verification"] = constraint_verification_list

    elif prob.status == pulp.LpStatusInfeasible:
        results["status"] = "Infeasible" # Standardize name slightly
    elif prob.status == pulp.LpStatusNotSolved:
         results["status"] = "Not Solved (Check Time Limit)"
    elif prob.status == pulp.LpStatusUndefined:
         results["status"] = "Undefined (Problem might be unbounded or infeasible)"
    # Add other statuses if needed

    return results


# --- Orchestration Function ---
def run_datacenter_resource_optimization(modules_path, spec_path):
    """
    Orchestrates the datacenter resource optimization process (no placement).

    Loads data, finds total area limit (if applicable) for each spec,
    calls the PuLP solver, and collects the results.
    """
    all_results = []

    # 1. Load Data
    try:
        module_data, all_specs_df, module_ids, unique_spec_names = load_data(modules_path, spec_path)
    except SystemExit:
        return None
    except Exception as e:
        print(f"Unexpected error during data loading: {e}")
        return None

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()
        if current_spec_df.empty:
            print(f"\nWarning: No rules found for specification '{spec_name}'. Skipping.")
            all_results.append({"spec_name": spec_name, "status": "Skipped - No Rules", "selected_modules_counts": {}})
            continue

        # *** Extract Total Area Limit for this Spec (if defined by Below_Amount) ***
        # This limit is only used if area is NOT being minimized.
        total_area_limit = 0 # Default to 0 (no constraint) if not found or invalid
        try:
            # Find Space_X and Space_Y constraints defining the total area limit
            width_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_x') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']
            height_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_y') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']

            # Only calculate if BOTH Below_Amount constraints exist
            if not width_rows.empty and not height_rows.empty:
                total_width = int(width_rows.iloc[0])
                total_height = int(height_rows.iloc[0])

                if total_width > 0 and total_height > 0:
                    total_area_limit = total_width * total_height
                else:
                    print(f"\nWarning: Non-positive dimensions found in Space_X/Y Below_Amount constraints "
                          f"for specification '{spec_name}'. Area limit set to 0 (no constraint).")


        except (ValueError, TypeError, IndexError) as e:
             # This might happen if Amount is not numeric after conversion attempts
             print(f"\nWarning: Invalid numeric value in Space_X/Y Below_Amount constraints "
                   f"for specification '{spec_name}'. Details: {e}. Area limit set to 0.")
             total_area_limit = 0


        # Solve the resource optimization problem
        # Pass the calculated limit, the solver function decides whether to use it
        spec_result = solve_resource_optimization_no_placement(
            module_data, current_spec_df, module_ids, spec_name,
            total_area_limit
        )
        all_results.append(spec_result)

    return all_results


# --- Main Execution and Printing Function ---
def run_optimization_and_print_results(modules_path, spec_path):
    """
    Runs the complete optimization process and prints the results.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        list or None: A list of result dictionaries for each specification,
                      or None if the initial data loading failed.
    """
    print("--- Starting Datacenter Resource Optimization Script (PuLP - No Placement) ---")
    print(f"--- Using Objective Weights: {OBJECTIVE_WEIGHTS} (Default: 1.0) ---")

    # Pre-load module data for final printing names, handle potential errors
    module_data_for_print = {}
    try:
        # Use a separate call or ensure load_data is robust
        # Note: load_data prints its own messages
        temp_module_data, _, _, _ = load_data(modules_path, spec_path)
        module_data_for_print = temp_module_data
    except SystemExit:
        print("\n--- Script Exited Due to Initial Data Loading Errors ---")
        return None # Indicate failure
    except Exception as e:
        print(f"\n--- Unexpected error during initial data load for printing names: {e} ---")
        # Decide if continuing without names is acceptable, returning None for now
        return None # Indicate failure

    optimization_results = run_datacenter_resource_optimization(
        modules_path, spec_path
    )

    if optimization_results is None:
        # Error message already printed by run_datacenter_resource_optimization or load_data
        print("\n--- Optimization run failed or was skipped. ---")
        return None # Indicate failure

    print()
    print()
    print("\n\n--- Final Resource Optimization Results (No Placement) ---")

    # Print results for each spec
    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        solve_time = result.get('solve_time_seconds')
        solve_time_str = f"{solve_time:.2f}s" if isinstance(solve_time, (int, float)) else 'N/A'
        print(f"Status: {result['status']} (Solve Time: {solve_time_str})")
        if result.get("area_minimized"):
            print("Area Handling: Minimized in Objective")
        else:
            print("Area Handling: Constrained (if limit > 0)")


        if result['status'] in ["Optimal", "Feasible"]: # PuLP status names
            obj_val = result.get('objective_value')
            print(f"Objective Value = {obj_val:.4f}" if obj_val is not None else "Objective Value = N/A")

            # Print Objective Components
            # Note: Objective units are now stored directly in the result dict by solve function
            max_units = [t for t in result.get('maximized_units', [])] # Get from results if available
            min_units = [t for t in result.get('minimized_units', [])] # Get from results if available

            if max_units:
                print(f"Objective Maximized: {', '.join(max_units)}")
            if min_units:
                print(f"Objective Minimized: {', '.join(min_units)}")
            if not max_units and not min_units and result['status'] != 'Infeasible':
                print("Objective: Default (Feasibility or Maximize 0)")

            print("\nSelected Modules (Count):")
            if result.get('selected_modules_counts'):
                sorted_mod_ids = sorted(result['selected_modules_counts'].keys())
                for mod_id in sorted_mod_ids:
                    count = result['selected_modules_counts'][mod_id]
                    # Use pre-loaded data for names
                    mod_name = module_data_for_print.get(mod_id, {}).get('name', f"Unknown_ID_{mod_id}")
                    print(f"  - {mod_name} (ID: {mod_id}): {count}")
            else:
                print("  (No modules selected)")

            # Always print total area used
            area_used = result.get('total_area_used')
            print(f"\nTotal Area Used: {area_used:.2f}" if isinstance(area_used, (int, float)) else "\nTotal Area Used: N/A")

            print("\nResulting Resource Summary (Excluding Dimensions):")
            if result.get('resource_summary'):
                # Sort by unit name for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    res = result['resource_summary'][unit]
                    inp = res.get('input')
                    outp = res.get('output')
                    net = res.get('net')
                    input_str = f"{inp:.2f}" if isinstance(inp, (int, float)) else 'N/A'
                    output_str = f"{outp:.2f}" if isinstance(outp, (int, float)) else 'N/A'
                    net_str = f"{net:.2f}" if isinstance(net, (int, float)) else 'N/A'
                    print(f"  - {unit:<20}: Input={input_str:>10}, Output={output_str:>10}, Net={net_str:>10}")
            else:
                print("  (Resource summary not calculated)")

            print("\nConstraint Verification:")
            if result.get('constraint_verification'):
                for line in result['constraint_verification']:
                    print(f"  - {line}")
            else:
                 print("  (No constraints to verify or verification failed)")

        elif result['status'] == 'Infeasible':
            print("\nDetails: The problem is infeasible. No selection of modules satisfies all constraints.")
            if result.get("area_minimized"):
                print("         (Note: Area was being minimized, infeasibility is due to other resource constraints).")
            else:
                print("         (This includes the total area limit if one was specified).")
        elif "Skipped" in result['status']:
             print(f"\nDetails: {result['status']}")
        else:
            print(f"\nDetails: Solver finished with status: {result['status']}. Solution might be non-optimal, timed out, or undefined.")

        print("=" * 63)

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")
    return optimization_results # Return the results list


# --- Main Execution Block ---
if __name__ == "__main__":
    # Call the main function with default paths
    results = run_optimization_and_print_results(MODULES_CSV_PATH, SPEC_CSV_PATH)

    if results is None:
        sys.exit(1) # Exit if the function indicated failure