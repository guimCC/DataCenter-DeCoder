import pandas as pd
import pulp

# 1) Load data
modules = pd.read_csv("Modules.csv", sep=";")
specs   = pd.read_csv("Data_Center_Spec.csv", sep=";")

# 2) Build parameter dictionaries
#    For each module i and resource j, get net contribution a[i,j]
a = (
    modules
    .assign(Sign=1)  # every row contributes positively to its Unit
    .pivot_table(index="ID", columns="Unit", values="Amount", aggfunc="sum")
    .fillna(0)
    .astype(float)
    .to_dict(orient="index")
)

module_ids = list(a.keys())
units      = set(u for d in a.values() for u in d)

def solve_for(block_name, verbose=True):
    """Builds and solves the LP for one spec block (Name == block_name)."""
    # filter the spec for this block
    block = specs.query("Name == @block_name")
    if block.empty:
        raise ValueError(f"No spec found for Name = {block_name!r}")

    # 3) Create LP
    prob = pulp.LpProblem(f"DataCenterDesign_{block_name}", pulp.LpMinimize)

    # decision vars
    x = {i: pulp.LpVariable(f"x_{i}", lowBound=0, cat="Integer")
         for i in module_ids}

    # 4) Objective: minimize total cost
    prob += pulp.lpSum(a[i].get("Price", 0) * x[i] for i in module_ids), "TotalCost"

    # 5) Add resource constraints
    for _, row in block.iterrows():
        unit = row.Unit
        lhs = pulp.lpSum(a[i].get(unit, 0) * x[i] for i in module_ids)
        
        # Check if Amount is defined and not NaN
        has_amount = pd.notna(row.Amount)
        
        # Add constraints based on flags
        if row.Above_Amount == 1 and has_amount:
            prob += lhs >= row.Amount, f"{unit}_min_{row.Amount}"
        
        if row.Below_Amount == 1 and has_amount:
            prob += lhs <= row.Amount, f"{unit}_max_{row.Amount}"
        
        # Handle Minimize/Maximize flags
        if row.Minimize == 1:
            # For minimization, add the term to the objective with a small weight
            # We use a small weight to prioritize cost minimization
            prob.objective += 0.001 * lhs
            
        if row.Maximize == 1:
            # For maximization, subtract the term from the objective with a small weight
            prob.objective -= 0.001 * lhs

    # 6) Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # 7) Collect results
    status = pulp.LpStatus[prob.status]
    solution = {i: int(x[i].value()) for i in module_ids if x[i].value() > 0}
    total_cost = pulp.value(prob.objective)

    if verbose:
        print(f"--- Spec Block: {block_name} ---")
        print(f"Status: {status}")
        print("Selected modules:")
        for i, qty in solution.items():
            print(f"  Module {i}: {qty} copies")
        print(f"Total cost: {total_cost:,.0f}\n")

    return {"status": status, "solution": solution, "total_cost": total_cost}

# Or solve for every block automatically:
results = {}
for name in specs['Name'].unique():
    results[name] = solve_for(name, verbose=True)
