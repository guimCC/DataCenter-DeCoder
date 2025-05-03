import { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent
} from '@mui/material';
import { Module } from '../types';

const ViewModulesPage = () => {
  const [modules, setModules] = useState<Module[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/modules")
      .then(res => res.json())
      .then(data => setModules(data))
      .catch(err => console.error("Failed to fetch modules:", err));
  }, []);

  return (
    <Box
      sx={{
        height: '100vh',
        width: '100vw',
        backgroundColor: '#201434',
        padding: '4rem 2rem',
        overflowY: 'auto',
        boxSizing: 'border-box',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 3
      }}
    >
      <Typography variant="h4">All Available Modules</Typography>

      {modules.map((mod, i) => (
        <Card
          key={i}
          sx={{
            width: '100%',
            maxWidth: '600px',
            backgroundColor: '#2a1b4f',
            color: 'white',
            border: '1px solid #444'
          }}
        >
          <CardContent>
            <Typography variant="h6">{mod.name}</Typography>
            {mod.io_fields.map((io, j) => (
              <Typography key={j} variant="body2">
                {io.is_input ? 'Input' : 'Output'} - {io.unit}: {io.amount}
              </Typography>
            ))}
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};

export default ViewModulesPage;
