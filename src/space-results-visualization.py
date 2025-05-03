import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

def visualize_datacenter_modules(modules_data, title="Data Center Module Placement"):
    # Determine grid dimensions
    max_x = max([m['x'] + m['width'] for m in modules_data])
    max_y = max([m['y'] + m['height'] for m in modules_data])
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 12))
    
    # Define colors for each module type
    module_colors = {
        6: '#8B4513',  # Water_Treatment_50 - Brown
        7: '#4682B4',  # Water_Treatment_250 - Steel Blue
        9: '#00CED1',  # Water_Chiller_100 - Dark Turquoise
        10: '#1E90FF', # Water_Chiller_400 - Dodger Blue
        11: '#FF9999',  # Network_Rack_50 - Light Red
        12: '#FF6347',  # Network_Rack_100 - Tomato
        13: '#DC143C',  # Network_Rack_200 - Crimson
        14: '#99FF99',  # Server_Rack_100 - Light Green
        15: '#9999FF',  # Server_Rack_200 - Light Blue
        16: '#FFFF99',  # Server_Rack_500 - Light Yellow
        17: '#FF99FF',  # Data_Rack_100 - Light Purple
        18: '#DDA0DD',  # Data_Rack_250 - Plum
        19: '#9370DB',  # Data_Rack_500 - Medium Purple
    }
    
    # Map IDs to names for legend
    id_to_name = {
        6: 'Water_Treatment_50',
        7: 'Water_Treatment_250',
        9: 'Water_Chiller_100',
        10: 'Water_Chiller_400',
        11: 'Network_Rack_50',
        12: 'Network_Rack_100',
        13: 'Network_Rack_200',
        14: 'Server_Rack_100',
        15: 'Server_Rack_200',
        16: 'Server_Rack_500',
        17: 'Data_Rack_100',
        18: 'Data_Rack_250',
        19: 'Data_Rack_500',
    }
    
    # For legend creation
    legend_handles = []
    legend_labels = []
    
    # Abbreviations for text in cells
    abbreviations = {
        6: 'WT50',
        7: 'WT250',
        9: 'WC100',
        10: 'WC400',
        11: 'NR50',
        12: 'NR100',
        13: 'NR200',
        14: 'SR100',
        15: 'SR200',
        16: 'SR500',
        17: 'DR100',
        18: 'DR250',
        19: 'DR500',
    }
    
    # Draw each module
    for module in modules_data:
        mod_id = module['id']
        color = module_colors.get(mod_id, '#CCCCCC')  # Default gray if ID not found
        
        # Create rectangle patch
        rect = patches.Rectangle(
            (module['x'], module['y']), 
            module['width'], 
            module['height'],
            linewidth=1,
            edgecolor='black',
            facecolor=color,
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Add text label
        ax.text(
            module['x'] + module['width']/2, 
            module['y'] + module['height']/2,
            abbreviations.get(mod_id, 'UNK'),
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=8
        )
        
        # Add to legend if not already added
        if mod_id not in [h.get_label() for h in legend_handles]:
            dummy_patch = patches.Patch(color=color, label=str(mod_id))
            legend_handles.append(dummy_patch)
            legend_labels.append(id_to_name.get(mod_id, f'Unknown-{mod_id}'))
    
    # Set axis limits
    ax.set_xlim(0, max_x)
    ax.set_ylim(0, max_y)
    
    # Invert y-axis to match coordinate system (0,0 at top-left)
    ax.invert_yaxis()
    
    # Add gridlines with automatic tick spacing for x-axis
    # ax.set_xticks(np.arange(0, max_x + 1, 40))
    ax.set_yticks(np.arange(0, max_y + 1, 40))
    ax.grid(True, linestyle='-', linewidth=0.5)
    
    # Set labels and title
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title(title)
    
    # Remove legend
    # ax.legend(legend_handles, legend_labels, loc='upper center', 
    #          bbox_to_anchor=(0.5, -0.05), ncol=4)
    
    plt.tight_layout()
    plt.show()

def parse_modules_from_string(input_string):
    """
    Parse a string with module specifications and return a list of module dictionaries.
    
    Expected input format:
    - Module_Name (ID: X) at (x, y) [W:width, H:height]
    
    Example:
    - Water_Treatment_50 (ID: 6) at (0, 0) [W:50, H:50]
    """
    modules = []
    lines = input_string.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or not line.startswith('-'):
            continue
            
        try:
            # Extract name and ID
            name_id_part = line.split(' at ')[0].strip('- ')
            name = name_id_part.split(' (ID:')[0].strip()
            module_id = int(name_id_part.split('(ID:')[1].split(')')[0].strip())
            
            # Extract position
            position_part = line.split(' at ')[1].split(' [')[0]
            x = int(position_part.strip('()').split(',')[0].strip())
            y = int(position_part.strip('()').split(',')[1].strip())
            
            # Extract dimensions
            dimensions_part = line.split('[')[1].split(']')[0]
            width = int(dimensions_part.split('W:')[1].split(',')[0].strip())
            height = int(dimensions_part.split('H:')[1].strip())
            
            modules.append({
                "name": name,
                "id": module_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height
            })
        except (IndexError, ValueError) as e:
            print(f"Error parsing line: {line}")
            print(f"Error details: {str(e)}")
            continue
    
    return modules

# Example usage:
input_string = """
  - Server_Rack_100 (ID: 14) at (0, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (0, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (40, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (80, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (120, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (160, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 360) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 400) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (200, 440) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 0) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 40) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 80) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 120) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 160) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 200) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 240) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 280) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 320) [W:40, H:40]
  - Server_Rack_200 (ID: 15) at (240, 360) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (240, 400) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (240, 440) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 0) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 40) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 80) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 120) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 160) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 200) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 240) [W:40, H:40]
  - Data_Rack_100 (ID: 17) at (280, 280) [W:40, H:40]
"""
modules = parse_modules_from_string(input_string)
# visualize_datacenter_modules(modules, "Custom Datacenter Configuration")

# Sample modules data - can be replaced with parsed data

# Call the visualization function
visualize_datacenter_modules(modules, "Server_Square Datacenter Configuration")