# DataCenter-DeCoder

<div align="center">
  <img src="https://raw.githubusercontent.com/username/DataCenter-DeCoder/main/docs/logo.png" alt="DataCenter-DeCoder Logo" width="200" />
  <p><em>Interactive data center design and optimization tool</em></p>
</div>

## 🌟 Project Overview

DataCenter-DeCoder is an interactive tool for designing and optimizing data center configurations. Developed in collaboration with Siemens Energy, this project helps create valid datacenter layouts that satisfy complex constraints and optimize objectives based on available modules like transformers, water supply units, and processors.

## ✨ Features

- **Constraint-based optimization** for data center layout generation
- **Interactive module placement** with drag-and-drop interface
- **Dynamic resource management** for modules and constraints
- **Visualization tools** for data center layouts
- **Support for multiple datacenter types** (Server Square, Dense Storage, Supercomputer)

## 🏛️ Architecture

- **Frontend**: React + TypeScript + Vite
- **Backend**: Python with FastAPI
- **Data Storage**: MongoDB for module and constraint data

## 💾 Data Structure

The project works with two primary data files:

### Modules.csv
Contains specifications for available modules (transformers, water supplies, etc.) with their:
- Resource requirements (inputs)
- Resource production (outputs)
- Space requirements
- Costs

Example:
```
ID;Name;Is_Input;Is_Output;Unit;Amount
1;Transformer_100;1;0;Grid_Connection;1
1;Transformer_100;1;0;Space_X;40
1;Transformer_100;1;0;Space_Y;45
1;Transformer_100;1;0;Price;1000
1;Transformer_100;0;1;Usable_Power;100
```

### Data_Center_Spec.csv
Defines datacenter types with constraints and objectives:
- Resource requirements and limits
- Space constraints
- Optimization goals (minimize/maximize)

Example:
```
ID;Name;Below_Amount;Above_Amount;Minimize;Maximize;Unconstrained;Unit;Amount
1;Server_Square;0;0;0;1;0;External_Network;
1;Server_Square;1;0;0;0;0;Grid_Connection;3
1;Server_Square;1;0;0;0;0;Space_X;1000
```

## 🚀 Installation

### Backend Setup
```bash
pip install fastapi uvicorn pymongo pydantic
pip install motor
pip install pymongo pymongo[srv] python-dotenv
```

Run the backend server:
```bash
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd app/frontend
npm install
```

Run the frontend development server:
```bash
npm run dev
```

## 🎯 Project Goals

Our project aims to:

- Generate valid datacenter configurations that satisfy constraints and optimize objectives
- Support dynamic addition of new modules and resources
- Handle complex, custom constraints and objectives
- Provide an intuitive user interface with:
  - Drag-and-drop module placement
  - Search and recommendation features
  - Visual aesthetics like wires/pipes and hallways
  - Detailed elements such as circuit breakers and control rooms

## 🔮 Future Development

We'll store our module and tabular data in MongoDB.

This is an incremental project with a long-term vision. Beyond the initial valid solution generation, we plan to:

- Place datacenters on geographical maps
- Modify existing setups with new constraints
- Add detailed aesthetics (wires/pipes, hallways, etc.)
- Implement advanced features like circuit breakers, control rooms, and ventilation
- Scale up to more complex environments and goals

## 👥 Team

A team of 4 students with backgrounds in Data Science, AI, and Mathematics, experienced in optimization and machine learning.

## 📸 Screenshots

![Server Square Datacenter](https://raw.githubusercontent.com/username/DataCenter-DeCoder/main/docs/server_square.png)
![Interactive Design Interface](https://raw.githubusercontent.com/username/DataCenter-DeCoder/main/docs/interface.png)

## 📄 License

[MIT](LICENSE)