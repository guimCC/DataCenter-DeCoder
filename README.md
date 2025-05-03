# DataCenter-DeCoder
The project is in collaboration with Siemens Energy, who provided us with detailed information about various modules—such as transformers, water supply units, and processors. Each module has several inputs and outputs, which are associated with specific units.

**Here’s an example of the module data:**

* Modules.csv:

ID;Name;Is_Input;Is_Output;Unit;Amount
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

* Data_Center_Spec.csv

ID;Name;Below_Amount;Above_Amount;Minimize;Maximize;Unconstrained;Unit;Amount

1;Server_Square;0;0;0;1;0;External_Network;
1;Server_Square;1;0;0;0;0;Grid_Connection;3
1;Server_Square;1;0;0;0;0;Water_Connection;1
1;Server_Square;1;0;0;0;0;Space_X;1000
1;Server_Square;1;0;0;0;0;Space_Y;500
1;Server_Square;0;1;0;0;0;Data_Storage;1000
1;Server_Square;0;1;0;0;0;Processing;1000
1;Server_Square;1;0;0;0;0;Price;1000000

2;Dense_Storage;0;0;0;0;1;Grid_Connection;
2;Dense_Storage;0;0;0;0;1;Water_Connection;
2;Dense_Storage;0;0;1;0;0;Space_X;
2;Dense_Storage;0;0;1;0;0;Space_Y;
2;Dense_Storage;0;0;0;1;0;Data_Storage;
2;Dense_Storage;1;0;0;0;0;Price;5000000

3;Supercomputer;0;0;0;0;1;Grid_Connection;
3;Supercomputer;0;0;0;0;1;Water_Connection;
3;Supercomputer;0;0;1;0;0;Usable_Power;
3;Supercomputer;0;0;0;1;0;Processing;
3;Supercomputer;1;0;0;0;0;Space_X;2000
3;Supercomputer;1;0;0;0;0;Space_Y;1000



## DataCenter Specifications
We are also provided with a set of objectives and constraints for designing a data center. These cover units such as:

external_network

grid_connections

water_connection

space_x / space_y

data_storage

processing

price

Each unit can be associated with constraints or goals like:

below_amount

above_amount

minimize

maximize

Goals
Our initial goal is to build a system that generates valid datacenter configurations that satisfy the constraints and optimize the given objectives based on the available modules.

But it’s not just about solving a static optimization problem. We also want:

The ability to add new modules and resources dynamically

Support for complex, custom constraints/objectives

A rich and intuitive user interface, with:

Drag-and-drop module placement

Search and recommendation features

Visual aesthetics like wires/pipes, hallways, power/cooling separation

Details such as circuit breakers, control rooms, maintenance access, ventilation

Tech & Team
We are a team of 4 students with backgrounds in Data Science, AI, and Mathematics. We have experience in optimization and machine learning. Our main language is Python, and we want to use tools as close to Python as possible.

We’ll store our module and tabular data in MongoDB.

Long-term Vision
This is an incremental project. The first step is to generate a valid solution, which is relatively easy. But we want to build it in a scalable way, so that we can later:

Place datacenters on a map

Modify an existing setup with new constraints

Scale up to more complex environments and goals

# Requirements
**Backend:**
- `pip install fastapi uvicorn pymongo pydantic`
- `pip install motor`
- `pip install pymongo pymongo[srv] python-dotenv`

Run with: `uvicorn main:app --reload --port 8000`

**Frontend:

Run with: `npm run dev`