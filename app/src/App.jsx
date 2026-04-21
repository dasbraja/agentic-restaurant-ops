import React, { useState, useRef, useEffect, useCallback } from 'react'
import {
  ThemeProvider, CssBaseline, Box, AppBar, Toolbar, Typography,
  IconButton, TextField, Button, Paper, Chip, Avatar, Tooltip,
  CircularProgress, Fade, Divider, InputAdornment, Collapse,
  alpha,
} from '@mui/material'
import {
  Restaurant as RestaurantIcon,
  Send as SendIcon,
  AddCircleOutline as NewSessionIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Wifi as OnlineIcon,
  WifiOff as OfflineIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material'
import theme from './theme'

// ── Suggestion chips ────────────────────────────────────────────────────────
const SUGGESTIONS = [
  'How long is the wait downtown?',
  'Is the salmon available tonight?',
  "What's on table 7's order?",
  'What time does Pike Place close?',
  "What's today's downtown revenue?",
  'Add party of 4 named "Smith" to waitlist',
]

// ── Helpers ─────────────────────────────────────────────────────────────────
const agentLabel = (name) =>
  name ? name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'Agent'

const formatTime = (date) =>
  date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

// ── Message bubble ───────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const isError = msg.role === 'error'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Fade in timeout={300}>
      <Box
        sx={{
          display: 'flex',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-end',
          gap: 1,
          mb: 1.5,
          px: { xs: 1, sm: 0 },
        }}
      >
        {/* Avatar */}
        <Avatar
          sx={{
            width: 28,
            height: 28,
            bgcolor: isUser
              ? 'primary.main'
              : isError
              ? 'error.main'
              : alpha(theme.palette.secondary.main, 0.25),
            flexShrink: 0,
            mb: 0.5,
          }}
        >
          {isUser ? (
            <PersonIcon sx={{ fontSize: 15 }} />
          ) : (
            <BotIcon sx={{ fontSize: 15, color: isError ? '#fff' : 'secondary.main' }} />
          )}
        </Avatar>

        {/* Bubble */}
        <Box sx={{ maxWidth: '78%', minWidth: 60 }}>
          {/* Agent label */}
          {!isUser && msg.agentName && (
            <Typography
              variant="caption"
              sx={{
                color: 'text.secondary',
                mb: 0.4,
                display: 'block',
                pl: 0.5,
                fontFamily: '"DM Mono", monospace',
              }}
            >
              {agentLabel(msg.agentName)}
            </Typography>
          )}

          <Paper
            elevation={0}
            sx={{
              px: 1.75,
              py: 1.25,
              borderRadius: isUser
                ? '16px 16px 4px 16px'
                : '16px 16px 16px 4px',
              background: isUser
                ? 'linear-gradient(135deg, #E8A045 0%, #C47E28 100%)'
                : isError
                ? alpha(theme.palette.error.main, 0.12)
                : alpha('#fff', 0.04),
              border: isUser
                ? 'none'
                : isError
                ? `1px solid ${alpha(theme.palette.error.main, 0.3)}`
                : '1px solid rgba(255,255,255,0.07)',
              position: 'relative',
              '&:hover .copy-btn': { opacity: 1 },
            }}
          >
            <Typography
              variant="body1"
              sx={{
                color: isUser
                  ? '#1A1410'
                  : isError
                  ? 'error.main'
                  : 'text.primary',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontWeight: isUser ? 500 : 400,
              }}
            >
              {msg.text}
            </Typography>

            {/* Copy button */}
            {!isUser && (
              <IconButton
                className="copy-btn"
                size="small"
                onClick={handleCopy}
                sx={{
                  position: 'absolute',
                  top: 4,
                  right: 4,
                  opacity: 0,
                  transition: 'opacity 0.2s',
                  color: 'text.secondary',
                  p: 0.4,
                  '&:hover': { color: 'primary.main' },
                }}
              >
                {copied ? <CheckIcon sx={{ fontSize: 13 }} /> : <CopyIcon sx={{ fontSize: 13 }} />}
              </IconButton>
            )}
          </Paper>

          {/* Timestamp */}
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              mt: 0.4,
              color: 'text.disabled',
              textAlign: isUser ? 'right' : 'left',
              px: 0.5,
            }}
          >
            {formatTime(msg.time)}
          </Typography>
        </Box>
      </Box>
    </Fade>
  )
}

// ── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <Fade in>
      <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 1, mb: 1.5, px: { xs: 1, sm: 0 } }}>
        <Avatar sx={{ width: 28, height: 28, bgcolor: alpha(theme.palette.secondary.main, 0.25), mb: 0.5 }}>
          <BotIcon sx={{ fontSize: 15, color: 'secondary.main' }} />
        </Avatar>
        <Paper
          elevation={0}
          sx={{
            px: 2,
            py: 1.5,
            borderRadius: '16px 16px 16px 4px',
            background: alpha('#fff', 0.04),
            border: '1px solid rgba(255,255,255,0.07)',
            display: 'flex',
            alignItems: 'center',
            gap: 0.6,
          }}
        >
          {[0, 1, 2].map((i) => (
            <Box
              key={i}
              sx={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                opacity: 0.6,
                animation: 'bounce 1.2s ease-in-out infinite',
                animationDelay: `${i * 0.2}s`,
                '@keyframes bounce': {
                  '0%, 60%, 100%': { transform: 'translateY(0)' },
                  '30%': { transform: 'translateY(-6px)', opacity: 1 },
                },
              }}
            />
          ))}
        </Paper>
      </Box>
    </Fade>
  )
}

// ── Settings panel ────────────────────────────────────────────────────────────
function SettingsPanel({ apiUrl, onApiUrlChange }) {
  const [open, setOpen] = useState(false)
  return (
    <Box>
      <Button
        size="small"
        startIcon={<SettingsIcon sx={{ fontSize: 15 }} />}
        endIcon={open ? <ExpandLessIcon sx={{ fontSize: 15 }} /> : <ExpandMoreIcon sx={{ fontSize: 15 }} />}
        onClick={() => setOpen((v) => !v)}
        sx={{ color: 'text.secondary', fontSize: '0.75rem', py: 0.5 }}
      >
        API settings
      </Button>
      <Collapse in={open}>
        <Box sx={{ pt: 1, pb: 0.5 }}>
          <TextField
            fullWidth
            size="small"
            label="Backend URL"
            value={apiUrl}
            onChange={(e) => onApiUrlChange(e.target.value.replace(/\/$/, ''))}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <Typography sx={{ fontFamily: '"DM Mono", monospace', fontSize: '0.7rem', color: 'text.disabled' }}>
                    /api/chat
                  </Typography>
                </InputAdornment>
              ),
              sx: { fontFamily: '"DM Mono", monospace', fontSize: '0.78rem' },
            }}
            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
          />
        </Box>
      </Collapse>
    </Box>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: 'agent',
      text: 'Hello! I can help with orders, wait times, inventory, and location info. What do you need?',
      agentName: 'restaurant_orchestrator',
      time: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [userId] = useState(() => {
    const stored = localStorage.getItem('restaurant_agent_user_id')
    if (stored) return stored
    const id = 'user_' + Math.random().toString(36).slice(2, 7)
    localStorage.setItem('restaurant_agent_user_id', id)
    return id
  })
  const [apiUrl, setApiUrl] = useState('http://localhost:8020')
  const [online, setOnline] = useState(true)
  const [msgId, setMsgId] = useState(1)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Ping health endpoint to show online status
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(3000) })
        setOnline(res.ok)
      } catch {
        setOnline(false)
      }
    }
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [apiUrl])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const addMessage = useCallback((msg) => {
    setMsgId((id) => {
      setMessages((prev) => [...prev, { id, ...msg }])
      return id + 1
    })
  }, [])

  const send = useCallback(
    async (text) => {
      const trimmed = text.trim()
      if (!trimmed || loading) return

      addMessage({ role: 'user', text: trimmed, time: new Date() })
      setInput('')
      setLoading(true)

      try {
        const res = await fetch(`${apiUrl}/api/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: trimmed, session_id: sessionId, user_id: userId }),
        })

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }))
          throw new Error(err.detail || res.statusText)
        }

        const data = await res.json()
        setSessionId(data.session_id)
        addMessage({
          role: 'agent',
          text: data.response,
          agentName: data.agent_used,
          time: new Date(),
        })
      } catch (e) {
        addMessage({ role: 'error', text: 'Error: ' + e.message, time: new Date() })
      } finally {
        setLoading(false)
        inputRef.current?.focus()
      }
    },
    [loading, sessionId, userId, apiUrl, addMessage]
  )

  const newSession = () => {
    setSessionId(null)
    setMessages([
      {
        id: 0,
        role: 'agent',
        text: 'New session started. How can I help?',
        agentName: 'restaurant_orchestrator',
        time: new Date(),
      },
    ])
    setMsgId(1)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          height: '100dvh',
          display: 'flex',
          flexDirection: 'column',
          bgcolor: 'background.default',
          backgroundImage:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(232,160,69,0.06), transparent)',
        }}
      >
        {/* ── AppBar ── */}
        <AppBar
          position="static"
          elevation={0}
          sx={{
            bgcolor: alpha('#1A1814', 0.9),
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <Toolbar sx={{ gap: 1.5, minHeight: '56px !important', px: { xs: 2, sm: 3 } }}>
            {/* Icon + title */}
            <Box
              sx={{
                width: 34,
                height: 34,
                borderRadius: 2,
                background: 'linear-gradient(135deg, #E8A045, #C47E28)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <RestaurantIcon sx={{ fontSize: 18, color: '#1A1410' }} />
            </Box>

            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" sx={{ fontSize: '0.95rem', lineHeight: 1.2 }}>
                Restaurant Agent
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                Multi-agent ops · Google ADK
              </Typography>
            </Box>

            {/* Session chip */}
            {sessionId && (
              <Tooltip title={`Session: ${sessionId}`}>
                <Chip
                  label={sessionId.slice(0, 8) + '…'}
                  size="small"
                  sx={{
                    fontFamily: '"DM Mono", monospace',
                    fontSize: '0.68rem',
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    color: 'primary.light',
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.25)}`,
                    height: 22,
                  }}
                />
              </Tooltip>
            )}

            {/* Online indicator */}
            <Tooltip title={online ? 'Backend online' : 'Backend offline'}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                {online ? (
                  <OnlineIcon sx={{ fontSize: 16, color: 'success.main' }} />
                ) : (
                  <OfflineIcon sx={{ fontSize: 16, color: 'error.main' }} />
                )}
              </Box>
            </Tooltip>

            {/* New session */}
            <Tooltip title="New session">
              <IconButton size="small" onClick={newSession} sx={{ color: 'text.secondary' }}>
                <NewSessionIcon sx={{ fontSize: 20 }} />
              </IconButton>
            </Tooltip>
          </Toolbar>
        </AppBar>

        {/* ── Message list ── */}
        <Box
          sx={{
            flex: 1,
            overflowY: 'auto',
            px: { xs: 1.5, sm: 3 },
            py: 2,
            display: 'flex',
            flexDirection: 'column',
            maxWidth: 780,
            width: '100%',
            mx: 'auto',
          }}
        >
          {messages.map((msg) => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </Box>

        {/* ── Suggestions ── */}
        {messages.length <= 2 && !loading && (
          <Box
            sx={{
              px: { xs: 1.5, sm: 3 },
              pb: 1,
              maxWidth: 780,
              width: '100%',
              mx: 'auto',
              display: 'flex',
              flexWrap: 'wrap',
              gap: 0.75,
            }}
          >
            {SUGGESTIONS.map((s) => (
              <Chip
                key={s}
                label={s}
                size="small"
                clickable
                onClick={() => send(s)}
                sx={{
                  fontSize: '0.75rem',
                  bgcolor: alpha('#fff', 0.04),
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'text.secondary',
                  '&:hover': {
                    bgcolor: alpha(theme.palette.primary.main, 0.1),
                    borderColor: alpha(theme.palette.primary.main, 0.35),
                    color: 'primary.light',
                  },
                  transition: 'all 0.15s',
                }}
              />
            ))}
          </Box>
        )}

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.06)' }} />

        {/* ── Input area ── */}
        <Box
          sx={{
            px: { xs: 1.5, sm: 3 },
            py: 1.5,
            maxWidth: 780,
            width: '100%',
            mx: 'auto',
          }}
        >
          <SettingsPanel apiUrl={apiUrl} onApiUrlChange={setApiUrl} />

          <Box sx={{ display: 'flex', gap: 1.5, mt: 1, alignItems: 'flex-end' }}>
            <TextField
              inputRef={inputRef}
              fullWidth
              multiline
              maxRows={4}
              placeholder="Ask about orders, wait times, inventory, locations…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              variant="outlined"
              sx={{
                '& .MuiOutlinedInput-root': {
                  borderRadius: 3,
                  bgcolor: alpha('#fff', 0.03),
                  fontSize: '0.875rem',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.1)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.18)' },
                  '&.Mui-focused fieldset': { borderColor: 'primary.main' },
                },
              }}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={() => send(input)}
              disabled={loading || !input.trim()}
              sx={{
                minWidth: 48,
                width: 48,
                height: 48,
                borderRadius: 3,
                p: 0,
                flexShrink: 0,
              }}
            >
              {loading ? (
                <CircularProgress size={18} sx={{ color: '#1A1410' }} />
              ) : (
                <SendIcon sx={{ fontSize: 18 }} />
              )}
            </Button>
          </Box>

          <Typography
            variant="caption"
            sx={{ display: 'block', textAlign: 'center', mt: 1, color: 'text.disabled' }}
          >
            Enter to send · Shift+Enter for new line
          </Typography>
        </Box>
      </Box>
    </ThemeProvider>
  )
}