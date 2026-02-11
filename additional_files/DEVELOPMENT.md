# Development Guide - Keeping Services Running

## Quick Start

### Option 1: Separate Terminals (Recommended)

**Terminal 1 - Backend:**
```bash
# Start backend with auto-reload
python3 dev-backend.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Option 2: Background Services

**Start backend in background:**
```bash
./dev-services.sh
```

**Start frontend separately:**
```bash
cd frontend && npm run dev
```

## Auto-Reload Behavior

### Backend (Flask)
- **`dev-backend.py`**: Uses Flask's built-in reloader
  - Automatically restarts when Python files change
  - Shows detailed error messages in terminal
  - Best for active development

- **`grace_api.py`**: Production mode (no auto-reload)
  - Use `dev-backend.py` for development instead

### Frontend (Vite)
- Vite automatically reloads on file changes
- Hot Module Replacement (HMR) updates without full page reload
- No additional configuration needed

## Service Ports

- **Frontend (Vite)**: `http://localhost:5173`
- **Backend (Flask)**: `http://localhost:5001`
- **FastAPI**: `http://localhost:8000` (if needed)
- **Express Proxy**: `http://localhost:3001` (if needed)

## Vite Proxy Configuration

The frontend automatically proxies `/api/*` requests to `http://localhost:5001` via Vite's proxy configuration in `frontend/vite.config.ts`.

This means:
- Frontend requests to `/api/health` → proxied to `http://localhost:5001/api/health`
- No CORS issues in development
- Backend must be running for API calls to work

## Troubleshooting

### Backend Not Responding

1. **Check if backend is running:**
   ```bash
   lsof -i :5001
   ```

2. **Check backend logs:**
   ```bash
   tail -f /tmp/grace_api.log
   # or if using dev-backend.py, check the terminal output
   ```

3. **Restart backend:**
   ```bash
   # Kill existing process
   lsof -ti:5001 | xargs kill -9
   
   # Start again
   python3 dev-backend.py
   ```

### Frontend Can't Connect to Backend

1. Ensure backend is running on port 5001
2. Check Vite proxy configuration in `frontend/vite.config.ts`
3. Verify no firewall blocking localhost connections
4. Check browser console for specific error messages

### Services Keep Stopping

- Use `dev-backend.py` instead of `grace_api.py` for development
- Keep terminals open (don't close them)
- Use `screen` or `tmux` if you need to detach:
  ```bash
  # Using screen
  screen -S backend
  python3 dev-backend.py
  # Press Ctrl+A then D to detach
  # Reattach with: screen -r backend
  ```

## Production vs Development

- **Development**: Use `dev-backend.py` (auto-reload enabled)
- **Production**: Use `grace_api.py` (no auto-reload, optimized)

## File Watching

Flask's reloader watches:
- All `.py` files in the project directory
- Files imported by your application

If you add new files that should trigger reloads, Flask will detect them automatically.

