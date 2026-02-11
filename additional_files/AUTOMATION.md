# Complete Automation System

## Overview

Your Prompt Portal now has **full stack automation** - you design in Figma, code in Cursor, push to GitHub, and everything else happens automatically.

---

## What You Do

1. **Design** in Figma
2. **Code** styling/UI in Cursor
3. **Push** to GitHub (`git push`)

**That's it. Everything else is automatic.**

---

## What Happens Automatically

### On Every Push to GitHub

#### 1. Frontend Build & Deploy
- ✅ Installs dependencies (`npm ci`)
- ✅ Builds production React app (`npm run build`)
- ✅ Deploys to SiteGround `public_html/`
- ✅ Live at `https://prompt-portal-prod.raibach.net`

#### 2. Backend Deploy & Start
- ✅ Uploads backend Python files to SiteGround `/api/`
- ✅ Creates `.env` with database credentials
- ✅ Installs Python dependencies
- ✅ Runs database migrations
- ✅ Stops old backend process
- ✅ Starts new backend process
- ✅ Runs health check

#### 3. Validation
- ✅ Confirms backend responds
- ✅ Checks database connectivity
- ✅ Reports deployment status

**Time**: ~2-3 minutes per push

---

### Every Hour (Automatic Monitoring)

#### Health Check System
- ✅ Checks frontend is accessible
- ✅ Verifies backend process running
- ✅ Tests backend health endpoint
- ✅ Validates database connection
- ✅ **Auto-restarts backend if down**

**You get notified only if something fails.**

---

## Local Development Automation

### Quick Start: `./scripts/local-deploy.sh`

**One command does everything**:
- ✅ Builds frontend
- ✅ Stops old services
- ✅ Starts backend (port 8001)
- ✅ Starts frontend dev server (port 5173)
- ✅ Runs health checks
- ✅ Shows you process IDs and logs

**No manual service management needed.**

---

## Files You Never Touch

### GitHub Actions Workflows
- `.github/workflows/deploy.yml` - Main deployment
- `.github/workflows/health-check.yml` - Hourly monitoring

### Scripts
- `scripts/local-deploy.sh` - Local automation
- `scripts/database/apply_all_migrations.py` - Auto migration runner

**These run automatically. You don't need to modify them.**

---

## Your GitHub Workflow

```bash
# 1. Make changes in Cursor
# 2. Commit
git add .
git commit -m "Update button styling"

# 3. Push (triggers automatic deployment)
git push

# 4. Done - check GitHub Actions tab for deployment status
```

**Live in 2-3 minutes.**

---

## Monitoring

### Check Deployment Status
- Go to: `https://github.com/Raibach/prompt-portal/actions`
- See real-time deployment logs
- Green checkmark = deployed successfully

### Check Production Health
- Frontend: `https://prompt-portal-prod.raibach.net`
- Backend Health: Automatic hourly checks (Actions tab)

### Emergency Manual Health Check
- GitHub Actions → "Production Health Check" → "Run workflow"

---

## What's Protected

✅ **Database migrations**: Run automatically, safe to re-run  
✅ **Backend restarts**: Graceful, zero-downtime  
✅ **Frontend builds**: Cached dependencies for speed  
✅ **Health monitoring**: Auto-recovery if backend crashes  

---

## Zero-Touch Operations

| Operation | Automated | Frequency |
|-----------|-----------|-----------|
| Frontend build | ✅ Yes | Every push |
| Backend deploy | ✅ Yes | Every push |
| Database migrations | ✅ Yes | Every push |
| Backend restart | ✅ Yes | Every push |
| Health checks | ✅ Yes | Hourly |
| Auto-recovery | ✅ Yes | On failure |
| Dependency install | ✅ Yes | Every push |

---

## Emergency Commands

### If local backend crashes:
```bash
./scripts/local-deploy.sh
```

### If you need to manually restart production:
Check GitHub Actions → Latest deploy → Logs

### View production backend logs:
(Requires SSH to SiteGround)
```bash
tail -f /tmp/backend.log
```

---

## The Point

**You focus on design and code. Everything else is automated.**

- No manual FTP uploads
- No manual server management
- No manual database updates
- No manual health monitoring
- No manual restarts

**Just push to GitHub. Done.**

---

**Last Updated**: 2026-02-09  
**Status**: Fully operational
