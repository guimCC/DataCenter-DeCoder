import { useState, useEffect } from 'react';
import {
  Box, TextField, Typography, Button, Paper, MenuItem, Select, FormControl, InputLabel
} from '@mui/material';
import { PositionedModule, DataCenter } from '../types';

const GRID_ROWS = 20;
const GRID_COLS = 20;
const CELL_SIZE = 10;

import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import RestartAltIcon from '@mui/icons-material/RestartAlt';


const MainPage = () => {
  const [constraints, setConstraints] = useState({
    maxPrice: '',
    maxSpaceX: '',
    maxSpaceY: ''
  });

  const [datacenters, setDatacenters] = useState<DataCenter[]>([]);
  const [selectedDC, setSelectedDC] = useState<number | "">("");

  const [gridDimensions, setGridDimensions] = useState({
    rows: GRID_ROWS,
    cols: GRID_COLS
  });

  const [zoom, setZoom] = useState(1);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [ghostPreview, setGhostPreview] = useState({ visible: false, row: 0, col: 0 });
  
  // Color map for different module types
  const MODULE_COLORS = {
    transformer: '#E9DA54',    // Yellow
    water_supply: '#2196f3',   // Light blue
    water_treatment: '#03a9f4', // Cyan
    water_chiller: '#00bcd4',  // Teal
    network_rack: '#ff9800',   // Orange
    server_rack: '#4caf50',    // Green
    data_rack: '#9c27b0',      // Purple
    default: '#757575'         // Gray (fallback)
  };

  const [resultModules, setResultModules] = useState<PositionedModule[]>([]);
  const [draggedModuleId, setDraggedModuleId] = useState<number | null>(null);

  const handleChange = (field: string, value: string) => {
    setConstraints(prev => ({ ...prev, [field]: value }));
  };

  const handleDesign = () => {
    fetch("http://localhost:8000/solve-dummy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        constraints: {
          price: parseFloat(constraints.maxPrice),
          space_x: parseFloat(constraints.maxSpaceX),
          space_y: parseFloat(constraints.maxSpaceY),
        }
      })
    })
      .then(res => res.json())
      .then(data => setResultModules(data.modules || []))
      .catch(err => console.error("Design failed:", err));
  };

  // Handle drag start
  const handleDragStart = (id: number) => {
    setDraggedModuleId(id);
    console.log(`Started dragging module #${id}`);
  };

  // Handle drag end
  const handleDragEnd = (newCol: number, newRow: number) => {
      if (draggedModuleId === null) return;
      
      // Update module position
      setResultModules(prev =>
        prev.map(mod =>
          mod.id === draggedModuleId
            ? { ...mod, gridColumn: newCol, gridRow: newRow }
            : mod
        )
      );
      
      // Reset dragged module
      setDraggedModuleId(null);
    };
  
    useEffect(() => {
      console.log("Fetching datacenters...");
      
      fetch("http://localhost:8000/datacenters")
        .then(res => res.json())
        .then(data => {
          console.log("Datacenters received:", data);
          setDatacenters(data);
        })
        .catch(err => console.error("Failed to fetch datacenters", err));
    }, []);

    useEffect(() => {
      if (draggedModuleId !== null) {
        // Find the grid element to get its position
        const gridElement = document.getElementById('grid');
        if (!gridElement) return;
        
        const handleMouseMove = (e: MouseEvent) => {
          const rect = gridElement.getBoundingClientRect();
          
          // Calculate relative position within grid, accounting for zoom and scroll
          const containerElement = gridElement.parentElement?.parentElement?.parentElement;
          const scrollLeft = containerElement?.scrollLeft || 0;
          const scrollTop = containerElement?.scrollTop || 0;
          
          // Calculate position within grid considering scroll and zoom
          const x = (e.clientX - rect.left + scrollLeft) / zoom;
          const y = (e.clientY - rect.top + scrollTop) / zoom;
          
          // Calculate grid coordinates
          const gridCol = Math.max(1, Math.floor(x / CELL_SIZE) + 1);
          const gridRow = Math.max(1, Math.floor(y / CELL_SIZE) + 1);
          
          // Only show ghost if inside grid bounds
          const isInBounds = 
            gridCol > 0 && 
            gridCol <= gridDimensions.cols && 
            gridRow > 0 && 
            gridRow <= gridDimensions.rows;
          
          // Update position
          setMousePosition({ x: e.clientX, y: e.clientY });
          setGhostPreview({
            visible: isInBounds,
            col: gridCol,
            row: gridRow
          });
        };
        
        document.addEventListener('mousemove', handleMouseMove);
        return () => document.removeEventListener('mousemove', handleMouseMove);
      } else {
        setGhostPreview({ visible: false, row: 0, col: 0 });
      }
    }, [draggedModuleId, zoom, gridDimensions]);
    

  // Draggable module component
  // Change the DraggableModule component implementation:
const DraggableModule = ({ mod, spanX, spanY }: {
    mod: PositionedModule;
    spanX: number;
    spanY: number;
  }) => {
    // Get module type for coloring and sprite
    const getModuleType = () => {
      const name = mod.name.toLowerCase();
      if (name.startsWith('transformer')) return 'transformer';
      if (name.includes('network_rack')) return 'network_rack';
      if (name.includes('server_rack')) return 'server_rack';
      if (name.includes('data_rack')) return 'data_rack';
      if (name.includes('water_supply')) return 'water_supply';
      if (name.includes('water_treatment')) return 'water_treatment';
      if (name.includes('water_chiller')) return 'water_chiller';
      return 'default';
    };

    // Get color based on module type
    const getModuleColor = () => {
      const type = getModuleType();
      return MODULE_COLORS[type as keyof typeof MODULE_COLORS] || MODULE_COLORS.default;
    };

    // Get sprite path based on module type
    const getSpritePath = () => {
      const type = getModuleType();
      return `/sprites/${type === 'default' ? 'transformer' : type}.png`;
    };
    
    // State to track if this module is being dragged
    const isDragged = mod.id === draggedModuleId;
    
    return (
      <Box
        onClick={(e) => {
          e.stopPropagation(); // Prevent parent click from triggering
          if (!isDragged) {
            // Start dragging this module
            handleDragStart(mod.id);
          }
        }}
        sx={{
          gridColumn: `${mod.gridColumn} / span ${spanX}`,
          gridRow: `${mod.gridRow} / span ${spanY}`,
          backgroundColor: isDragged ? 'rgba(255, 255, 255, 0.3)' : getModuleColor(),
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          borderRadius: 1,
          zIndex: isDragged ? 2 : 1, // Higher z-index when dragging
          cursor: isDragged ? 'grabbing' : 'grab', // Better cursor indicators
          padding: 0.5,
          border: isDragged ? '2px dashed white' : '1px solid rgba(255, 255, 255, 0.2)',
          opacity: isDragged ? 0.7 : 1,
          transition: '0.2s all',
          '&:hover': {
            boxShadow: '0 0 0 2px white',
            opacity: 0.9,
          },
          position: 'relative', // Important for positioning
        }}
      >
        {/* Add module name label */}
        <Typography 
          variant="caption" 
          sx={{ 
            position: 'absolute',
            top: 0,
            left: 2,
            color: 'white',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '2px 4px',
            borderRadius: 1,
            fontSize: '0.7rem',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            maxWidth: '90%'
          }}
        >
          {mod.name}
        </Typography>

        <Box
          component="img"
          src={getSpritePath()}
          alt={mod.name}
          sx={{
            width: '80%',
            height: '80%',
            objectFit: 'contain',
            filter: 'brightness(1.1)',
            pointerEvents: 'none', // Prevent image from interfering with clicks
          }}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </Box>
    );
};

  // Legend component
  const ModuleLegend = () => {
    const moduleTypes = [
      { name: 'transformer', displayName: 'Transformer' },
      { name: 'water_supply', displayName: 'Water Supply' },
      { name: 'water_treatment', displayName: 'Water Treatment' },
      { name: 'water_chiller', displayName: 'Water Chiller' },
      { name: 'network_rack', displayName: 'Network Rack' },
      { name: 'server_rack', displayName: 'Server Rack' },
      { name: 'data_rack', displayName: 'Data Rack' },
    ];
  
    return (
      <Paper sx={{ 
        p: 2, 
        ml: 2, 
        width: 200, 
        backgroundColor: 'rgba(32, 20, 52, 0.85)', // Match main background but with transparency
        position: 'absolute',
        right: 20,
        top: 20,
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
        zIndex: 2,
      }}>
        <Typography variant="h6" gutterBottom sx={{ color: 'white' }}>Legend</Typography>
        {moduleTypes.map((type) => (
          <Box key={type.name} sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            mb: 1,
            p: 0.5,
            borderRadius: 1,
            backgroundColor: MODULE_COLORS[type.name as keyof typeof MODULE_COLORS],
          }}>
            <Box
              component="img"
              src={`/sprites/${type.name}.png`}
              alt={type.displayName}
              sx={{ 
                width: 24, 
                height: 24, 
                mr: 1,
                filter: 'brightness(1.1)',
              }}
              onError={(e) => {
                console.log(`Error loading image: /sprites/${type.name}.png`);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <Typography variant="body2" sx={{ color: 'white', fontWeight: 'bold' }}>
              {type.displayName}
            </Typography>
          </Box>
        ))}
      </Paper>
    );
  };

  // Real-time constraints panel component
  const ConstraintsPanel = () => {
    // Calculate current usage
    const totalPrice = resultModules.reduce((sum, mod) => {
      const price = mod.io_fields.find(io => io.unit === 'Price')?.amount || 0;
      return sum + price;
    }, 0);
    
    // Find max X and Y positions
    const maxX = resultModules.reduce((max, mod) => {
      const spaceX = mod.io_fields.find(io => io.unit === 'Space_X')?.amount || 0;
      const spanX = Math.ceil(spaceX / CELL_SIZE);
      return Math.max(max, mod.gridColumn + spanX - 1);
    }, 0);
    
    const maxY = resultModules.reduce((max, mod) => {
      const spaceY = mod.io_fields.find(io => io.unit === 'Space_Y')?.amount || 0;
      const spanY = Math.ceil(spaceY / CELL_SIZE);
      return Math.max(max, mod.gridRow + spanY - 1);
    }, 0);
    
    // Calculate total power, cooling, processing
    const totalPower = resultModules.reduce((sum, mod) => {
      const power = mod.io_fields.find(io => !io.is_input && io.unit === 'Power')?.amount || 0;
      return sum + power;
    }, 0);
    
    const totalCooling = resultModules.reduce((sum, mod) => {
      const cooling = mod.io_fields.find(io => !io.is_input && io.unit === 'Cooling')?.amount || 0;
      return sum + cooling;
    }, 0);
    
    const totalProcessing = resultModules.reduce((sum, mod) => {
      const processing = mod.io_fields.find(io => !io.is_input && io.unit === 'Processing')?.amount || 0;
      return sum + processing;
    }, 0);
    
    // Check if constraints are met
    const isPriceInLimit = !constraints.maxPrice || totalPrice <= parseFloat(constraints.maxPrice);
    const isSpaceXInLimit = !constraints.maxSpaceX || maxX <= parseFloat(constraints.maxSpaceX);
    const isSpaceYInLimit = !constraints.maxSpaceY || maxY <= parseFloat(constraints.maxSpaceY);
    
    return (
      <Paper sx={{ 
        p: 2, 
        width: 250, 
        backgroundColor: 'rgba(32, 20, 52, 0.85)',
        position: 'absolute',
        left: 20,
        top: 20,
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
        zIndex: 2,
      }}>
        <Typography variant="h6" gutterBottom sx={{ color: 'white' }}>Constraints Status</Typography>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Price Usage:</Typography>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center',
            gap: 1, 
          }}>
            <Box sx={{ 
              flex: 1, 
              height: 10, 
              bgcolor: 'rgba(255,255,255,0.1)', 
              borderRadius: 5,
              overflow: 'hidden'
            }}>
              <Box 
                sx={{ 
                  height: '100%', 
                  width: constraints.maxPrice ? `${Math.min(100, (totalPrice / parseFloat(constraints.maxPrice)) * 100)}%` : '0%',
                  bgcolor: isPriceInLimit ? '#4caf50' : '#f44336'
                }} 
              />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
              {totalPrice}/{constraints.maxPrice || '∞'}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Space X Usage:</Typography>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center',
            gap: 1, 
          }}>
            <Box sx={{ 
              flex: 1, 
              height: 10, 
              bgcolor: 'rgba(255,255,255,0.1)', 
              borderRadius: 5,
              overflow: 'hidden'
            }}>
              <Box 
                sx={{ 
                  height: '100%', 
                  width: constraints.maxSpaceX ? `${Math.min(100, (maxX / parseFloat(constraints.maxSpaceX)) * 100)}%` : '0%',
                  bgcolor: isSpaceXInLimit ? '#4caf50' : '#f44336'
                }} 
              />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
              {maxX}/{constraints.maxSpaceX || '∞'}
            </Typography>
          </Box>
        </Box>
        
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Space Y Usage:</Typography>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center',
            gap: 1, 
          }}>
            <Box sx={{ 
              flex: 1, 
              height: 10, 
              bgcolor: 'rgba(255,255,255,0.1)', 
              borderRadius: 5,
              overflow: 'hidden'
            }}>
              <Box 
                sx={{ 
                  height: '100%', 
                  width: constraints.maxSpaceY ? `${Math.min(100, (maxY / parseFloat(constraints.maxSpaceY)) * 100)}%` : '0%',
                  bgcolor: isSpaceYInLimit ? '#4caf50' : '#f44336'
                }} 
              />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
              {maxY}/{constraints.maxSpaceY || '∞'}
            </Typography>
          </Box>
        </Box>
        
        <Typography variant="h6" gutterBottom sx={{ color: 'white', mt: 3 }}>Production</Typography>
        
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Power:</Typography>
          <Typography variant="body2" sx={{ color: '#4caf50' }}>{totalPower}</Typography>
        </Box>
        
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Cooling:</Typography>
          <Typography variant="body2" sx={{ color: '#2196f3' }}>{totalCooling}</Typography>
        </Box>
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Processing:</Typography>
          <Typography variant="body2" sx={{ color: '#ff9800' }}>{totalProcessing}</Typography>
        </Box>
      </Paper>
    );
  };

  // Create a grid cell click handler component
  const GridCell = ({ row, col, onClick }: { row: number; col: number; onClick: (row: number, col: number) => void }) => {
    // Check if we're dragging and this cell could be a valid drop target
    const isDropTarget = draggedModuleId !== null;
    
    return (
      <Box
        onClick={() => onClick(row, col)}
        sx={{
          gridColumn: col,
          gridRow: row,
          width: CELL_SIZE,
          height: CELL_SIZE,
          cursor: isDropTarget ? 'cell' : 'default',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: isDropTarget ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
            boxShadow: isDropTarget ? 'inset 0 0 0 1px rgba(255, 255, 255, 0.5)' : 'none',
          },
          transition: 'background-color 0.2s',
          zIndex: 0,
        }}
      />
    );
  };

  // Cell click handler
  const handleCellClick = (row: number, col: number) => {
    if (draggedModuleId !== null) {
      console.log(`Dropping module #${draggedModuleId} at cell: row=${row}, col=${col}`);
      
      // Get the module being dragged
      const draggedModule = resultModules.find(mod => mod.id === draggedModuleId);
      if (!draggedModule) {
        console.warn('Could not find dragged module');
        setDraggedModuleId(null);
        return;
      }
  
      // Get module dimensions for collision detection
      const spanX = draggedModule.width;
      const spanY = draggedModule.height;
      
      // Ensure the module doesn't go outside grid bounds
      if (col + spanX - 1 > gridDimensions.cols || row + spanY - 1 > gridDimensions.rows) {
        console.warn('Cannot place module: would extend beyond grid boundaries');
        // Optionally show a warning to the user here
        return;
      }
  
      // Update module position
      setResultModules(prev =>
        prev.map(mod =>
          mod.id === draggedModuleId
            ? { ...mod, gridColumn: col, gridRow: row }
            : mod
        )
      );
      
      // Reset dragged module
      setDraggedModuleId(null);
    }
  };

  const cancelDrag = () => {
    if (draggedModuleId !== null) {
      setDraggedModuleId(null);
      console.log('Drag canceled');
    }
  };
  
  // Add keyboard support for drag operations
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && draggedModuleId !== null) {
        cancelDrag();
      }
    };
  
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [draggedModuleId]);

  return (
    <Box
      sx={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: '2rem',
        paddingBottom: '2rem',
        gap: 2,
        backgroundColor: '#201434',
        overflow: 'hidden',
      }}
    >
      {/* Header Controls */}
      <FormControl sx={{ minWidth: 200 }}>
        <InputLabel id="dc-select-label" sx={{ color: 'white' }}>Load Datacenter</InputLabel>
        <Select
          labelId="dc-select-label"
          value={selectedDC}
          onChange={(e) => {
            const dcId = e.target.value as number;
            setSelectedDC(dcId);
            
            const selected = datacenters.find(dc => dc.id === dcId);
            console.log("Selected datacenter:", selected);
            
            if (selected) {
              // Find space constraints in specs
              const spaceXSpec = selected.specs.find(spec => 
                spec.Unit?.toLowerCase() === "space_x");
              const spaceYSpec = selected.specs.find(spec => 
                spec.Unit?.toLowerCase() === "space_y");
          
              let maxGridX = 0;
              let maxGridY = 0;
              
              // Get specs dimensions
              if (spaceXSpec?.Amount) {
                maxGridX = Math.max(maxGridX, Math.ceil(spaceXSpec.Amount / CELL_SIZE));
              }
              if (spaceYSpec?.Amount) {
                maxGridY = Math.max(maxGridY, Math.ceil(spaceYSpec.Amount / CELL_SIZE));
              }
              
              // Update grid dimensions with padding
              maxGridX = Math.max(maxGridX + 5, GRID_COLS);
              maxGridY = Math.max(maxGridY + 5, GRID_ROWS);

              setGridDimensions({
                rows: maxGridY,
                cols: maxGridX
              });
              
              console.log(`Adjusting grid to ${maxGridX} x ${maxGridY} cells`);
              
              // Update constraints
              setConstraints({
                maxPrice: selected.specs.find(spec => 
                  spec.Unit?.toLowerCase() === "price")?.Amount?.toString() || "",
                maxSpaceX: spaceXSpec?.Amount?.toString() || "", 
                maxSpaceY: spaceYSpec?.Amount?.toString() || "",
              });
          
              // Convert modules with proper coordinate transformation
              if (Array.isArray(selected.modules)) {
                const mods: PositionedModule[] = selected.modules.map((m) => {
                  
                  // Convert raw coordinates to grid coordinates if they exist,
                  // otherwise use the module's actual position properties
                  const gridCol = Math.floor((m.gridColumn || 0) / CELL_SIZE) + 1;
                  const gridRow = Math.floor((m.gridRow || 0) / CELL_SIZE) + 1;

                  return {
                    id: m.id,
                    name: m.name,
                    gridColumn: gridCol,
                    gridRow: gridRow,
                    height: Math.ceil(m.height / CELL_SIZE),
                    width: Math.ceil(m.width / CELL_SIZE),
                    io_fields: m.io_fields || []
                  };
                });
                
                setResultModules(mods);
              } else {
                console.error("Modules is not an array:", selected.modules);
              }
            }
          }}
          sx={{ color: 'white' }}
        >
          {datacenters.map(dc => (
            <MenuItem key={dc.id} value={dc.id}>{dc.name}</MenuItem>
          ))}
        </Select>
      </FormControl>
  
      <Typography variant="h4" color="white">DataCenter Specs</Typography>
  
      <Box sx={{ display: 'flex', gap: 2 }}>
        <TextField
          label="Max Price"
          value={constraints.maxPrice}
          onChange={(e) => handleChange('maxPrice', e.target.value)}
          type="number"
        />
        <TextField
          label="Max Space X"
          value={constraints.maxSpaceX}
          onChange={(e) => handleChange('maxSpaceX', e.target.value)}
          type="number"
        />
        <TextField
          label="Max Space Y"
          value={constraints.maxSpaceY}
          onChange={(e) => handleChange('maxSpaceY', e.target.value)}
          type="number"
        />
        <Button variant="contained" onClick={handleDesign}>
          Design
        </Button>
      </Box>
  
      <Typography variant="h6" color="white">Configuration Result:</Typography>
  
      {/* Main visualization container - FIXED HEIGHT */}
      <Box sx={{ 
        width: '90%',
        height: '60vh',
        position: 'relative',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 2,
        overflow: 'hidden', // This prevents overflow
      }}>
        {/* Zoom controls */}
        <Paper sx={{ 
          position: 'absolute',
          bottom: 16,
          right: 16,
          zIndex: 10,
          padding: 1,
          display: 'flex',
          backgroundColor: 'rgba(32, 20, 52, 0.85)',
          gap: 1,
          borderRadius: 1,
        }}>
          <Button 
            variant="outlined" 
            size="small"
            onClick={() => setZoom(prev => Math.max(0.5, prev - 0.2))}
            sx={{ minWidth: '40px', color: 'white' }}
          >
            <ZoomOutIcon />
          </Button>
          <Typography sx={{ 
            color: 'white', 
            display: 'flex', 
            alignItems: 'center',
            px: 1,
          }}>
            {Math.round(zoom * 100)}%
          </Typography>
          <Button 
            variant="outlined" 
            size="small"
            onClick={() => setZoom(prev => Math.min(3, prev + 0.2))}
            sx={{ minWidth: '40px', color: 'white' }}
          >
            <ZoomInIcon />
          </Button>
          <Button 
            variant="outlined" 
            size="small"
            onClick={() => setZoom(1)}
            sx={{ minWidth: '40px', color: 'white' }}
          >
            <RestartAltIcon />
          </Button>
        </Paper>
  
        {/* Status message when dragging */}
        {draggedModuleId !== null && (
          <Box
            sx={{
              position: 'absolute',
              bottom: 16,
              left: 16,
              zIndex: 10,
              padding: 1,
              backgroundColor: 'rgba(0,0,0,0.7)',
              color: 'white',
              borderRadius: 1,
            }}
          >
            Dragging Module #{draggedModuleId} - Click on a grid cell to place
          </Box>
        )}
  
        {/* Grid dimensions indicator */}
        <Box
          sx={{
            position: 'absolute',
            bottom: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 10,
            padding: 1,
            backgroundColor: 'rgba(0,0,0,0.7)',
            color: 'white',
            borderRadius: 1,
          }}
        >
          Grid: {gridDimensions.cols} × {gridDimensions.rows}
        </Box>
  
        {/* Scrollable container with AUTOMATIC sizing */}
        <Box
          sx={{
            width: '100%',
            height: '100%',
            overflow: 'auto', // Enable scrolling when content is larger than container
            position: 'relative',
          }}
          onClick={() => {
            if (draggedModuleId !== null) {
              cancelDrag();
            }
          }}
        >
          {/* Centered grid with zoom */}
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'flex-start',
              minHeight: '100%',
              padding: 2,
            }}
          >
            <Box
              sx={{
                transformOrigin: 'top left',
                transform: `scale(${zoom})`,
                transition: 'transform 0.2s ease',
              }}
            >
              {/* The actual grid */}
              <Box
                id="grid"
                sx={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${gridDimensions.cols}, ${CELL_SIZE}px)`,
                  gridTemplateRows: `repeat(${gridDimensions.rows}, ${CELL_SIZE}px)`,
                  backgroundColor: '#201434',
                  border: '1px solid #333',
                  backgroundImage: `
                    linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                    linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
                  `,
                  backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
                  position: 'relative',
                }}
              >
                {/* Grid cells for click handling */}
                {Array.from({ length: gridDimensions.rows }, (_, rowIndex) =>
                  Array.from({ length: gridDimensions.cols }, (_, colIndex) => (
                    <GridCell
                      key={`cell-${rowIndex + 1}-${colIndex + 1}`}
                      row={rowIndex + 1}
                      col={colIndex + 1}
                      onClick={handleCellClick}
                    />
                  ))
                )}
                
                {/* Modules with unique keys */}
                {resultModules.map((mod, index) => (
                  <DraggableModule
                    key={`module-${mod.id}-${index}`}
                    mod={mod}
                    spanX={mod.width}  // Use the calculated width property
                    spanY={mod.height} // Use the calculated height property
                  />
                ))}
                {/* Add ghost preview here */}
                {ghostPreview.visible && draggedModuleId !== null && (() => {
                // Get the module being dragged for size info
                const draggedModule = resultModules.find(mod => mod.id === draggedModuleId);
                if (!draggedModule) return null;
                
                // Get module dimensions

                const spanX = draggedModule.width;
                const spanY = draggedModule.height;
                
                // Check if placement would go out of bounds
                const outOfBounds = (ghostPreview.col + spanX - 1 > gridDimensions.cols || 
                                    ghostPreview.row + spanY - 1 > gridDimensions.rows);
                
                return (
                  <Box
                    sx={{
                      gridColumn: `${ghostPreview.col} / span ${spanX}`,
                      gridRow: `${ghostPreview.row} / span ${spanY}`,
                      backgroundColor: outOfBounds ? 'rgba(255, 0, 0, 0.2)' : 'rgba(255, 255, 255, 0.3)',
                      border: `2px dashed ${outOfBounds ? 'red' : 'white'}`,
                      zIndex: 1,
                      pointerEvents: 'none', // Important to not interfere with clicks
                    }}
                  />
                );
                })()}
              </Box>
            </Box>
          </Box>
        </Box>
        
        {/* Legends and panels (positioned absolutely) */}
        {resultModules.length > 0 && (
          <>
            <ModuleLegend />
            <ConstraintsPanel />
          </>
        )}
      </Box>
    </Box>
  );
};

export default MainPage;