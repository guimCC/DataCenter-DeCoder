import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Button, Container } from '@mui/material';
import MainPage from './pages/MainPage';
import AddModulePage from './pages/AddModulePage';
import ViewModulesPage from './pages/ViewModulesPage';

function App() {
  return (
    <Router>
      <AppBar position="static">
        <Toolbar>
          <Button color="inherit" component={Link} to="/">Main Page</Button>
          <Button color="inherit" component={Link} to="/add">Add Module</Button>
          <Button color="inherit" component={Link} to="/view">View Modules</Button>
        </Toolbar>
      </AppBar>

      <Container sx={{ mt: 4 }}>
        <Routes>
          <Route path="/" element={<MainPage />} />
          <Route path="/add" element={<AddModulePage />} />
          <Route path="/view" element={<ViewModulesPage />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
