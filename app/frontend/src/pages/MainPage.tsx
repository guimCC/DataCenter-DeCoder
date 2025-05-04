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
  NodeTypes
} from 'reactflow';
import 'reactflow/dist/style.css'; // Essential React Flow styles

// --- Material UI Imports ---
import {
  Box, TextField, Typography, Button, Paper, MenuItem, Select, FormControl, InputLabel,
  List, ListItem, ListItemText, Divider, LinearProgress, Tooltip, IconButton,
  ListSubheader, SelectChangeEvent, CircularProgress // Added missing MUI types
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import { Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions } from '@mui/material';

// *** IMPORT YOUR ACTUAL TYPES ***
// Make sure this path points correctly to your types file (e.g., '../types')
import { PositionedModule, DataCenter, Module, IOField, SpecRule } from '../types';

// Types for the new Dynamic Constraints Panel
export type ConstraintOperation = 'Minimize' | 'Maximize' | 'Below Value' | 'Above Value';

export interface ActiveConstraint {
  id: string; // Unique ID for React keys and removal
  resource: Resource; // The name of the resource being constrained
  type: 'INPUT' | 'OUTPUT'; // Determines available operations
  operation: ConstraintOperation;
  value: number; // Threshold for Below/Above, Weight for Min/Max
}

// Define the resource lists (can also be constants in MainPage.tsx)
export const INPUT_RESOURCES = ['price', 'grid_connection', 'water_connection'] as const;
export const OUTPUT_RESOURCES = ['external_network', 'data_storage', 'processing'] as const;

export type InputResource = typeof INPUT_RESOURCES[number];
export type OutputResource = typeof OUTPUT_RESOURCES[number];
export type Resource = InputResource | OutputResource;

// Mapping from user-facing resource names to internal IOField units
// *** IMPORTANT: Adjust this map to match the EXACT 'unit' strings used in your Module's io_fields ***
export const RESOURCE_UNIT_MAP: Record<Resource, string> = {
  price: 'Price',            // Cost is usually an input characteristic
  grid_connection: 'Power',  // Assuming grid connection represents Power INPUT
  water_connection: 'Water', // Assuming water connection represents Water INPUT
  external_network: 'Network', // Assuming external network is Network OUTPUT
  data_storage: 'Storage',   // Assuming data storage is Storage OUTPUT
  processing: 'Processing',  // Assuming processing is Processing OUTPUT
};

// Helper to determine if a resource is input or output based on our lists
export function getResourceType(resource: Resource): 'INPUT' | 'OUTPUT' {
  return (INPUT_RESOURCES as readonly string[]).includes(resource) ? 'INPUT' : 'OUTPUT';
}

// Helper to generate simple unique IDs for constraints and potentially nodes if needed differently
function generateUniqueId(prefix: string = 'id'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// --- Configuration Constants ---
const CELL_SIZE = 10; // Pixel size of one grid cell for layout calculations
const DEFAULT_GRID_DIMENSIONS = { rows: 100, cols: 100 }; // Fallback grid size if constraints missing
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

// --- Constraints Panel Component ---
// (Defined here for inclusion in the single file as requested)

interface ConstraintsPanelProps {
  activeConstraints: ActiveConstraint[];
  resultModules: PositionedModule[]; // Needed to calculate current values
  onAddConstraint: (constraint: Omit<ActiveConstraint, 'id' | 'type'>) => void; // Type is derived internally
  onRemoveConstraint: (id: string) => void;
  onDesign: () => void; // Optional: Callback to trigger design action
  onRefine?: () => void;
}

const ConstraintsPanel: React.FC<ConstraintsPanelProps> = ({
  activeConstraints,
  resultModules,
  onAddConstraint,
  onRemoveConstraint,
  onDesign,
  onRefine
}) => {
  // State for the 'Add Constraint' form
  const [selectedResource, setSelectedResource] = useState<Resource | ''>('');
  const [selectedOperation, setSelectedOperation] = useState<ConstraintOperation | ''>('');
  const [constraintValue, setConstraintValue] = useState<string>('');

  // --- Derived state ---
  const resourceType = useMemo(() => selectedResource ? getResourceType(selectedResource) : null, [selectedResource]);
  const availableOps = useMemo((): ConstraintOperation[] => {
      if (resourceType === 'INPUT') return ['Minimize', 'Below Value'];
      if (resourceType === 'OUTPUT') return ['Maximize', 'Above Value'];
      return [];
  }, [resourceType]);
  const valueLabel = useMemo(() => {
      if (selectedOperation === 'Minimize' || selectedOperation === 'Maximize') return 'Weight Factor';
      if (selectedOperation === 'Below Value' || selectedOperation === 'Above Value') return 'Threshold Value';
      return 'Value';
  }, [selectedOperation]);
  const showValueInput = selectedOperation !== '';
  const isAddDisabled = !selectedResource || !selectedOperation || !constraintValue || isNaN(parseFloat(constraintValue));


  // --- Helper Functions ---
  const calculateCurrentValue = useCallback((resource: Resource, modules: PositionedModule[]): number => {
      const targetUnit = RESOURCE_UNIT_MAP[resource];
      const targetType = getResourceType(resource); // 'INPUT' or 'OUTPUT'
      if (!targetUnit || !modules) return 0;

      return modules.reduce((sum, mod) => {
          const ioFields = Array.isArray(mod.io_fields) ? mod.io_fields : [];
          const relevantField = ioFields.find(io => {
              if (!io || io.unit !== targetUnit) return false;
              // Match unit AND direction (Input/Output)
              // Price is a special case, usually considered an input cost attribute, not output production
              if (targetUnit === 'Price') return true; // Assume price is always relevant if matched unit
              const isInputMatch = targetType === 'INPUT' && io.is_input;
              const isOutputMatch = targetType === 'OUTPUT' && !io.is_input; // !is_input implies output
              return isInputMatch || isOutputMatch;
          });
          return sum + (relevantField?.amount || 0);
      }, 0);
  }, []); // Depends only on static maps/types

  const formatConstraintText = (constraint: ActiveConstraint): string => {
      const opText = constraint.operation;
      const valText = constraint.value.toLocaleString();
      const resourceName = constraint.resource.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

      switch (opText) {
          case 'Minimize': return `${resourceName}: Minimize (Weight: ${valText})`;
          case 'Maximize': return `${resourceName}: Maximize (Weight: ${valText})`;
          case 'Below Value': return `${resourceName}: ≤ ${valText}`; // Use symbols for brevity
          case 'Above Value': return `${resourceName}: ≥ ${valText}`; // Use symbols for brevity
          default: return `${resourceName}: ${opText} ${valText}`; // Fallback
      }
  };

  const getConstraintStatus = useCallback((constraint: ActiveConstraint): { current: number; percentage: number | null; withinLimits: boolean | null; tooltip: string } => {
      const current = calculateCurrentValue(constraint.resource, resultModules);
      let percentage: number | null = null;
      let withinLimits: boolean | null = null;
      let tooltip = `Current ${constraint.resource.replace(/_/g, ' ')}: ${current.toLocaleString()}`;

      if ((constraint.operation === 'Below Value' || constraint.operation === 'Above Value')) {
           const targetValue = constraint.value;
           tooltip += ` / ${constraint.operation === 'Below Value' ? 'Limit' : 'Target'}: ${targetValue.toLocaleString()}`;
           if (targetValue > 0) {
                // Calculate percentage relative to the target/limit
                percentage = Math.min(100, Math.max(0, (current / targetValue) * 100));
                withinLimits = constraint.operation === 'Below Value' ? current <= targetValue : current >= targetValue;
           } else if (targetValue === 0 && constraint.operation === 'Below Value') {
                // Special case: Below 0 means must be 0 or less
                percentage = current <= 0 ? 0 : 100; // Show 0% if compliant, 100% if over
                withinLimits = current <= 0;
           } else if (targetValue === 0 && constraint.operation === 'Above Value') {
                // Special case: Above 0 means must be 0 or more (usually always true for positive resources)
                percentage = current >= 0 ? 100 : 0; // Show 100% if compliant, 0% if somehow negative
                withinLimits = current >= 0;
           }

      } else if (constraint.operation === 'Minimize' || constraint.operation === 'Maximize') {
          // For Min/Max, there's no simple progress bar or limit check, just show current value and weight
          tooltip += ` (Weight: ${constraint.value.toLocaleString()})`;
          // withinLimits remains null
          // percentage remains null
      }

      return { current, percentage, withinLimits, tooltip };
  }, [resultModules, calculateCurrentValue]); // Recalculate when modules change


  // --- Event Handlers ---
  const handleResourceChange = (event: SelectChangeEvent<Resource | ''>) => {
      const newResource = event.target.value as Resource | '';
      setSelectedResource(newResource);
      setSelectedOperation(''); // Reset operation when resource changes
      setConstraintValue('');   // Reset value
  };

  const handleOperationChange = (event: SelectChangeEvent<ConstraintOperation | ''>) => {
      setSelectedOperation(event.target.value as ConstraintOperation | '');
      // Keep value for now, user might be switching between similar ops like Below/Above
  };

  const handleValueChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      // Allow only numbers and a single decimal point
      const value = event.target.value;
      if (/^\d*\.?\d*$/.test(value)) { // Basic regex for positive numbers/decimals
           setConstraintValue(value);
      }
  };

  const handleAddClick = () => {
      if (isAddDisabled || !selectedResource || !selectedOperation) return; // Redundant check, but safe

      const valueNum = parseFloat(constraintValue); // Already checked !isNaN via isAddDisabled

      // Call the callback passed from MainPage
      onAddConstraint({
          resource: selectedResource,
          operation: selectedOperation,
          value: valueNum,
      });

      // Reset form after adding
      setSelectedResource('');
      setSelectedOperation('');
      setConstraintValue('');
  };

  // --- Render ---
  return (
      <Paper elevation={3} sx={{
          p: 1.5, width: 280, // Fixed width
          backgroundColor: 'rgba(32, 20, 52, 0.9)', // Dark theme background
          position: 'absolute', left: 16, top: 16, // Position top-left
          border: '1px solid rgba(255, 255, 255, 0.2)', borderRadius: 2, zIndex: 10,
          maxHeight: 'calc(100% - 32px)', // Prevent overflow
          display: 'flex', flexDirection: 'column' // Allow vertical scrolling
      }}>
          <Typography variant="subtitle2" gutterBottom sx={{ color: 'white', fontWeight: 'bold', mb: 1.5 }}>
              Define Constraints
          </Typography>

          {/* --- Add Constraint Form --- */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mb: 2 }}>
              {/* Resource Selector */}
              <FormControl size="small" fullWidth>
                  <InputLabel id="resource-select-label" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Resource</InputLabel>
                  <Select
                      labelId="resource-select-label"
                      value={selectedResource}
                      label="Resource"
                      onChange={handleResourceChange}
                      sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' }, '& .MuiSvgIcon-root': { color: 'rgba(255, 255, 255, 0.7)' } }}
                      MenuProps={{ PaperProps: { sx: { bgcolor: '#332a4f', color: 'white', border: '1px solid rgba(255,255,255,0.2)', mt: 0.5 } } }}
                  >
                      <MenuItem value="" disabled><em>-- Select Resource --</em></MenuItem>
                      <ListSubheader sx={{bgcolor: '#332a4f', color: 'rgba(255,255,255,0.6)', lineHeight: '24px', py:0.5}}>Input Resources</ListSubheader>
                      {INPUT_RESOURCES.map(res => <MenuItem key={res} value={res}>{res.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>)}
                       <ListSubheader sx={{bgcolor: '#332a4f', color: 'rgba(255,255,255,0.6)', lineHeight: '24px', py:0.5}}>Output Resources</ListSubheader>
                      {OUTPUT_RESOURCES.map(res => <MenuItem key={res} value={res}>{res.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</MenuItem>)}
                  </Select>
              </FormControl>

              {/* Operation Selector (conditional) */}
              {resourceType && (
                  <FormControl size="small" fullWidth disabled={!selectedResource}>
                      <InputLabel id="operation-select-label" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Operation</InputLabel>
                      <Select
                          labelId="operation-select-label"
                          value={selectedOperation}
                          label="Operation"
                          onChange={handleOperationChange}
                          sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' }, '& .MuiSvgIcon-root': { color: 'rgba(255, 255, 255, 0.7)' } }}
                          MenuProps={{ PaperProps: { sx: { bgcolor: '#332a4f', color: 'white', border: '1px solid rgba(255,255,255,0.2)', mt: 0.5 } } }}
                      >
                         <MenuItem value="" disabled><em>-- Select Operation --</em></MenuItem>
                          {availableOps.map(op => <MenuItem key={op} value={op}>{op}</MenuItem>)}
                      </Select>
                  </FormControl>
              )}

              {/* Value Input (conditional) */}
              {showValueInput && (
                  <TextField
                      size="small"
                      label={valueLabel}
                      value={constraintValue}
                      onChange={handleValueChange}
                      type="text" // Use text for better control with regex
                      inputMode='decimal' // Hint for mobile keyboards (decimal allows .)
                      variant="outlined"
                      fullWidth
                      InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }}
                      InputProps={{ sx: { color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' }, '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#9065f0' } } }}
                  />
              )}

              {/* Add Button */}
              <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleAddClick}
                  disabled={isAddDisabled} // Use calculated disabled state
                  sx={{ alignSelf: 'flex-end' }} // Position to the right
              >
                  Add
              </Button>
          </Box>

          <Divider sx={{ my: 1, borderColor: 'rgba(255, 255, 255, 0.2)' }} />

          {/* --- Active Constraints List --- */}
           <Typography variant="subtitle2" gutterBottom sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 'bold', mb: 1 }}>
              Active Constraints ({activeConstraints.length})
          </Typography>
          {/* Scrollable container for the list */}
          <Box sx={{ overflowY: 'auto', flexGrow: 1, pr: 0.5 }}> {/* Add padding right for scrollbar */}
              <List dense disablePadding>
                  {activeConstraints.length === 0 ? (
                       <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.6)', fontStyle: 'italic', textAlign:'center', display:'block', py:2 }}>
                           No constraints defined.
                       </Typography>
                  ) : (
                      activeConstraints.map((constraint) => {
                          const { current, percentage, withinLimits, tooltip } = getConstraintStatus(constraint);
                          const showProgress = percentage !== null; // Show progress only for Below/Above
                          const progressColor = withinLimits === null ? 'primary' : (withinLimits ? 'success' : 'error');

                          return (
                              <ListItem
                                  key={constraint.id}
                                  disableGutters
                                  sx={{
                                      display: 'flex', flexDirection: 'column', alignItems: 'stretch',
                                      mb: 1.5, p:0, position: 'relative' // Needed for absolute positioning delete icon
                                  }}
                              >
                                  {/* Delete Button positioned top-right */}
                                  <IconButton
                                      edge="end"
                                      aria-label={`delete constraint ${constraint.resource}`}
                                      onClick={() => onRemoveConstraint(constraint.id)} // Call remove handler
                                      size="small"
                                      sx={{
                                          position: 'absolute', top: -2, right: -4, // Adjust positioning
                                          color: 'rgba(255,255,255,0.4)',
                                          '&:hover': { color: '#f44336', backgroundColor: 'rgba(255, 0, 0, 0.1)' },
                                           zIndex: 1 // Ensure it's above text
                                      }}
                                  >
                                      <DeleteIcon fontSize="inherit" /> {/* Smaller icon */}
                                  </IconButton>

                                 <Tooltip title={tooltip} placement="top-start" arrow>
                                      <ListItemText
                                          primary={formatConstraintText(constraint)}
                                          primaryTypographyProps={{ variant: 'body2', color: 'white', sx:{ mb: 0.5, pr: '24px'} }} // Padding right to avoid delete icon overlap
                                          // Only show secondary if no progress bar (for Min/Max)
                                          secondary={!showProgress && `Current: ${current.toLocaleString()}`}
                                          secondaryTypographyProps={{ variant: 'caption', color: 'rgba(255, 255, 255, 0.7)' }}
                                      />
                                  </Tooltip>

                                  {/* Progress Bar (conditional) */}
                                  {showProgress && (
                                      <Box sx={{ width: '100%', mt: 0.5 }}>
                                          <LinearProgress
                                              variant="determinate"
                                              value={percentage ?? 0}
                                              color={progressColor}
                                              sx={{ height: 6, borderRadius: 3 }}
                                          />
                                      </Box>
                                  )}
                              </ListItem>
                          );
                      })
                  )}
              </List>
          </Box>

          <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.2)' }} />
          
          <Button 
              size="large" 
              variant="contained" 
              onClick={onDesign} 
              sx={{ 
                  mt: 'auto', // Push to bottom
                  backgroundColor: '#9c27b0',
                  '&:hover': { backgroundColor: '#7b1fa2' },
                  fontWeight: 'bold'
              }}
          >
              Design DataCenter
          </Button>

          {/* Add Refine button */}
          {onRefine && (
              <Button 
                  size="large" 
                  variant="outlined" 
                  onClick={onRefine}
                  sx={{ 
                      mt: 1, // Space from the Design button
                      borderColor: '#9c27b0',
                      color: '#9c27b0',
                      '&:hover': { borderColor: '#7b1fa2', backgroundColor: 'rgba(156, 39, 176, 0.08)' },
                      fontWeight: 'bold'
                  }}
              >
                  Refine Design
              </Button>
          )}

      </Paper>
  );
};


// --- Main Page Component Definition ---
const MainPage = () => {
  // --- State ---
  const [gridInputCells, setGridInputCells] = useState({
      x: DEFAULT_GRID_DIMENSIONS.cols.toString(),
      y: DEFAULT_GRID_DIMENSIONS.rows.toString()
  });
  const [constraints, setConstraints] = useState({ maxPrice: '', maxSpaceX: '', maxSpaceY: '' });
  const [datacenters, setDatacenters] = useState<DataCenter[]>([]);
  const [selectedDC, setSelectedDC] = useState<number | "">("");
  const [currentZoom, setCurrentZoom] = useState<number>(1);
  const [resultModules, setResultModules] = useState<PositionedModule[]>([]); // Canonical data
  const [activeConstraints, setActiveConstraints] = useState<ActiveConstraint[]>([]); // State for dynamic constraints
  const [rawSolution, setRawSolution] = useState<{
        modules: Record<string, number>; // Dictionary of module IDs to quantities
        states: Record<string, any>;    // Solver state information
        specs: Array<{
            Unit: string;
            Below_Amount: number;
            Above_Amount: number;
            Minimize: number;
            Maximize: number;
            Unconstrained: number;
            Amount: number | null;
        }>;
    } | null>(null);

  // RF State
  const [nodes, setNodes, onNodesChange] = useNodesState<ModuleNodeData | BoundaryNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useReactFlow<ModuleNodeData | BoundaryNodeData, Edge>();
  const [isLoading, setIsLoading] = useState<boolean>(false);


  // Calculate grid dimensions
  // Calculate grid dimensions IN PIXELS
  const gridPixelDimensions = useMemo(() => {
    const cols = parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols;
    const rows = parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows;
    return {
        width: cols , // Multiply by CELL_SIZE to get pixels
        height: rows , // Multiply by CELL_SIZE to get pixels
    };
    // Make sure CELL_SIZE is included in the dependency array if it could ever change dynamically
  }, [constraints.maxSpaceX, constraints.maxSpaceY, CELL_SIZE]);
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
      const widthCells = mod.width / CELL_SIZE; const heightCells = mod.height / CELL_SIZE;
      const widthPx = widthCells * CELL_SIZE; const heightPx = heightCells * CELL_SIZE;
      const gridCol = mod.gridColumn / CELL_SIZE + 1; const gridRow = mod.gridRow / CELL_SIZE + 1;
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

  // Handler for Adding a Constraint (called by ConstraintsPanel)
  const handleAddConstraint = useCallback((constraintData: Omit<ActiveConstraint, 'id' | 'type'>) => {
    const newConstraint: ActiveConstraint = {
        ...constraintData,
        id: generateUniqueId('constraint'), // Generate unique ID
        type: getResourceType(constraintData.resource), // Determine type based on resource
    };
      setActiveConstraints(prev => [...prev, newConstraint]);
      console.log("Added Constraint:", newConstraint);
  }, []); // Stable function identity

  // Handler for Removing a Constraint (called by ConstraintsPanel)
  const handleRemoveConstraint = useCallback((idToRemove: string) => {
        setActiveConstraints(prev => prev.filter(c => c.id !== idToRemove));
        console.log("Removed Constraint ID:", idToRemove);
    }, []); // Stable function identity
    
    const createNodesFromModules = useCallback((modules: PositionedModule[]): Node<ModuleNodeData>[] => {
      // Placeholder implementation to be enhanced later
      return modules.map((mod, index) => {
        const widthPx = mod.width; 
        const heightPx = mod.height;
        const initialPosX = (mod.gridColumn - 1) * CELL_SIZE;
        const initialPosY = (mod.gridRow - 1) * CELL_SIZE;
    
        return {
          id: mod.id.toString(), // Use the module ID as the node ID
          type: 'moduleNode',
          position: { x: initialPosX, y: initialPosY },
          data: { module: mod, widthPx, heightPx },
          draggable: true,
          zIndex: 1
        };
      });
    }, [CELL_SIZE]);

    const refineDesign = useCallback(() => {
      // Only proceed if we have a raw solution
      if (!rawSolution) {
        alert("No initial solution available to refine.");
        return;
      }
    
      // Extract the current state of all modules from the nodes
      // Extract the grid dimensions
      const gridWidth = parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols;
      const gridHeight = parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows;

      // Get only the modules inside the grid boundaries
      const currentModules = nodes
        .filter(node => node.type === 'moduleNode')
        .filter(node => {
          const mod = node.data.module;
          const gridCol = mod.gridColumn || 0;
          const gridRow = mod.gridRow || 0;
          const width = mod.width || 1;
          const height = mod.height || 1;
          
          // Check if module is completely inside the grid
          return (
            gridCol >= 1 &&
            gridRow >= 1 &&
            gridCol + width - 1 <= gridWidth &&
            gridRow + height - 1 <= gridHeight
          );
        })
        .map(node => ({
          id: node.data.module.id,
          name: node.data.module.name,
          width: node.data.module.width,
          height: node.data.module.height,
          gridColumn: node.data.module.gridColumn*CELL_SIZE,
          gridRow: node.data.module.gridRow*CELL_SIZE,
          io_fields: node.data.module.io_fields || []
        }));
    
      if (currentModules.length === 0) {
        alert("No modules to refine. Place some modules first.");
        return;
      }
    
      // Build the data object for the backend
      const placementData = {
        modules: currentModules,  // Current state of modules with positions
        specs: rawSolution.specs,  // Use original constraints
        module_quantities: rawSolution.modules,  // Original module quantities
        grid_dimensions: {
          width: parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols,
          height: parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows
        }
      };
    
      console.log("Sending data to solve-placements:", placementData);
      setIsLoading(true);
    
      // Send request to the backend
      fetch("http://localhost:8000/solve-placements", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(placementData)
      })
      .then(res => {
        if (!res.ok) {
          return res.text().then(text => {
            throw new Error(`Error ${res.status}: ${text}`);
          });
        }
        return res.json();
      })
      .then((data) => {
        if (data && data.modules) {
          // Process the returned modules with new positions
          const refinedModules: PositionedModule[] = data.modules
            .map((m: any) => ({
              id: m.id,
              name: m.name,
              instanceId: m.instanceId || generateUniqueId(`refined_${m.id}`), 
              gridColumn: Number(m.gridColumn || 1),
              gridRow: Number(m.gridRow || 1),
              width: Number(m.width || 1),
              height: Number(m.height || 1),
              io_fields: m.io_fields || []
            }));
            
          setResultModules(refinedModules);
          
          // Create React Flow nodes from the refined modules
          const newNodes = createNodesFromModules(refinedModules);
          setNodes(newNodes);
          
          // Update the raw solution if returned
          if (data.raw_solution) {
            setRawSolution(data.raw_solution);
          }
    
          // Auto-fit view to show all modules
          setTimeout(() => {
            reactFlowInstance.fitView({ padding: 0.2 });
          }, 100);
        } else {
          console.error("Invalid response from solver:", data);
          alert("The solver returned an invalid response. Check the console for details.");
        }
      })
      .catch(err => {
        console.error("Error in refinement process:", err);
        alert(`Design refinement failed: ${err.message}`);
      })
      .finally(() => {
        setIsLoading(false);
      });
    }, [rawSolution, nodes, constraints, DEFAULT_GRID_DIMENSIONS, generateUniqueId, createNodesFromModules, reactFlowInstance]);
    
    
    // Handler for the "Design" Button
    const handleDesign = useCallback(() => {
      console.log("Handling Design button click...");
      
      // Create complete format specs from constraints
      const specs = activeConstraints.map(c => {
        const unit = RESOURCE_UNIT_MAP[c.resource] || c.resource;
        return {
          Unit: unit,
          Below_Amount: c.operation === 'Below Value' ? 1 : 0,
          Above_Amount: c.operation === 'Above Value' ? 1 : 0,
          Minimize: c.operation === 'Minimize' ? 1 : 0,
          Maximize: c.operation === 'Maximize' ? 1 : 0,
          Unconstrained: !['Below Value', 'Above Value', 'Minimize', 'Maximize'].includes(c.operation) ? 1 : 0,
          Amount: c.operation === 'Below Value' || c.operation === 'Above Value' ? parseFloat(c.value) : null
        };
      });
      
      // Add constraints from form fields
      const maxSpaceX = parseFloat(constraints.maxSpaceX);
      const maxSpaceY = parseFloat(constraints.maxSpaceY);
      const maxPrice = parseFloat(constraints.maxPrice);
      
      if (!isNaN(maxSpaceX) && maxSpaceX > 0) {
        specs.push({
          Unit: 'Space_X',
          Below_Amount: 1,
          Above_Amount: 0,
          Minimize: 0,
          Maximize: 0,
          Unconstrained: 0,
          Amount: maxSpaceX
        });
      }
      
      if (!isNaN(maxSpaceY) && maxSpaceY > 0) {
        specs.push({
          Unit: 'Space_Y',
          Below_Amount: 1,
          Above_Amount: 0,
          Minimize: 0,
          Maximize: 0,
          Unconstrained: 0,
          Amount: maxSpaceY
        });
      }
      
      if (!isNaN(maxPrice) && maxPrice > 0) {
        specs.push({
          Unit: 'Price',
          Below_Amount: 1,
          Above_Amount: 0,
          Minimize: 0,
          Maximize: 0,
          Unconstrained: 0,
          Amount: maxPrice
        });
      }
    
      // Create weights from active constraints
      const weights = {};
      activeConstraints.forEach(c => {
        if (c.operation === 'Minimize' || c.operation === 'Maximize') {
          const unit = RESOURCE_UNIT_MAP[c.resource] || c.resource;
          weights[unit] = c.operation === 'Minimize' ? -parseFloat(c.value || '1') : parseFloat(c.value || '1');
        }
      });
    
      // Get any fixed modules
      const fixedModules = nodes
        .filter(n => n.type === 'moduleNode' && n.data?.isFixed)
        .map(n => ({
          id: n.data.module.id,
          name: n.data.module.name,
          gridColumn: n.data.module.gridColumn,
          gridRow: n.data.module.gridRow,
          width: n.data.module.width,
          height: n.data.module.height,
          io_fields: n.data.module.io_fields || []
        }));
      
      setIsLoading(true);
      
      // Convert the specs and weights to JSON strings
      const specsJsonString = JSON.stringify(specs);
      const weightsJsonString = JSON.stringify(weights);
      
      // Build query string for specs and weights
      const queryParams = new URLSearchParams();
      queryParams.append('specs', specsJsonString);
      queryParams.append('weights', weightsJsonString);
      
      console.log("Sending specs:", specs);
      console.log("Sending weights:", weights);
      
      // Make the API request
      fetch(`http://localhost:8000/solve-components?${queryParams.toString()}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fixedModules)
      })
      .then(res => {
        if (!res.ok) {
          return res.text().then(text => {
            throw new Error(`Error ${res.status}: ${text}`);
          });
        }
        return res.json();
      })
      .then((data) => {
        if (data && data.modules) {
          if (data.raw_solution) {
            setRawSolution(data.raw_solution);
          }
          // Get grid dimensions
          const gridWidth = parseInt(constraints.maxSpaceX) || DEFAULT_GRID_DIMENSIONS.cols;
          const gridHeight = parseInt(constraints.maxSpaceY) || DEFAULT_GRID_DIMENSIONS.rows;
          const spacing = 2; // Gap between modules in cells
          
          // Group modules by type for better organization
          const modulesByType: {[key: string]: any[]} = {};
          data.modules.forEach((m: any) => {
            const type = m.name?.toLowerCase() || 'unknown';
            const key = getModuleType(type);
            if (!modulesByType[key]) modulesByType[key] = [];
            modulesByType[key].push(m);
          });
          
          // Position trackers for each edge of the grid
          let topX = 0; // Left to right along top edge
          let rightY = 0; // Top to bottom along right edge
          let bottomX = gridWidth; // Right to left along bottom edge
          let leftY = gridHeight; // Bottom to top along left edge
          
          const processedModules: PositionedModule[] = [];
          
          // Place modules by type around the grid
          Object.entries(modulesByType).forEach(([type, modules], typeIndex) => {
            // Decide which edge to place this module type on
            const edge = typeIndex % 4;
            
            modules.forEach((m: any, moduleIndex: number) => {
              const width = Number(m.width || 1);
              const height = Number(m.height || 1);
              let gridCol: number;
              let gridRow: number;
              
              switch(edge) {
                case 0: // Top edge (above grid)
                  gridCol = topX + 1;
                  gridRow = 0 - height - 1;
                  topX += width + spacing;
                  break;
                  
                case 1: // Right edge
                  gridCol = gridWidth + 2;
                  gridRow = rightY + 1;
                  rightY += height + spacing;
                  break;
                  
                case 2: // Bottom edge
                  gridCol = bottomX - width + 1;
                  gridRow = gridHeight + 2;
                  bottomX -= width + spacing;
                  break;
                  
                case 3: // Left edge
                  gridCol = 0 - width - 1;
                  gridRow = leftY - height + 1;
                  leftY -= height + spacing;
                  break;
              }
              
              processedModules.push({
                id: m.id,
                name: m.name,
                instanceId: generateUniqueId(`design_${m.id}_${moduleIndex}`),
                gridColumn: gridCol,
                gridRow: gridRow,
                width: width,
                height: height,
                io_fields: m.io_fields || []
              });
            });
          });
          
          setResultModules(processedModules);
          
          // Create React Flow nodes from the processed modules
          const newNodes = createNodesFromModules(processedModules);
          setNodes(newNodes);
          
          // Add timeout to fit view after modules are placed
          setTimeout(() => {
            reactFlowInstance.fitView({ padding: 0.2 });
          }, 100);
        } else {
          console.error("Invalid response from solver:", data);
          alert("The solver returned an invalid response. Check the console for details.");
        }
      })
      .catch(err => {
        console.error("Error in design process:", err);
        alert(`Design process failed: ${err.message}`);
      })
      .finally(() => {
        setIsLoading(false);
      });
    
    }, [activeConstraints, nodes, RESOURCE_UNIT_MAP, createNodesFromModules, generateUniqueId]);


  const handleDCSelect = (dcId: number | "") => {
    console.log(`Handling DC Select change: ${dcId}`);
    setSelectedDC(dcId);
    setActiveConstraints([]); // Clear dynamic constraints when loading a DC

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
        position: 'absolute', right: 16, bottom: 16, // Positioned top-left
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

        {/* Constraints Panel (Left Side) */}
        <ConstraintsPanel
            activeConstraints={activeConstraints}
            resultModules={resultModules}
            onAddConstraint={handleAddConstraint}
            onRemoveConstraint={handleRemoveConstraint}
            onDesign={handleDesign}
            onRefine={refineDesign} 
        />

    <Box sx={{
                position: 'absolute', bottom: 10, left: '50%', transform: 'translateX(-50%)',
                zIndex: 10, padding: '4px 12px', bgcolor: 'rgba(0,0,0,0.7)',
                color: 'rgba(255,255,255,0.8)', borderRadius: '4px', fontSize: '0.75rem',
                display: 'flex', gap: 2, alignItems: 'center', whiteSpace: 'nowrap'
            }}>
      <Typography variant="caption">Grid: {gridInputCells.x || '?'}×{gridInputCells.y || '?'} Cells</Typography>
      <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
      <Typography variant="caption">Zoom: {currentZoom.toFixed(2)}x</Typography>
      <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
      <Typography variant="caption">Modules: {nodes.filter(n => n.type === 'moduleNode').length}</Typography>
      <Typography variant="caption" sx={{color: 'rgba(255,255,255,0.4)'}}>|</Typography>
      <Typography variant="caption">Constraints: {activeConstraints.length}</Typography>
    </Box>
      </Box>
      {/* {isLoading && (
    <Box sx={{ 
      position: 'absolute', 
      top: 0, left: 0, right: 0, bottom: 0, 
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', 
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      zIndex: 999
    }}>
      <CircularProgress size={60} sx={{ color: '#9065f0', mb: 2 }} />
      <Typography variant="h6" sx={{ color: 'white' }}>
        Designing Data Center...
      </Typography>
    </Box> */}

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