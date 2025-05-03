import { useState } from 'react';
import {
  Box, TextField, Typography, Button, Paper
} from '@mui/material';
import { PositionedModule } from '../types';

const GRID_ROWS = 20;
const GRID_COLS = 20;
const CELL_SIZE = 20;
const ZOOM_SCALE = 1.5;

const MainPage = () => {
  const [constraints, setConstraints] = useState({
    maxPrice: '',
    maxSpaceX: '',
    maxSpaceY: ''
  });

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

  // Helper function to extract module type from name
  const getModuleTypeByName = (name: string) => {
    const nameLower = name.toLowerCase();
    if (nameLower.startsWith('transformer')) return 'transformer';
    if (nameLower.includes('network_rack')) return 'network_rack';
    if (nameLower.includes('server_rack')) return 'server_rack';
    if (nameLower.includes('data_rack')) return 'data_rack';
    if (nameLower.includes('water_supply')) return 'water_supply';
    if (nameLower.includes('water_treatment')) return 'water_treatment';
    if (nameLower.includes('water_chiller')) return 'water_chiller';
    return 'default';
  };

  const getModuleColorById = (mod: PositionedModule) => {
    const type = getModuleTypeByName(mod.name);
    return MODULE_COLORS[type as keyof typeof MODULE_COLORS] || MODULE_COLORS.default;
  };

  const getModuleSpriteById = (mod: PositionedModule) => {
    const type = getModuleTypeByName(mod.name);
    return `/sprites/${type === 'default' ? 'transformer' : type}.png`;
  };

  const getModuleSizeX = (mod: PositionedModule) => {
    const spaceX = mod.io_fields.find(io => io.unit === 'Space_X')?.amount || 1;
    return Math.max(1, Math.round(spaceX / CELL_SIZE));
  };

  const getModuleSizeY = (mod: PositionedModule) => {
    const spaceY = mod.io_fields.find(io => io.unit === 'Space_Y')?.amount || 1;
    return Math.max(1, Math.round(spaceY / CELL_SIZE));
  };

  // Handle drag start
  const handleDragStart = (id: number) => {
    setDraggedModuleId(id);
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

  // Draggable module component
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
    
    // Handle click on a grid cell
    const handleCellClick = () => {
      if (draggedModuleId !== null) {
        // If we're in dragging mode, handle dropping on this cell
        handleDragEnd(mod.gridColumn, mod.gridRow);
      } else {
        // Start dragging this module
        handleDragStart(mod.id);
      }
    };
      
    return (
      <Box
        onClick={handleCellClick}
        sx={{
          gridColumn: `${mod.gridColumn} / span ${spanX}`,
          gridRow: `${mod.gridRow} / span ${spanY}`,
          backgroundColor: mod.id === draggedModuleId ? 'rgba(255, 255, 255, 0.3)' : getModuleColor(),
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          borderRadius: 1,
          zIndex: 1,
          cursor: mod.id === draggedModuleId ? 'default' : 'pointer',
          padding: 0.5,
          border: mod.id === draggedModuleId ? '2px dashed white' : '1px solid rgba(255, 255, 255, 0.2)',
          opacity: mod.id === draggedModuleId ? 0.7 : 1,
          transition: '0.2s all',
          '&:hover': {
            boxShadow: '0 0 0 2px white',
          }
        }}
      >
        <Box
          component="img"
          src={getSpritePath()}
          alt={mod.name}
          sx={{
            width: '80%',
            height: '80%',
            objectFit: 'contain',
            filter: 'brightness(1.1)',
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
    return (
      <Box
        onClick={() => onClick(row, col)}
        sx={{
          gridColumn: col,
          gridRow: row,
          width: CELL_SIZE,
          height: CELL_SIZE,
          cursor: draggedModuleId !== null ? 'cell' : 'default',
          '&:hover': {
            backgroundColor: draggedModuleId !== null ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
          },
          zIndex: 0,
        }}
      />
    );
  };

  // Cell click handler
  const handleCellClick = (row: number, col: number) => {
    if (draggedModuleId !== null) {
      console.log(`Cell clicked: row=${row}, col=${col}`);
      // Place the module with its top-left corner at this cell
      setResultModules(prev =>
        prev.map(mod =>
          mod.id === draggedModuleId
            ? { ...mod, gridColumn: col, gridRow: row }
            : mod
        )
      );
      setDraggedModuleId(null);
    }
  };

  return (
    <Box
      sx={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: '4rem',
        gap: 4,
        backgroundColor: '#201434',
        overflow: 'hidden',
      }}
    >
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

      {/* Contenedor flexible para el grid y la leyenda */}
      <Box sx={{ 
        display: 'flex', 
        width: '100%',
        justifyContent: 'center',
        position: 'relative',
        marginLeft: 'auto',
        marginRight: 'auto',
      }}>
        {/* Grid con zoom centrado */}
        <Box
          sx={{
            transform: 'scale(2)',
            transformOrigin: 'center top',
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <Box
            id="grid"
            sx={{
              display: 'grid',
              gridTemplateColumns: `repeat(${GRID_COLS}, ${CELL_SIZE}px)`,
              gridTemplateRows: `repeat(${GRID_ROWS}, ${CELL_SIZE}px)`,
              backgroundColor: '#201434',
              border: '1px solid #333',
              backgroundImage: `
                linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)
              `,
              backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
              position: 'relative',
              overflow: 'visible',
            }}
          >
            {/* Create explicit grid cells for clicking */}
            {Array.from({ length: GRID_ROWS }, (_, rowIndex) =>
              Array.from({ length: GRID_COLS }, (_, colIndex) => (
                <GridCell
                  key={`cell-${rowIndex + 1}-${colIndex + 1}`}
                  row={rowIndex + 1}
                  col={colIndex + 1}
                  onClick={handleCellClick}
                />
              ))
            )}
            
            {/* Render modules on top of the cells */}
            {resultModules.map((mod) => {
              const spaceX = mod.io_fields.find(io => io.unit === 'Space_X')?.amount || 1;
              const spaceY = mod.io_fields.find(io => io.unit === 'Space_Y')?.amount || 1;

              const spanX = Math.max(1, Math.round(spaceX / CELL_SIZE));
              const spanY = Math.max(1, Math.round(spaceY / CELL_SIZE));

              return (
                <DraggableModule
                  key={mod.id}
                  mod={mod}
                  spanX={spanX}
                  spanY={spanY}
                />
              );
            })}
          </Box>
        </Box>
        
        {/* Leyenda y panel de restricciones (sólo cuando hay módulos) */}
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