"""
Solves the datacenter module configuration problem using Mixed Integer Linear Programming (MILP).

This script reads module specifications and datacenter requirements from CSV files,
formulates an optimization problem for each datacenter specification found,
and uses the PuLP library with the CBC solver to find the optimal number of each module
to maximize/minimize certain resource net values while satisfying input/output constraints.
"""
import pandas as pd
import pulp
import sys
# Removed math import as it wasn't used

# --- Configuration ---
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"


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
    and structures the data for use in the optimization problem.

    Args:
        modules_path (str): Path to the Modules CSV file.
        spec_path (str): Path to the Data Center Specification CSV file.

    Returns:
        tuple: A tuple containing:
            - module_data (dict): Dictionary mapping module IDs to their info
              (name, inputs, outputs).
            - specs_df (pd.DataFrame): DataFrame containing all processed
              specification rules.
            - module_ids (np.ndarray): Array of unique module IDs.
            - unique_spec_names (np.ndarray): Array of unique specification names
              found in the specs file.
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

    # *** Improved Unit Name Standardization ***
    modules_df['Unit'] = modules_df['Unit'].apply(standardize_unit_name)
    specs_df['Unit'] = specs_df['Unit'].apply(standardize_unit_name)
    # Drop rows where unit name became None after standardization (if any)
    modules_df.dropna(subset=['Unit'], inplace=True)
    specs_df.dropna(subset=['Unit'], inplace=True)

    # --- Process Modules Data ---
    module_data = {}
    module_ids = modules_df['ID'].unique()
    module_names = modules_df.drop_duplicates('ID').set_index('ID')['Name'].to_dict()

    for mod_id in module_ids:
        df_mod = modules_df[modules_df['ID'] == mod_id]
        # Group by Unit and sum amounts in case a module has multiple entries for the same unit (shouldn't happen based on data but safer)
        inputs_series = df_mod[df_mod['Is_Input'] == 1].groupby('Unit')['Amount'].sum()
        outputs_series = df_mod[df_mod['Is_Output'] == 1].groupby('Unit')['Amount'].sum()

        inputs = {k: v for k, v in inputs_series.items() if pd.notna(v)}
        outputs = {k: v for k, v in outputs_series.items() if pd.notna(v)}

        module_data[mod_id] = {
            "name": module_names.get(mod_id, f"Unknown_{mod_id}"),
            "inputs": inputs,
            "outputs": outputs
        }

    # --- Process Spec Data (Load all, identify unique names) ---
    # Standardize unit names first
    specs_df['Unit'] = specs_df['Unit'].apply(standardize_unit_name)
    specs_df.dropna(subset=['Unit'], inplace=True) # Drop rows with invalid units after standardization

    # Get unique specification names
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


    print(f"--- Loaded Data ---")
    print(f"Found {len(module_data)} module types.")
    print(f"Found {len(specs_df)} total spec rules across {len(unique_spec_names)} specifications.")
    print(f"Specifications to solve: {', '.join(unique_spec_names)}")
    print("-" * 30)

    # Return module data, the *full* specs dataframe, module IDs, and unique spec names
    return module_data, specs_df, module_ids, unique_spec_names


# --- Main Optimization Function ---
def solve_datacenter_config(module_data, target_spec_df, module_ids, target_spec_name):
    """
    Creates and solves the MILP problem for a specific datacenter specification.

    Formulates the objective function and constraints based on the provided
    specification rules and module data. Solves the problem using PuLP and CBC.

    Args:
        module_data (dict): Dictionary mapping module IDs to their info.
        target_spec_df (pd.DataFrame): DataFrame filtered for the rules of the
                                       current specification.
        module_ids (np.ndarray): Array of unique module IDs.
        target_spec_name (str): The name of the specification being solved.

    Returns:
        dict: A dictionary containing the results of the optimization:
            - spec_name (str): The name of the specification.
            - status (str): The solver status ('Optimal', 'Infeasible', etc.).
            - objective_value (float or None): The optimal value of the objective function.
            - selected_modules (list): A list of dictionaries, each representing a
              selected module and its count ({'id', 'name', 'count'}).
            - resource_summary (dict): A dictionary summarizing the total input, output,
              and net amount for each relevant resource unit.
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
        "constraint_verification": []
    }

    # --- 1. Create the Problem ---
    prob = pulp.LpProblem(f"DataCenter_{target_spec_name}", pulp.LpMaximize) # Use spec name in problem name

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
            # Only add if the expression is not empty (though lpSum handles this)
            if net_unit_expr: # Check if it has terms
                 print(f"  - Adding objective term for unit '{unit}' with weight {weight}")
                 objective += weight * net_unit_expr
                 objective_terms_added += 1

    if objective_terms_added == 0:
        print("  - Warning: No terms were added to the objective function!")
        # Add a dummy objective if it's empty to avoid PuLP errors, though results meaningless
        objective += 0.0

    prob += objective, "Overall_Objective"
    print("-" * 30)

    # --- 4. Define Constraints ---
    print("Adding Constraints:")
    constraints_added = 0
    for _, row in target_spec_df.iterrows():
        unit = row['Unit']
        limit = row['Amount']

        if unit is None: continue # Skip if unit name is invalid

        # Below Amount Constraint (Limit on Total Input)
        if row['Below_Amount'] == 1:
            if pd.notna(limit):
                input_expr = pulp.lpSum(
                    module_data[mod_id]['inputs'].get(unit, 0) * module_vars[mod_id]
                    for mod_id in module_ids
                )
                constraint = input_expr <= limit
                prob += constraint, f"Limit_Input_{unit}" # Use cleaned unit name
                print(f"  - INPUT {unit} <= {limit}")
                constraints_added += 1
            else:
                print(f"  - Warning: Skipping 'Below' constraint for {unit} due to missing limit.")

        # Above Amount Constraint (Minimum Total Output)
        if row['Above_Amount'] == 1:
            if pd.notna(limit):
                output_expr = pulp.lpSum(
                    module_data[mod_id]['outputs'].get(unit, 0) * module_vars[mod_id]
                    for mod_id in module_ids
                )
                constraint = output_expr >= limit
                prob += constraint, f"Require_Output_{unit}" # Use cleaned unit name
                print(f"  - OUTPUT {unit} >= {limit}")
                constraints_added +=1
            else:
                print(f"  - Warning: Skipping 'Above' constraint for {unit} due to missing limit.")

    if constraints_added == 0:
         print("  - Warning: No constraints were added to the problem!")
    print("-" * 30)

    # --- 5. Solve the Problem ---
    print(f"Solving the MILP problem for {target_spec_name}...")
    solver = pulp.PULP_CBC_CMD(msg=0) # Suppress solver messages
    prob.solve(solver)
    print("-" * 30)

    # --- 6. Process Results ---
    # print(f"\n--- Optimization Results for {target_spec_name} ---") # Moved printing outside
    status = pulp.LpStatus[prob.status]
    # print(f"Status: {status}") # Moved printing outside
    results["status"] = status

    objective_value = pulp.value(prob.objective)
    results["objective_value"] = objective_value
    # if objective_value is not None:
    #     print(f"Optimal Objective Value = {objective_value:.4f}") # Moved printing outside
    # else:
    #     print("Optimal Objective Value = None (Objective might be empty or solver issue)") # Moved printing outside


    if prob.status == pulp.LpStatusOptimal:
        # print("\nSelected Modules:") # Moved printing outside
        selected_modules_list = []
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()

        for mod_id in module_ids:
            count = module_vars[mod_id].varValue
            if count is not None and count > 1e-6: # Use a small tolerance
                int_count = int(round(count))
                if int_count > 0:
                    mod_info = module_data[mod_id]
                    # print(f"  - {mod_info['name']} (ID: {mod_id}): {int_count}") # Moved printing outside
                    selected_modules_list.append({'id': mod_id, 'name': mod_info['name'], 'count': int_count}) # Store name too

                    # Accumulate resources
                    for unit, amount in mod_info['inputs'].items():
                        total_inputs[unit] = total_inputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)
                    for unit, amount in mod_info['outputs'].items():
                        total_outputs[unit] = total_outputs.get(unit, 0) + amount * int_count
                        all_units_in_solution.add(unit)

        results["selected_modules"] = selected_modules_list
        # if not selected_modules_list:
        #      print("  (No modules selected - optimal solution might be zero for all)") # Moved printing outside

        # --- Calculate Resource Totals ---
        # print("\nResulting Resource Summary:") # Moved printing outside
        resource_summary_dict = {}
        spec_units = set(target_spec_df['Unit'].dropna())
        relevant_units = sorted(list(all_units_in_solution | spec_units))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            resource_summary_dict[unit] = {"input": inp, "output": outp, "net": net}
            # print(f"  - {unit:<20}: Input={inp:10.2f}, Output={outp:10.2f}, Net={net:10.2f}") # Moved printing outside
        results["resource_summary"] = resource_summary_dict

        # --- Verify Constraints ---
        # print("\nConstraint Verification:") # Moved printing outside
        constraint_verification_list = []
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            if unit is None: continue

            if row['Below_Amount'] == 1 and pd.notna(limit):
                actual_input = total_inputs.get(unit, 0)
                status_ok = actual_input <= limit + 1e-6 # Tolerance for float comparison
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Below Input  {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)
                # print(f"  - {verification_str}") # Moved printing outside

            if row['Above_Amount'] == 1 and pd.notna(limit):
                actual_output = total_outputs.get(unit, 0)
                status_ok = actual_output >= limit - 1e-6 # Tolerance for float comparison
                status_str = "OK" if status_ok else "VIOLATED"
                verification_str = f"Above Output {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})"
                constraint_verification_list.append(verification_str)
                # print(f"  - {verification_str}") # Moved printing outside
        results["constraint_verification"] = constraint_verification_list

    # elif status == 'Infeasible':
    #     print("The problem is infeasible. No combination of modules can satisfy all constraints.") # Moved printing outside
    # elif status == 'Unbounded':
    #     print("The problem is unbounded. The objective can be increased indefinitely (check constraints and objective function).") # Moved printing outside
    # else:
    #     print("Solver finished with a non-optimal status.") # Moved printing outside

    # Add empty lines for separation - handled by the caller now
    # print("\n\n")
    return results


# --- Encapsulating Function ---
def run_datacenter_optimization(modules_path, spec_path):
    """
    Orchestrates the datacenter optimization process.

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

    # 1. Load Data (including all specs and unique names)
    try:
        module_data, all_specs_df, module_ids, unique_spec_names = load_data(modules_path, spec_path)
    except SystemExit: # Catch exit from load_data on error
        return None # Indicate failure

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
                "objective_value": None, "selected_modules": [], "resource_summary": {}, "constraint_verification": []
            })
            continue

        # Solve the problem for the current specification
        spec_result = solve_datacenter_config(module_data, current_spec_df, module_ids, spec_name)
        all_results.append(spec_result)

    return all_results



# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Datacenter Optimization Script ---")

    # Run the optimization for all specs
    optimization_results = run_datacenter_optimization(MODULES_CSV_PATH, SPEC_CSV_PATH)

    # Check if optimization ran successfully
    if optimization_results is None:
        print("\n--- Script Exited Due to Data Loading Errors ---")
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
            if result['status'] not in ["Optimal", "Not Solved", "Skipped - No Rules"]:
                 print(f"Objective Value: N/A ({result['status']})")
            else:
                 print("Optimal Objective Value = None (Objective might be empty or solver issue)")


        if result['status'] == 'Optimal':
            print("\nSelected Modules:")
            if result['selected_modules']:
                for mod in result['selected_modules']:
                    print(f"  - {mod['name']} (ID: {mod['id']}): {mod['count']}")
            else:
                print("  (No modules selected - optimal solution might be zero for all)")

            print("\nResulting Resource Summary:")
            if result['resource_summary']:
                # Sort units for consistent output
                for unit in sorted(result['resource_summary'].keys()):
                    res = result['resource_summary'][unit]
                    print(f"  - {unit:<20}: Input={res['input']:10.2f}, Output={res['output']:10.2f}, Net={res['net']:10.2f}")
            else:
                print("  (No resources used or generated)")


            print("\nConstraint Verification:")
            if result['constraint_verification']:
                for line in result['constraint_verification']:
                    print(f"  - {line}")
            else:
                print("  (No constraints to verify or none were active)")

        elif result['status'] == 'Infeasible':
            print("\nDetails: The problem is infeasible. No combination of modules can satisfy all constraints.")
        elif result['status'] == 'Unbounded':
            print("\nDetails: The problem is unbounded. The objective can be increased indefinitely (check constraints and objective function).")
        elif result['status'] == 'Skipped - No Rules':
            print("\nDetails: This specification was skipped because no valid rules were found in the input file.")
        # Add other statuses if needed

        print("=" * (len(result['spec_name']) + 34)) # Footer line matching header width

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")