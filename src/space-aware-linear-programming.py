"""
Solves the datacenter module configuration and placement problem using
Google OR-Tools CP-SAT solver.

This script reads module specifications (including dimensions derived from /Y inputs)
and datacenter requirements (including total area dimensions from Space_X/Y constraints)
from CSV files. It formulates a Constraint Programming problem for each spec, aiming
to place modules without overlap within the area while optimizing resource objectives
and satisfying resource constraints.
"""
import pandas as pd
from ortools.sat.python import cp_model
import sys
import time # To measure solve time
import math # Import math for ceiling division if needed, or use //

# --- Configuration ---
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"
# Max potential instances per module type (adjust based on expected scale/area)
# A higher number allows more flexibility but increases model size.
# DEFAULT_MAX_INSTANCES_PER_TYPE = 20 # Removed
# Solver time limit in seconds
SOLVER_TIME_LIMIT_SECONDS = 60.0


# --- Helper Function to Load and Process Data ---
def standardize_unit_name(name):
    """Converts unit name to standard format: lowercase_with_underscores."""
    if pd.isna(name):
        return None
    # Convert to string first to handle potential non-string types
    return str(name).strip().lower().replace(' ', '_')


def load_data(modules_path, spec_path):
    """
    Loads module and specification data, extracting module dimensions.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        tuple: module_data (dict), all_specs_df (pd.DataFrame),
               module_ids (np.ndarray), unique_spec_names (np.ndarray)
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
    module_ids = modules_df['ID'].unique()
    module_names = modules_df.drop_duplicates('ID').set_index('ID')['Name'].to_dict()

    print("Processing Module Dimensions (assuming Space_X -> Width, Space_Y -> Height):")
    for mod_id in module_ids:
        df_mod = modules_df[modules_df['ID'] == mod_id]
        inputs_series = df_mod[df_mod['Is_Input'] == 1].set_index('Unit')['Amount']
        outputs_series = df_mod[df_mod['Is_Output'] == 1].set_index('Unit')['Amount']

        inputs = {k: v for k, v in inputs_series.items() if pd.notna(v)}
        outputs = {k: v for k, v in outputs_series.items() if pd.notna(v)}

        # *** Extract Dimensions ***
        # Assume Space_X input IS the width, Space_Y input IS the height
        width = inputs.get('space_x', 0) # Get width from inputs dict
        height = inputs.get('space_y', 0) # Get height from inputs dict

        # Convert dimensions to integers, handle potential errors/non-positives
        try:
            mod_width = int(width)
            mod_height = int(height)
            if mod_width <= 0 or mod_height <= 0:
                 print(f"  - Warning: Module ID {mod_id} ({module_names.get(mod_id)}) has non-positive dimensions "
                       f"(W={mod_width}, H={mod_height}). It cannot be placed.")
                 # Store 0 dimensions to exclude it from placement logic
                 mod_width = 0
                 mod_height = 0
            else:
                 # print(f"  - Module ID {mod_id} ({module_names.get(mod_id)}): Width={mod_width}, Height={mod_height}") # Verbose
                 pass

        except (ValueError, TypeError):
             print(f"  - Warning: Module ID {mod_id} ({module_names.get(mod_id)}) has invalid dimension values "
                   f"(W='{width}', H='{height}'). It cannot be placed.")
             mod_width = 0
             mod_height = 0

        # Remove Space_X/Y from standard inputs if they represent dimensions
        inputs.pop('space_x', None)
        inputs.pop('space_y', None)

        module_data[mod_id] = {
            "name": module_names.get(mod_id, f"Unknown_{mod_id}"),
            "inputs": inputs,
            "outputs": outputs,
            "width": mod_width,
            "height": mod_height
        }
    print("-" * 30)


    # --- Process Spec Data ---
    unique_spec_names = specs_df['Name'].unique()
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


# --- CP-SAT Optimization Function ---
def solve_datacenter_placement(module_data, target_spec_df, module_ids,
                               target_spec_name, total_width, total_height): # Removed max_instances_per_type
    """
    Creates and solves the CP-SAT problem for module placement and resource optimization.

    Args:
        module_data (dict): Module info including dimensions (width, height).
        target_spec_df (pd.DataFrame): Specification rules for the current target.
        module_ids (np.ndarray): Array of unique module IDs.
        target_spec_name (str): Name of the specification being solved.
        total_width (int): The total available width of the datacenter area.
        total_height (int): The total available height of the datacenter area.
        # Removed max_instances_per_type parameter doc

    Returns:
        dict: Results including status, objective value, placed modules with coordinates,
              resource summary, and constraint verification.
    """
    print(f"\n##### Solving Placement for Specification: {target_spec_name} #####")
    print(f"Area Dimensions: Width={total_width}, Height={total_height}")
    # print(f"Max Instances per Module Type: {max_instances_per_type}") # Removed print
    print("-" * 30)

    model = cp_model.CpModel()
    start_time = time.time()

    # --- Data Structures for CP-SAT variables ---
    # List to hold tuples: (instance_id, mod_id, width, height)
    all_potential_instances_info = []
    # Dict to hold CP-SAT variables for each instance:
    # {instance_id: {'x':.., 'y':.., 'ix':.., 'iy':.., 'present':.., 'mod_id':..}}
    instance_vars = {}
    instance_counter = 0

    # --- Create Placement Variables for Potential Instances ---
    print("Creating placement variables...")
    module_max_instances = {} # Store calculated max instances per type
    for mod_id in module_ids:
        width = module_data[mod_id]['width']
        height = module_data[mod_id]['height']

        # Only create variables for modules that *can* be placed
        if width <= 0 or height <= 0 or width > total_width or height > total_height:
            # print(f"  - Skipping Module ID {mod_id} due to invalid/too large dimensions.") # Verbose
            module_max_instances[mod_id] = 0 # Store 0 max instances
            continue

        # Calculate a theoretical maximum number of instances based on area
        # This is a loose upper bound, but prevents infinite variables.
        max_possible_w = total_width // width
        max_possible_h = total_height // height
        max_possible = max_possible_w * max_possible_h
        module_max_instances[mod_id] = max_possible # Store calculated max
        # print(f"  - Module ID {mod_id}: Max possible instances based on area = {max_possible}") # Optional verbose print

        # Use the calculated max_possible for the loop range
        for i in range(max_possible):
            instance_id = instance_counter
            all_potential_instances_info.append((instance_id, mod_id, width, height))
            prefix = f"inst_{instance_id}_mod_{mod_id}"

            # Core position and presence variables
            x_var = model.NewIntVar(0, total_width - width, f'{prefix}_x')
            y_var = model.NewIntVar(0, total_height - height, f'{prefix}_y')
            present_var = model.NewBoolVar(f'{prefix}_present')

            # Optional Interval variables (active only if present_var is true)
            # IntervalVar(start, size, end, is_present, name)
            # The 'end' argument is start + size
            interval_x = model.NewOptionalIntervalVar(x_var, width, x_var + width, present_var, f'{prefix}_ix')
            interval_y = model.NewOptionalIntervalVar(y_var, height, y_var + height, present_var, f'{prefix}_iy')

            instance_vars[instance_id] = {
                'x': x_var, 'y': y_var, 'ix': interval_x, 'iy': interval_y,
                'present': present_var, 'mod_id': mod_id
            }
            instance_counter += 1
    print(f"Created {instance_counter} potential instance variables.")
    print("-" * 30)


    # --- Add 2D Non-Overlap Constraint ---
    if instance_vars: # Only add if there are placeable modules
        print("Adding Non-Overlap Constraint...")
        x_intervals = [v['ix'] for v in instance_vars.values()]
        y_intervals = [v['iy'] for v in instance_vars.values()]
        model.AddNoOverlap2D(x_intervals, y_intervals)
    else:
        print("Warning: No placeable modules found, skipping non-overlap constraint.")
    print("-" * 30)


    # --- Link Instance Presence to Module Counts ---
    print("Linking presence variables to module counts...")
    module_count_vars = {}
    for mod_id in module_ids:
         # Sum of present_vars for instances of this module type
         instances_of_type = [inst_id for inst_id, m_id, _, _ in all_potential_instances_info if m_id == mod_id]
         # Use the calculated max instances for this type as the upper bound
         max_inst = module_max_instances.get(mod_id, 0) # Get calculated max, default 0
         count_var = model.NewIntVar(0, max_inst, f"count_mod_{mod_id}")
         if instances_of_type: # Only add if variables were created for this type
            model.Add(count_var == sum(instance_vars[inst_id]['present'] for inst_id in instances_of_type))
         else: # If no instances possible (e.g., too large), fix count to 0
            model.Add(count_var == 0)
         module_count_vars[mod_id] = count_var
    print("-" * 30)


    # --- Define Objective Function (using module_count_vars) ---
    print("Building Objective:")
    objective_expr = 0 # CP-SAT uses linear expressions directly
    objective_terms_added = 0

    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        if unit is None: continue

        weight = 0
        if row['Maximize'] == 1: weight = 1
        elif row['Minimize'] == 1: weight = -1

        if weight != 0:
            # Calculate net contribution for this unit across all module *types*
            unit_net_contrib = sum(
                int(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0)) # Cast difference to int
                * module_count_vars[mod_id]
                for mod_id in module_ids if mod_id in module_count_vars # Ensure var exists
            )
            # Check if the linear expression has terms before adding
            # (This check is less critical in CP-SAT compared to PuLP's LpAffineExpression)
            if isinstance(unit_net_contrib, int) and unit_net_contrib == 0:
                 pass # Skip if expression is trivially zero
            elif hasattr(unit_net_contrib, 'Proto') and not unit_net_contrib.Proto().vars:
                 pass # Skip if expression has no variables (more robust check)
            else:
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective_expr += weight * unit_net_contrib
                 objective_terms_added += 1


    if objective_terms_added == 0:
        print("  - Warning: No terms added to the objective function!")
        # CP-SAT doesn't strictly need an objective, but we add a dummy one if maximizing/minimizing
        model.Maximize(0) # Define a dummy objective
    else:
        model.Maximize(objective_expr) # Maximize the combined expression

    print("-" * 30)


    # --- Define Resource Constraints (using module_count_vars) ---
    print("Adding Resource Constraints:")
    constraints_added = 0
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']
        is_below = row['Below_Amount'] == 1
        is_above = row['Above_Amount'] == 1

        # Skip units defining the area dimensions, they are handled by placement boundaries
        if unit in ['space_x', 'space_y'] and is_below:
             continue

        if unit is None: continue

        if is_below and pd.notna(limit):
            input_expr = sum(
                int(module_data[mod_id]['inputs'].get(unit, 0)) * module_count_vars[mod_id] # Cast input amount to int
                for mod_id in module_ids if mod_id in module_count_vars
            )
            model.Add(input_expr <= int(limit)) # Ensure limit is integer
            print(f"  - INPUT {unit} <= {int(limit)}")
            constraints_added += 1
        elif is_above and pd.notna(limit):
             output_expr = sum(
                int(module_data[mod_id]['outputs'].get(unit, 0)) * module_count_vars[mod_id] # Cast output amount to int
                for mod_id in module_ids if mod_id in module_count_vars
             )
             model.Add(output_expr >= int(limit)) # Ensure limit is integer
             print(f"  - OUTPUT {unit} >= {int(limit)}")
             constraints_added += 1
        elif (is_below or is_above) and pd.isna(limit):
             print(f"  - Warning: Skipping constraint for {unit} due to missing limit.")

    if constraints_added == 0:
         print("  - Warning: No resource constraints were added (besides placement)!")
    print("-" * 30)


    # --- Solve the Problem ---
    print(f"Solving the CP-SAT problem for {target_spec_name} (Time Limit: {SOLVER_TIME_LIMIT_SECONDS}s)...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    # Optional: Increase logging level for more details
    # solver.parameters.log_search_progress = True
    status = solver.Solve(model)
    solve_time = time.time() - start_time
    print(f"Solve Time: {solve_time:.2f} seconds")
    print("-" * 30)

    # --- Process Results ---
    results = {
        "spec_name": target_spec_name,
        "status": solver.StatusName(status),
        "objective_value": None,
        "placed_modules": [], # Changed from selected_modules
        "selected_modules_counts": {}, # Added to store counts
        "resource_summary": {},
        "constraint_verification": [],
        "solve_time_seconds": solve_time
    }

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        results["objective_value"] = solver.ObjectiveValue()
        placed_modules_list = []
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()

        # Get placed module info
        for inst_id, inst_info in instance_vars.items():
            if solver.Value(inst_info['present']):
                mod_id = inst_info['mod_id']
                mod_details = module_data[mod_id]
                placed_module = {
                    'id': mod_id,
                    'name': mod_details['name'],
                    'x': solver.Value(inst_info['x']),
                    'y': solver.Value(inst_info['y']),
                    'width': mod_details['width'],
                    'height': mod_details['height']
                }
                placed_modules_list.append(placed_module)

        results["placed_modules"] = placed_modules_list

        # Calculate resource totals based on module counts derived from placed instances
        current_module_counts = {}
        for mod_id in module_ids:
             if mod_id in module_count_vars:
                 count = solver.Value(module_count_vars[mod_id])
                 if count > 0:
                     current_module_counts[mod_id] = count
                     mod_details = module_data[mod_id]
                     for unit, amount in mod_details['inputs'].items():
                          total_inputs[unit] = total_inputs.get(unit, 0) + amount * count
                          all_units_in_solution.add(unit)
                     for unit, amount in mod_details['outputs'].items():
                          total_outputs[unit] = total_outputs.get(unit, 0) + amount * count
                          all_units_in_solution.add(unit)

        # Store the calculated counts in the results
        results["selected_modules_counts"] = current_module_counts

        # --- Calculate Resource Totals ---
        resource_summary_dict = {}
        spec_units = set(target_spec_df['Unit'].dropna())
        relevant_units = sorted(list(all_units_in_solution | spec_units))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            is_below = row['Below_Amount'] == 1
            is_above = row['Above_Amount'] == 1

            # Skip area constraints verification (implicitly handled)
            if unit in ['space_x', 'space_y'] and is_below: continue
            if unit is None: continue

            if is_below and pd.notna(limit):
                actual_input = total_inputs.get(unit, 0)
                status_ok = actual_input <= limit + 1e-6 # Tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Below Input  {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)

            if is_above and pd.notna(limit):
                actual_output = total_outputs.get(unit, 0)
                status_ok = actual_output >= limit - 1e-6 # Tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Above Output {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)
        results["constraint_verification"] = constraint_verification_list

    return results


# --- Orchestration Function ---
def run_datacenter_placement_optimization(modules_path, spec_path): # Removed max_instances
    """
    Orchestrates the datacenter placement optimization process.

    Loads data, finds total dimensions for each spec, calls the CP-SAT solver,
    and collects the results.
    """
    all_results = []

    # 1. Load Data
    try:
        module_data, all_specs_df, module_ids, unique_spec_names = load_data(modules_path, spec_path)
    except SystemExit:
        return None

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()
        if current_spec_df.empty:
            print(f"\nWarning: No rules found for specification '{spec_name}'. Skipping.")
            all_results.append({"spec_name": spec_name, "status": "Skipped - No Rules", "placed_modules": []})
            continue

        # *** Extract Total Dimensions for this Spec ***
        total_width = current_spec_df[
            (current_spec_df['Unit'] == 'space_x') & (current_spec_df['Below_Amount'] == 1)
        ]['Amount'].iloc[0] if not current_spec_df[
            (current_spec_df['Unit'] == 'space_x') & (current_spec_df['Below_Amount'] == 1)
        ].empty else 0

        total_height = current_spec_df[
            (current_spec_df['Unit'] == 'space_y') & (current_spec_df['Below_Amount'] == 1)
        ]['Amount'].iloc[0] if not current_spec_df[
            (current_spec_df['Unit'] == 'space_y') & (current_spec_df['Below_Amount'] == 1)
        ].empty else 0

        try:
            total_width = int(total_width)
            total_height = int(total_height)
            if total_width <= 0 or total_height <= 0:
                raise ValueError("Total dimensions must be positive.")
        except (ValueError, TypeError):
             print(f"\nError: Invalid or missing total dimensions (Space_X/Y Below_Amount constraints) "
                   f"for specification '{spec_name}'. Skipping.")
             all_results.append({"spec_name": spec_name, "status": "Skipped - Invalid Dimensions", "placed_modules": []})
             continue

        # Solve the placement problem
        spec_result = solve_datacenter_placement(
            module_data, current_spec_df, module_ids, spec_name,
            total_width, total_height # Removed max_instances argument
        )
        all_results.append(spec_result)

    return all_results


# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Placement Optimization Script (CP-SAT) ---")

    # Need module_data here to look up names for the final print
    try:
        module_data_for_print, _, _, _ = load_data(MODULES_CSV_PATH, SPEC_CSV_PATH)
    except SystemExit:
        module_data_for_print = {} # Handle case where loading fails before run
        print("\n--- Script Exited Due to Data Loading Errors ---")
        sys.exit(1)
    except Exception as e:
        module_data_for_print = {}
        print(f"\n--- Unexpected error during initial data load for printing: {e} ---")
        # Decide if you want to exit or continue without names
        # sys.exit(1) # Optional: exit if names are critical

    optimization_results = run_datacenter_placement_optimization(
        MODULES_CSV_PATH, SPEC_CSV_PATH # Removed DEFAULT_MAX_INSTANCES_PER_TYPE argument
    )

    if optimization_results is None:
        # Error message already printed in run_... function or load_data
        sys.exit(1)

    print("\n\n--- Final Placement Optimization Results ---")

    # Print results for each spec in the requested format
    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        print(f"Status: {result['status']}") # Removed solve time here, can be added if needed

        if result['status'] in ["OPTIMAL", "FEASIBLE"]:
            if result['objective_value'] is not None:
                 # Format matches user request
                 print(f"Optimal Objective Value = {result['objective_value']:.4f}")
            else:
                 print("Objective Value = None") # Should not happen for OPTIMAL/FEASIBLE with CP-SAT

            print("\nSelected Modules:") # Changed header
            if result.get('selected_modules_counts'): # Use .get for safety
                # Sort by module ID for consistent output
                sorted_mod_ids = sorted(result['selected_modules_counts'].keys())
                for mod_id in sorted_mod_ids:
                    count = result['selected_modules_counts'][mod_id]
                    # Look up name, handle potential missing module_data
                    mod_name = module_data_for_print.get(mod_id, {}).get('name', f"Unknown_ID_{mod_id}")
                    print(f"  - {mod_name} (ID: {mod_id}): {count}")
            else:
                print("  (No modules selected/placed)") # Adjusted message

            print("\nResulting Resource Summary:")
            if result.get('resource_summary'): # Use .get for safety
                # Sort by unit name for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    res = result['resource_summary'][unit]
                    # Format matches user request
                    print(f"  - {unit:<20}: Input={res['input']:10.2f}, Output={res['output']:10.2f}, Net={res['net']:10.2f}")
            else:
                print("  (Resource summary not calculated)")

            print("\nConstraint Verification:")
            if result.get('constraint_verification'): # Use .get for safety
                for line in result['constraint_verification']:
                     # Add prefix to match user request
                    print(f"  - {line}")
            else:
                 print("  (No resource constraints to verify)")

        elif result['status'] == 'INFEASIBLE':
            print("\nDetails: The problem is infeasible. No valid placement satisfies all constraints.")
        # Add brief messages for other statuses if desired
        # elif result['status'] == 'MODEL_INVALID':
        #      print("\nDetails: The CP-SAT model formulation is invalid.")
        # elif result['status'] == 'UNKNOWN':
        #      print("\nDetails: Solver finished with an unknown status (e.g., time limit reached).")
        elif "Skipped" in result['status']:
             print(f"\nDetails: {result['status']}")
        else:
            print(f"\nDetails: Solver finished with status: {result['status']}")

        # Print the final separator line as requested
        print("=" * 63) # Adjusted length to roughly match example

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")