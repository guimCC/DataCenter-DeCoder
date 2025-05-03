import pandas as pd
import pulp
import sys
import math

# --- Configuration ---
# TARGET_DATACENTER_SPEC_NAME = "Server_Square" # Removed - will iterate through all specs
MODULES_CSV_PATH = "data/Modules.csv"
SPEC_CSV_PATH = "data/Data_Center_Spec.csv"

# --- Helper Function to Load and Process Data ---
def standardize_unit_name(name):
    """Converts unit name to a standard format: lowercase, underscore."""
    if pd.isna(name):
        return None
    return str(name).strip().lower().replace(' ', '_')

def load_data(modules_path, spec_path):
    """Loads data from CSVs and preprocesses it."""
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
    """Creates and solves the MILP problem for a specific datacenter spec."""

    print(f"\n#####  Solving for Specification: {target_spec_name}  #####\n")

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
    solver = pulp.PULP_CBC_CMD(msg=0)
    prob.solve(solver)
    print("-" * 30)

    # --- 6. Process and Print Results ---
    print(f"\n--- Optimization Results for {target_spec_name} ---")
    status = pulp.LpStatus[prob.status]
    print(f"Status: {status}")

    # *** Check Objective Value Before Formatting ***
    objective_value = pulp.value(prob.objective)
    if objective_value is not None:
        print(f"Optimal Objective Value = {objective_value:.4f}")
    else:
        print("Optimal Objective Value = None (Objective might be empty or solver issue)")


    if prob.status == pulp.LpStatusOptimal:
        # (Rest of the result processing logic remains the same)
        print("\nSelected Modules:")
        selected_modules = []
        total_inputs = {}
        total_outputs = {}
        all_units_in_solution = set()

        for mod_id in module_ids:
            count = module_vars[mod_id].varValue
            if count is not None and count > 1e-6:
                int_count = int(round(count))
                if int_count > 0:
                    mod_info = module_data[mod_id]
                    print(f"  - {mod_info['name']} (ID: {mod_id}): {int_count}")
                    selected_modules.append({'id': mod_id, 'count': int_count, 'info': mod_info})

        if not selected_modules:
             print("  (No modules selected - optimal solution might be zero for all)")

        # --- Calculate and Print Resource Totals ---
        print("\nResulting Resource Summary:")
        for selection in selected_modules:
            mod_id = selection['id']
            count = selection['count']
            mod_info = selection['info']
            for unit, amount in mod_info['inputs'].items():
                total_inputs[unit] = total_inputs.get(unit, 0) + amount * count
                all_units_in_solution.add(unit)
            for unit, amount in mod_info['outputs'].items():
                total_outputs[unit] = total_outputs.get(unit, 0) + amount * count
                all_units_in_solution.add(unit)

        spec_units = set(target_spec_df['Unit'].dropna())
        relevant_units = sorted(list(all_units_in_solution | spec_units))

        for unit in relevant_units:
            inp = total_inputs.get(unit, 0)
            outp = total_outputs.get(unit, 0)
            net = outp - inp
            print(f"  - {unit:<20}: Input={inp:10.2f}, Output={outp:10.2f}, Net={net:10.2f}")

        # --- Verify Constraints ---
        print("\nConstraint Verification:")
        for _, row in target_spec_df.iterrows():
            unit = row['Unit']
            limit = row['Amount']
            if unit is None: continue

            if row['Below_Amount'] == 1 and pd.notna(limit):
                actual_input = total_inputs.get(unit, 0)
                status_ok = actual_input <= limit + 1e-6 # Tolerance for float comparison
                status_str = "OK" if status_ok else "VIOLATED"
                print(f"  - Below Input  {unit:<15}: Actual={actual_input:10.2f} <= Limit={limit:10.2f} ({status_str})")

            if row['Above_Amount'] == 1 and pd.notna(limit):
                actual_output = total_outputs.get(unit, 0)
                status_ok = actual_output >= limit - 1e-6 # Tolerance for float comparison
                status_str = "OK" if status_ok else "VIOLATED"
                print(f"  - Above Output {unit:<15}: Actual={actual_output:10.2f} >= Limit={limit:10.2f} ({status_str})")


    elif status == 'Infeasible':
        print("The problem is infeasible. No combination of modules can satisfy all constraints.")
    elif status == 'Unbounded':
        print("The problem is unbounded. The objective can be increased indefinitely (check constraints and objective function).")
    else:
        print("Solver finished with a non-optimal status.")

    # Add empty lines for separation
    print("\n\n") # Add a couple of empty lines after processing each spec

# --- Main Execution Block ---
if __name__ == "__main__":
    # 1. Load Data (including all specs and unique names)
    module_data, all_specs_df, module_ids, unique_spec_names = load_data(MODULES_CSV_PATH, SPEC_CSV_PATH)

    # 2. Iterate through each specification and solve
    for spec_name in unique_spec_names:
        # Filter the specs DataFrame for the current specification
        current_spec_df = all_specs_df[all_specs_df['Name'] == spec_name].copy()

        if current_spec_df.empty:
            print(f"\nWarning: No valid rules found for specification '{spec_name}'. Skipping.")
            continue

        # Solve the problem for the current specification
        solve_datacenter_config(module_data, current_spec_df, module_ids, spec_name)

    print("\n--- All Specifications Processed ---")
    print("\n--- Script Finished ---")