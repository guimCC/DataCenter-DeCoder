import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Divider,
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
      }}
    >
      <Typography variant="h4" textAlign="center" gutterBottom>
        Available Modules
      </Typography>

      <Grid container spacing={3} justifyContent="center">
        {modules.map((mod, i) => (
          <Grid item key={i} xs={12} sm={10} md={6} lg={4}>
            <Card
              sx={{
                backgroundColor: '#2a1b4f',
                border: '1px solid #444',
              }}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {mod.name}
                </Typography>

                <Divider sx={{ borderColor: '#444', mb: 1 }} />

                {mod.io_fields.map((io, j) => (
                  <Typography
                    key={j}
                    variant="body2"
                    sx={{ color: io.is_input ? '#90caf9' : '#80cbc4' }}
                  >
                    {io.is_input ? 'Input' : 'Output'} — {io.unit}: {io.amount}
                  </Typography>
                ))}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default ViewModulesPage;
