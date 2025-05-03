import { useEffect, useState } from 'react';
import { Container, Typography, Button, Card, CardContent } from '@mui/material';

function App() {
  const [modules, setModules] = useState([]);

  // Fetch modules from FastAPI when page loads
  useEffect(() => {
    fetch("http://localhost:8000/modules")
      .then(res => res.json())
      .then(data => setModules(data))
      .catch(err => console.error("Failed to fetch modules:", err));
  }, []);

  return (
    <Container>
      <Typography variant="h4" gutterBottom>Data Center Modules</Typography>

      {modules.map((mod, i) => (
        <Card key={i} sx={{ marginBottom: 2 }}>
          <CardContent>
            <Typography variant="h6">{mod.name}</Typography>
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
