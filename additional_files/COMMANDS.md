# Grace Editor - Command Line Reference

## Quick Start Commands

### Start All Services
```bash
# 1. Start PostgreSQL (if not running)
brew services start postgresql@15

# 2. Start llama-server
cd /Users/raibach/Documents/development/grace-editor
bash scripts/model-management/start_llama_server.sh

# 3. Start Flask API
python3 grace_api.py > /tmp/grace_api.log 2>&1 &

# 4. Start Frontend (in separate terminal)
cd frontend && npm run dev
```

### Stop All Services
```bash
# Stop Flask
lsof -ti:5001 | xargs kill -9

# Stop llama-server
lsof -ti:8080 | xargs kill -9

# Stop Frontend (Ctrl+C in terminal or)
lsof -ti:5173 | xargs kill -9

# Stop PostgreSQL (if needed)
brew services stop postgresql@15
```

## Service Management

### Check Service Status
```bash
# Check PostgreSQL
brew services list | grep postgresql
# OR
ps aux | grep postgres

# Check Flask API (port 5001)
lsof -ti:5001 && echo "✅ Running" || echo "❌ Not running"
curl http://localhost:5001/api/health

# Check llama-server (port 8080)
lsof -ti:8080 && echo "✅ Running" || echo "❌ Not running"
curl http://localhost:8080/v1/models

# Check Frontend (port 5173)
lsof -ti:5173 && echo "✅ Running" || echo "❌ Not running"
```

### Restart Services
```bash
# Restart Flask API
lsof -ti:5001 | xargs kill -9 2>/dev/null && sleep 2 && \
cd /Users/raibach/Documents/development/grace-editor && \
python3 grace_api.py > /tmp/grace_api.log 2>&1 &

# Restart llama-server
lsof -ti:8080 | xargs kill -9 2>/dev/null && sleep 2 && \
cd /Users/raibach/Documents/development/grace-editor && \
bash scripts/model-management/start_llama_server.sh
```

## Logs and Debugging

### View Logs
```bash
# Flask API logs
tail -f /tmp/grace_api.log

# Flask API logs (last 50 lines)
tail -50 /tmp/grace_api.log

# Search Flask logs for persona
tail -f /tmp/grace_api.log | grep -i persona

# Search Flask logs for errors
tail -f /tmp/grace_api.log | grep -i error

# llama-server logs (if running in foreground)
# Check the terminal where you started it

# Frontend logs (if running in foreground)
# Check the terminal where you started it
```

### Database Commands
```bash
# Connect to PostgreSQL
psql -d railway

# List all tables
psql -d railway -c "\dt"

# Check conversations table
psql -d railway -c "SELECT COUNT(*) FROM conversations;"

# Check projects table
psql -d railway -c "SELECT id, name, created_at FROM projects LIMIT 10;"

# Check users table
psql -d railway -c "SELECT id, email FROM users LIMIT 10;"
```

## Development Commands

### Test API Endpoints
```bash
# Health check
curl http://localhost:5001/api/health

# Test conversation creation
curl -X POST http://localhost:5001/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Conversation", "project_id": null}'

# Test projects
curl http://localhost:5001/api/projects
```

### Clear Python Cache
```bash
# Clear .pyc files and __pycache__ directories
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null
```

## Model Management

### Start llama-server
```bash
cd /Users/raibach/Documents/development/grace-editor
bash scripts/model-management/start_llama_server.sh
```

### Check Model Status
```bash
# Check if model file exists
ls -lh models/Llama3.1-8B-Instruct/Llama3.1-8B-Instruct-Q6_K-WORKING.gguf

# Test llama-server API
curl http://localhost:8080/v1/models
```

## File Management

### Find Files
```bash
# Find persona file
find . -name "grace_persona.yaml"

# Find Python files
find . -name "*.py" | grep -E "(grace_api|conversation|project)"

# Find configuration files
find . -name "*.yaml" -o -name "*.yml" | grep -E "(config|persona)"
```

### Edit Files
```bash
# Edit persona file
code fine-tuning/grace_persona.yaml
# OR
nano fine-tuning/grace_persona.yaml

# Edit Flask API
code grace_api.py
```

## Git Commands

### Check Status
```bash
git status
git log --oneline -10
```

### Common Git Operations
```bash
# Add changes
git add .

# Commit
git commit -m "Your commit message"

# Push
git push
```

## Environment

### Check Environment Variables
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Check all env vars
env | grep -E "(DATABASE|API|LLM)"

# Load .env file
source .env  # or
export $(cat .env | xargs)
```

## One-Liner Commands

### Full System Check
```bash
echo "=== SERVICE STATUS ===" && \
echo "PostgreSQL:" && (brew services list | grep postgresql || echo "Not found") && \
echo "Flask (5001):" && (lsof -ti:5001 && echo "✅ Running" || echo "❌ Not running") && \
echo "llama-server (8080):" && (lsof -ti:8080 && echo "✅ Running" || echo "❌ Not running") && \
echo "Frontend (5173):" && (lsof -ti:5173 && echo "✅ Running" || echo "❌ Not running")
```

### Quick Restart Everything
```bash
# Stop all
lsof -ti:5001 | xargs kill -9 2>/dev/null
lsof -ti:8080 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

# Start all
cd /Users/raibach/Documents/development/grace-editor
bash scripts/model-management/start_llama_server.sh &
sleep 3
python3 grace_api.py > /tmp/grace_api.log 2>&1 &
cd frontend && npm run dev &
```

### View All Logs
```bash
# Watch Flask logs
tail -f /tmp/grace_api.log

# Watch with filtering
tail -f /tmp/grace_api.log | grep -E "(persona|error|conversation|✅|❌)"
```

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 5001
lsof -i:5001

# Kill process on port 5001
lsof -ti:5001 | xargs kill -9

# Same for other ports
lsof -ti:8080 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

### Database Connection Issues
```bash
# Test database connection
psql -d railway -c "SELECT 1;"

# Check PostgreSQL is running
brew services list | grep postgresql

# Restart PostgreSQL
brew services restart postgresql@15
```

### Clear All Caches
```bash
# Python cache
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null

# Node modules (if needed)
cd frontend && rm -rf node_modules/.cache

# Restart Flask to reload persona
lsof -ti:5001 | xargs kill -9 2>/dev/null && sleep 2 && \
cd /Users/raibach/Documents/development/grace-editor && \
python3 grace_api.py > /tmp/grace_api.log 2>&1 &
```

