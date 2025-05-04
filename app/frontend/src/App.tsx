import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AppBar, Toolbar, Button, Container, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import MainPage from './pages/MainPage';
import OldMainPage from './pages/OldMainPage';
import AddModulePage from './pages/AddModulePage';
import ViewModulesPage from './pages/ViewModulesPage';

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#1976d2',
    },
    background: {
      default: '#201434',
      paper: '#2b1b4f',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Router>
        <AppBar position="static">
          <Toolbar sx={{ display: 'flex', gap: 2 }}>
            <Button color="inherit" component={Link} to="/">Main Page</Button>
            <Button color="inherit" component={Link} to="/old">Old Page</Button>
            <Button color="inherit" component={Link} to="/add">Add Module</Button>
            <Button color="inherit" component={Link} to="/view">View Modules</Button>
          </Toolbar>
        </AppBar>

          <Routes>
            <Route path="/" element={<MainPage />} />
            <Route path="/old" element={<OldMainPage />} />
            <Route path="/add" element={<AddModulePage />} />
            <Route path="/view" element={<ViewModulesPage />} />
          </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
