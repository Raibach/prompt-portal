# Grace Editor - Service Management

## Quick Start

### Start All Services
```bash
./restart-services.sh
```
This will:
- Start backend (8001), frontend (5173), llama-server (8080), ngrok
- Optionally start PostgreSQL if not running
- Print ngrok URL (use for `NGROK_MODEL_URL` in production)

### Check Service Status
```bash
./scripts/utils/check_services.sh
```
Shows which services are running and their health status.

### Restart All Services
```bash
./restart-services.sh
```
Stops and restarts all services.

### Stop All Services
```bash
./stop-services.sh
```

## Service Ports

- **Backend (Flask)**: Port 8001 - http://localhost:8001
- **Frontend (Vite)**: Port 5173 - http://localhost:5173
- **llama-server**: Port 8080 - http://localhost:8080
- **karen-server**: Port 8081 - http://localhost:8081
- **PostgreSQL**: Port 5432

## Logs

View service logs:
```bash
# Backend
tail -f /tmp/backend.log

# Frontend
tail -f /tmp/frontend.log

# llama-server
tail -f /tmp/llama_server.log

# ngrok
tail -f /tmp/ngrok.log
```

## Troubleshooting

### Services Keep Crashing

1. Check logs for errors:
   ```bash
   tail -50 /tmp/backend.log
   ```

2. Check if ports are already in use:
   ```bash
   lsof -ti:8001  # Backend
   lsof -ti:5173  # Frontend
   ```

3. Check PostgreSQL is running:
   ```bash
   brew services list | grep postgresql
   # Or
   pg_isready -h localhost -p 5432
   ```

### Backend Returns 500 Errors

The backend now has better error handling and won't crash. Check:
1. Database connection (PostgreSQL must be running)
2. Backend logs: `tail -f /tmp/backend.log`
3. Health endpoint: `curl http://localhost:8001/api/health`

### Services Disappear During Testing

Run `./restart-services.sh` again to stop and restart all services.

