// src/components/MainPage.tsx

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  ReactFlowProvider, // Provides context for hooks
  useNodesState,     // Hook to manage node state
  useEdgesState,     // Hook to manage edge state
  useReactFlow,      // Hook to access React Flow instance methods
  Controls,          // Standard zoom/pan controls
  Background,        // Background pattern (dots/lines)
  Node,              // Type for nodes array
  Edge,              // Type for edges array
  NodeDragHandler,   // Type for drag stop handler
  Position,          // Enum for Handle positions (if used)
  Handle,            // Component for connection points (if used)
  Viewport,          // Type for viewport object
} from 'reactflow';
import 'reactflow/dist/style.css'; // Essential React Flow styles

import {
  Box, TextField, Typography, Button, Paper, MenuItem, Select, FormControl, InputLabel
} from '@mui/material'; // Material UI components

// *** IMPORT YOUR ACTUAL TYPES ***
// Make sure this path points correctly to your types file (e.g., '../types')
import { PositionedModule, DataCenter, Module, IOField, SpecRule } from '../types';

// --- Configuration Constants ---
const CELL_SIZE = 10; // Pixel size of one grid cell for layout calculations
const DEFAULT_GRID_DIMENSIONS = { rows: 100, cols: 100 }; // Fallback grid size
const BOUNDARY_NODE_ID = 'grid-boundary-node'; // Unique ID for the boundary node

// --- Module Styling Helpers (Defined Outside Component) ---
// Color mapping for different module types
const MODULE_COLORS = {
    transformer: '#E9DA54', water_supply: '#2196f3', water_treatment: '#03a9f4',
    water_chiller: '#00bcd4', network_rack: '#ff9800', server_rack: '#4caf50',
    data_rack: '#9c27b0', default: '#757575'
};
// Determines the type category based on the module name
const getModuleType = (name: string): keyof typeof MODULE_COLORS => {
  const lowerName = name?.toLowerCase() || ''; // Use nullish coalescing for safety
  if (lowerName.startsWith('transformer')) return 'transformer';
  if (lowerName.includes('network_rack')) return 'network_rack';
  if (lowerName.includes('server_rack')) return 'server_rack';
  if (lowerName.includes('data_rack')) return 'data_rack';
  if (lowerName.includes('water_supply')) return 'water_supply';
  if (lowerName.includes('water_treatment')) return 'water_treatment';
  if (lowerName.includes('water_chiller')) return 'water_chiller';
  return 'default'; // Fallback type
};
// Gets the background color for a module
const getModuleColor = (moduleName: string) => MODULE_COLORS[getModuleType(moduleName)] || MODULE_COLORS.default;
// Gets the path to the sprite image (ensure '/sprites/' is correct relative to your public folder)
const getSpritePath = (moduleName: string) => `/sprites/${getModuleType(moduleName)}.png`;


// --- Custom Node Components ---

// Component for Module Nodes
interface ModuleNodeData {
  module: PositionedModule; // The data associated with the node
  widthPx: number;         // Calculated width in pixels
  heightPx: number;        // Calculated height in pixels
}
const ModuleNode: React.FC<{ data: ModuleNodeData; id: string; selected: boolean }> = React.memo(({ data, selected }) => {
  const { module, widthPx, heightPx } = data;
  // Defensive check in case module data is somehow invalid
  if (!module) {
      console.error("ModuleNode received invalid data:", data);
      return <Box sx={{width: widthPx, height: heightPx, backgroundColor: 'red', border: '1px solid white', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 9}}>Data Error</Box>;
  }
  const color = getModuleColor(module.name);
  const spritePath = getSpritePath(module.name);

  // Main container for the node visual
  return (
    <Box sx={{
        width: `${widthPx}px`, height: `${heightPx}px`, backgroundColor: color, borderRadius: 1,
        border: selected ? '3px solid white' : `1px solid rgba(255, 255, 255, 0.4)`, // Highlight when selected
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
        padding: '4px', position: 'relative', boxShadow: selected ? '0 0 10px rgba(255, 255, 255, 0.6)' : '0 2px 5px rgba(0,0,0,0.3)',
        transition: 'border 0.15s ease-out, box-shadow 0.15s ease-out', fontSize: '10px', color: 'white',
        overflow: 'hidden', cursor: 'grab', '&:active': { cursor: 'grabbing' }, // Cursors for dragging
    }}>
      {/* Module Image */}
      <Box component="img" src={spritePath} alt={module.name} sx={{
          maxWidth: '70%', maxHeight: '65%', objectFit: 'contain', filter: 'brightness(1.1)',
          pointerEvents: 'none', mb: '2px', // Prevent image interfering with drag
      }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}/>
       {/* Module Name Label */}
       <Typography variant="caption" sx={{
           textAlign: 'center', pointerEvents: 'none', overflow: 'hidden', textOverflow: 'ellipsis',
           whiteSpace: 'nowrap', width: '95%', lineHeight: 1.2, fontWeight: 'medium',
       }}>{module.name || 'Unnamed'}</Typography>
    </Box>
  );
});
ModuleNode.displayName = 'ModuleNode'; // Helps in React DevTools debugging

// Component for the Grid Boundary Node
interface BoundaryNodeData {
    widthPx: number;
    heightPx: number;
}
const BoundaryNode: React.FC<{ data: BoundaryNodeData }> = React.memo(({ data }) => {
    const { widthPx, heightPx } = data;
    // Renders a non-interactive dashed box representing the grid limits
    return (
        <Box
            sx={{
                width: `${widthPx}px`,
                height: `${heightPx}px`,
                border: '8px dashed rgba(255, 255, 255, 0.4)', // Visual style of the boundary
                backgroundColor: 'transparent', // No fill
                borderRadius: '4px',
                // Critical: Prevent this node from interfering with mouse events
                pointerEvents: 'none',
                boxSizing: 'border-box', // Ensure border is included in width/height
            }}
        />
    );
});
BoundaryNode.displayName = 'BoundaryNode';

// ***** Define nodeTypes CONSTANT AT THE TOP LEVEL *****
// Maps string identifiers used in node objects to the actual React components.
// Includes the new boundary node type.
const nodeTypes = {
  moduleNode: ModuleNode,
  boundaryNode: BoundaryNode,
};


// --- Main Page Component Definition ---
const MainPage = () => {
  // --- State Management ---
  const [constraints, setConstraints] = useState({ maxPrice: '', maxSpaceX: '', maxSpaceY: '' });
  const [datacenters, setDatacenters] = useState<DataCenter[]>([]);
  const [selectedDC, setSelectedDC] = useState<number | "">("");
  const [currentZoom, setCurrentZoom] = useState<number>(1);
  const [resultModules, setResultModules] = useState<PositionedModule[]>([]); // Canonical data source

  // React Flow State Hooks
  const [nodes, setNodes, onNodesChange] = useNodesState<ModuleNodeData | BoundaryNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useReactFlow<ModuleNodeData | BoundaryNodeData, Edge>();

  // Memoized calculation of grid dimensions in pixels based on constraints
  const gridPixelDimensions = useMemo(() => ({
    width: (parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols) * CELL_SIZE,
    height: (parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows) * CELL_SIZE,
  }), [constraints.maxSpaceX, constraints.maxSpaceY]);

  // --- Data Fetching Effect ---
  // Fetches the list of datacenters when the component first mounts
  useEffect(() => {
    console.log("Effect: Fetching datacenters...");
    let isMounted = true;
    fetch("http://localhost:8000/datacenters") // Replace with your API endpoint
      .then(res => {
          if (!res.ok) { throw new Error(`Fetch error! status: ${res.status}`); }
          return res.json();
      })
      .then((data: DataCenter[]) => {
          if (isMounted) {
              console.log(`Effect: Datacenters received: ${data?.length ?? 0}`);
              setDatacenters(data || []);
          }
      })
      .catch(err => console.error("Effect: Failed to fetch datacenters:", err));
    return () => { isMounted = false; console.log("Effect: Cleanup fetch datacenters."); };
  }, []); // Empty dependency array ensures it runs only once

  // --- Data Transformation Function ---
  // Converts the `resultModules` array into React Flow `Node` objects for modules
  const transformModulesToNodes = useCallback((modules: PositionedModule[]): Node<ModuleNodeData>[] => {
    console.log(`Transforming ${modules?.length ?? 0} modules to nodes...`);
    const moduleNodes: Node<ModuleNodeData>[] = [];
    if (!Array.isArray(modules)) return moduleNodes;

    const usedIds = new Set<string>();
    modules.forEach((mod, index) => {
      if (!mod || typeof mod.id === 'undefined' || mod.id === null) {
          console.warn(`Skipping module at index ${index} due to missing data or ID.`);
          return;
      }
      const uniqueNodeId = `mod_${mod.id}_${index}`; // Create unique ID for RF
      if (usedIds.has(uniqueNodeId)) {
           console.warn(`Duplicate Node ID generated: ${uniqueNodeId}. Skipping.`); return;
      }
      usedIds.add(uniqueNodeId);
      const widthCells = mod.width ?? 1; const heightCells = mod.height ?? 1;
      const widthPx = widthCells * CELL_SIZE; const heightPx = heightCells * CELL_SIZE;
      const gridCol = mod.gridColumn ?? 1; const gridRow = mod.gridRow ?? 1;
      const posX = (gridCol - 1) * CELL_SIZE; const posY = (gridRow - 1) * CELL_SIZE;
      moduleNodes.push({
        id: uniqueNodeId, type: 'moduleNode', position: { x: posX, y: posY },
        data: { module: mod, widthPx, heightPx }, draggable: true, zIndex: 1, // Ensure modules are above boundary
      });
    });
    console.log(`Transformation resulted in ${moduleNodes.length} module nodes.`);
    return moduleNodes;
  }, []); // Callback depends only on constant CELL_SIZE

  // --- State Synchronization Effect ---
  // Updates the React Flow `nodes` state whenever `resultModules` or `gridPixelDimensions` change
  useEffect(() => {
    console.log("Effect: resultModules or grid dimensions changed, updating nodes...");

    // 1. Generate nodes for the modules
    const moduleNodes = transformModulesToNodes(resultModules);

    // 2. Create the grid boundary node if dimensions are valid
    let boundaryNode: Node<BoundaryNodeData> | null = null;
    if (gridPixelDimensions.width > 0 && gridPixelDimensions.height > 0) {
        boundaryNode = {
            id: BOUNDARY_NODE_ID,
            type: 'boundaryNode',
            // Position slightly offset so border appears correctly at 0,0
            position: { x: -1, y: -1 },
            data: {
                // Add border width compensation to pixel dimensions
                widthPx: gridPixelDimensions.width + 2,
                heightPx: gridPixelDimensions.height + 2,
            },
            draggable: false,     // Not draggable
            selectable: false,    // Not selectable
            zIndex: -1,           // Render behind everything else
        };
    }

    // 3. Combine module nodes and the boundary node (if created)
    const allNodes = boundaryNode ? [...moduleNodes, boundaryNode] : moduleNodes;

    console.log(`Setting ${allNodes.length} total nodes (Modules: ${moduleNodes.length}). Boundary ${boundaryNode ? 'included' : 'excluded'}.`);
    setNodes(allNodes); // Update the combined node list for React Flow

    // 4. Adjust Viewport (Fit or Reset) - Logic remains the same
     if (moduleNodes.length > 0) {
        const fitViewTimeout = setTimeout(() => {
            if (reactFlowInstance) {
                console.log("Effect: Fitting view...");
                try {
                    reactFlowInstance.fitView({ padding: 0.25, duration: 300, includeHiddenNodes: true });
                    setCurrentZoom(reactFlowInstance.getViewport().zoom);
                } catch (error) { console.error("Error during fitView:", error); }
            }
        }, 150);
        return () => clearTimeout(fitViewTimeout);
    } else {
        const resetTimeout = setTimeout(() => {
            if (reactFlowInstance) {
                console.log("Effect: No nodes, resetting viewport.");
                try {
                    reactFlowInstance.setViewport({ x: 0, y: 0, zoom: 1 });
                    setCurrentZoom(1);
                } catch (error) { console.error("Error during setViewport:", error); }
            }
        }, 150);
        return () => clearTimeout(resetTimeout);
    }
  // This effect depends on the module data and the calculated grid dimensions
  }, [resultModules, gridPixelDimensions, transformModulesToNodes, setNodes, reactFlowInstance]);

  // --- Event Handlers ---

  // Handles constraint input changes
  const handleChange = (field: string, value: string) => {
    setConstraints(prev => ({ ...prev, [field]: value.replace(/[^0-9.]/g, '') }));
  };

  // Handles "Design" button click (fetch solved layout)
  const handleDesign = () => {
    console.log("Handling Design button click...");
    fetch("http://localhost:8000/solve-dummy", { // Replace with your solve endpoint
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ /* ... constraints ... */ })
    })
    .then(res => { if (!res.ok) throw new Error(`Solve error: ${res.status}`); return res.json(); })
    .then((data: { modules?: PositionedModule[] }) => {
        const modules = data?.modules || [];
        console.log(`Received ${modules.length} modules from design solve.`);
        const processedModules: PositionedModule[] = modules
            .filter(m => m != null && m.id != null)
            .map((m, index) => ({
                ...m, id: `design_${m.id}_${index}`, // Unique ID
                // Provide defaults if solve endpoint doesn't guarantee position/size
                gridColumn: m.gridColumn ?? 1, gridRow: m.gridRow ?? 1,
                width: m.width ?? 1, height: m.height ?? 1,
                io_fields: m.io_fields ?? [],
            }));
        setResultModules(processedModules);
    })
    .catch(err => console.error("Design fetch/process failed:", err));
  };

  // Handles selection from the "Load Datacenter" dropdown
  const handleDCSelect = (dcId: number | "") => {
    console.log(`Handling DC Select change: ${dcId}`);
    setSelectedDC(dcId);
    if (dcId === "") {
        setResultModules([]); setConstraints({ maxPrice: '', maxSpaceX: '', maxSpaceY: ''}); return;
    }
    const selected: DataCenter | undefined = datacenters.find(dc => dc.id === dcId);
    if (selected) {
      console.log(`Selected datacenter (ID: ${dcId}): ${selected.name}`);
      const spaceXRule = selected.specs?.find(spec => spec.Unit?.toLowerCase() === "space_x");
      const spaceYRule = selected.specs?.find(spec => spec.Unit?.toLowerCase() === "space_y");
      const priceRule = selected.specs?.find(spec => spec.Unit?.toLowerCase() === "price");
      const spaceXCells = spaceXRule?.Amount ? Math.ceil(spaceXRule.Amount) : DEFAULT_GRID_DIMENSIONS.cols;
      const spaceYCells = spaceYRule?.Amount ? Math.ceil(spaceYRule.Amount) : DEFAULT_GRID_DIMENSIONS.rows;
      const maxPrice = priceRule?.Amount?.toString() || "";
      setConstraints({ maxPrice: maxPrice, maxSpaceX: spaceXCells.toString(), maxSpaceY: spaceYCells.toString() });

      if (Array.isArray(selected.modules)) {
          const processedModules: PositionedModule[] = selected.modules
              .filter(m => m != null && m.id != null)
              .map((m, index) => ({ ...m, id: `dc_${selected.id}_${m.id}_${index}` })); // Unique ID
           const validMods = processedModules.filter(mod => { // Filter based on DC bounds
                const gCol=mod.gridColumn +1; const gRow=mod.gridRow + 1; const w=mod.width??1; const h=mod.height??1;
                return gCol > 0 && gRow > 0 && (gCol + w - 1) <= spaceXCells && (gRow + h - 1) <= spaceYCells;
           });
           console.log(`Setting ${validMods.length} valid modules from DC ${selected.id}.`);
           setResultModules(validMods);
      } else { console.warn(`No valid modules array for DC ${selected.id}`); setResultModules([]); }
    } else { console.warn(`DC with ID ${dcId} not found.`); setResultModules([]); setConstraints({ maxPrice: '', maxSpaceX: '', maxSpaceY: ''}); }
  }

  // Handles node drag stop: Snaps node to grid, checks bounds and collisions
  const onNodeDragStop: NodeDragHandler = useCallback((event, draggedNode) => {
    // Ignore event if it's for the boundary node
    if (draggedNode.id === BOUNDARY_NODE_ID || !draggedNode.data) return;

    const uniqueDraggedNodeId = draggedNode.id;
    console.log(`Node Drag Stop: ${uniqueDraggedNodeId}`);
    const nodesCopy = reactFlowInstance.getNodes();

    // --- 1. Calculate Snapped Position ---
    const snappedX = Math.round(draggedNode.position.x / CELL_SIZE) * CELL_SIZE;
    const snappedY = Math.round(draggedNode.position.y / CELL_SIZE) * CELL_SIZE;
    console.log(`  Original Pos: (${draggedNode.position.x.toFixed(1)}, ${draggedNode.position.y.toFixed(1)}), Snapped: (${snappedX}, ${snappedY})`);

    // --- 2. Boundary Checks (using SNAPPED position) ---
    const nodeWidth = (draggedNode.data as ModuleNodeData).widthPx; // Type assertion needed here
    const nodeHeight = (draggedNode.data as ModuleNodeData).heightPx;
    const maxX = gridPixelDimensions.width; const maxY = gridPixelDimensions.height;
    const withinBounds = snappedX >= 0 && snappedY >= 0 && (snappedX + nodeWidth) <= maxX && (snappedY + nodeHeight) <= maxY;

    // --- 3. Collision Detection (using SNAPPED position) ---
    let collision = false;
    if (withinBounds) {
        for (const otherNode of nodesCopy) {
            if (otherNode.id === uniqueDraggedNodeId || otherNode.id === BOUNDARY_NODE_ID) continue;
            if (!otherNode.position || !(otherNode.data as ModuleNodeData)?.widthPx || !(otherNode.data as ModuleNodeData)?.heightPx) continue;
            const otherX=otherNode.position.x; const otherY=otherNode.position.y;
            const otherW=(otherNode.data as ModuleNodeData).widthPx; const otherH=(otherNode.data as ModuleNodeData).heightPx;
            const xOverlap = snappedX < otherX + otherW && (snappedX + nodeWidth) > otherX;
            const yOverlap = snappedY < otherY + otherH && (snappedY + nodeHeight) > otherY;
            if (xOverlap && yOverlap) { collision = true; break; }
        }
    }

    // --- 4. Update State or Revert ---
    if (withinBounds && !collision) {
      console.log(`  Drop Valid. Updating state with SNAPPED position.`);
      setNodes((nds) => nds.map((n) => n.id === uniqueDraggedNodeId ? { ...n, position: { x: snappedX, y: snappedY } } : n));
      setResultModules((prevModules) => prevModules.map(mod =>
            mod.id === uniqueDraggedNodeId
            ? { ...mod, gridColumn: (snappedX / CELL_SIZE) + 1, gridRow: (snappedY / CELL_SIZE) + 1 }
            : mod
          )
      );
    } else {
      console.warn(`  Drop Invalid. Bounds: ${withinBounds}, Collision: ${collision}. Reverting visual.`);
      setNodes((nds) => [...nds]); // Trigger re-render to snap back visually
    }
  }, [reactFlowInstance, setNodes, gridPixelDimensions, setResultModules]); // Dependencies

  // Handles viewport change event (e.g., after zoom/pan stops)
  const handleViewportChange = useCallback((viewport: Viewport | undefined) => {
      if (viewport && typeof viewport.zoom === 'number') {
          setCurrentZoom(viewport.zoom); // Update displayed zoom level
      }
  }, []); // No dependencies needed

  // --- Memoized UI Elements (Legend and Constraints Panels) ---

  // Memoized Legend Panel
  const ModuleLegendElement = useMemo(() => {
    // *** FULL moduleTypes Array Definition ***
    const moduleTypes = [
     { name: 'transformer', displayName: 'Transformer' },
     { name: 'water_supply', displayName: 'Water Supply' },
     { name: 'water_treatment', displayName: 'Water Treatment' },
     { name: 'water_chiller', displayName: 'Water Chiller' },
     { name: 'network_rack', displayName: 'Network Rack' },
     { name: 'server_rack', displayName: 'Server Rack' },
     { name: 'data_rack', displayName: 'Data Rack' },
     { name: 'default', displayName: 'Other' }, // Fallback for uncategorized modules
   ];
   // ****************************************

    return (
      <Paper elevation={3} sx={{
        p: 1.5,
        width: 180,
        backgroundColor: 'rgba(32, 20, 52, 0.9)',
        position: 'absolute', // Position relative to the React Flow container Box
        right: 16,            // Distance from right edge
        top: 16,             // Distance from top edge
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
        zIndex: 10,          // Ensure it's above React Flow elements
      }}>
        <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mb: 1 }}>
          Legend
        </Typography>
        {/* Iterate over the defined module types to create legend items */}
        {moduleTypes.map((type) => (
          <Box key={type.name} sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
            {/* Display the module sprite */}
            <Box
              component="img"
              // Use the helper function to get the correct sprite path
              src={getSpritePath(type.name)}
              alt={type.displayName}
              sx={{
                width: 20, // Consistent small image size
                height: 20,
                mr: 1,
                objectFit: 'contain', // Ensure sprite fits well
                filter: 'brightness(1.1)', // Slight brightness increase
              }}
              // Hide the image element if the sprite fails to load
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            {/* Display the module type name */}
            <Typography variant="caption" sx={{ color: 'white', fontWeight: 'medium' }}>
              {type.displayName}
            </Typography>
          </Box>
        ))}
      </Paper>
    );
  // The content of the legend is static based on the hardcoded moduleTypes array,
  // so the dependency array is empty. It only needs to compute once.
  }, []); // Empty dependency array

  // Memoized Constraints Status Panel
  const ConstraintsPanelElement = useMemo(() => {
    // Calculate totals... (same logic as before using resultModules)
    const totals = resultModules.reduce((acc, mod) => { /* ... calculation logic ... */ return acc; }, { price: 0, power: 0, cooling: 0, processing: 0, maxX: 0, maxY: 0 });
    const maxPriceNum = parseFloat(constraints.maxPrice) || Infinity;
    // ... other max values and checks ...
    const formatConstraint = (v: number, m: number) => {/* ... */}; const getPercentage = (v: number, m: number) => {/* ... */};
    return (
      <Paper elevation={3} sx={{
        p: 1.5, width: 220, backgroundColor: 'rgba(32, 20, 52, 0.9)',
        position: 'absolute', left: 16, top: 16, // Positioned top-left
        border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2, zIndex: 10,
      }}>
        {/* ... Panel content using totals, constraints, formatters ... */}
        <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mb: 1.5 }}>Status</Typography>
        {/* ... Bars for Price, Space X, Space Y ... */}
        {/* ... Production totals ... */}
      </Paper>
    );
  }, [resultModules, constraints]); // Depends on data


  // --- Component Render ---
  return (
    <Box sx={{
        height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column',
        alignItems: 'center', paddingTop: '1rem', paddingBottom: '1rem',
        gap: 1, backgroundColor: '#201434', overflow: 'hidden',
    }}>
      {/* Header Controls */}
      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', width: '95%', justifyContent: 'center', flexWrap: 'wrap', mb: 1 }}>
         <FormControl size="small" sx={{ minWidth: 180, mb: { xs: 1, md: 0 } }}>
            <InputLabel id="dc-select-label" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Load Datacenter</InputLabel>
            <Select labelId="dc-select-label" label="Load Datacenter" value={selectedDC} onChange={(e) => handleDCSelect(e.target.value as number | "")} sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' }, '& .MuiSvgIcon-root': { color: 'rgba(255, 255, 255, 0.7)' } }} MenuProps={{ PaperProps: { sx: { bgcolor: '#332a4f', color: 'white', border: '1px solid rgba(255,255,255,0.2)' } } }}>
                <MenuItem value=""><em>-- Clear Selection --</em></MenuItem>
                {datacenters.map(dc => (<MenuItem key={dc.id} value={dc.id}>{dc.name}</MenuItem>))}
            </Select>
         </FormControl>
         <TextField size="small" label="Max Price" value={constraints.maxPrice} onChange={(e) => handleChange('maxPrice', e.target.value)} type="text" inputMode='numeric' variant="outlined" InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }} InputProps={{ sx: { color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' } } }} sx={{ mb: { xs: 1, md: 0 }, width: 120 }} />
         <TextField size="small" label="Max X (Cells)" value={constraints.maxSpaceX} onChange={(e) => handleChange('maxSpaceX', e.target.value)} type="text" inputMode='numeric' variant="outlined" InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }} InputProps={{ sx: { color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' } } }} sx={{ mb: { xs: 1, md: 0 }, width: 120 }} />
         <TextField size="small" label="Max Y (Cells)" value={constraints.maxSpaceY} onChange={(e) => handleChange('maxSpaceY', e.target.value)} type="text" inputMode='numeric' variant="outlined" InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }} InputProps={{ sx: { color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' } } }} sx={{ mb: { xs: 1, md: 0 }, width: 120 }} />
         <Button size="medium" variant="contained" onClick={handleDesign} sx={{ height: '40px', mb: { xs: 1, md: 0 } }}>Design</Button>
      </Box>

      {/* React Flow Area Container */}
      <Box sx={{
          width: '95%', height: '100%', minHeight: '400px',
          position: 'relative', // For overlay positioning
          border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2,
          overflow: 'hidden', backgroundColor: '#281f3d',
      }}>
        <ReactFlow
            nodes={nodes} // Includes modules + boundary node
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop} // Implements snapping
            onMoveEnd={handleViewportChange}
            nodeTypes={nodeTypes} // Includes custom module and boundary nodes
            defaultViewport={{ x: 0, y: 0, zoom: 0.75 }}
            minZoom={0.05} maxZoom={4}
            fitViewOptions={{ padding: 0.25, duration: 300 }}
            nodesDraggable={true} selectNodesOnDrag={true}
            proOptions={{ hideAttribution: true }}
            style={{ width: '100%', height: '100%' }}
          >
          <Controls showInteractive={false}/>
          <Background variant="dots" gap={CELL_SIZE} size={1.5} color="#443a5f" />
        </ReactFlow>

        {/* Overlays: Legend and Constraints Panel */}
        {/* Conditionally render based on whether modules exist */}
        {resultModules.length > 0 && ModuleLegendElement}
        {resultModules.length > 0 && ConstraintsPanelElement}

        {/* Bottom Status Indicator Bar */}
        <Box sx={{
            position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 10,
            padding: '4px 12px', backgroundColor: 'rgba(0,0,0,0.75)', color: 'rgba(255,255,255,0.8)',
            borderRadius: 1, fontSize: '0.75rem', display: 'flex', gap: 2, alignItems: 'center', whiteSpace: 'nowrap',
        }}>
           <Typography variant="caption">Grid: {constraints.maxSpaceX || '?'}×{constraints.maxSpaceY || '?'} Cells</Typography>
           <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
           <Typography variant="caption">Zoom: {(currentZoom ?? 1).toFixed(2)}x</Typography>
           <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
           {/* Display count of actual module nodes, excluding the boundary */}
           <Typography variant="caption">Nodes: {nodes.filter(n => n.id !== BOUNDARY_NODE_ID).length}</Typography>
        </Box>
      </Box>
    </Box>
  );
};

// Wrap MainPage with ReactFlowProvider to enable hook usage
const MainPageWrapper = () => (
  <ReactFlowProvider>
    <MainPage />
  </ReactFlowProvider>
);

export default MainPageWrapper;

// --- src/types.ts (Example - Ensure your file matches this structure) ---
/*
export interface IOField {
    is_input: boolean;
    is_output?: boolean; // Make optional if not always present
    unit: string;
    amount: number;
}

export interface Module {
    id: string; // Expect string ID from backend
    name: string;
    io_fields: IOField[];
}

export interface PositionedModule extends Module {
    gridColumn: number;
    gridRow: number;
    height: number; // In cells
    width: number;  // In cells
}

export interface SpecRule {
    Below_Amount?: number;
    Above_Amount?: number;
    Minimize?: number;
    Maximize?: number;
    Unconstrained?: number;
    Unit: string; // The key identifier (e.g., "space_x", "price")
    Amount?: number; // The value associated with the unit (e.g., 1000, 50000)
}

export interface DataCenter {
    id: number;
    name: string;
    specs: SpecRule[]; // Array of constraint rules
    details?: Record<string, number>; // Optional key-value details
    modules: PositionedModule[]; // Expects modules to have position info from backend
}
*/