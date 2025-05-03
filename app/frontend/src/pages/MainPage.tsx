import { useState } from 'react';
import {
  Box, TextField, Typography, Button
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
const CELL_SIZE = 10;
const ZOOM_SCALE = 2;


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

  const DraggableModule = ({ mod, spanX, spanY, onDragEnd }: {
    mod: PositionedModule;
    spanX: number;
    spanY: number;
    onDragEnd: (id: number, newCol: number, newRow: number) => void;
  }) => {
    const { attributes, listeners, setNodeRef } = useDraggable({
      id: mod.id.toString(),
    });
  
    return (
      <Box
        ref={setNodeRef}
        {...listeners}
        {...attributes}
        sx={{
          gridColumn: `${mod.gridColumn} / span ${spanX}`,
          gridRow: `${mod.gridRow} / span ${spanY}`,
          backgroundColor: '#1976d2',
          color: 'white',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          fontSize: 10,
          borderRadius: 1,
          zIndex: 1,
          overflow: 'hidden',
          textAlign: 'center',
          padding: 0.5,
          cursor: 'move',
        }}
      >
        {mod.name}
      </Box>
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

      <Box
        sx={{
          transform: 'scale(2)', // ⬅️ 2x bigger
          transformOrigin: 'top left', // ⬅️ keep layout aligned
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

    </Box>
  );
};

export default MainPage;
