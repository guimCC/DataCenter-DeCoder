import pandas as pd
from collections import defaultdict

# Load the CSV string as if it were a file
csv_text = """ID;Name;Is_Input;Is_Output;Unit;Amount
1;Transformer_100;1;0;Grid_Connection;1
1;Transformer_100;1;0;Space_X;40
1;Transformer_100;1;0;Space_Y;45
1;Transformer_100;1;0;Price;1000
1;Transformer_100;0;1;Usable_Power;100
2;Transformer_1000;1;0;Grid_Connection;1
2;Transformer_1000;1;0;Space_X;100
2;Transformer_1000;1;0;Space_Y;100
2;Transformer_1000;1;0;Price;50000
2;Transformer_1000;0;1;Usable_Power;1000
3;Transformer_5000;1;0;Grid_Connection;1
3;Transformer_5000;1;0;Space_X;200
3;Transformer_5000;1;0;Space_Y;200
3;Transformer_5000;1;0;Price;250000
3;Transformer_5000;0;1;Usable_Power;5000
4;Water_Supply_100;1;0;Water_Connection;1
4;Water_Supply_100;1;0;Space_X;50
4;Water_Supply_100;1;0;Space_Y;50
4;Water_Supply_100;1;0;Price;200
4;Water_Supply_100;0;1;Fresh_Water;100
5;Water_Supply_500;1;0;Water_Connection;1
5;Water_Supply_500;1;0;Space_X;150
5;Water_Supply_500;1;0;Space_Y;100
5;Water_Supply_500;1;0;Price;400
5;Water_Supply_500;0;1;Fresh_Water;500
6;Water_Treatment_50;1;0;Fresh_Water;50
6;Water_Treatment_50;1;0;Usable_Power;50
6;Water_Treatment_50;1;0;Space_X;50
6;Water_Treatment_50;1;0;Space_Y;50
6;Water_Treatment_50;1;0;Price;10000
6;Water_Treatment_50;0;1;Distilled_Water;50
7;Water_Treatment_250;1;0;Fresh_Water;250
7;Water_Treatment_250;1;0;Usable_Power;90
7;Water_Treatment_250;1;0;Space_X;200
7;Water_Treatment_250;1;0;Space_Y;200
7;Water_Treatment_250;1;0;Price;40000
7;Water_Treatment_250;0;1;Distilled_Water;250
8;Water_Treatment_500;1;0;Fresh_Water;500
8;Water_Treatment_500;1;0;Usable_Power;150
8;Water_Treatment_500;1;0;Space_X;400
8;Water_Treatment_500;1;0;Space_Y;400
8;Water_Treatment_500;1;0;Price;70000
8;Water_Treatment_500;0;1;Distilled_Water;500
9;Water_Chiller_100;1;0;Distilled_Water;100
9;Water_Chiller_100;1;0;Usable_Power;500
9;Water_Chiller_100;1;0;Space_X;100
9;Water_Chiller_100;1;0;Space_Y;100
9;Water_Chiller_100;1;0;Price;40000
9;Water_Chiller_100;0;1;Chilled_Water;95
10;Water_Chiller_400;1;0;Distilled_Water;400
10;Water_Chiller_400;1;0;Usable_Power;1500
10;Water_Chiller_400;1;0;Space_X;300
10;Water_Chiller_400;1;0;Space_Y;100
10;Water_Chiller_400;1;0;Price;150000
10;Water_Chiller_400;0;1;Chilled_Water;390
11;Network_Rack_50;1;0;Usable_Power;50
11;Network_Rack_50;1;0;Chilled_Water;5
11;Network_Rack_50;0;1;Internal_Network;50
11;Network_Rack_50;0;1;Fresh_Water;5
11;Network_Rack_50;1;0;Space_X;40
11;Network_Rack_50;1;0;Space_Y;40
11;Network_Rack_50;1;0;Price;2000
12;Network_Rack_100;1;0;Usable_Power;75
12;Network_Rack_100;1;0;Chilled_Water;7
12;Network_Rack_100;0;1;Internal_Network;100
12;Network_Rack_100;0;1;Fresh_Water;7
12;Network_Rack_100;1;0;Space_X;40
12;Network_Rack_100;1;0;Space_Y;40
12;Network_Rack_100;1;0;Price;8000
13;Network_Rack_200;1;0;Usable_Power;95
13;Network_Rack_200;1;0;Chilled_Water;10
13;Network_Rack_200;0;1;Internal_Network;200
13;Network_Rack_200;0;1;Fresh_Water;40
13;Network_Rack_200;1;0;Space_X;40
13;Network_Rack_200;1;0;Space_Y;40
13;Network_Rack_200;1;0;Price;20000
14;Server_Rack_100;1;0;Usable_Power;75
14;Server_Rack_100;1;0;Chilled_Water;15
14;Server_Rack_100;1;0;Internal_Network;10
14;Server_Rack_100;0;1;Distilled_Water;15
14;Server_Rack_100;0;1;Processing;100
14;Server_Rack_100;0;1;External_Network;100
14;Server_Rack_100;1;0;Space_X;40
14;Server_Rack_100;1;0;Space_Y;40
14;Server_Rack_100;1;0;Price;8000
15;Server_Rack_200;1;0;Usable_Power;125
15;Server_Rack_200;1;0;Chilled_Water;25
15;Server_Rack_200;1;0;Internal_Network;18
15;Server_Rack_200;0;1;Distilled_Water;25
15;Server_Rack_200;0;1;Processing;150
15;Server_Rack_200;0;1;External_Network;200
15;Server_Rack_200;1;0;Space_X;40
15;Server_Rack_200;1;0;Space_Y;40
15;Server_Rack_200;1;0;Price;12000
16;Server_Rack_500;1;0;Usable_Power;240
16;Server_Rack_500;1;0;Chilled_Water;50
16;Server_Rack_500;1;0;Internal_Network;32
16;Server_Rack_500;0;1;Distilled_Water;50
16;Server_Rack_500;0;1;Processing;1000
16;Server_Rack_500;0;1;External_Network;400
16;Server_Rack_500;1;0;Space_X;40
16;Server_Rack_500;1;0;Space_Y;40
16;Server_Rack_500;1;0;Price;50000
17;Data_Rack_100;1;0;Usable_Power;15
17;Data_Rack_100;1;0;Chilled_Water;3
17;Data_Rack_100;1;0;Internal_Network;5
17;Data_Rack_100;0;1;Distilled_Water;3
17;Data_Rack_100;0;1;Data_Storage;100
17;Data_Rack_100;1;0;Space_X;40
17;Data_Rack_100;1;0;Space_Y;40
17;Data_Rack_100;1;0;Price;2000
18;Data_Rack_250;1;0;Usable_Power;25
18;Data_Rack_250;1;0;Chilled_Water;3
18;Data_Rack_250;1;0;Internal_Network;10
18;Data_Rack_250;0;1;Distilled_Water;3
18;Data_Rack_250;0;1;Data_Storage;250
18;Data_Rack_250;1;0;Space_X;40
18;Data_Rack_250;1;0;Space_Y;40
18;Data_Rack_250;1;0;Price;7500
19;Data_Rack_500;1;0;Usable_Power;40
19;Data_Rack_500;1;0;Chilled_Water;6
19;Data_Rack_500;1;0;Internal_Network;20
19;Data_Rack_500;0;1;Distilled_Water;6
19;Data_Rack_500;0;1;Data_Storage;500
19;Data_Rack_500;1;0;Space_X;40
19;Data_Rack_500;1;0;Space_Y;40
19;Data_Rack_500;1;0;Price;20500
20;UPS_Small;1;0;Usable_Power;5
20;UPS_Small;1;0;Space_X;30
20;UPS_Small;1;0;Space_Y;30
20;UPS_Small;1;0;Price;15000
20;UPS_Small;0;1;Usable_Power;4.5
20;UPS_Small;0;1;Backup_Power;50
21;UPS_Medium;1;0;Usable_Power;20
21;UPS_Medium;1;0;Space_X;80
21;UPS_Medium;1;0;Space_Y;80
21;UPS_Medium;1;0;Price;55000
21;UPS_Medium;0;1;Usable_Power;18
21;UPS_Medium;0;1;Backup_Power;250
22;Liquid_Cooling_Unit_A;1;0;Distilled_Water;150
22;Liquid_Cooling_Unit_A;1;0;Usable_Power;400
22;Liquid_Cooling_Unit_A;1;0;Space_X;120
22;Liquid_Cooling_Unit_A;1;0;Space_Y;80
22;Liquid_Cooling_Unit_A;1;0;Price;70000
22;Liquid_Cooling_Unit_A;0;1;Chilled_Water;145
22;Liquid_Cooling_Unit_A;0;1;Waste_Heat;500
23;Heat_Recovery_System_Water;1;0;Waste_Heat;1000
23;Heat_Recovery_System_Water;1;0;Usable_Power;20
23;Heat_Recovery_System_Water;1;0;Space_X;150
23;Heat_Recovery_System_Water;1;0;Space_Y;150
23;Heat_Recovery_System_Water;1;0;Price;90000
23;Heat_Recovery_System_Water;0;1;Fresh_Water;10
23;Heat_Recovery_System_Water;0;1;Usable_Power;50
24;Heat_Recovery_System_Power;1;0;Waste_Heat;1500
24;Heat_Recovery_System_Power;1;0;Space_X;200
24;Heat_Recovery_System_Power;1;0;Space_Y;150
24;Heat_Recovery_System_Power;1;0;Price;120000
24;Heat_Recovery_System_Power;0;1;Usable_Power;80
25;Core_Router_HighBW;1;0;Usable_Power;150
25;Core_Router_HighBW;1;0;Space_X;50
25;Core_Router_HighBW;1;0;Space_Y;50
25;Core_Router_HighBW;1;0;Price;120000
25;Core_Router_HighBW;0;1;Internal_Network;500
25;Core_Router_HighBW;0;1;External_Network;200
26;GPU_Rack_Compute;1;0;Usable_Power;2000
26;GPU_Rack_Compute;1;0;Chilled_Water;200
26;GPU_Rack_Compute;1;0;Internal_Network;50
26;GPU_Rack_Compute;1;0;Space_X;40
26;GPU_Rack_Compute;1;0;Space_Y;60
26;GPU_Rack_Compute;1;0;Price;150000
26;GPU_Rack_Compute;0;1;Processing;5000
26;GPU_Rack_Compute;0;1;Waste_Heat;1800
26;GPU_Rack_Compute;0;1;Distilled_Water;200
27;Archive_Storage_Unit;1;0;Usable_Power;10
27;Archive_Storage_Unit;1;0;Space_X;60
27;Archive_Storage_Unit;1;0;Space_Y;80
27;Archive_Storage_Unit;1;0;Price;30000
27;Archive_Storage_Unit;1;0;Internal_Network;5
27;Archive_Storage_Unit;0;1;Data_Storage;2000
28;Water_Chiller_400_Eco;1;0;Distilled_Water;400
28;Water_Chiller_400_Eco;1;0;Usable_Power;1300
28;Water_Chiller_400_Eco;1;0;Space_X;280
28;Water_Chiller_400_Eco;1;0;Space_Y;90
28;Water_Chiller_400_Eco;1;0;Price;135000
28;Water_Chiller_400_Eco;0;1;Chilled_Water;385
28;Water_Chiller_400_Eco;0;1;Waste_Heat;1400
29;Water_Treatment_Advanced;1;0;Fresh_Water;300
29;Water_Treatment_Advanced;1;0;Recycled_Water;100
29;Water_Treatment_Advanced;1;0;Usable_Power;120
29;Water_Treatment_Advanced;1;0;Space_X;250
29;Water_Treatment_Advanced;1;0;Space_Y;250
29;Water_Treatment_Advanced;1;0;Price;60000
29;Water_Treatment_Advanced;0;1;Distilled_Water;380
30;Water_Recycling_Unit;1;0;Distilled_Water;50
30;Water_Recycling_Unit;1;0;Usable_Power;30
30;Water_Recycling_Unit;1;0;Space_X;70
30;Water_Recycling_Unit;1;0;Space_Y;70
30;Water_Recycling_Unit;1;0;Price;25000
30;Water_Recycling_Unit;0;1;Recycled_Water;45
31;Server_Rack_500_Balanced;1;0;Usable_Power;220
31;Server_Rack_500_Balanced;1;0;Chilled_Water;45
31;Server_Rack_500_Balanced;1;0;Internal_Network;30
31;Server_Rack_500_Balanced;1;0;Space_X;40
31;Server_Rack_500_Balanced;1;0;Space_Y;40
31;Server_Rack_500_Balanced;1;0;Price;45000
31;Server_Rack_500_Balanced;0;1;Distilled_Water;45
31;Server_Rack_500_Balanced;0;1;Processing;800
31;Server_Rack_500_Balanced;0;1;External_Network;350
31;Server_Rack_500_Balanced;0;1;Data_Storage;100
31;Server_Rack_500_Balanced;0;1;Waste_Heat;200
32;Network_Firewall_Appliance;1;0;Usable_Power;80
32;Network_Firewall_Appliance;1;0;Internal_Network;10
32;Network_Firewall_Appliance;1;0;External_Network;10
32;Network_Firewall_Appliance;1;0;Space_X;30
32;Network_Firewall_Appliance;1;0;Space_Y;30
32;Network_Firewall_Appliance;1;0;Price;60000
32;Network_Firewall_Appliance;0;1;Internal_Network;10
32;Network_Firewall_Appliance;0;1;External_Network;10
"""  # Truncated for execution - you can load full CSV from file in real usage

# Read into DataFrame
from io import StringIO
df = pd.read_csv(StringIO(csv_text), sep=';')

# Group by ID and Name
modules_dict = defaultdict(lambda: {"id": None, "name": "", "io_fields": []})

for _, row in df.iterrows():
    mod_id = row["ID"]
    name = row["Name"]
    io_field = {
        "is_input": bool(row["Is_Input"]),
        "is_output": bool(row["Is_Output"]),
        "unit": row["Unit"],
        "amount": float(row["Amount"])
    }

    modules_dict[mod_id]["id"] = mod_id
    modules_dict[mod_id]["name"] = name
    modules_dict[mod_id]["io_fields"].append(io_field)

# Convert to list
modules_list = list(modules_dict.values())

import json

# Save to JSON file
json_output_path = "../data/modules.json"
with open(json_output_path, "w") as f:
    json.dump(modules_list, f, indent=4)
