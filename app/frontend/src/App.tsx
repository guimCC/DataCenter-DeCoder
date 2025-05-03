import { useEffect, useState } from 'react';
import {
  Container, Typography, Button, Card, CardContent,
  TextField, Checkbox, FormControlLabel, Box, Divider
} from '@mui/material';

function App() {
  const [modules, setModules] = useState([]);
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [ioFields, setIOFields] = useState([]);
  const [currentIO, setCurrentIO] = useState({
    is_input: false,
    is_output: false,
    unit: '',
    amount: ''
  });

  // fetch existing modules from FastAPI
  useEffect(() => {
    fetch("http://localhost:8000/modules")
      .then(res => res.json())
      .then(data => setModules(data))
      .catch(err => console.error("Failed to fetch modules:", err));
  }, []);

  // Handle adding one I/O field
  const addIOField = () => {
    setIOFields([...ioFields, currentIO]);
    setCurrentIO({ is_input: false, is_output: false, unit: '', amount: '' });
  };

  // Submit full module
  const handleSubmit = () => {
    const newModule = {
      id: parseInt(id),
      name,
      io_fields: ioFields.map(io => ({
        ...io,
        amount: parseFloat(io.amount)
      }))
    };

    fetch("http://localhost:8000/modules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newModule)
    })
    .then(() => {
      setModules([...modules, newModule]); // update list
      // clear form
      setId('');
      setName('');
      setIOFields([]);
    });
  };

  return (
    <Container>
      <Typography variant="h4" gutterBottom>Data Center Modules</Typography>

      {/* MODULE FORM */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6">Add Module</Typography>
        <TextField label="ID" fullWidth value={id} onChange={e => setId(e.target.value)} sx={{ my: 1 }} />
        <TextField label="Name" fullWidth value={name} onChange={e => setName(e.target.value)} sx={{ my: 1 }} />

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1">Add IO Field</Typography>
        <FormControlLabel
          control={<Checkbox checked={currentIO.is_input} onChange={e => setCurrentIO({...currentIO, is_input: e.target.checked})} />}
          label="Is Input"
        />
        <FormControlLabel
          control={<Checkbox checked={currentIO.is_output} onChange={e => setCurrentIO({...currentIO, is_output: e.target.checked})} />}
          label="Is Output"
        />
        <TextField label="Unit" fullWidth value={currentIO.unit} onChange={e => setCurrentIO({...currentIO, unit: e.target.value})} sx={{ my: 1 }} />
        <TextField label="Amount" fullWidth value={currentIO.amount} onChange={e => setCurrentIO({...currentIO, amount: e.target.value})} sx={{ my: 1 }} />
        <Button onClick={addIOField} variant="outlined" sx={{ mt: 1 }}>Add IO Field</Button>

        <Typography variant="body2" sx={{ mt: 2 }}>Added IOs: {ioFields.length}</Typography>
        <Button onClick={handleSubmit} variant="contained" sx={{ mt: 2 }}>Submit Module</Button>
      </Box>

      {/* MODULE LIST */}
      {modules.map((mod, i) => (
        <Card key={i} sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6">{mod.name} (ID: {mod.id})</Typography>
            {mod.io_fields.map((io, j) => (
              <Typography key={j}>
                {io.is_input ? "Input" : "Output"} - {io.unit}: {io.amount}
              </Typography>
            ))}
          </CardContent>
        </Card>
      ))}
    </Container>
  );
}

export default App;
