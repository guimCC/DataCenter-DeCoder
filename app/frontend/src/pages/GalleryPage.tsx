import { useEffect, useState } from 'react';
import './GalleryPage.css'; // Import the CSS file
import mongoImage from './mongo.png';
import dist1 from './dist1.jpg';
import dist2 from './dist2.png';
import dist3 from './dist3.jpg';

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
  Dialog, // Import Dialog components
  DialogTitle,
  DialogContent,
  // DialogContentText, // Can remove if not strictly needed with custom content
  DialogActions,
  Button,
  CardActionArea, // Import CardActionArea
  CardMedia, // Add CardMedia for displaying images
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info'; // Optional: Icon for info cards
import { Module } from '../types'; // Assuming '../types' defines the Module type correctly

// Module type categorization function
const getModuleType = (name: string): string => {
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

// Mapping module types to icon filenames (assuming they exist in /public/sprites/)
const ICON_MAP: Record<string, string> = {
  'Transformer': 'transformer',
  'Water Chiller': 'water_chiller',
  'Water Supply': 'water_supply',
  'Water Treatment': 'water_treatment',
  'Water Recycling': 'water_treatment', // Assuming same icon as treatment
  'Liquid Cooling': 'water_chiller',   // Assuming same icon as chiller
  'Heat Recovery': 'transformer',     // Assuming same icon as transformer
  'UPS': 'transformer',             // Assuming same icon as transformer
  'Server Rack': 'server_rack',
  'Data Rack': 'data_rack',
  'Network Rack': 'network_rack',
  'Network Infra': 'network_rack',   // Assuming same icon as network rack
  'GPU Rack': 'server_rack',         // Assuming same icon as server rack
  'Archive Storage': 'data_rack',    // Assuming same icon as data rack
  'Other': 'transformer',          // Default icon
};

// Define the structure for info section content
interface InfoContent {
  title: string;
  description: React.ReactNode; // Use ReactNode for potentially richer content
  image?: string; // Optional image for the info section
}

const GalleryPage = () => { // Renamed component to GalleryPage based on error message
  const [modules, setModules] = useState<Module[]>([]);
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState<boolean>(false);
  const [dialogContent, setDialogContent] = useState<InfoContent | null>(null);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);

  // Fetch modules on component mount
  useEffect(() => {
    fetch("http://localhost:8000/modules") // Replace with your actual API endpoint if different
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then(data => setModules(data))
      .catch(err => console.error("Failed to fetch modules:", err));
  }, []); // Empty dependency array ensures this runs only once on mount

  // Group modules by type
  const groupedModules: Record<string, Module[]> = modules.reduce((acc, mod) => {
    const type = getModuleType(mod.name);
    if (!acc[type]) {
      acc[type] = [];
    }
    acc[type].push(mod);
    return acc;
  }, {} as Record<string, Module[]>);
  const infoSections: Record<string, InfoContent> = {
    dataset: {
      title: 'Dataset Overview',
      description: (
        <>
          <Typography variant="body1" gutterBottom>
            The application utilizes a dataset containing various hardware modules available for building a data center.
          </Typography>
          <Typography variant="body2" sx={{ color: '#bdbdbd', mt: 1 }}>
            Key characteristics captured for each module include:
          </Typography>
          <ul>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Name and Type</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Input Requirements</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Output Resources/Capacities</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Physical Dimensions</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Cost (Price)</Typography></li>
          </ul>
          <Typography variant="body1" sx={{ mt: 2 }}>
            This gallery below displays all modules available in the current dataset, grouped by their functional type.
          </Typography>
          <Typography variant="body1" sx={{ mt: 2 }}>
            MongoDB is used to store the dataset, and the application fetches data from it using a REST API.
          </Typography>
          {/* <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
            <img 
                src={mongoImage}
                alt="MILP Optimization Diagram" 
                style={{ maxWidth: '100%', borderRadius: '4px' }}
            />
          </Box> */}
        </>
      ),
    },
    selection: {
      title: 'Module Selection & MILP Optimization',
      description: (
         <>
          <Typography variant="body1" gutterBottom>
            The Module Selection process uses Mixed Integer Linear Programming (MILP) to find the optimal combination of modules.
          </Typography>
          
          <Typography variant="body2" sx={{ color: '#bdbdbd', mt: 1, fontWeight: 'bold' }}>
            How MILP Works for Module Selection:
          </Typography>
          
          <ul>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>
              <strong>Decision Variables:</strong> Integer counters for each module type (how many to include)
            </Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>
              <strong>Objective Function:</strong> Weighted combination of goals (maximize outputs like processing power, minimize inputs like cost)
            </Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>
              <strong>Constraints:</strong> Resource limits (e.g., power budget, total area), internal resource balance, and minimum output requirements
            </Typography></li>
          </ul>
          
          <Typography variant="body1" sx={{ mt: 2 }}>
            The solver attempts to find the best integer values for each module count that satisfies all constraints while optimizing the objective.
          </Typography>
        </>
      ),
    },
    distribution: {
      title: 'Modules Distribution',
      description: (
         <>
          <Typography variant="body1" gutterBottom>
            Once modules are selected, the "Modules Distribution" phase focuses on placing these modules physically within the data center layout.
          </Typography>
           <Typography variant="body2" sx={{ color: '#bdbdbd', mt: 1 }}>
            Key objectives include:
          </Typography>
           <ul>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Minimizing cable lengths and infrastructure costs.</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Adhering to physical constraints.</Typography></li>
            <li><Typography variant="body2" sx={{ color: '#bdbdbd' }}>Facilitating maintenance access.</Typography></li>
          </ul>
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
            <img 
                src={dist1}
                alt="Modules Distributions Diagrams" 
                style={{ maxWidth: '100%', borderRadius: '4px' }}
            />
          </Box>
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
            <img 
                src={dist2}
                alt="Modules Distributions Diagrams with restrictions" 
                style={{ maxWidth: '100%', borderRadius: '4px' }}
            />
          </Box>
          <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
            <img 
                src={dist3}
                alt="Modules Distribution in the final layout" 
                style={{ maxWidth: '100%', borderRadius: '4px' }}
            />
          </Box>
        </>
      ),
    },
  };


  // Handlers for the info dialog
  const handleOpenInfoDialog = (contentKey: string) => {
    if (infoSections[contentKey]) {
      setDialogContent(infoSections[contentKey]);
      setIsInfoDialogOpen(true);
    }
  };

  const handleCloseInfoDialog = () => {
    setIsInfoDialogOpen(false);
    // Optional: Reset content after closing animation finishes if needed
    // setTimeout(() => setDialogContent(null), 300);
  };


  return (
    <Box sx={{ minHeight: '100vh', width: '100vw', backgroundColor: '#201434', padding: '4rem 2rem', color: 'white', overflowY: 'auto' }}>
      <Typography variant="h4" textAlign="center" gutterBottom sx={{ mb: 4 }}>
        Module Gallery & App Info {/* Updated title */}
      </Typography>

      {/* --- Info Cards Section --- */}
      <Box sx={{ mb: 5 }}> {/* Add margin below the info cards */}
        {/* Modified grid to stack vertically and make boxes wider */}
        <Grid container spacing={3} direction="column" alignItems="center">
          {Object.entries(infoSections).map(([key, content]) => (
            <Grid item key={key} xs={12} sx={{ width: '100%', maxWidth: '800px' }}>
                <Card 
                sx={{ 
                    backgroundColor: '#3a2264', 
                    border: '1px solid #555', 
                    height: '100%',
                    borderRadius: '8px', 
                    overflow: 'hidden',
                }} 
                className="info-card-hover"
                >
                <CardActionArea 
                    onClick={() => handleOpenInfoDialog(key)} 
                    sx={{ 
                    height: '100%', 
                    display: 'flex', 
                    flexDirection: 'column', 
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    p: 3,
                    background: 'linear-gradient(135deg, #3a2264 0%, #331d58 100%)',
                    }}
                >
                    <InfoIcon 
                    sx={{ 
                        fontSize: 50, 
                        color: '#90caf9', 
                        mb: 2,
                        filter: 'drop-shadow(0 3px 5px rgba(0,0,0,0.3))'
                    }}
                    className="module-icon"
                    />
                    <Typography 
                    variant="h5" 
                    textAlign="center" 
                    sx={{ 
                        color: 'white',
                        textShadow: '0 2px 4px rgba(0,0,0,0.3)',
                        mb: 1
                    }}
                    className="gradient-text"
                    >
                    {content.title.replace(' Overview','').replace('Modules ','')}
                    </Typography>
                    <Typography 
                    variant="body2" 
                    textAlign="center" 
                    sx={{ 
                        color: '#bdbdbd', 
                        mt: 1,
                        fontStyle: 'italic'
                    }}
                    >
                    Click to learn more
                    </Typography>
                    <Divider 
                    sx={{ 
                        borderColor: 'rgba(144, 202, 249, 0.3)', 
                        width: '50%', 
                        mt: 2 
                    }} 
                    className="divider-glow"
                    />
                </CardActionArea>
                </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
       {/* --- End Info Cards Section --- */}

       <Divider sx={{ borderColor: '#555', mb: 5, mt:3 }} /> {/* Divider between sections */}


      {/* --- Module Gallery Section --- */}
       <Typography variant="h5" sx={{ color: '#bdbdbd', mb: 3, textAlign: 'center' }}>
           Available Modules
        </Typography>
      {Object.entries(groupedModules).map(([group, mods]) => {
        // Determine unique input and output units for the group header
        const allInputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_input).map(io => io.unit));
        const allOutputs = mods.flatMap(mod => mod.io_fields.filter(io => io.is_output).map(io => io.unit));
        const ignoreUnits = ['Price', 'Space_X', 'Space_Y']; // Units to ignore in the header summary
        const inputUnits = [...new Set(allInputs)].filter(u => !ignoreUnits.includes(u));
        const outputUnits = [...new Set(allOutputs)];

        return (
          <Accordion key={group} sx={{ backgroundColor: '#2a1b4f', color: 'white', mb: 2, '&:before': { display: 'none' } }} /* Remove default top border */ >
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
              <Box sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                   {/* Use icon based on group type */}
                   <Box component="img" src={`/sprites/${ICON_MAP[group]}.png`} alt={`${group} icon`} sx={{ width: 24, height: 24, objectFit: 'contain' }} />
                   <Typography variant="h6" sx={{ color: '#90caf9' }}>{group}</Typography>
                   <Typography variant="body2" sx={{ color: '#bdbdbd', ml: 1 }}>({mods.length} {mods.length === 1 ? 'module' : 'modules'})</Typography>
                </Box>
                 {/* Display summary of inputs/outputs for the group */}
                {(inputUnits.length > 0 || outputUnits.length > 0) && (
                  <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                    {inputUnits.length > 0 && <Typography variant="body2" sx={{ color: '#90caf9', fontWeight: 'bold', mr: 0.5 }}>Inputs:</Typography>}
                    {inputUnits.map((unit, i) => (
                      <Chip key={`in-header-${i}`} label={unit} color="primary" size="small" variant="outlined" sx={{ borderColor: 'rgba(144, 202, 249, 0.5)', color: '#90caf9' }} />
                    ))}
                    {outputUnits.length > 0 && <Typography variant="body2" sx={{ color: '#80cbc4', fontWeight: 'bold', ml: inputUnits.length > 0 ? 2 : 0, mr: 0.5 }}>Outputs:</Typography>}
                    {outputUnits.map((unit, i) => (
                      <Chip key={`out-header-${i}`} label={unit} color="success" size="small" variant="outlined" sx={{ borderColor: 'rgba(128, 203, 196, 0.5)', color: '#80cbc4' }} />
                    ))}
                  </Box>
                )}
              </Box>
            </AccordionSummary>

            <AccordionDetails sx={{ backgroundColor: '#311b92' /* Slightly different background */ }}>
              <Grid container spacing={2}>
                {mods.map((mod) => {
                  const inputs = mod.io_fields.filter(io => io.is_input);
                  const outputs = mod.io_fields.filter(io => io.is_output);
                  const sprite = ICON_MAP[getModuleType(mod.name)]; // Get specific icon for this module

                  return (
                    <Grid item key={mod.id} xs={12} sm={6} md={4} lg={3}>
                      {/* Use module ID as key for better performance */}
                      <Card 
                        sx={{ 
                            backgroundColor: '#3a2264', 
                            border: '1px solid #555', 
                            height: '100%', 
                            display: 'flex', 
                            flexDirection: 'column',
                            transition: 'all 0.3s ease',
                            '&:hover': {
                            transform: 'translateY(-5px)',
                            boxShadow: '0 8px 16px rgba(0, 0, 0, 0.5)',
                            borderColor: '#90caf9',
                            }
                        }} 
                        className="module-card-hover"
                        >
                        <CardContent sx={{ flexGrow: 1, p: 2 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Box
                                component="img"
                                src={`/sprites/${sprite}.png`}
                                alt={mod.name}
                                sx={{
                                width: 28,
                                height: 28,
                                objectFit: 'contain',
                                filter: 'brightness(1.2) drop-shadow(0 2px 3px rgba(0,0,0,0.3))',
                                }}
                                onError={(e) => {
                                (e.target as HTMLImageElement).style.display = 'none';
                                }}
                            />
                            <Typography 
                                variant="subtitle1" 
                                sx={{ 
                                fontWeight: 'medium',
                                color: '#e0e0e0',
                                textShadow: '0 1px 2px rgba(0,0,0,0.3)'
                                }}
                            >
                                {mod.name}
                            </Typography>
                            </Box>

                            <Divider sx={{ borderColor: '#555', mb: 1.5 }} />

                            {/* Display Inputs */}
                            {inputs.length > 0 && (
                            <>
                                <Typography variant="body2" sx={{ color: '#90caf9', mb: 0.5, fontWeight: 'bold' }}>
                                Inputs:
                                </Typography>
                                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1.5 }}>
                                {inputs.map((io, j) => (
                                    <Chip
                                    key={`in-${mod.id}-${j}`}
                                    size="small"
                                    label={`${io.unit}: ${io.amount}`}
                                    color="primary"
                                    variant="outlined"
                                    sx={{ 
                                        borderColor: 'rgba(144, 202, 249, 0.5)', 
                                        color: '#90caf9',
                                        '&:hover': {
                                        backgroundColor: 'rgba(144, 202, 249, 0.1)'
                                        }
                                    }}
                                    />
                                ))}
                                </Stack>
                            </>
                            )}

                            {/* Display Outputs */}
                            {outputs.length > 0 && (
                            <>
                                <Typography variant="body2" sx={{ color: '#80cbc4', mb: 0.5, fontWeight: 'bold' }}>
                                Outputs:
                                </Typography>
                                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                                {outputs.map((io, j) => (
                                    <Chip
                                    key={`out-${mod.id}-${j}`}
                                    size="small"
                                    label={`${io.unit}: ${io.amount}`}
                                    color="success"
                                    variant="outlined"
                                    sx={{ 
                                        borderColor: 'rgba(128, 203, 196, 0.5)', 
                                        color: '#80cbc4',
                                        '&:hover': {
                                        backgroundColor: 'rgba(128, 203, 196, 0.1)'
                                        }
                                    }}
                                    />
                                ))}
                                </Stack>
                            </>
                            )}

                            {/* Display message if no inputs/outputs */}
                            {(inputs.length === 0 && outputs.length === 0) && (
                            <Typography variant="caption" sx={{ color: '#bdbdbd', fontStyle: 'italic', display: 'block', mt: 1 }}>
                                No input/output fields defined.
                            </Typography>
                            )}
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
      {/* --- End Module Gallery Section --- */}


      {/* --- Info Dialog --- */}
      <Dialog
        open={isInfoDialogOpen}
        onClose={handleCloseInfoDialog}
        aria-labelledby="info-dialog-title"
        aria-describedby="info-dialog-description"
        maxWidth="md" // Increased from default 'sm'
        PaperProps={{
            sx: {
                backgroundColor: '#2a1b4f', // Dark background for dialog
                color: 'white',
                minWidth: '400px', // Increased minimum width
                width: '90%', // Use percentage of available width
                maxWidth: '800px'  // Increased maximum width
            }
        }}
      >
        {dialogContent && (
          <>
            <DialogTitle id="info-dialog-title" sx={{ color: '#90caf9' }}>
              {dialogContent.title}
            </DialogTitle>
            <DialogContent dividers sx={{ borderColor: 'rgba(255, 255, 255, 0.12)' /* Add divider */ }}>
                 {/* Wrap description in Box for potential scroll */}
                 <Box id="info-dialog-description">
                    {dialogContent.description}
                 </Box>
            </DialogContent>
            <DialogActions sx={{pb: 2, pr: 2}}>
              <Button onClick={handleCloseInfoDialog} variant="outlined" color="primary" sx={{ color: '#90caf9', borderColor: 'rgba(144, 202, 249, 0.5)' }}>
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
       {/* --- End Info Dialog --- */}

    </Box>
  );
};

export default GalleryPage; // Exporting as GalleryPage