import { useState } from 'react';
import {
  Box, TextField, Typography, Button, Paper
} from '@mui/material';
import { PositionedModule } from '../types';
import {
  DndContext,
  useDraggable,
  useDroppable,
  DragEndEvent
} from '@dnd-kit/core';


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

  const [resultModules, setResultModules] = useState<PositionedModule[]>([]);

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

  // Replace your current DraggableModule component with this:

  const DraggableModule = ({ mod, spanX, spanY, onDragEnd }: {
    mod: PositionedModule;
    spanX: number;
    spanY: number;
    onDragEnd: (id: number, newCol: number, newRow: number) => void;
  }) => {
    const { attributes, listeners, setNodeRef } = useDraggable({
      id: mod.id.toString(),
    });
  
    // Get sprite name from module name
    // Get sprite name from module name
    // Get sprite name from module name
    // Modifica tu función getSpritePath
    const getSpritePath = () => {
      let path = '';
      console.log(`Procesando módulo: ${mod.name}`);
      
      // Para transformador, el formato es "Transformer_100"
      if (mod.name.toLowerCase().startsWith('transformer')) {
        path = `/sprites/transformer.png`;
      }
      // Para Network_Rack, Server_Rack, Data_Rack (formato es "Network_Rack_50")
      else if (mod.name.toLowerCase().includes('network_rack')) {
        path = `/sprites/network_rack.png`;
      }
      else if (mod.name.toLowerCase().includes('server_rack')) {
        path = `/sprites/server_rack.png`;
      }
      else if (mod.name.toLowerCase().includes('data_rack')) {
        path = `/sprites/data_rack.png`;
      }
      // Para sistemas de agua (Water_Supply, Water_Treatment, Water_Chiller)
      else if (mod.name.toLowerCase().includes('water_supply')) {
        path = `/sprites/water_supply.png`;
      }
      else if (mod.name.toLowerCase().includes('water_treatment')) {
        path = `/sprites/water_treatment.png`;
      }
      else if (mod.name.toLowerCase().includes('water_chiller')) {
        path = `/sprites/water_chiller.png`;
      }
      // Para cualquier otro caso, usa el transformador como fallback
      else {
        path = `/sprites/transformer.png`;
      }
      
      console.log(`Ruta del sprite: ${path}`);
      return path;
    };
      
    return (
      <Box
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        sx={{
          gridColumn: `${mod.gridColumn} / span ${spanX}`,
          gridRow: `${mod.gridRow} / span ${spanY}`,
          backgroundColor: '#1976d2',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          borderRadius: 1,
          zIndex: 1,
          cursor: 'move',
          padding: 0.5,
        }}
      >
        {/* Solo el sprite sin el nombre */}
        <Box
          component="img"
          src={getSpritePath()}
          alt={mod.name}
          sx={{
            width: '80%',          // Relativo al tamaño de la celda
            height: '80%',         // Relativo al tamaño de la celda
            objectFit: 'contain',
          }}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </Box>
    );
  };

  // Añade este componente para la leyenda
  // Modifica el componente ModuleLegend
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
        backgroundColor: 'rgba(200, 200, 200, 0.9)', 
        position: 'absolute',
        right: 20,
        top: 20,
      }}>
        <Typography variant="h6" gutterBottom sx={{ color: '#333' }}>Legend</Typography>
        {moduleTypes.map((type) => (
          <Box key={type.name} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Box
              component="img"
              src={`/sprites/${type.name}.png`}
              alt={type.displayName}
              sx={{ width: 24, height: 24, mr: 1 }}
              onError={(e) => {
                console.log(`Error loading image: /sprites/${type.name}.png`);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <Typography variant="body2" sx={{ color: '#333' }}>
              {type.displayName}
            </Typography>
          </Box>
        ))}
      </Paper>
    );
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const draggedId = parseInt(event.active.id as string);
  
    const grid = document.getElementById("grid");
    if (!grid) return;
  
    const gridRect = grid.getBoundingClientRect();
  
    // Translate pointer position, adjusted for zoom
    const translatedLeft = event.active.rect.current.translated?.left ?? 0;
    const translatedTop = event.active.rect.current.translated?.top ?? 0;
  
    const relativeX = (translatedLeft - gridRect.left) / ZOOM_SCALE;
    const relativeY = (translatedTop - gridRect.top) / ZOOM_SCALE;
  
    const newCol = Math.floor(relativeX / CELL_SIZE) + 1;
    const newRow = Math.floor(relativeY / CELL_SIZE) + 1;
  
    setResultModules(prev =>
      prev.map(mod =>
        mod.id === draggedId
          ? {
              ...mod,
              gridColumn: Math.max(1, Math.min(GRID_COLS, newCol)),
              gridRow: Math.max(1, Math.min(GRID_ROWS, newRow)),
            }
          : mod
      )
    );
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
    <Box sx={{ display: 'flex', width: '100%', justifyContent: 'center', gap: 2 }}>
      {/* Grid con zoom */}
      <Box
        sx={{
          transform: 'scale(2)',
          transformOrigin: 'top left',
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
          <DndContext onDragEnd={handleDragEnd}>
            {resultModules.map((mod, i) => {
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
                  onDragEnd={handleDragEnd}
                />
              );
            })}
          </DndContext>
        </Box>
      </Box>
      
      {/* Leyenda al lado del grid */}
      {resultModules.length > 0 && <ModuleLegend />}
    </Box>
  </Box>
);
};
export default MainPage;
