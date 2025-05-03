"""
Solves the datacenter module configuration problem using Mixed Integer Linear Programming (MILP),
considering total area constraints and specific rules for input, output, and internal resources.

This script reads module specifications and datacenter requirements from CSV files,
formulates an optimization problem for each datacenter specification found,
and uses the PuLP library with the CBC solver to find the optimal number of each module
to maximize/minimize certain resource net values while satisfying input/output constraints,
internal resource balance, and a total area constraint.
"""
import pandas as pd
import pulp
import sys
import numpy as np # Import numpy for unique

# --- Configuration ---
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"
# Standardized unit names for space dimensions and total area
SPACE_X_UNIT = "space_x"
SPACE_Y_UNIT = "space_y"
TOTAL_AREA_UNIT = "total_area"

# --- Resource Categories (Raw Names) ---
# These will be standardized before use
_RAW_INPUT_RESOURCES = ['Price', 'Grid_Connection', 'Water_Connection']
_RAW_OUTPUT_RESOURCES = ['External_Network', 'Data_Storage', 'Processing']
_RAW_INTERNAL_RESOURCES = ['Usable_Power', 'Fresh_Water', 'Distilled_Water', 'Chilled_Water', 'Internal_Network']


# --- Helper Function to Load and Process Data ---
def standardize_unit_name(name):
    """
    Converts a unit name to a standard format: lowercase with underscores.

    Handles potential NaN values.

    Args:
        name: The unit name (string or NaN).

    Returns:
        The standardized unit name as a string, or None if input was NaN.
    """
    if pd.isna(name):
        return None
    return str(name).strip().lower().replace(' ', '_')

# --- Standardized Resource Categories ---
# Apply standardization to the raw lists
INPUT_RESOURCES = {standardize_unit_name(r) for r in _RAW_INPUT_RESOURCES}
OUTPUT_RESOURCES = {standardize_unit_name(r) for r in _RAW_OUTPUT_RESOURCES}
INTERNAL_RESOURCES = {standardize_unit_name(r) for r in _RAW_INTERNAL_RESOURCES}
# Ensure no overlap between categories (optional sanity check)
if INPUT_RESOURCES & OUTPUT_RESOURCES or \
   INPUT_RESOURCES & INTERNAL_RESOURCES or \
   OUTPUT_RESOURCES & INTERNAL_RESOURCES:
    print("Warning: Overlap detected between resource categories after standardization.")
    # You might want to raise an error here depending on requirements


def load_data(modules_path, spec_path):
    """
    Loads module and specification data from CSV files and preprocesses it.

    Standardizes unit names, converts relevant columns to numeric types,
    calculates module area, and structures the data for the optimization problem.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        tuple: A tuple containing:
            - module_data (dict): Dictionary mapping module IDs to their info
              (name, inputs, outputs, area).
            - specs_df (pd.DataFrame): DataFrame containing all processed
              specification rules.
            - module_ids (np.ndarray): Array of unique module IDs.
            - unique_spec_names (np.ndarray): Array of unique specification names
              found in the specs file.
            - spec_limits (dict): Dictionary mapping spec names to their {'space_x': limit, 'space_y': limit}.
    Raises:
        SystemExit: If CSV files cannot be found or read, or if no specifications
                    are found in the spec file.
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

    # *** Standardize Unit Names ***
    modules_df['Unit'] = modules_df['Unit'].apply(standardize_unit_name)
    specs_df['Unit'] = specs_df['Unit'].apply(standardize_unit_name)
    # Drop rows where unit name became None after standardization
    modules_df.dropna(subset=['Unit'], inplace=True)
    specs_df.dropna(subset=['Unit'], inplace=True)

    # --- Process Modules Data ---
    module_data = {}
    module_ids = modules_df['ID'].unique()
    module_names = modules_df.drop_duplicates('ID').set_index('ID')['Name'].to_dict()

    for mod_id in module_ids:
        df_mod = modules_df[modules_df['ID'] == mod_id]

        # Group by Unit and sum amounts for inputs/outputs
        inputs_series = df_mod[df_mod['Is_Input'] == 1].groupby('Unit')['Amount'].sum()
        outputs_series = df_mod[df_mod['Is_Output'] == 1].groupby('Unit')['Amount'].sum()

        inputs = {k: v for k, v in inputs_series.items() if pd.notna(v)}
        outputs = {k: v for k, v in outputs_series.items() if pd.notna(v)}

        # --- Calculate Module Area ---
        # Get Space_X and Space_Y values
        space_x = inputs_series.get(SPACE_X_UNIT, 0)
        space_y = inputs_series.get(SPACE_Y_UNIT, 0)

        area = space_x * space_y
        if area < 0: # Ensure area is non-negative
            print(f"Warning: Module ID {mod_id} has negative space dimensions ({space_x}, {space_y}). Area set to 0.")
            area = 0

        module_data[mod_id] = {
            "name": module_names.get(mod_id, f"Unknown_{mod_id}"),
            "inputs": inputs,
            "outputs": outputs,
            "area": area # Store calculated area
        }
        # Remove space_x and space_y from inputs if they were treated as such
        if SPACE_X_UNIT in module_data[mod_id]["inputs"]:
            del module_data[mod_id]["inputs"][SPACE_X_UNIT]
        if SPACE_Y_UNIT in module_data[mod_id]["inputs"]:
            del module_data[mod_id]["inputs"][SPACE_Y_UNIT]


    # --- Process Spec Data (Load all, identify unique names) ---
    unique_spec_names = specs_df['Name'].unique()
    if len(unique_spec_names) == 0:
        print(f"Error: No specifications found in {spec_path}")
        sys.exit(1)

    # Convert relevant columns to numeric for the entire specs_df
    num_cols_spec = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained', 'Amount']
    for col in num_cols_spec:
         if col in specs_df.columns:
              specs_df[col] = pd.to_numeric(specs_df[col], errors='coerce')
         else:
              print(f"Warning: Column '{col}' not found in {spec_path}")
              specs_df[col] = 0 # Add the column with default 0 if missing

    # Fill NaN in objective/constraint flags with 0 after numeric conversion
    flag_cols = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained']
    for col in flag_cols:
        if col in specs_df.columns:
             specs_df[col] = specs_df[col].fillna(0).astype(int)

    # --- Extract Space Limits per Specification ---
    spec_limits = {}
    for spec_name in unique_spec_names:
        spec_df_filtered = specs_df[(specs_df['Name'] == spec_name) & (specs_df['Below_Amount'] == 1)]
        limit_x_row = spec_df_filtered[spec_df_filtered['Unit'] == SPACE_X_UNIT]
        limit_y_row = spec_df_filtered[spec_df_filtered['Unit'] == SPACE_Y_UNIT]

        limit_x = limit_x_row['Amount'].iloc[0] if not limit_x_row.empty and pd.notna(limit_x_row['Amount'].iloc[0]) else None
        limit_y = limit_y_row['Amount'].iloc[0] if not limit_y_row.empty and pd.notna(limit_y_row['Amount'].iloc[0]) else None

        spec_limits[spec_name] = {'space_x': limit_x, 'space_y': limit_y}
        if limit_x is None:
            print(f"Warning: No valid '{SPACE_X_UNIT}' limit found for specification '{spec_name}'. Area constraint might not be applied.")
        if limit_y is None:
            print(f"Warning: No valid '{SPACE_Y_UNIT}' limit found for specification '{spec_name}'. Area constraint might not be applied.")


    print(f"--- Loaded Data ---")
    print(f"Found {len(module_data)} module types.")
    print(f"Found {len(specs_df)} total spec rules across {len(unique_spec_names)} specifications.")
    print(f"Specifications to solve: {', '.join(unique_spec_names)}")
    print(f"Identified Resource Categories:")
    print(f"  Input: {', '.join(sorted(list(INPUT_RESOURCES)))}")
    print(f"  Output: {', '.join(sorted(list(OUTPUT_RESOURCES)))}")
    print(f"  Internal: {', '.join(sorted(list(INTERNAL_RESOURCES)))}")
    print("-" * 30)

    return module_data, specs_df, module_ids, unique_spec_names, spec_limits


# --- Main Optimization Function ---
def solve_datacenter_config(module_data, target_spec_df, module_ids, target_spec_name, total_area_limit_input):
    """
    Creates and solves the MILP problem for a specific datacenter specification,
    including total area constraints and resource category rules.

    Formulates the objective function and constraints based on the provided
    specification rules, module data, and resource category logic. Solves the
    problem using PuLP and CBC.

    Args:
        module_data (dict): Dictionary mapping module IDs to their info (including 'area').
        target_spec_df (pd.DataFrame): DataFrame filtered for the rules of the
                                       current specification.
        module_ids (np.ndarray): Array of unique module IDs.
        target_spec_name (str): The name of the specification being solved.
        total_area_limit_input (float or None): The pre-calculated maximum total area allowed.

    Returns:
        dict: A dictionary containing the results of the optimization:
            - spec_name (str): The name of the specification.
            - status (str): The solver status ('Optimal', 'Infeasible', etc.).
            - objective_value (float or None): The optimal value of the objective function.
            - selected_modules (list): A list of dictionaries, each representing a
              selected module and its count ({'id', 'name', 'count'}).
            - resource_summary (dict): A dictionary summarizing the total input, output,
              and net amount for each relevant resource unit.
            - total_area_used (float or None): The total area consumed by the selected modules.
            - total_area_limit (float or None): The maximum total area allowed by the constraints, if specified.
            - constraint_verification (list): A list of strings describing the status
              of each applied constraint (e.g., "OK" or "VIOLATED").
    """
    print(f"\n#####  Solving for Specification: {target_spec_name}  #####\n")
    results = {
        "spec_name": target_spec_name,
        "status": "Not Solved",
        "objective_value": None,
        "selected_modules": [],
        "resource_summary": {},
        "total_area_used": None,
        "total_area_limit": total_area_limit_input,
        "constraint_verification": []
    }

    # --- 1. Create the Problem ---
    prob = pulp.LpProblem(f"DataCenter_{target_spec_name}_Area_ResourceRules", pulp.LpMaximize) # Updated problem name

    # --- 2. Define Decision Variables ---
    module_vars = pulp.LpVariable.dicts(
        "Module", module_ids, lowBound=0, cat='Integer'
    )

    # --- 3. Define Objective Function (Applying Resource Rules) ---
    objective = pulp.LpAffineExpression()
    objective_terms_added = 0

    print("Building Objective (Applying Resource Rules):")
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        if unit is None: continue
        if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]: continue # Skip space/area units

        weight = 0
        valid_objective = True

        if row['Maximize'] == 1:
            if unit in INPUT_RESOURCES:
                print(f"  - Warning: Ignoring 'Maximize' for INPUT resource '{unit}'. Input resources can only be minimized.")
                valid_objective = False
            elif unit in INTERNAL_RESOURCES:
                print(f"  - Warning: Ignoring 'Maximize' for INTERNAL resource '{unit}'. Internal resources cannot be in the objective.")
                valid_objective = False
            elif unit in OUTPUT_RESOURCES:
                weight = 1 # Valid: Maximize Output resource
            else: # Uncategorized resource
                print(f"  - Warning: Resource '{unit}' is not categorized. Allowing 'Maximize'.")
                weight = 1
        elif row['Minimize'] == 1:
            if unit in OUTPUT_RESOURCES:
                print(f"  - Warning: Ignoring 'Minimize' for OUTPUT resource '{unit}'. Output resources can only be maximized.")
                valid_objective = False
            elif unit in INTERNAL_RESOURCES:
                print(f"  - Warning: Ignoring 'Minimize' for INTERNAL resource '{unit}'. Internal resources cannot be in the objective.")
                valid_objective = False
            elif unit in INPUT_RESOURCES:
                weight = -1 # Valid: Minimize Input resource
            else: # Uncategorized resource
                 print(f"  - Warning: Resource '{unit}' is not categorized. Allowing 'Minimize'.")
                 weight = -1

        if valid_objective and weight != 0:
            net_unit_expr = pulp.lpSum(
                (module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_vars[mod_id]
                for mod_id in module_ids
            )
            if net_unit_expr:
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective += weight * net_unit_expr
                 objective_terms_added += 1

    if objective_terms_added == 0:
        print("  - Warning: No valid terms were added to the objective function based on resource rules!")
        objective += 0.0 # Dummy objective

    prob += objective, "Overall_Objective"
    print("-" * 30)

    # --- 4. Define Constraints (Applying Resource Rules) ---
    print("Adding Constraints (Applying Resource Rules):")
    constraints_added = 0

    # --- Area Constraint ---
    if total_area_limit_input is not None and total_area_limit_input > 0:
        area_expr = pulp.lpSum(
            module_data[mod_id]['area'] * module_vars[mod_id]
            for mod_id in module_ids if module_data[mod_id]['area'] > 0
        )
        if area_expr:
            constraint = area_expr <= total_area_limit_input
            prob += constraint, f"Limit_{TOTAL_AREA_UNIT}"
            print(f"  - AREA {TOTAL_AREA_UNIT} <= {total_area_limit_input:.2f} (Derived from Space X/Y)")
            constraints_added += 1
        else:
            print(f"  - Skipping Area constraint (no modules have area > 0).")
    else:
        print(f"  - Info: No valid total area limit provided or calculated ({total_area_limit_input}). Area constraint not applied.")

    # --- Constraints from Spec Rules (Applying Resource Rules) ---
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']

        if unit is None or pd.isna(limit):
            if unit: print(f"  - Warning: Skipping constraint for {unit} due to missing limit.")
            continue

        # Skip space/area units here (area handled above, space limits used for area calc)
        if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]:
             continue

        valid_constraint = True
        constraint_type = None # 'Below', 'Above'

        # Below Amount Constraint (Limit on Total Input or Net Consumption)
        if row['Below_Amount'] == 1:
            if unit in OUTPUT_RESOURCES:
                 print(f"  - Warning: Ignoring 'Below_Amount' for OUTPUT resource '{unit}'. Output resources can only have 'Above_Amount'.")
                 valid_constraint = False
            elif unit in INTERNAL_RESOURCES:
                 print(f"  - Warning: Ignoring 'Below_Amount' for INTERNAL resource '{unit}'. Internal resources have fixed balance constraints.")
                 valid_constraint = False
            elif unit in INPUT_RESOURCES:
                 constraint_type = 'Below' # Valid: Limit Input resource
            else: # Uncategorized resource
                 print(f"  - Warning: Resource '{unit}' is not categorized. Allowing 'Below_Amount'.")
                 constraint_type = 'Below'

            if valid_constraint and constraint_type == 'Below':
                # For Input resources, constrain the total input
                input_expr = pulp.lpSum(
                    module_data[mod_id]['inputs'].get(unit, 0) * module_vars[mod_id]
                    for mod_id in module_ids
                )
                if input_expr:
                    constraint = input_expr <= limit
                    prob += constraint, f"Limit_Input_{unit}"
                    print(f"  - INPUT {unit} <= {limit}")
                    constraints_added += 1
                else:
                    print(f"  - Skipping 'Below' constraint for {unit} (no modules consume it).")


        # Above Amount Constraint (Minimum Total Output or Net Production)
        elif row['Above_Amount'] == 1:
            if unit in INPUT_RESOURCES:
                 print(f"  - Warning: Ignoring 'Above_Amount' for INPUT resource '{unit}'. Input resources can only have 'Below_Amount'.")
                 valid_constraint = False
            elif unit in INTERNAL_RESOURCES:
                 print(f"  - Warning: Ignoring 'Above_Amount' for INTERNAL resource '{unit}'. Internal resources have fixed balance constraints.")
                 valid_constraint = False
            elif unit in OUTPUT_RESOURCES:
                 constraint_type = 'Above' # Valid: Require Output resource
            else: # Uncategorized resource
                 print(f"  - Warning: Resource '{unit}' is not categorized. Allowing 'Above_Amount'.")
                 constraint_type = 'Above'

            if valid_constraint and constraint_type == 'Above':
                 # For Output resources, constrain the total output
                 output_expr = pulp.lpSum(
                     module_data[mod_id]['outputs'].get(unit, 0) * module_vars[mod_id]
                     for mod_id in module_ids
                 )
                 if output_expr:
                     constraint = output_expr >= limit
                     prob += constraint, f"Require_Output_{unit}"
                     print(f"  - OUTPUT {unit} >= {limit}")
                     constraints_added +=1
                 else:
                     print(f"  - Skipping 'Above' constraint for {unit} (no modules produce it).")


    # --- Add Internal Resource Balance Constraints (Net >= 0) ---
    print("\nAdding Internal Resource Balance Constraints:")
    internal_constraints_added = 0
    for unit in INTERNAL_RESOURCES:
        net_internal_expr = pulp.lpSum(
            (module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
            * module_vars[mod_id]
            for mod_id in module_ids
        )
        # Only add constraint if the expression is not trivially zero
        # (i.e., if the resource is actually used/produced by some module)
        # Check if the expression has any variables associated with it
        if net_internal_expr is not None and (hasattr(net_internal_expr, 'variables') and net_internal_expr.variables()):
            constraint = net_internal_expr >= 0
            prob += constraint, f"Balance_Internal_{unit}"
            print(f"  - NET INTERNAL {unit} >= 0")
            internal_constraints_added += 1
            constraints_added += 1
        # else:
        #     print(f"  - Skipping internal balance for {unit} (not used/produced by any module).")

    if internal_constraints_added == 0:
        print("  - No internal resource balance constraints added (or needed).")


    if constraints_added == 0:
         print("  - Warning: No constraints were added to the problem!")
    print("-" * 30)

    # --- 5. Solve the Problem ---
    print(f"Solving the MILP problem for {target_spec_name}...")
    solver = pulp.PULP_CBC_CMD(msg=0) # Suppress solver messages
    prob.solve(solver)
    print("-" * 30)

    # --- 6. Process Results ---
    status = pulp.LpStatus[prob.status]
    results["status"] = status

    objective_value = None
    try:
        # Reading objective value might fail if problem is infeasible/unbounded
        objective_value = pulp.value(prob.objective)
    except AttributeError:
        print("  - Could not retrieve objective value (likely due to status).")
    results["objective_value"] = objective_value


    if prob.status == pulp.LpStatusOptimal:
        selected_modules_list = []
        total_inputs = {}
        total_outputs = {}
        total_area = 0.0
        all_units_in_solution = set()

        for mod_id in module_ids:
            count = module_vars[mod_id].varValue
            if count is not None and count > 1e-6:
                int_count = int(round(count))
                if int_count > 0:
                    mod_info = module_data[mod_id]
                    selected_modules_list.append({'id': mod_id, 'name': mod_info['name'], 'count': int_count})

                    for unit, amount in mod_info['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_info['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)

                    total_area += mod_info['area'] * int_count

        results["selected_modules"] = selected_modules_list
        results["total_area_used"] = total_area

        # --- Calculate Resource Totals ---
        resource_summary_dict = {}
        # Include units from spec (that weren't ignored), units from solution, and internal resources
        spec_units_used = set()
        for _, row in target_spec_df.iterrows():
             unit = row['Unit']
             if unit is None: continue
             if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]: continue
             # Check if the constraint/objective for this unit was potentially valid according to rules
             is_input_ok = unit in INPUT_RESOURCES and (row['Below_Amount']==1 or row['Minimize']==1)
             is_output_ok = unit in OUTPUT_RESOURCES and (row['Above_Amount']==1 or row['Maximize']==1)
             is_uncategorized_ok = unit not in INPUT_RESOURCES and unit not in OUTPUT_RESOURCES and unit not in INTERNAL_RESOURCES
             if is_input_ok or is_output_ok or is_uncategorized_ok:
                 spec_units_used.add(unit)

        relevant_units = sorted(list(all_units_in_solution | spec_units_used | INTERNAL_RESOURCES))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
        tolerance = 1e-6

        # --- Verify Area Constraint ---
        if results["total_area_limit"] is not None and results["total_area_limit"] > 0:
            actual_area = total_area
            limit = results["total_area_limit"]
            status_ok = actual_area <= limit + tolerance
            status_str = "OK" if status_ok else "VIOLATED"
            verification_str = f"Area Limit   {TOTAL_AREA_UNIT:<15}: Actual={actual_area:10.2f} <= Limit={limit:10.2f} ({status_str})"
            constraint_verification_list.append(verification_str)

        # --- Verify Constraints from Spec Rules (Only if applied) ---
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            if unit is None or pd.isna(limit): continue
            if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]: continue

            # Verify Below Input Constraints (if it was valid and applied)
            if row['Below_Amount'] == 1 and unit in INPUT_RESOURCES:
                actual_input = total_inputs.get(unit, 0)
                status_ok = actual_input <= limit + tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Below Input  {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)
            elif row['Below_Amount'] == 1 and unit not in INPUT_RESOURCES and unit not in OUTPUT_RESOURCES and unit not in INTERNAL_RESOURCES: # Uncategorized
                actual_input = total_inputs.get(unit, 0) # Assuming Below means input for uncategorized
                status_ok = actual_input <= limit + tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Below Uncat. {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)


            # Verify Above Output Constraints (if it was valid and applied)
            elif row['Above_Amount'] == 1 and unit in OUTPUT_RESOURCES:
                actual_output = total_outputs.get(unit, 0)
                status_ok = actual_output >= limit - tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Above Output {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)
            elif row['Above_Amount'] == 1 and unit not in INPUT_RESOURCES and unit not in OUTPUT_RESOURCES and unit not in INTERNAL_RESOURCES: # Uncategorized
                actual_output = total_outputs.get(unit, 0) # Assuming Above means output for uncategorized
                status_ok = actual_output >= limit - tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Above Uncat. {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)

        # --- Verify Internal Resource Balance Constraints ---
        for unit in INTERNAL_RESOURCES:
             # Check if constraint was actually added (i.e., resource is relevant)
             constraint_name = f"Balance_Internal_{unit}"
             if constraint_name in prob.constraints:
                 net_val = resource_summary_dict.get(unit, {}).get("net", 0)
                 status_ok = net_val >= 0 - tolerance
                 status_str = "OK" if status_ok else "VIOLATED"
                 verification_str = f"Internal Bal {unit:<15}: Actual Net={net_val:10.2f} >= Limit=   0.00 ({status_str})"
                 constraint_verification_list.append(verification_str)


        results["constraint_verification"] = constraint_verification_list

    return results


# --- Encapsulating Function ---
def run_datacenter_optimization(modules_path, spec_path):
    """
    Orchestrates the datacenter optimization process with area constraints and resource rules.

    Loads data using load_data(), iterates through each unique specification found,
    calls solve_datacenter_config() for each, and collects the results.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        list: A list of dictionaries, where each dictionary is the result
              returned by solve_datacenter_config() for a specific specification.
              Returns None if data loading fails.
    """
    all_results = []

    # 1. Load Data
    try:
        module_data, all_specs_df, module_ids, unique_spec_names, spec_limits = load_data(modules_path, spec_path)
    except SystemExit:
        return None
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return None

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()

        if current_spec_df.empty:
            print(f"\nWarning: No valid rules found for specification '{spec_name}'. Skipping.")
            all_results.append({
                "spec_name": spec_name, "status": "Skipped - No Rules",
                "objective_value": None, "selected_modules": [], "resource_summary": {},
                "total_area_used": None, "total_area_limit": None, "constraint_verification": []
            })
            continue

        # Calculate Total Area Limit for this spec
        limits = spec_limits.get(spec_name, {'space_x': None, 'space_y': None})
        limit_x = limits['space_x']
        limit_y = limits['space_y']
        calculated_area_limit = None
        if limit_x is not None and limit_y is not None and limit_x > 0 and limit_y > 0:
            calculated_area_limit = limit_x * limit_y
        else:
            print(f"\nWarning: Cannot calculate area limit for '{spec_name}' due to missing/invalid Space X/Y limits ({limit_x}, {limit_y}).")


        # Solve the problem for the current specification
        try:
            spec_result = solve_datacenter_config(module_data, current_spec_df, module_ids, spec_name, calculated_area_limit)
            all_results.append(spec_result)
        except Exception as e:
             print(f"\nError solving specification '{spec_name}': {e}")
             # Add a result indicating the error
             all_results.append({
                "spec_name": spec_name,
                "status": f"Error - {type(e).__name__}",
                "objective_value": None, "selected_modules": [], "resource_summary": {},
                "total_area_used": None, "total_area_limit": calculated_area_limit, # Store limit even if error
                "constraint_verification": [f"Solver Error: {e}"]
            })


    return all_results



# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Optimization Script (Area Constraint & Resource Rules Version) ---")

    optimization_results = run_datacenter_optimization(MODULES_CSV_PATH, SPEC_CSV_PATH)

    if optimization_results is None:
        print("\n--- Script Exited Due to Data Loading or Critical Errors ---")
        sys.exit(1)

    print("\n\n--- Final Optimization Results ---")

    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        print(f"Status: {result['status']}")

        if result['objective_value'] is not None:
            print(f"Optimal Objective Value = {result['objective_value']:.4f}")
        else:
            if result['status'] not in ["Optimal", "Not Solved", "Skipped - No Rules"] and not result['status'].startswith("Error"):
                 print(f"Objective Value: N/A ({result['status']})")
            elif result['status'].startswith("Error"):
                 print(f"Objective Value: N/A (Solver Error)")
            else: # Not Solved, Skipped, or Optimal but objective was 0/empty
                 print("Objective Value = None (Problem might be infeasible, objective empty, or other solver issue)")


        if result['status'] == 'Optimal':
            print("\nSelected Modules:")
            if result['selected_modules']:
                for mod in result['selected_modules']:
                    print(f"  - {mod['name']} (ID: {mod['id']}): {mod['count']}")
            else:
                print("  (No modules selected - optimal solution might be zero for all)")

            if result['total_area_used'] is not None:
                print(f"\nTotal Area Used: {result['total_area_used']:.2f}")
                if result['total_area_limit'] is not None:
                    limit = result['total_area_limit']
                    used = result['total_area_used']
                    tolerance = 1e-6
                    status_ok = used <= limit + tolerance
                    status_str = "OK" if status_ok else "VIOLATED"
                    print(f"Total Area Limit: {limit:.2f} ({status_str})")
                else:
                    print("Total Area Limit: Not specified or calculated")


            print("\nResulting Resource Summary:")
            if result['resource_summary']:
                for unit in sorted(result['resource_summary'].keys()):
                    res = result['resource_summary'][unit]
                    category = ""
                    if unit in INPUT_RESOURCES: category = "(Input)"
                    elif unit in OUTPUT_RESOURCES: category = "(Output)"
                    elif unit in INTERNAL_RESOURCES: category = "(Internal)"
                    elif unit == TOTAL_AREA_UNIT: category = "(Area)"
                    elif unit in [SPACE_X_UNIT, SPACE_Y_UNIT]: category = "(Space)"
                    else: category = "(Uncategorized)"
                    print(f"  - {unit:<20} {category:<15}: Input={res['input']:10.2f}, Output={res['output']:10.2f}, Net={res['net']:10.2f}")
            else:
                print("  (No resources used or generated)")


            print("\nConstraint Verification:")
            if result['constraint_verification']:
                for line in result['constraint_verification']:
                    print(f"  - {line}")
            else:
                print("  (No constraints to verify or none were active/valid)")

        elif result['status'] == 'Infeasible':
            print("\nDetails: The problem is infeasible. No combination of modules can satisfy all constraints (including area and resource rules). Check warnings during constraint setup.")
        elif result['status'] == 'Unbounded':
            print("\nDetails: The problem is unbounded. The objective can be changed indefinitely (check constraints, objective function, and resource rules).")
        elif result['status'] == 'Skipped - No Rules':
            print("\nDetails: This specification was skipped because no valid rules were found in the input file.")
        elif result['status'].startswith("Error"):
             print(f"\nDetails: An error occurred during solving: {result['constraint_verification'][0] if result['constraint_verification'] else 'Unknown Error'}")
        else: # Other statuses like Not Solved, Undefined
             print(f"\nDetails: Solver finished with status '{result['status']}'. Solution may not be optimal or available.")


        print("=" * (len(result['spec_name']) + 34))

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")