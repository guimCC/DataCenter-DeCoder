import { useState } from 'react';
import {
  Box, TextField, Typography, Button, Grid, Paper
} from '@mui/material';
import { Module } from '../types';


const GRID_ROWS = 10;
const GRID_COLS = 10;
const CELL_SIZE = 40; // pixels (each "5x5 space" will be 40x40)


const MainPage = () => {
  const [constraints, setConstraints] = useState({
    maxPrice: '',
    maxSpaceX: '',
    maxSpaceY: ''
  });

  const [resultModules, setResultModules] = useState<Module[]>([]);

  const handleChange = (field: string, value: string) => {
    setConstraints(prev => ({ ...prev, [field]: value }));
  };

  const handleDesign = () => {
    fetch("http://localhost:8000/solve", {
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

  const renderEmptyCells = () => {
    const total = GRID_ROWS * GRID_COLS;
    return Array.from({ length: total }).map((_, index) => (
      <Box
        key={`cell-${index}`}
        sx={{
          width: CELL_SIZE,
          height: CELL_SIZE,
          border: '1px solid rgba(0,0,0,0.1)',
          boxSizing: 'border-box',
        }}
      />
    ));
  };
  

  return (
    <Box>
      <Typography variant="h4" gutterBottom>DataCenter Specs</Typography>

      {/* === Constraint Input Form === */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
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

      {/* === Result Grid === */}
      <Typography variant="h6">Configuration Result:</Typography>
      {/* === Visual Grid Layout === */}
      <Box /* Això és la GRID en sí*/
        sx={{
          display: 'grid',
          gridTemplateColumns: `repeat(${GRID_COLS}, ${CELL_SIZE}px)`,
          gridTemplateRows: `repeat(${GRID_ROWS}, ${CELL_SIZE}px)`,
          gap: '2px',
          backgroundColor: '#ccc',
          padding: 1,
          width: `${GRID_COLS * (CELL_SIZE + 2)}px`,
          height: `${GRID_ROWS * (CELL_SIZE + 2)}px`,
          border: '1px solid black',
          position: 'relative',
        }}
      >
        {renderEmptyCells()}
        {resultModules.map((mod, i) => (
          <Box /* Això és cada MODUL*/
            key={i}
            sx={{
              gridColumn: `${1 + (i % GRID_COLS)} / span 2`, // for now, place in a line
              gridRow: `${1 + Math.floor(i / GRID_COLS)} / span 2`,
              backgroundColor: '#1976d2',
              color: 'white',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              fontSize: 12,
              borderRadius: 1,
            }}
          >
            {mod.name}
          </Box>
        ))}
      </Box>

    </Box>
  );
};

export default MainPage;
