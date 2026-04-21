# Restaurant Agent — React Chat UI

A Material UI chat interface for the Restaurant Agent API (Google ADK).

## Setup

```bash
npm install
npm run dev
```

Open http://localhost:5173

## Configure

- **Backend URL**: Defaults to `http://localhost:8020`. Change it via the
  "API settings" toggle in the UI, or set the `VITE_API_URL` env variable:
  ```
  VITE_API_URL=http://your-backend:8020
  ```
  Then in `src/App.jsx` initialise state as:
  ```js
  const [apiUrl, setApiUrl] = useState(import.meta.env.VITE_API_URL || 'http://localhost:8020')
  ```

## Build for production

```bash
npm run build
# Output is in /dist — deploy to any static host (Netlify, Vercel, S3, etc.)
```

## Features

- 🌙 Dark theme with amber restaurant accents
- 💬 Multi-turn sessions with session ID badge
- 🟢 Live backend health indicator
- ✨ Animated typing indicator
- 📋 One-click message copy
- 💡 Suggestion chips on first load
- ⚙️  Collapsible API URL settings panel
- ⌨️  Enter to send, Shift+Enter for newline
