import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#E8A045',       // warm amber
      light: '#F2BC78',
      dark: '#C47E28',
      contrastText: '#1A1410',
    },
    secondary: {
      main: '#6B7FD7',
      contrastText: '#fff',
    },
    background: {
      default: '#0F0E0C',
      paper: '#1A1814',
    },
    surface: {
      card: '#211F1A',
      elevated: '#2A2720',
      input: '#161412',
    },
    text: {
      primary: '#F0EDE6',
      secondary: '#8A8478',
      disabled: '#4A4740',
    },
    divider: 'rgba(255,255,255,0.07)',
    error: { main: '#E05252' },
    success: { main: '#52A882' },
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", sans-serif',
    h6: { fontWeight: 600, letterSpacing: '-0.01em' },
    body1: { fontSize: '0.9rem', lineHeight: 1.6 },
    body2: { fontSize: '0.8rem' },
    caption: { fontSize: '0.72rem', letterSpacing: '0.03em' },
    button: { fontWeight: 600, textTransform: 'none', letterSpacing: '0.01em' },
    mono: { fontFamily: '"DM Mono", monospace', fontSize: '0.75rem' },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#0F0E0C',
          scrollbarWidth: 'thin',
          scrollbarColor: '#3A3730 transparent',
          '&::-webkit-scrollbar': { width: 6 },
          '&::-webkit-scrollbar-track': { background: 'transparent' },
          '&::-webkit-scrollbar-thumb': { background: '#3A3730', borderRadius: 3 },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 10, padding: '8px 20px' },
        containedPrimary: {
          background: 'linear-gradient(135deg, #E8A045 0%, #C47E28 100%)',
          boxShadow: '0 2px 12px rgba(232,160,69,0.25)',
          '&:hover': {
            background: 'linear-gradient(135deg, #F2BC78 0%, #D4922E 100%)',
            boxShadow: '0 4px 20px rgba(232,160,69,0.35)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 500 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#2A2720',
          border: '1px solid rgba(255,255,255,0.08)',
          fontSize: '0.75rem',
        },
      },
    },
  },
})

export default theme
