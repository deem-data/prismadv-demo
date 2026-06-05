import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './app/App'
import './styles/index.css'

// Set document title from environment variable
document.title = import.meta.env.VITE_APP_NAME || 'PrismaDV Demo'

// Clear the session cookie on every page load so a backend restart always
// starts a fresh session (clearing in-memory state and litellm cache).
document.cookie = 'session_id=; Max-Age=0; path=/'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
