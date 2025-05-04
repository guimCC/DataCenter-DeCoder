import csv
import os
from collections import defaultdict
from solver_utils_list import _solve_module_list
from models import Module, IOField # Changed import source

# --- Define file paths relative to this script ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), '../data') # Go up one level to 'app' then into 'data'
MODULES_CSV_PATH = os.path.join(DATA_DIR, 'Modules.csv')
SPECS_CSV_PATH = os.path.join(DATA_DIR, 'Data_Center_Spec.csv')

# --- 1. Load Modules from CSV ---
print(f"Loading modules from: {MODULES_CSV_PATH}")
modules_raw_data = defaultdict(lambda: {'name': None, 'io_fields': []})
try:
    with open(MODULES_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                mod_id = int(row['ID'])
                if modules_raw_data[mod_id]['name'] is None:
                    modules_raw_data[mod_id]['name'] = row['Name']

                modules_raw_data[mod_id]['io_fields'].append(
                    IOField(
                        is_input=bool(int(row['Is_Input'])),
                        is_output=bool(int(row['Is_Output'])),
                        unit=str(row['Unit']),
                        amount=float(row['Amount'])
                    )
                )
            except (ValueError, KeyError, TypeError) as e:
                print(f"Warning: Skipping row due to error ({e}): {row}")
                continue # Skip malformed rows

except FileNotFoundError:
    print(f"Error: Modules CSV file not found at {MODULES_CSV_PATH}")
    exit()
except Exception as e:
    print(f"Error reading Modules CSV: {e}")
    exit()


available_modules = [
    Module(id=mod_id, name=data['name'], io_fields=data['io_fields'])
    for mod_id, data in modules_raw_data.items()
]
print(f"Loaded {len(available_modules)} module types.")

# --- 2. Load Specs from CSV (Example: Using Spec ID 1) ---
TARGET_SPEC_ID = 1
print(f"Loading specs for ID {TARGET_SPEC_ID} from: {SPECS_CSV_PATH}")
specs = []
try:
    with open(SPECS_CSV_PATH, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                if int(row['ID']) == TARGET_SPEC_ID:
                    # Handle potential None/empty string for Amount
                    amount_str = row.get('Amount', '').strip()
                    amount_val = float(amount_str) if amount_str and amount_str != '-1' else None # Treat -1 or empty as None

                    specs.append({
                        "Unit": str(row['Unit']),
                        "Below_Amount": int(row['Below_Amount']),
                        "Above_Amount": int(row['Above_Amount']),
                        "Minimize": int(row['Minimize']),
                        "Maximize": int(row['Maximize']),
                        "Unconstrained": int(row['Unconstrained']),
                        "Amount": amount_val
                    })
            except (ValueError, KeyError, TypeError) as e:
                 print(f"Warning: Skipping spec row due to error ({e}): {row}")
                 continue # Skip malformed rows

except FileNotFoundError:
    print(f"Error: Specs CSV file not found at {SPECS_CSV_PATH}")
    exit()
except Exception as e:
    print(f"Error reading Specs CSV: {e}")
    exit()

print(f"Loaded {len(specs)} spec rules for ID {TARGET_SPEC_ID}.")


# --- 3. Define Sample Weights ---
# Relative importance of objectives (adjust as needed based on loaded specs)
# These might need adjustment depending on which spec ID you load
weights = {
    "external_network": 1.0, # From Spec ID 1
    "data_storage": 1.0,     # From Spec ID 1
    "processing": 1.0,       # From Spec ID 1
    "price": 1.0,            # From Spec ID 1
    "total_area": 0.1        # Example weight if minimizing area
}
print(f"Using weights: {weights}")

# --- 4. Call the Function ---
print("--- Running Test ---")
selected_counts, net_resources = _solve_module_list(available_modules, specs, weights)

# --- 5. Print Results ---
print("\n--- Test Results ---")
if selected_counts:
    print("Selected Module Counts:")
    for mod_id, count in selected_counts.items():
        # Find module name for better readability
        mod_name = next((m.name for m in available_modules if m.id == mod_id), "Unknown")
        print(f"  Module ID {mod_id} ({mod_name}): {count}")

    print("\nNet Resources:")
    for resource, value in net_resources.items():
        print(f"  {resource}: {value:.2f}")

    # Example Assertion (Optional - for automated testing)
    # You would calculate the expected outcome manually or based on a known good run
    # expected_counts = {2: 2} # Example: Expect 2 Server Racks
    # assert selected_counts == expected_counts, f"Expected {expected_counts}, but got {selected_counts}"
    # print("\nAssertion Passed (Example)")

else:
    print("Solver did not find a feasible/optimal solution or returned empty.")

print("\n--- Test Complete ---")

