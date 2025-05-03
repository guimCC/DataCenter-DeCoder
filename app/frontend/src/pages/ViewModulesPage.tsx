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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Checkbox,
  FormControlLabel,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
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

const ICON_MAP: Record<string, string> = {
  'Transformer': 'transformer',
  'Water Chiller': 'water_chiller',
  'Water Supply': 'water_supply',
  'Water Treatment': 'water_treatment',
  'Water Recycling': 'water_treatment',
  'Liquid Cooling': 'water_chiller',
  'Heat Recovery': 'transformer',
  'UPS': 'transformer',
  'Server Rack': 'server_rack',
  'Data Rack': 'data_rack',
  'Network Rack': 'network_rack',
  'Network Infra': 'network_rack',
  'GPU Rack': 'server_rack',
  'Archive Storage': 'data_rack',
  'Other': 'transformer',
};

const ViewModulesPage = () => {
  const [modules, setModules] = useState<Module[]>([]);
  const [editOpen, setEditOpen] = useState(false);
  const [editModule, setEditModule] = useState<Module | null>(null);

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

  const handleDelete = (id: number) => {
    if (!confirm("Are you sure you want to delete this module?")) return;
    fetch(`http://localhost:8000/modules/${id}`, {
      method: 'DELETE',
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setModules(prev => prev.filter(m => m.id !== id));
        } else {
          alert("Delete failed.");
        }
      });
  };

  const handleEdit = (mod: Module) => {
    const copy = JSON.parse(JSON.stringify(mod));
    setEditModule(copy);
    setEditOpen(true);
  };

  const handleEditSubmit = () => {
    if (!editModule) return;
    fetch(`http://localhost:8000/modules/${editModule.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editModule),
    })
      .then(res => res.json())
      .then(() => {
        setModules(prev =>
          prev.map(m => (m.id === editModule.id ? editModule : m))
        );
        setEditOpen(false);
      });
  };

  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', backgroundColor: '#201434', padding: '4rem 2rem', color: 'white', overflowY: 'auto' }}>
      <Typography variant="h4" textAlign="center" gutterBottom>
        Modules Catalog
      </Typography>

      {Object.entries(groupedModules).map(([group, mods]) => {
        const allInputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_input).map(io => io.unit));
        const allOutputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_output).map(io => io.unit));
        const ignoreInputs = ['Price', 'Space_X', 'Space_Y'];
        const inputUnits = [...new Set(allInputs)].filter(u => !ignoreInputs.includes(u));
        const outputUnits = [...new Set(allOutputs)];

        return (
          <Accordion key={group} sx={{ backgroundColor: '#2a1b4f', color: 'white', mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
              <Box sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                   <Box component="img" src={`/sprites/${ICON_MAP[group]}.png`} alt={group} sx={{ width: 24, height: 24, objectFit: 'contain' }} />
                   <Typography variant="h6" sx={{ color: '#90caf9' }}>{group}</Typography>
                </Box>
                <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {inputUnits.length > 0 && <Typography variant="body2" sx={{ color: '#90caf9', fontWeight: 'bold', mr: 1 }}>Inputs:</Typography>}
                  {inputUnits.map((unit, i) => (
                    <Chip key={`in-${i}`} label={unit} color="primary" size="small" variant="outlined" />
                  ))}
                  {outputUnits.length > 0 && <Typography variant="body2" sx={{ color: '#80cbc4', fontWeight: 'bold', ml: 2, mr: 1 }}>Outputs:</Typography>}
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
                  const sprite = ICON_MAP[getModuleType(mod.name)];

                  return (
                    <Grid item key={i} xs={12} sm={6} md={4} lg={3}>
                      <Card sx={{ backgroundColor: '#311b92', border: '1px solid #555' }}>
                        <CardContent>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Box
                                component="img"
                                src={`/sprites/${sprite}.png`}
                                alt={mod.name}
                                sx={{
                                  width: 24,
                                  height: 24,
                                  objectFit: 'contain',
                                  filter: 'brightness(1.1)',
                                }}
                                onError={(e) => {
                                  (e.target as HTMLImageElement).style.display = 'none';
                                }}
                              />
                              <Typography variant="subtitle1">{mod.name}</Typography>
                            </Box>
                            <Stack direction="row" spacing={1}>
                              <IconButton onClick={() => handleEdit(mod)} sx={{ color: '#ffd54f' }}><EditIcon /></IconButton>
                              <IconButton onClick={() => handleDelete(mod.id)} sx={{ color: '#f44336' }}><DeleteIcon /></IconButton>
                            </Stack>
                          </Box>

                          <Divider sx={{ borderColor: '#444', mb: 1 }} />

                          <Typography variant="body2" sx={{ color: '#90caf9', mb: 0.5 }}>Inputs:</Typography>
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

                          <Typography variant="body2" sx={{ color: '#80cbc4', mt: 2 }}>Outputs:</Typography>
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

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Module</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {editModule && (
            <>
              <TextField
                label="Module Name"
                value={editModule.name}
                onChange={(e) => setEditModule({ ...editModule, name: e.target.value })}
                fullWidth
              />
              {editModule.io_fields.map((io, index) => (
                <Box key={index} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <TextField
                    label="Unit"
                    value={io.unit}
                    onChange={(e) => {
                      const updated = [...editModule.io_fields];
                      updated[index].unit = e.target.value;
                      setEditModule({ ...editModule, io_fields: updated });
                    }}
                  />
                  <TextField
                    label="Amount"
                    type="number"
                    value={io.amount}
                    onChange={(e) => {
                      const updated = [...editModule.io_fields];
                      updated[index].amount = parseFloat(e.target.value);
                      setEditModule({ ...editModule, io_fields: updated });
                    }}
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={io.is_input}
                        onChange={(e) => {
                          const updated = [...editModule.io_fields];
                          updated[index].is_input = e.target.checked;
                          setEditModule({ ...editModule, io_fields: updated });
                        }}
                      />
                    }
                    label="Input"
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={io.is_output}
                        onChange={(e) => {
                          const updated = [...editModule.io_fields];
                          updated[index].is_output = e.target.checked;
                          setEditModule({ ...editModule, io_fields: updated });
                        }}
                      />
                    }
                    label="Output"
                  />
                </Box>
              ))}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button onClick={handleEditSubmit} variant="contained" color="primary">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ViewModulesPage;
