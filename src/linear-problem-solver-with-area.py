"""
Solves the datacenter module configuration problem using Mixed Integer Linear Programming (MILP),
considering total area constraints.

This script reads module specifications and datacenter requirements from CSV files,
formulates an optimization problem for each datacenter specification found,
and uses the PuLP library with the CBC solver to find the optimal number of each module
to maximize/minimize certain resource net values while satisfying input/output constraints
and a total area constraint.
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
        # Get Space_X and Space_Y values (assuming they are inputs for simplicity, adjust if needed)
        # Use .get() with default 0 in case a module doesn't have space defined
        space_x = inputs_series.get(SPACE_X_UNIT, 0)
        space_y = inputs_series.get(SPACE_Y_UNIT, 0)

        # Alternative: Directly query df_mod if space isn't input/output
        # space_x_row = df_mod[df_mod['Unit'] == SPACE_X_UNIT]
        # space_y_row = df_mod[df_mod['Unit'] == SPACE_Y_UNIT]
        # space_x = space_x_row['Amount'].iloc[0] if not space_x_row.empty else 0
        # space_y = space_y_row['Amount'].iloc[0] if not space_y_row.empty else 0

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
    # Standardize unit names first (already done)
    # specs_df['Unit'] = specs_df['Unit'].apply(standardize_unit_name) # Done above
    # specs_df.dropna(subset=['Unit'], inplace=True) # Done above

    # Get unique specification names
    unique_spec_names = specs_df['Name'].unique()
    if len(unique_spec_names) == 0:
        print(f"Error: No specifications found in {spec_path}")
        sys.exit(1)

    # Convert relevant columns to numeric for the entire specs_df
    num_cols_spec = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained', 'Amount']
    for col in num_cols_spec:
         if col in specs_df.columns:
              # Use errors='coerce' to handle non-numeric values gracefully
              specs_df[col] = pd.to_numeric(specs_df[col], errors='coerce')
         else:
              print(f"Warning: Column '{col}' not found in {spec_path}")
              specs_df[col] = 0 # Add the column with default 0 if missing

    # Fill NaN in objective/constraint flags with 0 after numeric conversion
    flag_cols = ['Below_Amount', 'Above_Amount', 'Minimize', 'Maximize', 'Unconstrained']
    for col in flag_cols:
        if col in specs_df.columns:
             # Fill NaN with 0 and ensure integer type for flags
             specs_df[col] = specs_df[col].fillna(0).astype(int)

    # --- Extract Space Limits per Specification ---
    spec_limits = {}
    for spec_name in unique_spec_names:
        spec_df_filtered = specs_df[(specs_df['Name'] == spec_name) & (specs_df['Below_Amount'] == 1)]
        limit_x_row = spec_df_filtered[spec_df_filtered['Unit'] == SPACE_X_UNIT]
        limit_y_row = spec_df_filtered[spec_df_filtered['Unit'] == SPACE_Y_UNIT]

        # Get the first valid limit found for X and Y for this spec
        limit_x = limit_x_row['Amount'].iloc[0] if not limit_x_row.empty and pd.notna(limit_x_row['Amount'].iloc[0]) else None
        limit_y = limit_y_row['Amount'].iloc[0] if not limit_y_row.empty and pd.notna(limit_y_row['Amount'].iloc[0]) else None

        spec_limits[spec_name] = {'space_x': limit_x, 'space_y': limit_y}
        if limit_x is None:
            print(f"Warning: No valid '{SPACE_X_UNIT}' limit found for specification '{spec_name}'. Area constraint might not be applied.")
        if limit_y is None:
            print(f"Warning: No valid '{SPACE_Y_UNIT}' limit found for specification '{spec_name}'. Area constraint might not be applied.")


    print(f"--- Loaded Data ---")
    print(f"Found {len(module_data)} module types.")
    # Print area for verification
    # for mod_id, data in module_data.items():
    #     print(f"  - Module {mod_id} ({data['name']}): Area = {data['area']:.2f}")
    print(f"Found {len(specs_df)} total spec rules across {len(unique_spec_names)} specifications.")
    print(f"Specifications to solve: {', '.join(unique_spec_names)}")
    print("-" * 30)

    # Return module data, the *full* specs dataframe, module IDs, and unique spec names
    return module_data, specs_df, module_ids, unique_spec_names, spec_limits


# --- Main Optimization Function ---
def solve_datacenter_config(module_data, target_spec_df, module_ids, target_spec_name, total_area_limit_input):
    """
    Creates and solves the MILP problem for a specific datacenter specification,
    including total area constraints.

    Formulates the objective function and constraints based on the provided
    specification rules and module data. Solves the problem using PuLP and CBC.

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
        "total_area_used": None, # Added field for area
        "total_area_limit": total_area_limit_input, # Store the passed-in limit
        "constraint_verification": []
    }

    # --- 1. Create the Problem ---
    prob = pulp.LpProblem(f"DataCenter_{target_spec_name}_Area", pulp.LpMaximize) # Use spec name in problem name

    # --- 2. Define Decision Variables ---
    module_vars = pulp.LpVariable.dicts(
        "Module", module_ids, lowBound=0, cat='Integer'
    )

    # --- 3. Define Objective Function ---
    objective = pulp.LpAffineExpression()
    objective_terms_added = 0 # Counter to check if objective is empty

    print("Building Objective:")
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        if unit is None: continue # Skip if unit name is invalid
        # Skip space/area units in objective, they are usually constraints
        if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]:
            continue

        weight = 0
        if row['Maximize'] == 1:
            weight = 1
        elif row['Minimize'] == 1:
            weight = -1

        if weight != 0:
            # Calculate net contribution expression for this unit across all modules
            net_unit_expr = pulp.lpSum(
                (module_data[mod_id]['outputs'].get(unit, 0) - module_data[mod_id]['inputs'].get(unit, 0))
                * module_vars[mod_id]
                for mod_id in module_ids
            )
            # Only add if the expression is not empty
            if net_unit_expr: # Check if it has terms
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective += weight * net_unit_expr
                 objective_terms_added += 1

    if objective_terms_added == 0:
        print("  - Warning: No terms were added to the objective function!")
        # Add a dummy objective if it's empty to avoid PuLP errors
        objective += 0.0

    prob += objective, "Overall_Objective"
    print("-" * 30)

    # --- 4. Define Constraints ---
    print("Adding Constraints:")
    constraints_added = 0

    # --- NEW: Add Total Area Constraint using the pre-calculated limit ---
    if total_area_limit_input is not None and total_area_limit_input > 0:
        area_expr = pulp.lpSum(
            module_data[mod_id]['area'] * module_vars[mod_id]
            for mod_id in module_ids if module_data[mod_id]['area'] > 0
        )
        # Only add constraint if the expression is not empty
        if area_expr:
            constraint = area_expr <= total_area_limit_input
            prob += constraint, f"Limit_{TOTAL_AREA_UNIT}"
            print(f"  - AREA {TOTAL_AREA_UNIT} <= {total_area_limit_input:.2f} (Derived from Space X/Y)")
            constraints_added += 1
        else:
            print(f"  - Skipping Area constraint (no modules have area > 0).")

    else:
        print(f"  - Info: No valid total area limit provided or calculated ({total_area_limit_input}). Area constraint not applied.")


    # --- Add Standard Input/Output Constraints from Spec Rules ---
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']

        if unit is None or pd.isna(limit):
            if unit:
                 print(f"  - Warning: Skipping constraint for {unit} due to missing limit.")
            continue # Skip if unit name is invalid or limit is missing

        # --- Ignore Space_X/Space_Y/Total_Area Below_Amount constraints here ---
        # They are handled by the pre-calculated limit or ignored.
        if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT] and row['Below_Amount'] == 1:
             # Print info message only if it wasn't the source of the limit
             if unit != SPACE_X_UNIT and unit != SPACE_Y_UNIT:
                 print(f"  - Ignoring explicit constraint for {unit} (handled separately or ignored).")
             continue

        # Below Amount Constraint (Limit on Total Input) - Excluding space/area
        if row['Below_Amount'] == 1: # Already checked unit not in [SPACE_X/Y/AREA]
            input_expr = pulp.lpSum(
                module_data[mod_id]['inputs'].get(unit, 0) * module_vars[mod_id]
                for mod_id in module_ids
            )
            # Only add constraint if the expression is not trivially zero
            if input_expr:
                constraint = input_expr <= limit
                prob += constraint, f"Limit_Input_{unit}"
                print(f"  - INPUT {unit} <= {limit}")
                constraints_added += 1
            else:
                 print(f"  - Skipping 'Below' constraint for {unit} (no modules consume it).")


        # Above Amount Constraint (Minimum Total Output) - Excluding space/area
        elif row['Above_Amount'] == 1 and unit not in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]:
            output_expr = pulp.lpSum(
                module_data[mod_id]['outputs'].get(unit, 0) * module_vars[mod_id]
                for mod_id in module_ids
            )
             # Only add constraint if the expression is not trivially zero
            if output_expr:
                constraint = output_expr >= limit
                prob += constraint, f"Require_Output_{unit}"
                print(f"  - OUTPUT {unit} >= {limit}")
                constraints_added +=1
            else:
                 print(f"  - Skipping 'Above' constraint for {unit} (no modules produce it).")


    # Store the found area limit in results - ALREADY DONE AT INITIALIZATION
    # results["total_area_limit"] = total_area_limit_input

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

    objective_value = pulp.value(prob.objective)
    results["objective_value"] = objective_value


    if prob.status == pulp.LpStatusOptimal:
        selected_modules_list = []
        total_inputs = {}
        total_outputs = {}
        total_area = 0.0 # Initialize total area
        all_units_in_solution = set()

        for mod_id in module_ids:
            count = module_vars[mod_id].varValue
            if count is not None and count > 1e-6: # Use a small tolerance
                int_count = int(round(count))
                if int_count > 0:
                    mod_info = module_data[mod_id]
                    selected_modules_list.append({'id': mod_id, 'name': mod_info['name'], 'count': int_count})

                    # Accumulate resources
                    for unit, amount in mod_info['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_info['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)

                    # Accumulate total area
                    total_area += mod_info['area'] * int_count

        results["selected_modules"] = selected_modules_list
        results["total_area_used"] = total_area # Store calculated area

        # --- Calculate Resource Totals ---
        resource_summary_dict = {}
        # Include units from spec AND units from solution
        spec_units = set(target_spec_df['Unit'].dropna()) - {SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT} # Exclude space/area units here
        relevant_units = sorted(list(all_units_in_solution | spec_units))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        constraint_verification_list = []
        tolerance = 1e-6 # Tolerance for float comparison

        # --- Verify Area Constraint Separately ---
        if results["total_area_limit"] is not None and results["total_area_limit"] > 0:
            actual_area = total_area
            limit = results["total_area_limit"]
            status_ok = actual_area <= limit + tolerance
            status_str = "OK" if status_ok else "VIOLATED"
            verification_str = f"Below Area   {TOTAL_AREA_UNIT:<15}: Actual={actual_area:10.2f} <= Limit={limit:10.2f} ({status_str})"
            constraint_verification_list.append(verification_str)

        # --- Verify Other Constraints from Spec Rules ---
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            if unit is None or pd.isna(limit): continue

            # Skip Area/Space constraints verification here as they are handled above or ignored
            if unit in [SPACE_X_UNIT, SPACE_Y_UNIT, TOTAL_AREA_UNIT]:
                continue

            # Verify Below Input Constraints
            if row['Below_Amount'] == 1:
                actual_input = total_inputs.get(unit, 0)
                status_ok = actual_input <= limit + tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Below Input  {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)


            # Verify Above Output Constraints
            elif row['Above_Amount'] == 1:
                actual_output = total_outputs.get(unit, 0)
                status_ok = actual_output >= limit - tolerance
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Above Output {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)


        results["constraint_verification"] = constraint_verification_list

    return results


# --- Encapsulating Function ---
def run_datacenter_optimization(modules_path, spec_path):
    """
    Orchestrates the datacenter optimization process with area constraints.

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

    # 1. Load Data (including spec limits)
    try:
        # Now unpacks spec_limits as well
        module_data, all_specs_df, module_ids, unique_spec_names, spec_limits = load_data(modules_path, spec_path)
    except SystemExit: # Catch exit from load_data on error
        return None # Indicate failure
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        return None

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        # Filter the specs DataFrame for the current specification
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()

        if current_spec_df.empty:
            print(f"\nWarning: No valid rules found for specification '{spec_name}'. Skipping.")
            # Optionally add a result indicating skipped status
            all_results.append({
                "spec_name": spec_name,
                "status": "Skipped - No Rules",
                "objective_value": None, "selected_modules": [], "resource_summary": {},
                "total_area_used": None, "constraint_verification": []
            })
            continue

        # --- Calculate Total Area Limit for this spec ---
        limits = spec_limits.get(spec_name, {'space_x': None, 'space_y': None})
        limit_x = limits['space_x']
        limit_y = limits['space_y']
        calculated_area_limit = None
        if limit_x is not None and limit_y is not None and limit_x > 0 and limit_y > 0:
            calculated_area_limit = limit_x * limit_y
        else:
            print(f"\nWarning: Cannot calculate area limit for '{spec_name}' due to missing/invalid Space X/Y limits ({limit_x}, {limit_y}).")


        # Solve the problem for the current specification, passing the calculated limit
        try:
            # Pass calculated_area_limit to the solver function
            spec_result = solve_datacenter_config(module_data, current_spec_df, module_ids, spec_name, calculated_area_limit)
            all_results.append(spec_result)
        except Exception as e:
             print(f"\nError solving specification '{spec_name}': {e}")
             # Add a result indicating the error
             all_results.append({
                "spec_name": spec_name,
                "status": f"Error - {type(e).__name__}",
                "objective_value": None, "selected_modules": [], "resource_summary": {},
                "total_area_used": None, "constraint_verification": [f"Solver Error: {e}"]
            })


    return all_results



# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Optimization Script (Area Constraint Version) ---")

    # Run the optimization for all specs
    optimization_results = run_datacenter_optimization(MODULES_CSV_PATH, SPEC_CSV_PATH)

    # Check if optimization ran successfully
    if optimization_results is None:
        print("\n--- Script Exited Due to Data Loading or Critical Errors ---")
        sys.exit(1) # Exit if loading failed

    print("\n\n--- Final Optimization Results ---")

    # Print the results for each specification
    for result in optimization_results:
        print(f"\n========== Results for Specification: {result['spec_name']} ==========")
        print(f"Status: {result['status']}")

        if result['objective_value'] is not None:
            print(f"Optimal Objective Value = {result['objective_value']:.4f}")
        else:
             # Provide more context based on status
            if result['status'] not in ["Optimal", "Not Solved", "Skipped - No Rules"] and not result['status'].startswith("Error"):
                 print(f"Objective Value: N/A ({result['status']})")
            elif result['status'].startswith("Error"):
                 print(f"Objective Value: N/A (Solver Error)")
            else:
                 print("Optimal Objective Value = None (Objective might be empty or solver issue)")


        if result['status'] == 'Optimal':
            print("\nSelected Modules:")
            if result['selected_modules']:
                for mod in result['selected_modules']:
                    print(f"  - {mod['name']} (ID: {mod['id']}): {mod['count']}")
            else:
                print("  (No modules selected - optimal solution might be zero for all)")

            # Print Total Area Used and Limit
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
                    print("Total Area Limit: Not specified in constraints")


            print("\nResulting Resource Summary:")
            if result['resource_summary']:
                # Sort units for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    res = result['resource_summary'][unit]
                    print(f"  - {unit:<20}: Input={res['input']:10.2f}, Output={res['output']:10.2f}, Net={res['net']:10.2f}")
            else:
                print("  (No non-area resources used or generated)")


            print("\nConstraint Verification:")
            if result['constraint_verification']:
                for line in result['constraint_verification']:
                    print(f"  - {line}")
            else:
                print("  (No constraints to verify or none were active)")

        elif result['status'] == 'Infeasible':
            print("\nDetails: The problem is infeasible. No combination of modules can satisfy all constraints (including area).")
        elif result['status'] == 'Unbounded':
            print("\nDetails: The problem is unbounded. The objective can be increased indefinitely (check constraints and objective function).")
        elif result['status'] == 'Skipped - No Rules':
            print("\nDetails: This specification was skipped because no valid rules were found in the input file.")
        elif result['status'].startswith("Error"):
             print(f"\nDetails: An error occurred during solving: {result['constraint_verification'][0] if result['constraint_verification'] else 'Unknown Error'}")
        # Add other statuses if needed

        print("=" * (len(result['spec_name']) + 34)) # Footer line matching header width

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")