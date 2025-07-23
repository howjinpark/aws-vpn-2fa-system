import React, { useState } from 'react'
import {
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Paper
} from '@mui/material'
import axios from 'axios'

const API_BASE_URL = 'http://your-alb-domain.amazonaws.com/api/auth'

interface SetupResponse {
  success: boolean
  qr_code: string
  secret_key: string
  is_enabled: boolean
  error?: string
}

const TwoFactorAuth: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0)
  const [username, setUsername] = useState('')
  const [token, setToken] = useState('')
  const [qrCode, setQrCode] = useState('')
  const [secretKey, setSecretKey] = useState('')
  const [isEnabled, setIsEnabled] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const steps = ['사용자 입력', 'QR 코드 스캔', '인증 확인']

  const handleSetup2FA = async () => {
    if (!username.trim()) {
      setError('사용자명을 입력해주세요.')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await axios.post<SetupResponse>(`${API_BASE_URL}/setup-2fa/`, {
        username: username.trim()
      })

      if (response.data.success) {
        setQrCode(response.data.qr_code)
        setSecretKey(response.data.secret_key)
        setIsEnabled(response.data.is_enabled)
        setActiveStep(1)
        setSuccess('QR 코드가 생성되었습니다. Google Authenticator로 스캔해주세요.')
      } else {
        setError(response.data.error || '2FA 설정에 실패했습니다.')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '서버 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify2FA = async () => {
    if (!token.trim()) {
      setError('인증 코드를 입력해주세요.')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await axios.post(`${API_BASE_URL}/verify-2fa/`, {
        username,
        token: token.trim()
      })

      if (response.data.success) {
        setSuccess('2FA 인증이 성공했습니다!')
        setActiveStep(2)
      } else {
        setError(response.data.message || '인증에 실패했습니다.')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '인증 확인 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const handleEnable2FA = async () => {
    if (!token.trim()) {
      setError('인증 코드를 입력해주세요.')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await axios.post(`${API_BASE_URL}/enable-2fa/`, {
        username,
        token: token.trim()
      })

      if (response.data.success) {
        setIsEnabled(true)
        setSuccess('2FA가 성공적으로 활성화되었습니다!')
      } else {
        setError(response.data.message || '2FA 활성화에 실패했습니다.')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '2FA 활성화 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setActiveStep(0)
    setUsername('')
    setToken('')
    setQrCode('')
    setSecretKey('')
    setIsEnabled(false)
    setError('')
    setSuccess('')
  }

  return (
    <Card sx={{ maxWidth: 800, margin: '0 auto' }}>
      <CardContent>
        <Typography variant="h4" gutterBottom align="center">
          2차 인증 (2FA) 설정
        </Typography>

        <Box sx={{ width: '100%', mb: 4 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        {activeStep === 0 && (
          <Box>
            <TextField
              fullWidth
              label="사용자명"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              margin="normal"
              variant="outlined"
            />
            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Button
                variant="contained"
                onClick={handleSetup2FA}
                disabled={loading}
                size="large"
              >
                {loading ? '처리 중...' : '2FA 설정 시작'}
              </Button>
            </Box>
          </Box>
        )}

        {activeStep === 1 && qrCode && (
          <Box>
            <Typography variant="h6" gutterBottom align="center">
              Google Authenticator로 QR 코드를 스캔하세요
            </Typography>
            
            <Paper elevation={3} sx={{ p: 2, textAlign: 'center', mb: 2 }}>
              <img 
                src={`data:image/png;base64,${qrCode}`} 
                alt="QR Code" 
                style={{ maxWidth: '300px', width: '100%' }}
              />
            </Paper>

            <Typography variant="body2" gutterBottom align="center" color="text.secondary">
              또는 수동으로 입력하세요: <strong>{secretKey}</strong>
            </Typography>

            <TextField
              fullWidth
              label="Google Authenticator 코드"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              margin="normal"
              variant="outlined"
              placeholder="6자리 숫자 입력"
            />

            <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
              <Button onClick={resetForm} disabled={loading}>
                처음부터
              </Button>
              {isEnabled ? (
                <Button
                  variant="contained"
                  onClick={handleVerify2FA}
                  disabled={loading}
                >
                  {loading ? '확인 중...' : '인증 확인'}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  onClick={handleEnable2FA}
                  disabled={loading}
                >
                  {loading ? '활성화 중...' : '2FA 활성화'}
                </Button>
              )}
            </Box>
          </Box>
        )}

        {activeStep === 2 && (
          <Box textAlign="center">
            <Typography variant="h5" color="success.main" gutterBottom>
              2차 인증이 완료되었습니다! ✅
            </Typography>
            <Typography variant="body1" sx={{ mb: 2 }}>
              이제 AWS Client VPN에 연결할 때 2차 인증을 사용할 수 있습니다.
            </Typography>
            <Button variant="outlined" onClick={resetForm}>
              새로운 설정
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

export default TwoFactorAuth