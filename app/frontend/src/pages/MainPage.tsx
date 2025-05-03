import { useState } from 'react';
import {
  Box, TextField, Typography, Button
} from '@mui/material';
import { PositionedModule } from '../types';

const GRID_ROWS = 20;
const GRID_COLS = 20;
const CELL_SIZE = 10;

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
        {resultModules.map((mod, i) => {
          const spaceX = mod.io_fields.find(io => io.unit === 'Space_X')?.amount || 1;
          const spaceY = mod.io_fields.find(io => io.unit === 'Space_Y')?.amount || 1;

          const spanX = Math.max(1, Math.round(spaceX / CELL_SIZE));
          const spanY = Math.max(1, Math.round(spaceY / CELL_SIZE));

          return (
            <Box
              key={`mod-${i}`}
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
              }}
            >
              {mod.name}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

export default MainPage;
