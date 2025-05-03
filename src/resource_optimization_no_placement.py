# filepath: resource_optimization_no_placement.py
"""
Solves the datacenter module resource optimization problem using PuLP.

This script reads module specifications (including area derived from Space_X/Y inputs)
and datacenter requirements (including total area from Space_X/Y constraints)
from CSV files. It formulates a Mixed Integer Linear Programming problem for each spec,
aiming to select the optimal number of each module type to maximize/minimize
resource objectives, satisfy resource constraints (including total area),
and respect resource type rules. It does NOT consider module placement/layout.
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

# Define Resource Categories
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
# Add space dimensions here so they are ignored in resource constraint logic
# but used for area calculation and constraint.
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
    specs_df.dropna(subset=['Unit'], inplace=True)

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
                       f"(W={mod_width}, H={mod_height}). Area set to 0, cannot contribute to area constraint.")
                 mod_width = 0
                 mod_height = 0
                 mod_area = 0
            else:
                 mod_area = mod_width * mod_height
                 # print(f"  - Module ID {mod_id} ({module_names.get(mod_id)}): W={mod_width}, H={mod_height}, Area={mod_area}") # Verbose

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
    print("-" * 30)


    # --- Process Spec Data ---
    unique_spec_names = sorted(list(specs_df['Name'].unique())) # Use sorted list
    if len(unique_spec_names) == 0:
        print(f"Error: No specifications found in {spec_path}")
        sys.exit(1)

    # Convert relevant columns to numeric
    num_cols_spec = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained', 'Amount']
    for col in num_cols_spec:
         if col in specs_df.columns:
              specs_df[col] = pd.to_numeric(specs_df[col], errors='coerce')
         else:
              print(f"Warning: Column '{col}' not found in {spec_path}")
              specs_df[col] = 0

    # Fill NaN in flags with 0
    flag_cols = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained']
    for col in flag_cols:
        if col in specs_df.columns:
             specs_df[col] = specs_df[col].fillna(0).astype(int)


    print(f"--- Loaded Data ---")
    print(f"Found {len(module_data)} module types.")
    print(f"Found {len(specs_df)} total spec rules across {len(unique_spec_names)} specifications.")
    print(f"Specifications to solve: {', '.join(unique_spec_names)}")
    print("-" * 30)

    return module_data, specs_df, module_ids, unique_spec_names


# --- PuLP Optimization Function ---
def solve_resource_optimization_no_placement(module_data, target_spec_df, module_ids,
                                             target_spec_name, total_area):
    """
    Creates and solves the PuLP problem for module count selection and resource optimization.

    Args:
        module_data (dict): Module info including area.
        target_spec_df (pd.DataFrame): Specification rules for the current target.
        module_ids (list): List of unique module IDs.
        target_spec_name (str): Name of the specification being solved.
        total_area (int): The total available area from the spec.

    Returns:
        dict: Results including status, objective value, selected module counts,
              resource summary, and constraint verification.
    """
    print(f"\n##### Solving Resource Optimization for Specification: {target_spec_name} #####")
    print(f"Total Available Area: {total_area}")
    print("-" * 30)

    start_time = time.time()

    # --- Create PuLP Problem ---
    # Default to Maximization, can be adjusted if only minimization objectives exist
    prob = pulp.LpProblem(f"ResourceOpt_{target_spec_name}", pulp.LpMaximize)

    # --- Define Decision Variables ---
    # Integer count for each module type
    module_counts = pulp.LpVariable.dicts(
        "Count", module_ids, lowBound=0, cat='Integer'
    )
    print(f"Created {len(module_counts)} module count variables.")
    print("-" * 30)

    # --- Define Objective Function (respecting resource types) ---
    print("Building Objective (respecting resource types):")
    objective_expr = pulp.LpAffineExpression() # Start with an empty expression
    objective_terms_added = 0
    maximized_units = []
    minimized_units = []

    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        if unit is None or unit in DIMENSION_RESOURCES: continue # Skip dimensions

        weight = 0
        is_minimize = row['Minimize'] == 1
        is_maximize = row['Maximize'] == 1

        # Validate objective based on resource type
        if unit in INPUT_RESOURCES:
            if is_maximize:
                print(f"  - Warning: Cannot Maximize input resource '{unit}'. Ignoring objective term.")
                continue
            if is_minimize:
                weight = -1 # Minimization is maximizing the negative
        elif unit in OUTPUT_RESOURCES:
            if is_minimize:
                print(f"  - Warning: Cannot Minimize output resource '{unit}'. Ignoring objective term.")
                continue
            if is_maximize:
                weight = 1
        elif unit in INTERNAL_RESOURCES:
            if is_minimize or is_maximize:
                print(f"  - Warning: Cannot Minimize/Maximize internal resource '{unit}'. Ignoring objective term.")
                continue
        else: # Unknown resource type
            if is_minimize: weight = -1
            if is_maximize: weight = 1
            if weight != 0:
                 print(f"  - Warning: Applying objective to unknown resource type '{unit}'.")

        if weight != 0:
            # Calculate net contribution expression for this unit
            unit_net_contrib_expr = pulp.lpSum(
                int(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_counts[mod_id]
                for mod_id in module_ids if mod_id in module_counts # Ensure var exists
            )

            # Check if the expression is non-trivial before adding
            # (PuLP handles constant 0 terms okay, but good practice)
            if not (isinstance(unit_net_contrib_expr, (int, float)) and unit_net_contrib_expr == 0):
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective_expr += weight * unit_net_contrib_expr
                 objective_terms_added += 1
                 if weight > 0: maximized_units.append(unit)
                 elif weight < 0: minimized_units.append(unit)
            # else:
            #      print(f"  - Skipping trivial objective term for unit '{unit}'.")

    # Print the final objective details
    print(f"\nObjective Function Expression: {objective_expr}")
    if maximized_units:
        print(f"Units being Maximized (Positive Weight): {', '.join(maximized_units)}")
    if minimized_units:
        print(f"Units being Minimized (Negative Weight): {', '.join(minimized_units)}")

    if objective_terms_added == 0:
        print("  - Warning: No valid terms added to the objective function! Setting dummy objective (maximize 0).")
        prob += 0 # Define a dummy objective
    else:
        prob += objective_expr # Add the combined objective expression

    print("-" * 30)


    # --- Define Constraints ---

    # 1. Total Area Constraint
    print("Adding Total Area Constraint:")
    area_expr = pulp.lpSum(
        module_data[mod_id]['area'] * module_counts[mod_id]
        for mod_id in module_ids if mod_id in module_counts and module_data[mod_id]['area'] > 0
    )
    if not (isinstance(area_expr, (int, float)) and area_expr == 0): # Only add if non-trivial
        prob += area_expr <= total_area, "TotalAreaConstraint"
        print(f"  - Constraint: Total Area <= {total_area}")
    else:
        print("  - Info: No modules have positive area, skipping area constraint.")
    print("-" * 30)


    # 2. Resource Constraints from Spec (respecting resource types)
    print("Adding Resource Constraints from Spec (respecting resource types):")
    constraints_added = 0
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']
        is_below = row['Below_Amount'] == 1
        is_above = row['Above_Amount'] == 1
        is_unconstrained = row['Unconstrained'] == 1

        # Skip dimensions, unconstrained, or invalid rows
        if unit is None or unit in DIMENSION_RESOURCES: continue
        if is_unconstrained:
            print(f"  - Info: Resource '{unit}' is marked as unconstrained.")
            continue
        if pd.isna(limit) and (is_below or is_above):
            print(f"  - Warning: Skipping constraint for '{unit}' due to missing limit amount.")
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
        if unit in INPUT_RESOURCES:
            if is_above:
                print(f"  - Warning: Cannot apply 'Above_Amount' constraint to input resource '{unit}'. Ignoring.")
            elif is_below:
                if not (isinstance(input_expr, (int, float)) and input_expr == 0): # Add if non-trivial
                    prob += input_expr <= int(limit), f"InputLimit_{unit}"
                    print(f"  - INPUT Constraint: {unit} <= {int(limit)}")
                    constraint_added_for_unit = True

        elif unit in OUTPUT_RESOURCES:
            if is_below:
                print(f"  - Warning: Cannot apply 'Below_Amount' constraint to output resource '{unit}'. Ignoring.")
            elif is_above:
                 if not (isinstance(output_expr, (int, float)) and output_expr == 0): # Add if non-trivial
                    prob += output_expr >= int(limit), f"OutputReq_{unit}"
                    print(f"  - OUTPUT Constraint: {unit} >= {int(limit)}")
                    constraint_added_for_unit = True

        elif unit in INTERNAL_RESOURCES:
            if is_below or is_above:
                print(f"  - Warning: Cannot apply 'Below/Above_Amount' constraint to internal resource '{unit}'. Internal resources must always be >= 0 net (handled separately). Ignoring spec constraint.")

        else: # Unknown resource type - apply constraints as specified but warn
            print(f"  - Warning: Applying spec constraint to unknown resource type '{unit}'.")
            if is_below:
                if not (isinstance(input_expr, (int, float)) and input_expr == 0):
                    prob += input_expr <= int(limit), f"UnknownInputLimit_{unit}"
                    print(f"  - UNKNOWN TYPE Input Constraint: {unit} <= {int(limit)}")
                    constraint_added_for_unit = True
            elif is_above:
                 if not (isinstance(output_expr, (int, float)) and output_expr == 0):
                    prob += output_expr >= int(limit), f"UnknownOutputReq_{unit}"
                    print(f"  - UNKNOWN TYPE Output Constraint: {unit} >= {int(limit)}")
                    constraint_added_for_unit = True

        if constraint_added_for_unit:
            constraints_added += 1

    print("-" * 30)


    # 3. Implicit Constraints for Internal Resources (Net >= 0)
    print("Adding Implicit Constraints for Internal Resources (Net >= 0):")
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
            # Add constraint only if it's potentially non-zero
            if not (isinstance(net_expr, (int, float)) and net_expr == 0):
                prob += net_expr >= 0, f"InternalNet_{unit}"
                print(f"  - INTERNAL Constraint: Net {unit} >= 0")
                internal_constraints_added += 1
        # else:
        #     print(f"  - Info: Internal resource '{unit}' not used by any module, skipping Net >= 0 constraint.")


    if constraints_added == 0 and internal_constraints_added == 0 and total_area <= 0:
         print("\n  - Warning: No resource constraints or area constraint were added! Check spec file.")
    print("-" * 30)


    # --- Solve the Problem ---
    print(f"Solving the MIP problem for {target_spec_name} (Time Limit: {SOLVER_TIME_LIMIT_SECONDS}s)...")
    # Use default CBC solver, suppress excessive messages, set time limit
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=SOLVER_TIME_LIMIT_SECONDS)
    prob.solve(solver)
    solve_time = time.time() - start_time
    print(f"Solve Time: {solve_time:.2f} seconds")
    print("-" * 30)

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
        "solve_time_seconds": solve_time
    }

    if prob.status == pulp.LpStatusOptimal or prob.status == pulp.LpStatusFeasible:
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
                    total_area_used_calc += mod_details['area'] * count
                    for unit, amount in mod_details['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_details['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * count
                        all_units_in_solution.add(unit)

        results["selected_modules_counts"] = selected_counts
        results["total_area_used"] = total_area_used_calc

        # --- Calculate Resource Summary ---
        resource_summary_dict = {}
        spec_units = set(target_spec_df['Unit'].dropna())
        relevant_units = sorted(list(all_units_in_solution | spec_units | set(INTERNAL_RESOURCES)))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
        tolerance = 1e-6 # Tolerance for floating point comparisons

        # Verify Area Constraint
        if total_area > 0: # Only verify if there was an area limit
            area_ok = total_area_used_calc <= total_area + tolerance
            area_status = "OK" if area_ok else "VIOLATED"
            verification_str = f"Area            {'Total Area':<15}: Actual={total_area_used_calc:10.2f} <= Limit={total_area:10.2f} ({area_status})"
            constraint_verification_list.append(verification_str)

        # Verify Spec Constraints
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            is_below = row['Below_Amount'] == 1
            is_above = row['Above_Amount'] == 1
            is_unconstrained = row['Unconstrained'] == 1

            if unit is None or unit in DIMENSION_RESOURCES or is_unconstrained: continue
            if pd.isna(limit) and (is_below or is_above): continue # Skip invalid

            actual_input = total_inputs.get(unit, 0)
            actual_output = total_outputs.get(unit, 0)
            status_ok = True
            violation_type = ""
            verification_str = ""

            if unit in INPUT_RESOURCES:
                if is_above: continue # Ignore invalid spec constraint
                if is_below:
                    status_ok = actual_input <= limit + tolerance
                    violation_type = "Below Input"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

            elif unit in OUTPUT_RESOURCES:
                if is_below: continue # Ignore invalid spec constraint
                if is_above:
                    status_ok = actual_output >= limit - tolerance
                    violation_type = "Above Output"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

            elif unit in INTERNAL_RESOURCES:
                 # Spec constraints are ignored, only implicit >= 0 matters (verified next)
                 pass

            else: # Unknown resource type - verify as specified
                 if is_below:
                    status_ok = actual_input <= limit + tolerance
                    violation_type = "Below Input (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                 elif is_above:
                    status_ok = actual_output >= limit - tolerance
                    violation_type = "Above Output (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"

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
         results["status"] = "Not Solved (อาจจะหมดเวลา)"
    elif prob.status == pulp.LpStatusUndefined:
         results["status"] = "Undefined (อาจจะไม่มีทางออก)"
    # Add other statuses if needed

    return results


# --- Orchestration Function ---
def run_datacenter_resource_optimization(modules_path, spec_path):
    """
    Orchestrates the datacenter resource optimization process (no placement).

    Loads data, finds total area for each spec, calls the PuLP solver,
    and collects the results.
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

        # *** Extract Total Area for this Spec ***
        total_area = 0
        try:
            # Find Space_X and Space_Y constraints defining the total area
            width_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_x') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']
            height_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_y') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']

            if width_rows.empty or height_rows.empty:
                 raise ValueError("Missing Space_X or Space_Y Below_Amount constraint to define total area.")

            total_width = int(width_rows.iloc[0])
            total_height = int(height_rows.iloc[0])

            if total_width <= 0 or total_height <= 0:
                raise ValueError("Total dimensions (from Space_X/Y constraints) must be positive.")

            total_area = total_width * total_height

        except (ValueError, TypeError, IndexError) as e:
             print(f"\nError: Invalid or missing total area definition (Space_X/Y Below_Amount constraints) "
                   f"for specification '{spec_name}'. Details: {e}. Skipping.")
             all_results.append({"spec_name": spec_name, "status": "Skipped - Invalid Area Definition", "selected_modules_counts": {}})
             continue

        # Solve the resource optimization problem
        spec_result = solve_resource_optimization_no_placement(
            module_data, current_spec_df, module_ids, spec_name,
            total_area
        )
        all_results.append(spec_result)

    return all_results


# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Resource Optimization Script (PuLP - No Placement) ---")

    # Pre-load module data for final printing names, handle potential errors
    module_data_for_print = {}
    try:
        # Use a separate call or ensure load_data is robust
        temp_module_data, _, _, _ = load_data(MODULES_CSV_PATH, SPEC_CSV_PATH)
        module_data_for_print = temp_module_data
    except SystemExit:
        print("\n--- Script Exited Due to Initial Data Loading Errors ---")
        sys.exit(1)
    except Exception as e:
        print(f"\n--- Unexpected error during initial data load for printing names: {e} ---")
        # Decide if continuing without names is acceptable

    optimization_results = run_datacenter_resource_optimization(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )

    if optimization_results is None:
        # Error message already printed
        print("\n--- Optimization run failed or was skipped. ---")
        sys.exit(1)

    print("\n\n--- Final Resource Optimization Results (No Placement) ---")

    # Print results for each spec
    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        print(f"Status: {result['status']} (Solve Time: {result.get('solve_time_seconds', 'N/A'):.2f}s)")

        if result['status'] in ["Optimal", "Feasible"]: # PuLP status names
            obj_val = result.get('objective_value')
            if obj_val is not None:
                 print(f"Objective Value = {obj_val:.4f}")
            else:
                 print("Objective Value = N/A")

            print("\nSelected Modules (Count):")
            if result.get('selected_modules_counts'):
                sorted_mod_ids = sorted(result['selected_modules_counts'].keys())
                for mod_id in sorted_mod_ids:
                    count = result['selected_modules_counts'][mod_id]
                    mod_name = module_data_for_print.get(mod_id, {}).get('name', f"Unknown_ID_{mod_id}")
                    print(f"  - {mod_name} (ID: {mod_id}): {count}")
            else:
                print("  (No modules selected)")

            print(f"\nTotal Area Used: {result.get('total_area_used', 'N/A'):.2f}")

            print("\nResulting Resource Summary:")
            if result.get('resource_summary'):
                # Sort by unit name for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    # Skip dimension resources in summary
                    if unit in DIMENSION_RESOURCES: continue
                    res = result['resource_summary'][unit]
                    print(f"  - {unit:<20}: Input={res['input']:10.2f}, Output={res['output']:10.2f}, Net={res['net']:10.2f}")
            else:
                print("  (Resource summary not calculated)")

            print("\nConstraint Verification:")
            if result.get('constraint_verification'):
                for line in result['constraint_verification']:
                    print(f"  - {line}")
            else:
                 print("  (No constraints to verify or verification failed)")

        elif result['status'] == 'Infeasible':
            print("\nDetails: The problem is infeasible. No selection of modules satisfies all constraints (including area).")
        elif "Skipped" in result['status']:
             print(f"\nDetails: {result['status']}")
        else:
            print(f"\nDetails: Solver finished with status: {result['status']}. Solution might be non-optimal, timed out, or undefined.")

        print("=" * 63)

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")