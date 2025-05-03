import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  Stack,
  Divider,
  FormControlLabel,
  Checkbox,
  MenuItem,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';

const MODULE_TEMPLATES: Record<string, { inputs: string[]; outputs: string[] }> = {
  Transformer: {
    inputs: ['Grid_Connection', 'Space_X', 'Space_Y', 'Price'],
    outputs: ['Usable_Power'],
  },
  Water_Supply: {
    inputs: ['Water_Connection', 'Space_X', 'Space_Y', 'Price'],
    outputs: ['Fresh_Water'],
  },
  Server_Rack: {
    inputs: ['Usable_Power', 'Chilled_Water', 'Internal_Network', 'Space_X', 'Space_Y', 'Price'],
    outputs: ['Processing', 'External_Network', 'Distilled_Water'],
  },
  UPS: {
    inputs: ['Usable_Power', 'Space_X', 'Space_Y', 'Price'],
    outputs: ['Backup_Power', 'Usable_Power'],
  },
  Other: {
    inputs: ['Space_X', 'Space_Y', 'Price'],
    outputs: [],
  },
};

const AddModulePage = () => {
  const [type, setType] = useState('Transformer');
  const [name, setName] = useState('');
  const [fields, setFields] = useState<{ is_input: boolean; is_output: boolean; unit: string; amount: string }[]>([]);

  const generateFieldsFromType = (selectedType: string) => {
    const template = MODULE_TEMPLATES[selectedType];
    const inputs = template.inputs.map(unit => ({
      is_input: true,
      is_output: false,
      unit,
      amount: ''
    }));
    const outputs = template.outputs.map(unit => ({
      is_input: false,
      is_output: true,
      unit,
      amount: ''
    }));
    setFields([...inputs, ...outputs]);
  };

  const handleTypeChange = (value: string) => {
    setType(value);
    setName(`${value}_`);
    generateFieldsFromType(value);
  };

  const addField = () => {
    setFields(prev => [...prev, { is_input: true, is_output: false, unit: '', amount: '' }]);
  };

  const removeField = (index: number) => {
    setFields(prev => prev.filter((_, i) => i !== index));
  };

  const updateField = (index: number, key: string, value: string | boolean) => {
    setFields(prev => {
      const updated = [...prev];
      (updated[index] as any)[key] = value;
      return updated;
    });
  };

  const handleSubmit = () => {
    const io_fields = fields.map(f => ({
      is_input: f.is_input,
      is_output: f.is_output,
      unit: f.unit,
      amount: parseFloat(f.amount as string)
    }));

    fetch("http://localhost:8000/modules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: Date.now(),
        name,
        io_fields
      })
    })
      .then(() => {
        alert("Module added successfully.");
        setType('Transformer');
        setName('');
        setFields([]);
      })
      .catch(err => console.error("Add failed:", err));
  };

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
        Add New Module
      </Typography>

      <Box sx={{ maxWidth: 600, mx: 'auto', display: 'flex', flexDirection: 'column', gap: 3 }}>
        <TextField
          select
          label="Module Type"
          value={type}
          onChange={(e) => handleTypeChange(e.target.value)}
          fullWidth
          sx={{ input: { color: 'white' }, label: { color: '#aaa' } }}
          InputLabelProps={{ style: { color: '#aaa' } }}
        >
          {Object.keys(MODULE_TEMPLATES).map((t) => (
            <MenuItem key={t} value={t}>
              {t}
            </MenuItem>
          ))}
        </TextField>

        <TextField
          label="Module Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          fullWidth
          sx={{ input: { color: 'white' }, label: { color: '#aaa' } }}
          InputLabelProps={{ style: { color: '#aaa' } }}
        />

        <Divider sx={{ borderColor: '#444' }} />

        <Typography variant="h6">Inputs / Outputs</Typography>

        {fields.map((field, index) => (
          <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <TextField
              label="Unit"
              value={field.unit}
              onChange={(e) => updateField(index, 'unit', e.target.value)}
              sx={{ input: { color: 'white' }, label: { color: '#aaa' } }}
            />
            <TextField
              label="Amount"
              type="number"
              value={field.amount}
              onChange={(e) => updateField(index, 'amount', e.target.value)}
              sx={{ input: { color: 'white' }, label: { color: '#aaa' } }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={field.is_input}
                  onChange={(e) => updateField(index, 'is_input', e.target.checked)}
                  sx={{ color: '#90caf9' }}
                />
              }
              label="Input"
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={field.is_output}
                  onChange={(e) => updateField(index, 'is_output', e.target.checked)}
                  sx={{ color: '#80cbc4' }}
                />
              }
              label="Output"
            />
            <IconButton onClick={() => removeField(index)} sx={{ color: '#f44336' }}>
              <DeleteIcon />
            </IconButton>
          </Box>
        ))}

        <Button onClick={addField} variant="outlined" color="secondary">
          + Add Field
        </Button>

        <Button onClick={handleSubmit} variant="contained" color="primary">
          Submit Module
        </Button>
      </Box>
    </Box>
  );
};

export default AddModulePage;
