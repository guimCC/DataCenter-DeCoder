"""
Solves the datacenter module configuration and placement problem using
Google OR-Tools CP-SAT solver.

This script reads module specifications (including dimensions derived from /Y inputs)
and datacenter requirements (including total area dimensions from Space_X/Y constraints)
from CSV files. It formulates a Constraint Programming problem for each spec, aiming
to place modules without overlap within the area while optimizing resource objectives
and satisfying resource constraints, respecting resource type rules.
"""
import pandas as pd
from ortools.sat.python import cp_model
import sys
import time # To measure solve time
import math # Import math for ceiling division if needed, or use //

# --- Configuration ---
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"
# Solver time limit in seconds
SOLVER_TIME_LIMIT_SECONDS = 120.0

# Define Resource Categories
INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection']
OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing']
INTERNAL_RESOURCES = ['usable_power', 'fresh_water', 'distilled_water', 'chilled_water', 'internal_network']
# Add space dimensions here so they are ignored in resource constraint logic
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
                               target_spec_name, total_width, total_height):
    """
    Creates and solves the CP-SAT problem for module placement and resource optimization.

    Args:
        module_data (dict): Module info including dimensions (width, height).
        target_spec_df (pd.DataFrame): Specification rules for the current target.
        module_ids (np.ndarray): Array of unique module IDs.
        target_spec_name (str): Name of the specification being solved.
        total_width (int): The total available width of the datacenter area.
        total_height (int): The total available height of the datacenter area.

    Returns:
        dict: Results including status, objective value, placed modules with coordinates,
              resource summary, and constraint verification.
    """
    print(f"\n##### Solving Placement for Specification: {target_spec_name} #####")
    print(f"Area Dimensions: Width={total_width}, Height={total_height}")
    print("-" * 30)

    model = cp_model.CpModel()
    start_time = time.time()

    # --- Data Structures for CP-SAT variables ---
    all_potential_instances_info = []
    instance_vars = {}
    instance_counter = 0

    # --- Create Placement Variables for Potential Instances ---
    print("Creating placement variables...")
    module_max_instances = {} # Store calculated max instances per type
    for mod_id in module_ids:
        width = module_data[mod_id]['width']
        height = module_data[mod_id]['height']

        if width <= 0 or height <= 0 or width > total_width or height > total_height:
            module_max_instances[mod_id] = 0
            continue

        max_possible_w = total_width // width
        max_possible_h = total_height // height
        max_possible = max_possible_w * max_possible_h
        module_max_instances[mod_id] = max_possible
        # print(f"  - Module ID {mod_id}: Max possible instances based on area = {max_possible}") # Optional verbose print

        for i in range(max_possible):
            instance_id = instance_counter
            all_potential_instances_info.append((instance_id, mod_id, width, height))
            prefix = f"inst_{instance_id}_mod_{mod_id}"

            x_var = model.NewIntVar(0, total_width - width, f'{prefix}_x')
            y_var = model.NewIntVar(0, total_height - height, f'{prefix}_y')
            present_var = model.NewBoolVar(f'{prefix}_present')

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
    if instance_vars:
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
         instances_of_type = [inst_id for inst_id, m_id, _, _ in all_potential_instances_info if m_id == mod_id]
         max_inst = module_max_instances.get(mod_id, 0)
         count_var = model.NewIntVar(0, max_inst, f"count_mod_{mod_id}")
         if instances_of_type:
            model.Add(count_var == sum(instance_vars[inst_id]['present'] for inst_id in instances_of_type))
         else:
            model.Add(count_var == 0)
         module_count_vars[mod_id] = count_var
    print("-" * 30)


    # --- Define Objective Function (respecting resource types) ---
    print("Building Objective (respecting resource types):")
    objective_expr = 0
    objective_terms_added = 0
    maximized_units = [] # List to store names of maximized units
    minimized_units = [] # Optional: List to store names of minimized units

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
                weight = -1
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
            unit_net_contrib = sum(
                int(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_count_vars[mod_id]
                for mod_id in module_ids if mod_id in module_count_vars
            )

            # Check if the expression is non-trivial before adding
            is_trivial = False
            if isinstance(unit_net_contrib, int) and unit_net_contrib == 0:
                is_trivial = True
            elif hasattr(unit_net_contrib, 'Proto') and not unit_net_contrib.Proto().vars and unit_net_contrib.Proto().constant == 0:
                 is_trivial = True # Check constant term as well for CP-SAT expressions

            if not is_trivial:
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective_expr += weight * unit_net_contrib
                 objective_terms_added += 1
                 if weight > 0: # Maximizing
                     maximized_units.append(unit)
                 elif weight < 0: # Minimizing
                     minimized_units.append(unit)
            # else: # Optional: print if term was skipped due to being trivial
            #      print(f"  - Skipping trivial objective term for unit '{unit}'.")

    # Print the final objective expression and maximized units
    print(f"\nObjective Function Expression: {objective_expr}")
    if maximized_units:
        print(f"Units being Maximized: {', '.join(maximized_units)}")
    if minimized_units: # Optional: also print minimized units
        print(f"Units being Minimized: {', '.join(minimized_units)}")


    if objective_terms_added == 0:
        print("  - Warning: No valid terms added to the objective function!")
        model.Maximize(0) # Define a dummy objective
    else:
        model.Maximize(objective_expr)

    print("-" * 30)


    # --- Define Resource Constraints (respecting resource types) ---
    print("Adding Resource Constraints (respecting resource types):")
    constraints_added = 0
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']
        is_below = row['Below_Amount'] == 1
        is_above = row['Above_Amount'] == 1
        is_unconstrained = row['Unconstrained'] == 1

        # Skip dimensions (handled by placement) and invalid rows
        if unit is None or unit in DIMENSION_RESOURCES:
             continue
        if is_unconstrained:
            print(f"  - Info: Resource '{unit}' is marked as unconstrained in the spec.")
            continue
        if pd.isna(limit) and (is_below or is_above):
            print(f"  - Warning: Skipping constraint for '{unit}' due to missing limit amount.")
            continue

        # Calculate total input and output expressions for the unit
        input_expr = sum(
            int(module_data[mod_id]['inputs'].get(unit, 0)) * module_count_vars[mod_id]
            for mod_id in module_ids if mod_id in module_count_vars
        )
        output_expr = sum(
            int(module_data[mod_id]['outputs'].get(unit, 0)) * module_count_vars[mod_id]
            for mod_id in module_ids if mod_id in module_count_vars
        )

        # Apply constraints based on resource type
        if unit in INPUT_RESOURCES:
            if is_above:
                print(f"  - Warning: Cannot apply 'Above_Amount' constraint to input resource '{unit}'. Ignoring.")
            elif is_below:
                model.Add(input_expr <= int(limit))
                print(f"  - INPUT Constraint: {unit} <= {int(limit)}")
                constraints_added += 1
            # else: no constraint specified or unconstrained

        elif unit in OUTPUT_RESOURCES:
            if is_below:
                print(f"  - Warning: Cannot apply 'Below_Amount' constraint to output resource '{unit}'. Ignoring.")
            elif is_above:
                 model.Add(output_expr >= int(limit))
                 print(f"  - OUTPUT Constraint: {unit} >= {int(limit)}")
                 constraints_added += 1
            # else: no constraint specified or unconstrained

        elif unit in INTERNAL_RESOURCES:
            if is_below or is_above:
                print(f"  - Warning: Cannot apply 'Below/Above_Amount' constraint to internal resource '{unit}'. Internal resources must always be >= 0 net. Ignoring spec constraint.")
            # Implicit constraint added later for all internal resources

        else: # Unknown resource type - apply constraints as specified but warn
            print(f"  - Warning: Applying spec constraint to unknown resource type '{unit}'.")
            if is_below:
                model.Add(input_expr <= int(limit))
                print(f"  - UNKNOWN TYPE Input Constraint: {unit} <= {int(limit)}")
                constraints_added += 1
            elif is_above:
                 model.Add(output_expr >= int(limit))
                 print(f"  - UNKNOWN TYPE Output Constraint: {unit} >= {int(limit)}")
                 constraints_added += 1

    # --- Add Implicit Constraints for Internal Resources ---
    print("\nAdding Implicit Constraints for Internal Resources (Net >= 0):")
    internal_constraints_added = 0
    all_defined_units = set()
    for mod_id in module_ids:
        all_defined_units.update(module_data[mod_id]['inputs'].keys())
        all_defined_units.update(module_data[mod_id]['outputs'].keys())

    for unit in INTERNAL_RESOURCES:
        # Only add constraint if the resource is actually used by any module
        if unit in all_defined_units:
            net_expr = sum(
                int(module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_count_vars[mod_id]
                for mod_id in module_ids if mod_id in module_count_vars
            )
            model.Add(net_expr >= 0)
            print(f"  - INTERNAL Constraint: Net {unit} >= 0")
            internal_constraints_added += 1
        # else: # Optional: print if internal resource is defined but not used
        #     print(f"  - Info: Internal resource '{unit}' not used by any module, skipping Net >= 0 constraint.")


    if constraints_added == 0 and internal_constraints_added == 0:
         print("\n  - Warning: No resource constraints were added (besides placement and implicit internal)! Check spec file.")
    print("-" * 30)


    # --- Solve the Problem ---
    print(f"Solving the CP-SAT problem for {target_spec_name} (Time Limit: {SOLVER_TIME_LIMIT_SECONDS}s)...")
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    # solver.parameters.num_search_workers = 0 # Use default or specify based on cores
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
        "placed_modules": [],
        "selected_modules_counts": {},
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

        results["selected_modules_counts"] = current_module_counts

        # --- Calculate Resource Totals ---
        resource_summary_dict = {}
        spec_units = set(target_spec_df['Unit'].dropna())
        # Include internal resources even if not in spec for summary
        relevant_units = sorted(list(all_units_in_solution | spec_units | set(INTERNAL_RESOURCES)))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
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

            if unit in INPUT_RESOURCES:
                if is_above: continue # Ignore invalid spec constraint
                if is_below:
                    status_ok = actual_input <= limit + 1e-6 # Tolerance
                    violation_type = "Below Input"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                    constraint_verification_list.append(verification_str)

            elif unit in OUTPUT_RESOURCES:
                if is_below: continue # Ignore invalid spec constraint
                if is_above:
                    status_ok = actual_output >= limit - 1e-6 # Tolerance
                    violation_type = "Above Output"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                    constraint_verification_list.append(verification_str)

            elif unit in INTERNAL_RESOURCES:
                 # Spec constraints are ignored, only implicit >= 0 matters (verified next)
                 pass

            else: # Unknown resource type - verify as specified
                 if is_below:
                    status_ok = actual_input <= limit + 1e-6
                    violation_type = "Below Input (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                    constraint_verification_list.append(verification_str)
                 elif is_above:
                    status_ok = actual_output >= limit - 1e-6
                    violation_type = "Above Output (UNK)"
                    verification_str = f"{violation_type:<15} {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({'OK' if status_ok else 'VIOLATED'})"
                    constraint_verification_list.append(verification_str)

        # Verify Implicit Internal Resource Constraints
        for unit in INTERNAL_RESOURCES:
             if unit in resource_summary_dict: # Only verify if present in solution/modules
                actual_net = resource_summary_dict[unit]['net']
                status_ok = actual_net >= -1e-6 # Tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Internal Net    {unit:<15}: Actual={actual_net:10.2f} >= Limit=   0.00 ({status_str})"
                constraint_verification_list.append(verification_str)

        results["constraint_verification"] = constraint_verification_list

    return results


# --- Orchestration Function ---
def run_datacenter_placement_optimization(modules_path, spec_path):
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
    except Exception as e:
        print(f"Unexpected error during data loading: {e}")
        return None

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()
        if current_spec_df.empty:
            print(f"\nWarning: No rules found for specification '{spec_name}'. Skipping.")
            all_results.append({"spec_name": spec_name, "status": "Skipped - No Rules", "placed_modules": []})
            continue

        # *** Extract Total Dimensions for this Spec ***
        try:
            width_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_x') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']
            height_rows = current_spec_df[
                (current_spec_df['Unit'] == 'space_y') & (current_spec_df['Below_Amount'] == 1)
            ]['Amount']

            if width_rows.empty or height_rows.empty:
                 raise ValueError("Missing Space_X or Space_Y Below_Amount constraint.")

            total_width = int(width_rows.iloc[0])
            total_height = int(height_rows.iloc[0])

            if total_width <= 0 or total_height <= 0:
                raise ValueError("Total dimensions must be positive.")

        except (ValueError, TypeError, IndexError) as e:
             print(f"\nError: Invalid or missing total dimensions (Space_X/Y Below_Amount constraints) "
                   f"for specification '{spec_name}'. Details: {e}. Skipping.")
             all_results.append({"spec_name": spec_name, "status": "Skipped - Invalid Dimensions", "placed_modules": []})
             continue

        # Solve the placement problem
        spec_result = solve_datacenter_placement(
            module_data, current_spec_df, module_ids, spec_name,
            total_width, total_height
        )
        all_results.append(spec_result)

    return all_results


# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Placement Optimization Script (CP-SAT) ---")

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
        # sys.exit(1) # Optional: exit if names are critical

    optimization_results = run_datacenter_placement_optimization(
        MODULES_CSV_PATH, SPEC_CSV_PATH
    )

    if optimization_results is None:
        # Error message already printed in run_... function or load_data
        print("\n--- Optimization run failed or was skipped. ---")
        sys.exit(1)

    print("\n\n--- Final Placement Optimization Results ---")

    # Print results for each spec in the requested format
    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        print(f"Status: {result['status']} (Solve Time: {result.get('solve_time_seconds', 'N/A'):.2f}s)")

        if result['status'] in ["OPTIMAL", "FEASIBLE"]:
            obj_val = result.get('objective_value')
            if obj_val is not None:
                 print(f"Optimal Objective Value = {obj_val:.4f}")
            else:
                 print("Objective Value = N/A") # Should not happen for OPTIMAL/FEASIBLE with CP-SAT

            print("\nSelected Modules (Count):")
            if result.get('selected_modules_counts'):
                sorted_mod_ids = sorted(result['selected_modules_counts'].keys())
                for mod_id in sorted_mod_ids:
                    count = result['selected_modules_counts'][mod_id]
                    mod_name = module_data_for_print.get(mod_id, {}).get('name', f"Unknown_ID_{mod_id}")
                    print(f"  - {mod_name} (ID: {mod_id}): {count}")
            else:
                print("  (No modules selected/placed)")

            print("\nPlaced Modules (Coordinates):")
            if result.get('placed_modules'):
                # Sort by y then x for potentially clearer layout representation
                sorted_placed = sorted(result['placed_modules'], key=lambda p: (p['y'], p['x']))
                for p_mod in sorted_placed:
                     mod_name = module_data_for_print.get(p_mod['id'], {}).get('name', f"Unknown_ID_{p_mod['id']}")
                     print(f"  - {mod_name} (ID: {p_mod['id']}): X={p_mod['x']}, Y={p_mod['y']} (W={p_mod['width']}, H={p_mod['height']})")
            else:
                 print("  (No modules placed)")


            print("\nResulting Resource Summary:")
            if result.get('resource_summary'):
                # Sort by unit name for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    # Skip dimension resources in summary unless needed
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

        elif result['status'] == 'INFEASIBLE':
            print("\nDetails: The problem is infeasible. No valid placement satisfies all constraints.")
            # You might want to add analysis here later, e.g., finding conflicting constraints if possible.
        elif "Skipped" in result['status']:
             print(f"\nDetails: {result['status']}")
        else:
            print(f"\nDetails: Solver finished with status: {result['status']}. Solution might be partial or non-existent.")

        print("=" * 63)

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")