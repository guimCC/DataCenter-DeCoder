import { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { Module } from '../types';

const getModuleType = (name: string) => {
  const lower = name.toLowerCase();

  if (lower.startsWith('transformer')) return 'Transformer';
  if (lower.includes('chiller')) return 'Water Chiller';
  if (lower.includes('supply')) return 'Water Supply';
  if (lower.includes('treatment')) return 'Water Treatment';
  if (lower.includes('recycling')) return 'Water Recycling';
  if (lower.includes('liquid')) return 'Liquid Cooling';
  if (lower.includes('heat')) return 'Heat Recovery';
  if (lower.startsWith('ups')) return 'UPS';
  if (lower.startsWith('server')) return 'Server Rack';
  if (lower.startsWith('data')) return 'Data Rack';
  if (lower.startsWith('network')) return 'Network Rack';
  if (lower.startsWith('core') || lower.includes('firewall')) return 'Network Infra';
  if (lower.startsWith('gpu')) return 'GPU Rack';
  if (lower.includes('archive')) return 'Archive Storage';

  return 'Other';
};

const ViewModulesPage = () => {
  const [modules, setModules] = useState<Module[]>([]);

  useEffect(() => {
    fetch("http://localhost:8000/modules")
      .then(res => res.json())
      .then(data => setModules(data))
      .catch(err => console.error("Failed to fetch modules:", err));
  }, []);

  const groupedModules: Record<string, Module[]> = {};
  modules.forEach(mod => {
    const type = getModuleType(mod.name);
    if (!groupedModules[type]) groupedModules[type] = [];
    groupedModules[type].push(mod);
  });

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100vw',
        backgroundColor: '#201434',
        padding: '4rem 2rem',
        color: 'white',
        overflowY: 'auto',
      }}
    >
      <Typography variant="h4" textAlign="center" gutterBottom>
        Modules Catalog
      </Typography>

      {Object.entries(groupedModules).map(([group, mods]) => {
        // Gather and filter unit types
        const allInputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_input).map(io => io.unit));
        const allOutputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_output).map(io => io.unit));

        const ignoreInputs = ['Price', 'Space_X', 'Space_Y'];
        const inputUnits = [...new Set(allInputs)].filter(u => !ignoreInputs.includes(u));
        const outputUnits = [...new Set(allOutputs)];

        return (
          <Accordion key={group} sx={{ backgroundColor: '#2a1b4f', color: 'white', mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" sx={{ color: '#90caf9' }}>{group}</Typography>

                <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {inputUnits.length > 0 && (
                    <Typography variant="body2" sx={{ color: '#90caf9', fontWeight: 'bold', mr: 1 }}>
                      Inputs:
                    </Typography>
                  )}
                  {inputUnits.map((unit, i) => (
                    <Chip key={`in-${i}`} label={unit} color="primary" size="small" variant="outlined" />
                  ))}

                  {outputUnits.length > 0 && (
                    <Typography variant="body2" sx={{ color: '#80cbc4', fontWeight: 'bold', ml: 2, mr: 1 }}>
                      Outputs:
                    </Typography>
                  )}
                  {outputUnits.map((unit, i) => (
                    <Chip key={`out-${i}`} label={unit} color="success" size="small" variant="outlined" />
                  ))}
                </Box>
              </Box>
            </AccordionSummary>

            <AccordionDetails>
              <Grid container spacing={2}>
                {mods.map((mod, i) => {
                  const inputs = mod.io_fields.filter(io => io.is_input);
                  const outputs = mod.io_fields.filter(io => io.is_output);

                  return (
                    <Grid item key={i} xs={12} sm={6} md={4} lg={3}>
                      <Card sx={{ backgroundColor: '#311b92', border: '1px solid #555' }}>
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            {mod.name}
                          </Typography>

                          <Divider sx={{ borderColor: '#444', mb: 1 }} />

                          <Typography variant="body2" sx={{ color: '#90caf9', mb: 0.5 }}>
                            Inputs:
                          </Typography>
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {inputs.map((io, j) => (
                              <Chip
                                key={`in-${j}`}
                                size="small"
                                label={`${io.unit}: ${io.amount}`}
                                color="primary"
                                variant="outlined"
                              />
                            ))}
                          </Stack>

                          <Typography variant="body2" sx={{ color: '#80cbc4', mt: 2 }}>
                            Outputs:
                          </Typography>
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {outputs.map((io, j) => (
                              <Chip
                                key={`out-${j}`}
                                size="small"
                                label={`${io.unit}: ${io.amount}`}
                                color="success"
                                variant="outlined"
                              />
                            ))}
                          </Stack>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Box>
  );
};

export default ViewModulesPage;
