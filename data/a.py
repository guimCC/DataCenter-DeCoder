# Example MILP solution using PuLP
# Install PuLP first: pip install pulp
import pandas as pd
import pulp

# 1. Read input data files
modules = pd.read_csv('Modules.csv')
specs   = pd.read_csv('Data_Center_Spec.csv', sep=';')

print("DEBUG — modules.columns:", modules.columns.tolist())
print("DEBUG — specs.columns:", specs.columns.tolist())

# 2. Aggregate module–resource data
#    Rows: Module ID; Columns: Units; Values: Amount
resource_matrix = (
    modules
    .groupby(['ID','Unit'])['Amount']
    .sum()
    .unstack(fill_value=0)
)
# Map ID → Name for output
module_names = modules[['ID','Name']].drop_duplicates().set_index('ID')['Name']

# 3. Create MILP problem
prob = pulp.LpProblem("DataCenter_Design", pulp.LpMinimize)

# 4. Decision vars: integer count for each module
x = {
    mid: pulp.LpVariable(f"x_{mid}", lowBound=0, cat='Integer')
    for mid in module_names.index
}

# 5. Constraints from specs
for _, row in specs.iterrows():
    res = row['Unit']
    amt = row['Amount']
    # Build linear expression ∑(coeff * x_i)
    coeffs = resource_matrix.get(res, pd.Series())
    expr = pulp.lpSum(coeffs.get(mid,0) * x[mid] for mid in module_names.index)
    if row['Above_Amount'] == 1:
        prob += (expr >= amt), f"Min_{res}"
    if row['Below_Amount'] == 1:
        prob += (expr <= amt), f"Max_{res}"

# 6. Objective: minimize total price
price = resource_matrix.get('Price', pd.Series())
prob += pulp.lpSum(price.get(mid,0) * x[mid] for mid in module_names.index), "Total_Cost"

# 7. Solve
prob.solve()

# 8. Output results
print("Status:", pulp.LpStatus[prob.status])
print("Optimal module counts:")
for mid, var in x.items():
    cnt = var.value()
    if cnt and cnt > 0:
        print(f"  {module_names[mid]}: {int(cnt)}")
print("Total cost: ", pulp.value(prob.objective))
