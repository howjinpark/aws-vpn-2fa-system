import React, { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Box,
  CircularProgress,
  Alert,
  Button
} from '@mui/material'
import { Refresh as RefreshIcon } from '@mui/icons-material'
import axios from 'axios'

const API_BASE_URL = 'http://your-alb-domain.amazonaws.com/api/auth'

interface AccessLog {
  username: string
  client_ip: string
  access_time: string
  two_factor_verified: boolean
  access_granted: boolean
}

const AccessLogs: React.FC = () => {
  const [logs, setLogs] = useState<AccessLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchLogs = async () => {
    setLoading(true)
    setError('')
    
    try {
      const response = await axios.get(`${API_BASE_URL}/access-logs/`)
      
      if (response.data.success) {
        setLogs(response.data.logs)
      } else {
        setError('로그를 불러오는데 실패했습니다.')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || '서버 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getStatusColor = (granted: boolean) => {
    return granted ? 'success' : 'error'
  }

  const get2FAColor = (verified: boolean) => {
    return verified ? 'success' : 'warning'
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h4">
            VPN 접근 로그
          </Typography>
          <Button
            variant="outlined"
            onClick={fetchLogs}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          >
            새로고침
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {loading && !error && (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        )}

        {!loading && !error && (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>사용자명</strong></TableCell>
                  <TableCell><strong>IP 주소</strong></TableCell>
                  <TableCell><strong>접근 시간</strong></TableCell>
                  <TableCell align="center"><strong>2FA 인증</strong></TableCell>
                  <TableCell align="center"><strong>접근 허용</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography variant="body2" color="text.secondary">
                        접근 로그가 없습니다.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log, index) => (
                    <TableRow key={index} hover>
                      <TableCell>{log.username}</TableCell>
                      <TableCell>{log.client_ip}</TableCell>
                      <TableCell>{formatDateTime(log.access_time)}</TableCell>
                      <TableCell align="center">
                        <Chip
                          label={log.two_factor_verified ? '성공' : '실패'}
                          color={get2FAColor(log.two_factor_verified)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={log.access_granted ? '허용' : '거부'}
                          color={getStatusColor(log.access_granted)}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          * 최근 50개의 로그만 표시됩니다.
        </Typography>
      </CardContent>
    </Card>
  )
}

export default AccessLogs