import re
import csv
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import os

# Define the input string as a constant
DATA_STRING = """
  - Data_Rack_250 (ID: 18): X=0, Y=0 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=40, Y=0 (W=40, H=40)
  - Water_Chiller_400 (ID: 10): X=100, Y=0 (W=300, H=100)
  - Water_Chiller_100 (ID: 9): X=400, Y=0 (W=100, H=100)
  - Network_Rack_100 (ID: 12): X=500, Y=0 (W=40, H=40)
  - Server_Rack_100 (ID: 14): X=540, Y=0 (W=40, H=40)
  - Water_Chiller_100 (ID: 9): X=580, Y=0 (W=100, H=100)
  - Server_Rack_200 (ID: 15): X=680, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=720, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=760, Y=0 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=800, Y=0 (W=40, H=40)
  - Transformer_1000 (ID: 2): X=0, Y=40 (W=100, H=100)
  - Water_Chiller_100 (ID: 9): X=100, Y=100 (W=100, H=100)
  - Network_Rack_50 (ID: 11): X=200, Y=100 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=240, Y=100 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=100 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=320, Y=100 (W=40, H=40)
  - Transformer_5000 (ID: 3): X=360, Y=100 (W=200, H=200)
  - Transformer_1000 (ID: 2): X=0, Y=140 (W=100, H=100)
  - Network_Rack_50 (ID: 11): X=200, Y=140 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=240, Y=140 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=140 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=200, Y=180 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=240, Y=180 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=180 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=320, Y=180 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=100, Y=220 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=140, Y=220 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=180, Y=220 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=220 (W=40, H=40)
  - Water_Supply_100 (ID: 4): X=0, Y=240 (W=50, H=50)
  - Server_Rack_200 (ID: 15): X=240, Y=260 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=260 (W=40, H=40)
  - Water_Treatment_50 (ID: 6): X=0, Y=290 (W=50, H=50)
  - Network_Rack_50 (ID: 11): X=50, Y=300 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=240, Y=300 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=300 (W=40, H=40)
  - Network_Rack_100 (ID: 12): X=0, Y=340 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=40, Y=340 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=80, Y=340 (W=40, H=40)
  - Data_Rack_250 (ID: 18): X=320, Y=340 (W=40, H=40)
  - Network_Rack_50 (ID: 11): X=0, Y=380 (W=40, H=40)
  - Server_Rack_200 (ID: 15): X=280, Y=380 (W=40, H=40)
  - Water_Treatment_50 (ID: 6): X=50, Y=400 (W=50, H=50)
  - Server_Rack_200 (ID: 15): X=0, Y=420 (W=40, H=40)
  - Data_Rack_250 (ID: 18): X=40, Y=450 (W=40, H=40)
  - Data_Rack_250 (ID: 18): X=0, Y=460 (W=40, H=40)
  """

def parse_data_string(data_string):
    """Parse the data string and extract component information."""
    pattern = r"- ([\w_]+) \(ID: (\d+)\): X=(\d+), Y=(\d+) \(W=(\d+), H=(\d+)\)"
    components = []
    
    for line in data_string.strip().split('\n'):
        match = re.search(pattern, line)
        if match:
            name, id_num, x, y, w, h = match.groups()
            components.append({
                'name': name,
                'id': int(id_num),
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h)
            })
    
    return components

def save_to_csv(components, filename="datacenter_layout.csv"):
    """Save the components data to a CSV file."""
    # Create the output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create the full file path
    filepath = os.path.join(output_dir, filename)
    
    # Write the data to CSV
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = ['name', 'id', 'x', 'y', 'width', 'height']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for component in components:
            writer.writerow(component)
            
    return filepath

def visualize_layout(components):
    """Create a visualization of the datacenter layout."""
    # Determine figure size based on the max x and y coordinates
    max_x = max(comp['x'] + comp['width'] for comp in components)
    max_y = max(comp['y'] + comp['height'] for comp in components)
    
    # Create a color map for different component types
    component_types = set(comp['name'].split('_')[0] for comp in components)
    color_map = {
        'Data': 'blue',
        'Network': 'green',
        'Server': 'red',
        'Water': 'cyan',
        'Transformer': 'purple'
    }
    
    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(max_x/100 + 2, max_y/100 + 2))
    
    # Create a legend handles list
    legend_handles = []
    legend_names = []
    
    # Add each component as a rectangle
    for comp in components:
        component_type = comp['name'].split('_')[0]
        color = color_map.get(component_type, 'gray')
        
        # Add the rectangle
        rect = patches.Rectangle(
            (comp['x'], comp['y']),
            comp['width'], comp['height'],
            linewidth=1, edgecolor='black', facecolor=color, alpha=0.7
        )
        ax.add_patch(rect)
        
        # Add the component name in the center of the rectangle
        ax.text(
            comp['x'] + comp['width']/2,
            comp['y'] + comp['height']/2,
            comp['name'],
            ha='center', va='center',
            fontsize=8
        )
        
        # Add to legend if not already added
        if comp['name'] not in legend_names:
            legend_handles.append(patches.Patch(color=color, label=comp['name']))
            legend_names.append(comp['name'])
    
    # Set the axis limits and labels
    ax.set_xlim(-10, max_x + 10)
    ax.set_ylim(-10, max_y + 10)
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title('Data Center Layout')
    
    # Add a grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Add a legend with unique component types
    plt.legend(
        handles=[patches.Patch(color=color, label=ctype) for ctype, color in color_map.items() if ctype in component_types],
        loc='upper right',
        bbox_to_anchor=(1.1, 1)
    )
    
    # Save the figure
    output_dir = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, "datacenter_layout.png"), dpi=300, bbox_inches='tight')
    
    # Show the figure
    plt.tight_layout()
    plt.show()

def main():
    # Parse the data string
    components = parse_data_string(DATA_STRING)
    
    # Save to CSV
    csv_path = save_to_csv(components)
    print(f"Data saved to CSV: {csv_path}")
    
    # Visualize the layout
    visualize_layout(components)

if __name__ == "__main__":
    main()
