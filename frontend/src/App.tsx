import { useState } from 'react'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import { CssBaseline, Container, Box, Typography, Tabs, Tab } from '@mui/material'
import TwoFactorAuth from './components/TwoFactorAuth'
import AccessLogs from './components/AccessLogs'

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  const [activeTab, setActiveTab] = useState(0)

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom align="center">
            AWS Client VPN 2차 인증 관리
          </Typography>
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} centered>
              <Tab label="2차 인증 설정" />
              <Tab label="접근 로그" />
            </Tabs>
          </Box>
          
          {activeTab === 0 && <TwoFactorAuth />}
          {activeTab === 1 && <AccessLogs />}
        </Box>
      </Container>
    </ThemeProvider>
  )
}

export default App
