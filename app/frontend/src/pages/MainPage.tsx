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
  ReactFlowInstance, // Import for type safety
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
const DEFAULT_GRID_DIMENSIONS = { rows: 100, cols: 200 }; // Fallback grid size if constraints missing
const BOUNDARY_NODE_ID = 'grid-boundary-node'; // Unique ID for the boundary node

// --- Module Styling Helpers (Defined Outside Component) ---
const MODULE_COLORS = {
    transformer: '#E9DA54', water_supply: '#2196f3', water_treatment: '#03a9f4',
    water_chiller: '#00bcd4', network_rack: '#ff9800', server_rack: '#4caf50',
    data_rack: '#9c27b0', default: '#757575'
};
const getModuleType = (name: string): keyof typeof MODULE_COLORS => {
  const lowerName = name?.toLowerCase() || '';
  if (lowerName.startsWith('transformer')) return 'transformer';
  if (lowerName.includes('network_rack')) return 'network_rack';
  if (lowerName.includes('server_rack')) return 'server_rack';
  if (lowerName.includes('data_rack')) return 'data_rack';
  if (lowerName.includes('water_supply')) return 'water_supply';
  if (lowerName.includes('water_treatment')) return 'water_treatment';
  if (lowerName.includes('water_chiller')) return 'water_chiller';
  return 'default';
};
const getModuleColor = (moduleName: string) => MODULE_COLORS[getModuleType(moduleName)] || MODULE_COLORS.default;
const getSpritePath = (moduleName: string) => `/sprites/${getModuleType(moduleName)}.png`;


// --- Custom Node Components ---

// Component for Module Nodes (No Name Displayed)
interface ModuleNodeData {
  module: PositionedModule;
  widthPx: number;
  heightPx: number;
}
const ModuleNode: React.FC<{ data: ModuleNodeData; id: string; selected: boolean }> = React.memo(({ data, selected }) => {
  const { module, widthPx, heightPx } = data;
  if (!module) {
      return ( <Box sx={{width: widthPx||40, height: heightPx||40, backgroundColor:'red', border:'1px solid white', color:'white', display:'flex', alignItems:'center', justifyContent:'center', fontSize:9, borderRadius:1}}>Data Err</Box> );
  }
  const color = getModuleColor(module.name);
  const spritePath = getSpritePath(module.name);
  return (
    <Box sx={{
        width: `${widthPx}px`, height: `${heightPx}px`, backgroundColor: color, borderRadius: 1,
        border: selected ? '3px solid white' : `1px solid rgba(255, 255, 255, 0.4)`,
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
        padding: '4px', position: 'relative', boxShadow: selected ? '0 0 10px rgba(255, 255, 255, 0.6)' : '0 2px 5px rgba(0,0,0,0.3)',
        transition: 'border 0.15s ease-out, box-shadow 0.15s ease-out',
        overflow: 'hidden', cursor: 'grab', '&:active': { cursor: 'grabbing' },
        boxSizing: 'border-box',
    }}>
      <Box component="img" src={spritePath} alt={module.name || 'Module Image'} sx={{
          maxWidth: '85%', maxHeight: '85%', objectFit: 'contain',
          filter: 'brightness(1.1)', pointerEvents: 'none',
      }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}/>
      {/* No Typography component here to display the name */}
    </Box>
  );
});
ModuleNode.displayName = 'ModuleNode';

// Component for the Grid Boundary Node
interface BoundaryNodeData {
    widthPx: number;
    heightPx: number;
}
const BoundaryNode: React.FC<{ data: BoundaryNodeData }> = React.memo(({ data }) => {
    const { widthPx, heightPx } = data;
    return (
        <Box sx={{
                width: `${widthPx}px`, height: `${heightPx}px`,
                border: '8px dashed rgba(255, 255, 255, 0.4)', // Thicker boundary
                backgroundColor: 'transparent', borderRadius: '4px',
                pointerEvents: 'none', boxSizing: 'border-box',
            }} />
    );
});
BoundaryNode.displayName = 'BoundaryNode';

// Define nodeTypes CONSTANT AT THE TOP LEVEL
const nodeTypes = {
  moduleNode: ModuleNode,
  boundaryNode: BoundaryNode,
};


// --- Main Page Component Definition ---
const MainPage = () => {
  // --- State ---
  const [constraints, setConstraints] = useState({ maxPrice: '', maxSpaceX: '', maxSpaceY: '' });
  const [datacenters, setDatacenters] = useState<DataCenter[]>([]);
  const [selectedDC, setSelectedDC] = useState<number | "">("");
  const [currentZoom, setCurrentZoom] = useState<number>(1);
  const [resultModules, setResultModules] = useState<PositionedModule[]>([]); // Canonical data

  // RF State
  const [nodes, setNodes, onNodesChange] = useNodesState<ModuleNodeData | BoundaryNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useReactFlow<ModuleNodeData | BoundaryNodeData, Edge>();

  // Calculate grid dimensions
  const gridPixelDimensions = useMemo(() => ({
    width: (parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols) * CELL_SIZE,
    height: (parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows) * CELL_SIZE,
  }), [constraints.maxSpaceX, constraints.maxSpaceY, CELL_SIZE]); // Include CELL_SIZE

  // --- Effects ---

  // Fetch Datacenters on Mount
  useEffect(() => {
    console.log("Effect: Fetching datacenters...");
    let isMounted = true;
    fetch("http://localhost:8000/datacenters") // Replace with your API endpoint
      .then(res => { if (!res.ok) throw new Error(`Fetch error! status: ${res.status}`); return res.json(); })
      .then((data: DataCenter[]) => { if (isMounted) { setDatacenters(data || []); } })
      .catch(err => console.error("Effect: Failed to fetch datacenters:", err));
    return () => { isMounted = false; };
  }, []);

  // --- Data Transformation (Initial Node Structure) ---
  // Calculates initial node properties but DOES NOT set final position here.
  const transformModulesToNodes = useCallback((modules: PositionedModule[]): Node<ModuleNodeData>[] => {
    const moduleNodes: Node<ModuleNodeData>[] = [];
    if (!Array.isArray(modules)) return moduleNodes;
    const usedIds = new Set<string>();
    modules.forEach((mod, index) => {
      if (!mod || typeof mod.id === 'undefined' || mod.id === null) return;
      const uniqueNodeId = `mod_${mod.id}_${index}`;
      if (usedIds.has(uniqueNodeId)) return;
      usedIds.add(uniqueNodeId);
      const widthCells = mod.width ?? 1; const heightCells = mod.height ?? 1;
      const widthPx = widthCells * CELL_SIZE; const heightPx = heightCells * CELL_SIZE;
      const gridCol = mod.gridColumn ?? 1; const gridRow = mod.gridRow ?? 1;
      const initialPosX = (gridCol - 1) * CELL_SIZE; const initialPosY = (gridRow - 1) * CELL_SIZE;
      moduleNodes.push({
        id: uniqueNodeId, type: 'moduleNode', position: { x: initialPosX, y: initialPosY },
        data: { module: mod, widthPx, heightPx }, draggable: true, zIndex: 1,
      });
    });
    return moduleNodes;
  }, [CELL_SIZE]); // Dependency on CELL_SIZE

  // --- State Synchronization Effect (Reconciles Nodes) ---
  // Ensures RF nodes match `resultModules` for existence and data, but preserves positions set by drag.
  useEffect(() => {
    console.log("Effect: Reconciling nodes based on resultModules or grid dimensions...");

    setNodes(currentNodes => {
        const existingNodesMap = new Map<string, Node<ModuleNodeData | BoundaryNodeData>>();
        currentNodes.forEach(node => { if (node.id !== BOUNDARY_NODE_ID) existingNodesMap.set(node.id, node); });

        const desiredModuleStructures = transformModulesToNodes(resultModules);
        const desiredNodeIds = new Set(desiredModuleStructures.map(n => n.id));

        const reconciledModuleNodes: Node<ModuleNodeData>[] = desiredModuleStructures.map(desiredNode => {
            const existingNode = existingNodesMap.get(desiredNode.id) as Node<ModuleNodeData> | undefined;
            if (existingNode) {
                // Node exists: Keep existing position, update data if underlying module changed
                if (existingNode.data.module !== desiredNode.data.module || existingNode.data.widthPx !== desiredNode.data.widthPx || existingNode.data.heightPx !== desiredNode.data.heightPx) {
                     return { ...existingNode, data: desiredNode.data };
                } else { return existingNode; } // Data same, return original ref
            } else { return desiredNode; } // New node
        });

        // Filter out nodes no longer in resultModules (reconciliation)
        const finalModuleNodes = reconciledModuleNodes.filter(node => desiredNodeIds.has(node.id));

        // Create/Update Boundary Node
        let boundaryNode: Node<BoundaryNodeData> | null = null;
        if (gridPixelDimensions.width > 0 && gridPixelDimensions.height > 0) {
            boundaryNode = {
                id: BOUNDARY_NODE_ID, type: 'boundaryNode', position: { x: -4, y: -4 }, // Offset for border
                data: { widthPx: gridPixelDimensions.width + 8, heightPx: gridPixelDimensions.height + 8, }, // Size includes border
                draggable: false, selectable: false, zIndex: -1,
            };
        }
        const finalNodes = boundaryNode ? [...finalModuleNodes, boundaryNode] : finalModuleNodes;

        // Prevent unnecessary state update if nodes haven't changed significantly
        if (currentNodes.length !== finalNodes.length || !currentNodes.every((node, i) => node.id === finalNodes[i]?.id && node.position === finalNodes[i]?.position && node.data === finalNodes[i]?.data)) {
             console.log(`Reconciliation Result: ${finalNodes.length} nodes. Updating state.`);
             return finalNodes;
        } else {
             console.log(`Reconciliation Result: ${finalNodes.length} nodes. No significant state change needed.`);
             return currentNodes;
        }
    }); // End setNodes

    // Adjust Viewport
     if (resultModules.length > 0) {
        const fitViewTimeout = setTimeout(() => {
            if (reactFlowInstance?.fitView) {
                 console.log("Effect: Fitting view...");
                 try { reactFlowInstance.fitView({ padding: 0.25, duration: 300 }); }
                 catch (error) { console.error("Error during fitView:", error); }
             }
        }, 150);
        return () => clearTimeout(fitViewTimeout);
    }
    // No need for explicit viewport reset if defaultViewport is set

  }, [resultModules, gridPixelDimensions, setNodes, reactFlowInstance, transformModulesToNodes]);

  // --- Event Handlers ---
  const handleChange = (field: string, value: string) => {
    setConstraints(prev => ({ ...prev, [field]: value.replace(/[^0-9.]/g, '') }));
  };

  const handleDesign = () => {
    console.log("Handling Design button click...");
    fetch("http://localhost:8000/solve-dummy", { // Replace with your solve endpoint
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ constraints: { price: parseFloat(constraints.maxPrice) || 0, space_x: parseFloat(constraints.maxSpaceX) || 0, space_y: parseFloat(constraints.maxSpaceY) || 0, } })
    })
    .then(res => { if (!res.ok) throw new Error(`Solve error: ${res.status}`); return res.json(); })
    .then((data: { modules?: PositionedModule[] }) => {
        const modules = data?.modules || [];
        const processedModules: PositionedModule[] = modules
            .filter(m => m != null && m.id != null)
            .map((m, index) => ({
                ...m, id: `design_${m.id}_${index}`,
                gridColumn:  Math.floor(m.gridColumn / CELL_SIZE) + 1, gridRow:  Math.floor(m.gridRow / CELL_SIZE) + 1,
                width:  Math.floor(m.width / CELL_SIZE), height:  Math.floor(m.height / CELL_SIZE), io_fields: m.io_fields ?? [],
            }));
        setResultModules(processedModules);
    })
    .catch(err => console.error("Design fetch/process failed:", err));
  };

  const handleDCSelect = (dcId: number | "") => {
    console.log(`Handling DC Select change: ${dcId}`);
    setSelectedDC(dcId);
    if (dcId === "") { setResultModules([]); setConstraints({ maxPrice: '', maxSpaceX: '', maxSpaceY: ''}); return; }
    const selected: DataCenter | undefined = datacenters.find(dc => dc.id === dcId);
    if (selected) {
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
              .map((m, index) => ({ ...m, id: `dc_${selected.id}_${m.id}_${index}` }));
           const validMods = processedModules.filter(mod => {
                const gCol=(mod.gridColumn + 1); const gRow=(mod.gridRow+ 1); const w=(mod.width??1); const h=(mod.height??1);
                return gCol > 0 && gRow > 0 && (gCol + w - 1) <= spaceXCells && (gRow + h - 1) <= spaceYCells;
           });
           setResultModules(validMods);
      } else { setResultModules([]); }
    } else { setResultModules([]); setConstraints({ maxPrice: '', maxSpaceX: '', maxSpaceY: ''}); }
  };

  // Drag Stop Handler (Updates position in BOTH states if valid)
  const onNodeDragStop: NodeDragHandler = useCallback((event, draggedNode) => {
    if (draggedNode.id === BOUNDARY_NODE_ID || !draggedNode.data || !draggedNode.position) return;

    const uniqueDraggedNodeId = draggedNode.id;
    const nodeData = draggedNode.data as ModuleNodeData;
    console.log(`--- Node Drag Stop: ${uniqueDraggedNodeId} ---`);

    const snappedX = Math.round(draggedNode.position.x / CELL_SIZE) * CELL_SIZE;
    const snappedY = Math.round(draggedNode.position.y / CELL_SIZE) * CELL_SIZE;
    console.log(`  Snapped Pos: (${snappedX}, ${snappedY})`);

    const nodeWidth = nodeData.widthPx; const nodeHeight = nodeData.heightPx;
    const maxX = gridPixelDimensions.width; const maxY = gridPixelDimensions.height;
    const withinBounds = snappedX >= 0 && snappedY >= 0 && (snappedX + nodeWidth) <= maxX && (snappedY + nodeHeight) <= maxY;
    console.log(`  Within Bounds Check: ${withinBounds}`);

    let collision = false;
    if (withinBounds) {
        const nodesCopy = reactFlowInstance.getNodes();
        for (const otherNode of nodesCopy) {
            if (otherNode.id === uniqueDraggedNodeId || otherNode.id === BOUNDARY_NODE_ID) continue;
            if (!otherNode.position || !(otherNode.data as ModuleNodeData)?.widthPx) continue;
            const otherData = otherNode.data as ModuleNodeData;
            const otherX=otherNode.position.x; const otherY=otherNode.position.y;
            const otherW=otherData.widthPx; const otherH=otherData.heightPx;
            const xOverlap = snappedX < otherX + otherW && (snappedX + nodeWidth) > otherX;
            const yOverlap = snappedY < otherY + otherH && (snappedY + nodeHeight) > otherY;
            if (xOverlap && yOverlap) { collision = true; break; }
        }
    }
    console.log(`  Collision Check Result: ${collision}`);

    if (withinBounds && !collision) {
      console.log(`  Drop Valid. Updating states with SNAPPED position.`);
      setNodes((nds) => nds.map((n) => n.id === uniqueDraggedNodeId ? { ...n, position: { x: snappedX, y: snappedY } } : n ));
      setResultModules((prevModules) => prevModules.map(mod =>
            mod.id === uniqueDraggedNodeId
            ? { ...mod, gridColumn: (snappedX / CELL_SIZE) + 1, gridRow: (snappedY / CELL_SIZE) + 1 }
            : mod
          )
      );
    } else {
      console.warn(`  Drop Invalid/Rejected. Reverting visual.`);
      // No explicit state update needed here for revert with onNodesChange in use
    }
    console.log(`--- Node Drag Stop End: ${uniqueDraggedNodeId} ---`);
  }, [reactFlowInstance, setNodes, gridPixelDimensions, setResultModules, CELL_SIZE]); // Include CELL_SIZE

  // Viewport Change Handler
  const handleViewportChange = useCallback((viewport: Viewport | undefined) => {
    if (viewport && typeof viewport.zoom === 'number') { setCurrentZoom(viewport.zoom); }
  }, []);

  // --- Memoized UI Elements ---
  const ModuleLegendElement = useMemo(() => {
     const moduleTypes = [
        { name: 'transformer', displayName: 'Transformer' }, { name: 'water_supply', displayName: 'Water Supply' },
        { name: 'water_treatment', displayName: 'Water Treatment' }, { name: 'water_chiller', displayName: 'Water Chiller' },
        { name: 'network_rack', displayName: 'Network Rack' }, { name: 'server_rack', displayName: 'Server Rack' },
        { name: 'data_rack', displayName: 'Data Rack' }, { name: 'default', displayName: 'Other' }
      ];
     return (
       <Paper elevation={3} sx={{
         p: 1.5, width: 180, backgroundColor: 'rgba(32, 20, 52, 0.9)',
         position: 'absolute', right: 16, top: 16, // Positioned top-right
         border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2, zIndex: 10,
       }}>
         <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mb: 1 }}>Legend</Typography>
         {moduleTypes.map((type) => (
           <Box key={type.name} sx={{ display: 'flex', alignItems: 'center', mb: 0.8 }}>
             <Box component="img" src={getSpritePath(type.name)} alt={type.displayName} sx={{ width: 20, height: 20, mr: 1, objectFit: 'contain' }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}/>
             <Typography variant="caption" sx={{ color: 'white', fontWeight: 'medium' }}>{type.displayName}</Typography>
           </Box>
         ))}
       </Paper>
     );
   }, []); // Static

  const ConstraintsPanelElement = useMemo(() => {
    const totals = resultModules.reduce((acc, mod) => {
        const ioFields = Array.isArray(mod.io_fields) ? mod.io_fields : [];
        const priceIO = ioFields.find(io => io && io.unit === 'Price'); acc.price += priceIO?.amount || 0;
        acc.power += ioFields.find(io => io && !io.is_input && io.unit === 'Power')?.amount || 0;
        acc.cooling += ioFields.find(io => io && !io.is_input && io.unit === 'Cooling')?.amount || 0;
        acc.processing += ioFields.find(io => io && !io.is_input && io.unit === 'Processing')?.amount || 0;
        const gCol=mod.gridColumn??1; const gRow=mod.gridRow??1; const w=mod.width??1; const h=mod.height??1;
        acc.maxX = Math.max(acc.maxX, gCol + w - 1); acc.maxY = Math.max(acc.maxY, gRow + h - 1);
        return acc;
      }, { price: 0, power: 0, cooling: 0, processing: 0, maxX: 0, maxY: 0 });
    const maxPriceNum = parseFloat(constraints.maxPrice) || Infinity;
    const maxSpaceXNum = parseFloat(constraints.maxSpaceX) || Infinity;
    const maxSpaceYNum = parseFloat(constraints.maxSpaceY) || Infinity;
    const isPriceInLimit = totals.price <= maxPriceNum; const isSpaceXInLimit = totals.maxX <= maxSpaceXNum; const isSpaceYInLimit = totals.maxY <= maxSpaceYNum;
    const formatConstraint = (v: number, m: number) => { const vs=v.toFixed(0); return (!isFinite(m)||m===0)?`${vs}/∞`:`${vs}/${m.toFixed(0)}`; };
    const getPercentage = (v: number, m: number) => ((!isFinite(m)||m<=0)?'0%':`${Math.min(100,(v/m)*100).toFixed(0)}%`);
    return (
      <Paper elevation={3} sx={{
        p: 1.5, width: 220, backgroundColor: 'rgba(32, 20, 52, 0.9)',
        position: 'absolute', left: 16, top: 16, // Positioned top-left
        border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2, zIndex: 10,
      }}>
        <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mb: 1.5 }}>Status</Typography>
        <Box sx={{ mb: 1.5 }}><Typography variant="caption" sx={{ color: 'white', mb: 0.5, display:'block' }}>Price:</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><Box sx={{ flex: 1, height: 8, bgcolor: 'rgba(255,255,255,0.15)', borderRadius: 4, overflow: 'hidden' }}><Box sx={{ height: '100%', width: getPercentage(totals.price, maxPriceNum), bgcolor: isPriceInLimit?'#4caf50':'#f44336', transition:'width 0.3s ease' }} /></Box><Typography variant="caption" sx={{ color: 'white', minWidth: 60, textAlign:'right', fontFamily:'monospace' }}>{formatConstraint(totals.price, maxPriceNum)}</Typography></Box></Box>
        <Box sx={{ mb: 1.5 }}><Typography variant="caption" sx={{ color: 'white', mb: 0.5, display:'block' }}>Space X (Cells):</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><Box sx={{ flex: 1, height: 8, bgcolor: 'rgba(255,255,255,0.15)', borderRadius: 4, overflow: 'hidden' }}><Box sx={{ height: '100%', width: getPercentage(totals.maxX, maxSpaceXNum), bgcolor: isSpaceXInLimit?'#4caf50':'#f44336', transition:'width 0.3s ease' }} /></Box><Typography variant="caption" sx={{ color: 'white', minWidth: 60, textAlign:'right', fontFamily:'monospace' }}>{formatConstraint(totals.maxX, maxSpaceXNum)}</Typography></Box></Box>
        <Box sx={{ mb: 2 }}><Typography variant="caption" sx={{ color: 'white', mb: 0.5, display:'block' }}>Space Y (Cells):</Typography><Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><Box sx={{ flex: 1, height: 8, bgcolor: 'rgba(255,255,255,0.15)', borderRadius: 4, overflow: 'hidden' }}><Box sx={{ height: '100%', width: getPercentage(totals.maxY, maxSpaceYNum), bgcolor: isSpaceYInLimit?'#4caf50':'#f44336', transition:'width 0.3s ease' }} /></Box><Typography variant="caption" sx={{ color: 'white', minWidth: 60, textAlign:'right', fontFamily:'monospace' }}>{formatConstraint(totals.maxY, maxSpaceYNum)}</Typography></Box></Box>
        <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mt: 2, mb: 1 }}>Production</Typography>
        <Box sx={{ mb: 0.5, display: 'flex', justifyContent: 'space-between' }}><Typography variant="caption" sx={{ color: 'white' }}>Power:</Typography><Typography variant="caption" sx={{ color: '#4caf50', fontWeight:'bold' }}>{totals.power.toFixed(2)}</Typography></Box>
        <Box sx={{ mb: 0.5, display: 'flex', justifyContent: 'space-between' }}><Typography variant="caption" sx={{ color: 'white' }}>Cooling:</Typography><Typography variant="caption" sx={{ color: '#2196f3', fontWeight:'bold' }}>{totals.cooling.toFixed(2)}</Typography></Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}><Typography variant="caption" sx={{ color: 'white' }}>Processing:</Typography><Typography variant="caption" sx={{ color: '#ff9800', fontWeight:'bold' }}>{totals.processing.toFixed(2)}</Typography></Box>
      </Paper>
    );
  }, [resultModules, constraints]);


  // --- Component Render ---
  return (
    <Box sx={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', alignItems: 'center', p: '1rem', gap: 1, bgcolor: '#201434', overflow: 'hidden' }}>
      {/* Header */}
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
      <Box sx={{ width: '95%', height: '100%', minHeight: '400px', position: 'relative', border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2, overflow: 'hidden', bgcolor: '#281f3d' }}>
        <ReactFlow
            nodes={nodes} edges={edges}
            onNodesChange={onNodesChange} // Handles internal node events (like dragging position update)
            onEdgesChange={onEdgesChange}
            onNodeDragStop={onNodeDragStop} // Apply final snapping and validation
            onMoveEnd={handleViewportChange} // Update zoom display
            nodeTypes={nodeTypes}
            defaultViewport={{ x: 0, y: 0, zoom: 0.75 }}
            minZoom={0.05} maxZoom={4}
            fitViewOptions={{ padding: 0.25, duration: 300 }}
            nodesDraggable={true} selectNodesOnDrag={true}
            proOptions={{ hideAttribution: true }}
            // Important: snapToGrid prop applies visual snap *during* drag
            snapToGrid={true}
            snapGrid={[CELL_SIZE, CELL_SIZE]} // Snap visually to the grid size
            style={{ width: '100%', height: '100%' }}
          >
          <Controls showInteractive={false}/>
          <Background variant="dots" gap={CELL_SIZE} size={1.5} color="#443a5f" />
        </ReactFlow>

        {/* Overlays */}
        {resultModules.length > 0 && ModuleLegendElement}
        {resultModules.length > 0 && ConstraintsPanelElement}

        {/* Bottom Status Bar */}
        <Box sx={{ position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)', zIndex: 10, padding: '4px 12px', bgcolor: 'rgba(0,0,0,0.75)', color: 'rgba(255,255,255,0.8)', borderRadius: 1, fontSize: '0.75rem', display: 'flex', gap: 2, alignItems: 'center', whiteSpace: 'nowrap' }}>
           <Typography variant="caption">Grid: {constraints.maxSpaceX || '?'}×{constraints.maxSpaceY || '?'} Cells</Typography>
           <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
           <Typography variant="caption">Zoom: {(currentZoom ?? 1).toFixed(2)}x</Typography>
           <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
           <Typography variant="caption">Nodes: {nodes.filter(n => n.id !== BOUNDARY_NODE_ID).length}</Typography>
        </Box>
      </Box>
    </Box>
  );
};

// Wrap with Provider
const MainPageWrapper = () => ( <ReactFlowProvider><MainPage /></ReactFlowProvider> );
export default MainPageWrapper;

// --- types.ts reminder ---
/*
export interface IOField {
    is_input: boolean;
    is_output?: boolean;
    unit: string;
    amount: number;
}
export interface Module {
    id: string;
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
    Below_Amount?: number; Above_Amount?: number; Minimize?: number; Maximize?: number; Unconstrained?: number;
    Unit: string; Amount?: number;
}
export interface DataCenter {
    id: number; name: string; specs: SpecRule[]; details?: Record<string, number>; modules: PositionedModule[];
}
*/