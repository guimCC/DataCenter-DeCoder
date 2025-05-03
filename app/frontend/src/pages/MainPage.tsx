import { useState, useEffect, useCallback, useRef } from 'react'; // Import useCallback and useRef
import {
  Box, TextField, Typography, Button, Paper, MenuItem, Select, FormControl, InputLabel
} from '@mui/material';
import { PositionedModule, DataCenter } from '../types';

// Simple throttle function
function throttle<T extends (...args: any[]) => any>(func: T, limit: number): T {
  let inThrottle: boolean;
  let lastResult: ReturnType<T>;
  return function (this: ThisParameterType<T>, ...args: Parameters<T>): ReturnType<T> {
    if (!inThrottle) {
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
      lastResult = func.apply(this, args);
    }
    return lastResult;
  } as T;
}


const GRID_ROWS = 20;
const GRID_COLS = 20;
const CELL_SIZE = 10;
const THROTTLE_LIMIT = 50; // Throttle mousemove updates to every 50ms

import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import RestartAltIcon from '@mui/icons-material/RestartAlt';


const MainPage = () => {
  const [constraints, setConstraints] = useState({
    maxPrice: '',
    maxSpaceX: '',
    maxSpaceY: ''
  });

  const [datacenters, setDatacenters] = useState<DataCenter[]>([]);
  const [selectedDC, setSelectedDC] = useState<number | "">("");

  const [gridDimensions, setGridDimensions] = useState({
    rows: GRID_ROWS,
    cols: GRID_COLS
  });

  const [zoom, setZoom] = useState(1);
  // Removed mousePosition state as it wasn't strictly needed for drag ghost
  // const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [ghostPreview, setGhostPreview] = useState({ visible: false, row: 0, col: 0 });

  // Color map for different module types
  const MODULE_COLORS = {
    transformer: '#E9DA54',    // Yellow
    water_supply: '#2196f3',   // Light blue
    water_treatment: '#03a9f4', // Cyan
    water_chiller: '#00bcd4',  // Teal
    network_rack: '#ff9800',   // Orange
    server_rack: '#4caf50',    // Green
    data_rack: '#9c27b0',      // Purple
    default: '#757575'         // Gray (fallback)
  };

  const [resultModules, setResultModules] = useState<PositionedModule[]>([]);
  const [draggedModuleId, setDraggedModuleId] = useState<string | null>(null);

  // Refs for elements needed in mousemove
  const gridContainerRef = useRef<HTMLDivElement>(null); // Ref for the scrollable container
  const gridElementRef = useRef<HTMLDivElement>(null);   // Ref for the grid itself

  const handleChange = (field: string, value: string) => {
    setConstraints(prev => ({ ...prev, [field]: value }));
  };

  const handleDesign = () => {
    fetch("http://localhost:8000/solve-dummy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        constraints: {
          price: parseFloat(constraints.maxPrice) || 0, // Ensure valid numbers
          space_x: parseFloat(constraints.maxSpaceX) || 0,
          space_y: parseFloat(constraints.maxSpaceY) || 0,
        }
      })
    })
      .then(res => res.json())
      .then(data => setResultModules(data.modules || []))
      .catch(err => console.error("Design failed:", err));
  };

  // Handle drag start
  const handleDragStart = (id: string) => {
    setDraggedModuleId(id);
    console.log(`Started dragging module #${id}`);
  };

  useEffect(() => {
    console.log("Fetching datacenters...");

    fetch("http://localhost:8000/datacenters")
      .then(res => res.json())
      .then(data => {
        console.log("Datacenters received:", data);
        setDatacenters(data);
      })
      .catch(err => console.error("Failed to fetch datacenters", err));
    }, []);

  // --- Mouse Move Handling with Throttling ---

  // Memoize the core logic of handling mouse movement
  const handleMouseMoveLogic = useCallback((e: MouseEvent) => {
    const gridEl = gridElementRef.current;
    const containerEl = gridContainerRef.current;

    // Ensure elements exist and we are dragging
    if (!gridEl || !containerEl || draggedModuleId === null) return;

    const rect = gridEl.getBoundingClientRect();

    // Calculate relative position within grid, accounting for zoom and scroll
    const scrollLeft = containerEl.scrollLeft;
    const scrollTop = containerEl.scrollTop;

    // Calculate position within the *unscaled* grid element's coordinate system
    // Adjust clientX/Y relative to the *container's* viewport, then add scroll, then divide by zoom
    const containerRect = containerEl.getBoundingClientRect();
    const x = (e.clientX - rect.left) / zoom; // Position relative to the scaled grid's top-left
    const y = (e.clientY - rect.top) / zoom;  // Position relative to the scaled grid's top-left


    // Calculate grid coordinates (1-based index)
    const gridCol = Math.max(1, Math.floor(x / CELL_SIZE) + 1);
    const gridRow = Math.max(1, Math.floor(y / CELL_SIZE) + 1);

    // Only show ghost if inside grid bounds (check based on potential placement)
    // Find the module being dragged to get its dimensions
    const draggedMod = resultModules.find(mod => mod.id === draggedModuleId);
    const spanX = draggedMod?.width ?? 1;
    const spanY = draggedMod?.height ?? 1;

    const isInBounds =
          gridCol > 0 &&
          gridCol + spanX -1 <= gridDimensions.cols && // Check end column
          gridRow > 0 &&
          gridRow + spanY -1 <= gridDimensions.rows;   // Check end row

    setGhostPreview({
      visible: isInBounds, // Only show if placement starts within bounds
      col: gridCol,
      row: gridRow
    });

  }, [draggedModuleId, zoom, gridDimensions.cols, gridDimensions.rows, resultModules]); // Dependencies

  // Create a throttled version of the mouse move handler
  const throttledMouseMove = useRef(throttle(handleMouseMoveLogic, THROTTLE_LIMIT)).current;

  // Effect to add/remove the event listener
  useEffect(() => {
    if (draggedModuleId !== null) {
      // Attach listener to the document to capture mouse moves anywhere
      document.addEventListener('mousemove', throttledMouseMove);
      // console.log('Added mousemove listener'); // Debugging

      return () => {
        document.removeEventListener('mousemove', throttledMouseMove);
        // console.log('Removed mousemove listener'); // Debugging
        // Optionally hide ghost when listener is removed (e.g., drag ends)
        // setGhostPreview({ visible: false, row: 0, col: 0 });
      };
    } else {
      // Ensure ghost is hidden when not dragging
      setGhostPreview({ visible: false, row: 0, col: 0 });
    }
  }, [draggedModuleId, throttledMouseMove]); // Dependency is the stable throttled function


    // Draggable module component - No changes needed here
    const DraggableModule = ({ mod, spanX, spanY }: {
        mod: PositionedModule;
        spanX: number;
        spanY: number;
      }) => {
        const getModuleType = () => {
          const name = mod.name.toLowerCase();
          if (name.startsWith('transformer')) return 'transformer';
          if (name.includes('network_rack')) return 'network_rack';
          if (name.includes('server_rack')) return 'server_rack';
          if (name.includes('data_rack')) return 'data_rack';
          if (name.includes('water_supply')) return 'water_supply';
          if (name.includes('water_treatment')) return 'water_treatment';
          if (name.includes('water_chiller')) return 'water_chiller';
          return 'default';
        };
        const getModuleColor = () => {
          const type = getModuleType();
          return MODULE_COLORS[type as keyof typeof MODULE_COLORS] || MODULE_COLORS.default;
        };
        const getSpritePath = () => {
          const type = getModuleType();
          return `/sprites/${type === 'default' ? 'transformer' : type}.png`;
        };
        const isDragged = mod.id === draggedModuleId;

        return (
          <Box
            onClick={(e) => {
              e.stopPropagation();
              if (!isDragged) {
                handleDragStart(mod.id);
              }
              // If already dragging, clicking the module itself could potentially cancel the drag
              // else { cancelDrag(); } // Uncomment if you want this behavior
            }}
            sx={{
              gridColumn: `${mod.gridColumn} / span ${spanX}`,
              gridRow: `${mod.gridRow} / span ${spanY}`,
              backgroundColor: isDragged ? 'rgba(255, 255, 255, 0.1)' : getModuleColor(), // Make dragged more transparent
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              borderRadius: 1,
              zIndex: isDragged ? 10 : 1, // Much higher z-index when dragging
              cursor: isDragged ? 'grabbing' : 'grab',
              padding: 0.5,
              border: isDragged ? '2px dashed white' : '1px solid rgba(255, 255, 255, 0.2)',
              opacity: isDragged ? 0.5 : 1, // Make dragged more transparent
              transition: 'opacity 0.2s ease-out, background-color 0.2s ease-out', // Smooth transitions
              '&:hover': {
                boxShadow: !isDragged ? '0 0 0 2px white' : 'none', // Only hover effect if not being dragged
                opacity: isDragged ? 0.5 : 0.9,
              },
              position: 'relative',
              pointerEvents: isDragged ? 'none' : 'auto', // Prevent interaction with the original while dragging ghost
            }}
          >
            <Box
              component="img"
              src={getSpritePath()}
              alt={mod.name}
              sx={{
                width: '80%',
                height: '80%',
                objectFit: 'contain',
                filter: 'brightness(1.1)',
                pointerEvents: 'none',
              }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </Box>
        );
    };

  // Legend component - No changes needed
  const ModuleLegend = () => {
    const moduleTypes = [
      { name: 'transformer', displayName: 'Transformer' },
      { name: 'water_supply', displayName: 'Water Supply' },
      { name: 'water_treatment', displayName: 'Water Treatment' },
      { name: 'water_chiller', displayName: 'Water Chiller' },
      { name: 'network_rack', displayName: 'Network Rack' },
      { name: 'server_rack', displayName: 'Server Rack' },
      { name: 'data_rack', displayName: 'Data Rack' },
    ];

    return (
      <Paper sx={{
        p: 2,
        ml: 2,
        width: 200,
        backgroundColor: 'rgba(32, 20, 52, 0.85)',
        position: 'absolute',
        right: 20,
        top: 20,
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
        zIndex: 2,
      }}>
        <Typography variant="h6" gutterBottom sx={{ color: 'white' }}>Legend</Typography>
        {moduleTypes.map((type) => (
          <Box key={type.name} sx={{
            display: 'flex',
            alignItems: 'center',
            mb: 1,
            p: 0.5,
            borderRadius: 1,
            backgroundColor: MODULE_COLORS[type.name as keyof typeof MODULE_COLORS],
          }}>
            <Box
              component="img"
              src={`/sprites/${type.name}.png`}
              alt={type.displayName}
              sx={{
                width: 24,
                height: 24,
                mr: 1,
                filter: 'brightness(1.1)',
              }}
              onError={(e) => {
                console.log(`Error loading image: /sprites/${type.name}.png`);
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
            <Typography variant="body2" sx={{ color: 'white', fontWeight: 'bold' }}>
              {type.displayName}
            </Typography>
          </Box>
        ))}
      </Paper>
    );
  };

  // ConstraintsPanel component - No changes needed
  const ConstraintsPanel = () => {
    const totalPrice = resultModules.reduce((sum, mod) => {
      const price = mod.io_fields.find(io => io.unit === 'Price')?.amount || 0;
      return sum + price;
    }, 0);

    const maxX = resultModules.reduce((max, mod) => {
      // Use calculated width and gridColumn
      return Math.max(max, mod.gridColumn + mod.width - 1);
    }, 0);

    const maxY = resultModules.reduce((max, mod) => {
      // Use calculated height and gridRow
      return Math.max(max, mod.gridRow + mod.height - 1);
    }, 0);

    const totalPower = resultModules.reduce((sum, mod) => {
      const power = mod.io_fields.find(io => !io.is_input && io.unit === 'Power')?.amount || 0;
      return sum + power;
    }, 0);

    const totalCooling = resultModules.reduce((sum, mod) => {
      const cooling = mod.io_fields.find(io => !io.is_input && io.unit === 'Cooling')?.amount || 0;
      return sum + cooling;
    }, 0);

    const totalProcessing = resultModules.reduce((sum, mod) => {
      const processing = mod.io_fields.find(io => !io.is_input && io.unit === 'Processing')?.amount || 0;
      return sum + processing;
    }, 0);

    const maxPriceNum = parseFloat(constraints.maxPrice);
    const maxSpaceXNum = parseFloat(constraints.maxSpaceX);
    const maxSpaceYNum = parseFloat(constraints.maxSpaceY);

    const isPriceInLimit = isNaN(maxPriceNum) || totalPrice <= maxPriceNum;
    const isSpaceXInLimit = isNaN(maxSpaceXNum) || maxX <= maxSpaceXNum;
    const isSpaceYInLimit = isNaN(maxSpaceYNum) || maxY <= maxSpaceYNum;

    const formatConstraint = (value: number, max: string | number | undefined) => {
        const maxVal = typeof max === 'string' ? parseFloat(max) : max;
        if (maxVal === undefined || isNaN(maxVal) || maxVal === 0) return `${value}/∞`;
        return `${value}/${maxVal}`;
    }

    const getPercentage = (value: number, max: string | number | undefined) => {
        const maxVal = typeof max === 'string' ? parseFloat(max) : max;
        if (maxVal === undefined || isNaN(maxVal) || maxVal <= 0) return '0%';
        return `${Math.min(100, (value / maxVal) * 100)}%`;
    }


    return (
      <Paper sx={{
        p: 2,
        width: 250,
        backgroundColor: 'rgba(32, 20, 52, 0.85)',
        position: 'absolute',
        left: 20,
        top: 20,
        border: '1px solid rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
        zIndex: 2,
      }}>
        <Typography variant="h6" gutterBottom sx={{ color: 'white' }}>Constraints Status</Typography>

        {/* Price */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Price Usage:</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1, height: 10, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 5, overflow: 'hidden' }}>
              <Box sx={{ height: '100%', width: getPercentage(totalPrice, constraints.maxPrice), bgcolor: isPriceInLimit ? '#4caf50' : '#f44336' }} />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
                {formatConstraint(totalPrice, constraints.maxPrice)}
            </Typography>
          </Box>
        </Box>

        {/* Space X */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Space X Usage:</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1, height: 10, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 5, overflow: 'hidden' }}>
              <Box sx={{ height: '100%', width: getPercentage(maxX, constraints.maxSpaceX), bgcolor: isSpaceXInLimit ? '#4caf50' : '#f44336' }} />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
                {formatConstraint(maxX, constraints.maxSpaceX)}
            </Typography>
          </Box>
        </Box>

        {/* Space Y */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" sx={{ color: 'white', mb: 0.5 }}>Space Y Usage:</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1, height: 10, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 5, overflow: 'hidden' }}>
              <Box sx={{ height: '100%', width: getPercentage(maxY, constraints.maxSpaceY), bgcolor: isSpaceYInLimit ? '#4caf50' : '#f44336' }} />
            </Box>
            <Typography variant="caption" sx={{ color: 'white', minWidth: 70 }}>
                {formatConstraint(maxY, constraints.maxSpaceY)}
            </Typography>
          </Box>
        </Box>

        <Typography variant="h6" gutterBottom sx={{ color: 'white', mt: 3 }}>Production</Typography>
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Power:</Typography>
          <Typography variant="body2" sx={{ color: '#4caf50' }}>{totalPower.toFixed(2)}</Typography>
        </Box>
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Cooling:</Typography>
          <Typography variant="body2" sx={{ color: '#2196f3' }}>{totalCooling.toFixed(2)}</Typography>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="body2" sx={{ color: 'white' }}>Processing:</Typography>
          <Typography variant="body2" sx={{ color: '#ff9800' }}>{totalProcessing.toFixed(2)}</Typography>
        </Box>
      </Paper>
    );
  };

  // GridCell component - No changes needed
  const GridCell = ({ row, col, onClick }: { row: number; col: number; onClick: (row: number, col: number) => void }) => {
    const isDropTarget = draggedModuleId !== null;
    return (
      <Box
        onClick={() => onClick(row, col)}
        sx={{
          gridColumn: col,
          gridRow: row,
          width: CELL_SIZE,
          height: CELL_SIZE,
          cursor: isDropTarget ? 'cell' : 'default',
          backgroundColor: 'transparent',
          '&:hover': {
            backgroundColor: isDropTarget ? 'rgba(255, 255, 255, 0.1)' : 'transparent', // Subtle hover
            // boxShadow: isDropTarget ? 'inset 0 0 0 1px rgba(255, 255, 255, 0.5)' : 'none',
          },
          transition: 'background-color 0.1s', // Faster transition
          zIndex: 0, // Ensure it's behind modules
        }}
      />
    );
  };

  // Cell click handler - Collision detection logic remains the same
  const handleCellClick = (row: number, col: number) => {
    if (draggedModuleId !== null) {
      console.log(`Attempting drop module #${draggedModuleId} at cell: row=${row}, col=${col}`);

      const draggedModule = resultModules.find(mod => mod.id === draggedModuleId);
      if (!draggedModule) {
        console.warn('Could not find dragged module');
        setDraggedModuleId(null);
        return;
      }

      const spanX = draggedModule.width;
      const spanY = draggedModule.height;

      // Check grid bounds
      if (col + spanX - 1 > gridDimensions.cols || row + spanY - 1 > gridDimensions.rows) {
        console.warn('Cannot place module: would extend beyond grid boundaries');
        // Optionally provide visual feedback here (e.g., flash the ghost red)
        return; // Don't drop, keep dragging
      }

      // Check for collisions
      const hasCollision = resultModules.some(mod => {
        if (mod.id === draggedModuleId) return false;
        const modEndX = mod.gridColumn + mod.width - 1;
        const modEndY = mod.gridRow + mod.height - 1;
        const newEndX = col + spanX - 1;
        const newEndY = row + spanY - 1;

        const overlapX = col <= modEndX && newEndX >= mod.gridColumn;
        const overlapY = row <= modEndY && newEndY >= mod.gridRow;

        return overlapX && overlapY;
      });

      if (hasCollision) {
        console.warn('Cannot place module: would overlap with existing module');
        // Optionally provide visual feedback
        return; // Don't drop, keep dragging
      }

      // If no collision and within bounds, update the module position
      setResultModules(prev =>
        prev.map(mod =>
          mod.id === draggedModuleId
            ? { ...mod, gridColumn: col, gridRow: row }
            : mod
        )
      );

      console.log(`Successfully placed module #${draggedModuleId} at row=${row}, col=${col}`);
      setDraggedModuleId(null); // End drag
    }
  };


  // Cancel Drag
  const cancelDrag = useCallback(() => { // Wrap in useCallback
    if (draggedModuleId !== null) {
      setDraggedModuleId(null);
      console.log('Drag canceled');
    }
  }, [draggedModuleId]); // Dependency


  // Add keyboard support for drag operations
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { // Use Escape key to cancel drag
          cancelDrag();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [cancelDrag]); // Depend on the memoized cancelDrag


  // Ghost preview rendering logic - remains the same
  const ghostPreviewContent = () => {
    if (!ghostPreview.visible || draggedModuleId === null) return null;

    const draggedModule = resultModules.find(mod => mod.id === draggedModuleId);
    if (!draggedModule) return null;

    const spanX = draggedModule.width;
    const spanY = draggedModule.height;
    const { col, row } = ghostPreview;

    // Check bounds (same logic as drop)
    const outOfBounds = (
      col + spanX - 1 > gridDimensions.cols ||
      row + spanY - 1 > gridDimensions.rows ||
      col < 1 || row < 1 // Also check starting position
    );

    // Check collisions (same logic as drop)
    const hasCollision = resultModules.some(mod => {
        if (mod.id === draggedModuleId) return false; // Skip self
        const modEndX = mod.gridColumn + mod.width - 1;
        const modEndY = mod.gridRow + mod.height - 1;
        const ghostEndX = col + spanX - 1;
        const ghostEndY = row + spanY - 1;

        const overlapX = col <= modEndX && ghostEndX >= mod.gridColumn;
        const overlapY = row <= modEndY && ghostEndY >= mod.gridRow;
        return overlapX && overlapY;
      });

    // Determine appearance based on validity
    const isValidPlacement = !outOfBounds && !hasCollision;
    const bgColor = isValidPlacement ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 0, 0, 0.3)';
    const borderColor = isValidPlacement ? 'white' : 'red';

    return (
      <Box
        sx={{
          gridColumn: `${col} / span ${spanX}`,
          gridRow: `${row} / span ${spanY}`,
          backgroundColor: bgColor,
          border: `2px dashed ${borderColor}`,
          borderRadius: 1, // Match module style
          zIndex: 5, // Above grid cells but below dragged module maybe?
          pointerEvents: 'none', // Critical
          transition: 'background-color 0.1s, border-color 0.1s', // Smooth color change
        }}
      />
    );
  };

  // --- Main Render ---
  return (
    <Box
      sx={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        paddingTop: '2rem',
        paddingBottom: '2rem',
        gap: 2,
        backgroundColor: '#201434',
        overflow: 'hidden', // Keep this on the outermost container
      }}
    >
      {/* Header Controls */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', width: '90%', justifyContent: 'center', flexWrap: 'wrap' }}>
        <FormControl sx={{ minWidth: 200, mb: { xs: 1, md: 0 } }}>
          <InputLabel id="dc-select-label" sx={{ color: 'white' }}>Load Datacenter</InputLabel>
          <Select
            labelId="dc-select-label"
            value={selectedDC}
            onChange={(e) => {
              const dcId = e.target.value as number;
              setSelectedDC(dcId);
              const selected = datacenters.find(dc => dc.id === dcId);
              console.log("Selected datacenter:", selected);

              if (selected) {
                const spaceXSpec = selected.specs.find(spec => spec.Unit?.toLowerCase() === "space_x");
                const spaceYSpec = selected.specs.find(spec => spec.Unit?.toLowerCase() === "space_y");
                const priceSpec = selected.specs.find(spec => spec.Unit?.toLowerCase() === "price");

                let maxGridX = GRID_COLS;
                let maxGridY = GRID_ROWS;

                // Calculate required grid size based *only* on specs if available
                if (spaceXSpec?.Amount) {
                    maxGridX = Math.max(maxGridX, Math.ceil(spaceXSpec.Amount / CELL_SIZE) + 5); // Add padding
                }
                if (spaceYSpec?.Amount) {
                    maxGridY = Math.max(maxGridY, Math.ceil(spaceYSpec.Amount / CELL_SIZE) + 5); // Add padding
                }

                setGridDimensions({ rows: maxGridY, cols: maxGridX });
                console.log(`Adjusting grid to ${maxGridX} x ${maxGridY} cells based on specs`);

                setConstraints({
                  maxPrice: priceSpec?.Amount?.toString() || "",
                  maxSpaceX: spaceXSpec?.Amount?.toString() || "",
                  maxSpaceY: spaceYSpec?.Amount?.toString() || "",
                });

                if (Array.isArray(selected.modules)) {
                  const mods: PositionedModule[] = selected.modules.map((m, index) => {
                    // Use a more robust unique ID if m.id might not be unique across reloads
                    const uniqueId = m.id ? `${m.id}_${index}` : `gen_${index}`;
                    // Calculate grid positions from absolute coords IF THEY EXIST and are valid
                    // Fallback to 1,1 if no coords provided in data
                    const gridCol = (m.gridColumn !== undefined && m.gridColumn !== null) ? Math.max(1, Math.floor(m.gridColumn / CELL_SIZE) + 1) : 1;
                    const gridRow = (m.gridRow !== undefined && m.gridRow !== null) ? Math.max(1, Math.floor(m.gridRow / CELL_SIZE) + 1) : 1;

                    // Calculate span based on width/height
                    const widthSpan = Math.max(1, Math.ceil((m.width || CELL_SIZE) / CELL_SIZE));
                    const heightSpan = Math.max(1, Math.ceil((m.height || CELL_SIZE) / CELL_SIZE));


                    return {
                      id: uniqueId,
                      name: m.name || 'Unnamed Module',
                      gridColumn: gridCol,
                      gridRow: gridRow,
                      width: widthSpan, // Store calculated span
                      height: heightSpan, // Store calculated span
                      io_fields: m.io_fields || []
                    };
                  });
                   // Post-load check: Ensure no modules overlap or go out of initial bounds
                  // (This is a basic check, a more robust placement algorithm might be needed)
                  const checkedMods = mods.filter(mod =>
                    mod.gridColumn + mod.width -1 <= maxGridX &&
                    mod.gridRow + mod.height - 1 <= maxGridY
                  );
                  if(checkedMods.length !== mods.length) {
                      console.warn("Some modules from the loaded data were outside the calculated grid bounds and were removed.");
                  }

                  setResultModules(checkedMods); // Set the processed modules

                } else {
                  console.error("Loaded datacenter 'modules' is not an array or is missing:", selected.modules);
                  setResultModules([]); // Clear modules if data is bad
                }
              } else {
                 // Handle case where selected DC is not found (e.g., clear selection)
                 setResultModules([]);
                 setGridDimensions({ rows: GRID_ROWS, cols: GRID_COLS }); // Reset grid
                 setConstraints({ maxPrice: '', maxSpaceX: '', maxSpaceY: ''}); // Reset constraints
              }
            }}
            sx={{
                 color: 'white',
                '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.6)' },
                '.MuiSvgIcon-root': { color: 'white' }
            }}
            MenuProps={{ PaperProps: { sx: { bgcolor: '#332a4f', color: 'white' } } }} // Style dropdown
          >
            <MenuItem value="" disabled><em>Select Datacenter...</em></MenuItem> {/* Placeholder */}
            {datacenters.map(dc => (
              <MenuItem key={dc.id} value={dc.id}>{dc.name}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="Max Price"
          value={constraints.maxPrice}
          onChange={(e) => handleChange('maxPrice', e.target.value)}
          type="number"
          variant="outlined"
           InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }}
           InputProps={{ sx: { color: 'white', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' } } }}
           sx={{ mb: { xs: 1, md: 0 } }}
        />
        <TextField
          label="Max Space X (Cells)" // Clarify unit
          value={constraints.maxSpaceX}
          onChange={(e) => handleChange('maxSpaceX', e.target.value)}
          type="number"
           variant="outlined"
           InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }}
           InputProps={{ sx: { color: 'white', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' } } }}
           sx={{ mb: { xs: 1, md: 0 } }}
        />
        <TextField
          label="Max Space Y (Cells)" // Clarify unit
          value={constraints.maxSpaceY}
          onChange={(e) => handleChange('maxSpaceY', e.target.value)}
          type="number"
           variant="outlined"
           InputLabelProps={{ sx: { color: 'rgba(255, 255, 255, 0.7)' } }}
           InputProps={{ sx: { color: 'white', '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255, 255, 255, 0.3)' } } }}
           sx={{ mb: { xs: 1, md: 0 } }}
        />
        <Button variant="contained" onClick={handleDesign} sx={{ height: '56px', mb: { xs: 1, md: 0 } }}> {/* Match TextField height */}
          Design
        </Button>
       </Box>

      <Typography variant="h6" color="white" sx={{ mt: 1 }}>Configuration Result:</Typography>

      {/* Main visualization container */}
      <Box sx={{
        width: '95%', // Use more width
        height: 'calc(100vh - 250px)', // Adjust height dynamically based on controls height
        minHeight: '400px', // Ensure a minimum height
        position: 'relative',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: 2,
        overflow: 'hidden', // Keep this
        mt: 1, // Add some margin top
      }}>

         {/* Zoom controls */}
         <Paper sx={{
           position: 'absolute',
           bottom: 16,
           right: 16,
           zIndex: 10,
           padding: 1,
           display: 'flex',
           backgroundColor: 'rgba(32, 20, 52, 0.85)',
           gap: 1,
           borderRadius: 1,
         }}>
           <Button
             variant="outlined" size="small"
             onClick={() => setZoom(prev => Math.max(0.2, prev - 0.1))} // Slower zoom out
             sx={{ minWidth: '40px', color: 'white', borderColor: 'rgba(255,255,255,0.5)' }}
           ><ZoomOutIcon /></Button>
           <Typography sx={{ color: 'white', display: 'flex', alignItems: 'center', px: 1, minWidth: '50px', textAlign: 'center' }}>
             {Math.round(zoom * 100)}%
           </Typography>
           <Button
             variant="outlined" size="small"
             onClick={() => setZoom(prev => Math.min(5, prev + 0.1))} // Slower zoom in, higher max
             sx={{ minWidth: '40px', color: 'white', borderColor: 'rgba(255,255,255,0.5)' }}
           ><ZoomInIcon /></Button>
           <Button
             variant="outlined" size="small"
             onClick={() => setZoom(1)}
             sx={{ minWidth: '40px', color: 'white', borderColor: 'rgba(255,255,255,0.5)' }}
             title="Reset Zoom" // Tooltip
           ><RestartAltIcon /></Button>
         </Paper>

        {/* Status message when dragging */}
        {draggedModuleId !== null && (
          <Box sx={{
              position: 'absolute', bottom: 16, left: 16, zIndex: 10,
              padding: '4px 8px', backgroundColor: 'rgba(0,0,0,0.7)',
              color: 'white', borderRadius: 1, fontSize: '0.8rem'
          }}>
            Dragging Module #{draggedModuleId} - Click grid to place (Esc to cancel)
          </Box>
        )}

        {/* Grid dimensions indicator */}
        <Box sx={{
            position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
            zIndex: 10, padding: '4px 8px', backgroundColor: 'rgba(0,0,0,0.7)',
            color: 'white', borderRadius: 1, fontSize: '0.8rem'
        }}>
          Grid: {gridDimensions.cols} × {gridDimensions.rows}
        </Box>

        {/* Scrollable container */}
        <Box
          ref={gridContainerRef} // Add ref here
          sx={{
            width: '100%',
            height: '100%',
            overflow: 'auto', // Keep scroll enabled
            position: 'relative',
             // Add a background color to the scroll container if needed
            // backgroundColor: 'rgba(0,0,0,0.1)',
            cursor: draggedModuleId ? 'grabbing' : 'default', // Cursor change for container
          }}
          // Attach cancel drag to the container click as a fallback
          onClick={(e) => {
            // Only cancel if clicking directly on the container, not on a cell or module
             if (e.target === e.currentTarget && draggedModuleId !== null) {
               cancelDrag();
             }
          }}
        >
          {/* Centered grid container (for centering the scaled grid) */}
          <Box
            sx={{
              display: 'flex', // Use flex to center content
              justifyContent: 'center', // Center horizontally
              alignItems: 'flex-start', // Align to top
              minHeight: '100%', // Ensure it takes full height for vertical centering if grid is small
              padding: 4, // Add padding around the scaled grid
              // width: 'fit-content', // Let inner content determine width
              // margin: 'auto', // Center block element if not using flex
            }}
          >
            {/* The scaled grid wrapper */}
            <Box
              sx={{
                transformOrigin: 'top left', // Keep this
                transform: `scale(${zoom})`,
                transition: 'transform 0.2s ease', // Keep transition smooth
                // width: 'fit-content', // Ensure wrapper fits grid
                // height: 'fit-content',
              }}
            >
              {/* The actual grid */}
              <Box
                ref={gridElementRef} // Add ref here
                id="grid"
                sx={{
                  display: 'grid',
                  gridTemplateColumns: `repeat(${gridDimensions.cols}, ${CELL_SIZE}px)`,
                  gridTemplateRows: `repeat(${gridDimensions.rows}, ${CELL_SIZE}px)`,
                  backgroundColor: '#281f3d', // Slightly lighter grid background
                  border: '1px solid #443a5f', // Adjusted border color
                  backgroundImage: `
                    linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px),
                    linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)
                  `, // Subtler grid lines
                  backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
                  position: 'relative', // Needed for absolute positioning of modules/ghost
                  width: `${gridDimensions.cols * CELL_SIZE}px`, // Explicit width
                  height: `${gridDimensions.rows * CELL_SIZE}px`, // Explicit height
                }}
              >
                {/* Grid cells for click handling */}
                {Array.from({ length: gridDimensions.rows }, (_, rowIndex) =>
                  Array.from({ length: gridDimensions.cols }, (_, colIndex) => (
                    <GridCell
                      key={`cell-${rowIndex + 1}-${colIndex + 1}`}
                      row={rowIndex + 1}
                      col={colIndex + 1}
                      onClick={handleCellClick} // Pass the handler
                    />
                  ))
                )}

                {/* Render Modules */}
                 {resultModules.map((mod) => (
                   <DraggableModule
                     // Use a truly unique key, combining potential backend ID and its index/position
                     key={`module-${mod.id}-${mod.gridColumn}-${mod.gridRow}`}
                     mod={mod}
                     spanX={mod.width}
                     spanY={mod.height}
                   />
                 ))}

                {/* Render Ghost Preview */}
                {ghostPreviewContent()}

              </Box> {/* End Actual Grid */}
            </Box> {/* End Scaled Grid Wrapper */}
          </Box> {/* End Centered Grid Container */}
        </Box> {/* End Scrollable Container */}

        {/* Legends and panels */}
        {resultModules.length > 0 && (
          <>
            <ModuleLegend />
            <ConstraintsPanel />
          </>
        )}
      </Box> {/* End Main Visualization Container */}
    </Box> // End Page Container
  );
};

export default MainPage;