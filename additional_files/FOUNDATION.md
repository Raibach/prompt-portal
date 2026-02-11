# Prompt Portal - Foundation & Build Plan

## Project Overview

**Prompt Portal** - A production-ready React-based CMS-style application for managing and editing prompts, repurposed from the Grace editorial engine codebase.

## Current State

### Fully Functional Production Application
- ✅ Complete React application with TypeScript
- ✅ Production-ready styling system
- ✅ Responsive frontend (critical for CMS editing workflow)
- ✅ Comprehensive logging and debugging infrastructure
- ✅ Backend APIs (Flask/Python)
- ✅ Database schema (PostgreSQL)
- ✅ Frontend components and services

### Application Type
**CMS-like Prompt Portal** with real-time editing capabilities requiring:
- Responsive browser resizing behavior
- Multi-panel editing interface
- Real-time preview and editing
- Advanced debugging and logging

## Design-to-Production Pipeline

```
Figma Designs → Cursor Implementation → GitHub (main) → SiteGround (Live Production)
```

### Pipeline Rules
1. **Single Branch Deployment**
   - `main` branch = live production
   - No versioning, no separate staging branches
   - What's in `main` is what's live

2. **Code Quality Standards**
   - Production-grade code only
   - Microsoft senior engineer review standard (25+ years experience)
   - No bloat, no development artifacts
   - Clean, maintainable codebase

3. **Deployment Method**
   - GitHub Actions with FTP deploy to SiteGround
   - Automated deployment on push to `main`
   - Workflow: `.github/workflows/deploy.yml`

## Project Scope

### What We're Doing
- **Re-styling and re-branding** the existing Grace application
- Applying new visual design from Figma
- Maintaining all existing functionality
- Preserving responsive behavior

### What We're NOT Doing
- ❌ Changing folder structure
- ❌ Refactoring backend logic
- ❌ Rebuilding components from scratch
- ❌ Altering database schema
- ❌ Modifying logging/debugging systems

## Technical Stack

### Frontend
- React with TypeScript
- Vite build system
- Lexical editor framework
- TailwindCSS (existing styling)
- Responsive CSS architecture

### Backend
- Python/Flask API server (port 8001)
- PostgreSQL database
- Debug logging system
- Memory and monitoring infrastructure

### Deployment
- **GitHub**: `Raibach/prompt-portal`
- **Hosting**: SiteGround
- **Database**: SiteGround PostgreSQL (when configured)
- **FTP**: Automated via GitHub Actions

## Infrastructure

### Services (Development)
- Backend: `http://localhost:8001`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

### Production
- Site URL: `https://prompt-portal-prod.raibach.net`
- FTP Server: `ftp.raibach.net`
- Remote Path: `/public_html/`

## Active Systems

### Debugging & Logging
- Centralized debug logger (`backend/debug_logger.py`)
- Debug API endpoints (`/api/debug/*`)
- Frontend UI debug mode (`?debug=ui`)
- Log files in `logs/` directory
- Memory monitoring and leak detection

### Full Stack Automation

#### 1. Deployment Pipeline (`.github/workflows/deploy.yml`)
**Triggers**: Automatic on push to `main` branch

**What It Does**:
- Builds React frontend (`npm ci && npm run build`)
- Deploys frontend to SiteGround `/public_html/`
- Deploys backend files to SiteGround `/api/`
- Installs Python dependencies on SiteGround
- Runs database migrations automatically
- Restarts backend service with health checks
- Validates deployment success

**Required Secrets**:
- `FTP_SERVER` - SiteGround FTP hostname
- `FTP_USERNAME` - SiteGround username
- `FTP_PASSWORD` - SiteGround password
- `SITEGROUND_POSTGRE` - Database credentials (HOST, PORT, NAME, USER, PASSWORD)

#### 2. Health Monitoring (`.github/workflows/health-check.yml`)
**Triggers**: Hourly (every hour) + Manual dispatch

**What It Does**:
- Checks frontend HTTPS availability
- Verifies backend process is running
- Tests backend health endpoint
- Validates database connectivity
- **Auto-restarts backend if down**
- Reports status

#### 3. Local Development (`scripts/local-deploy.sh`)
**Usage**: `./scripts/local-deploy.sh`

**What It Does**:
- Builds frontend locally
- Stops existing services
- Starts backend with health checks
- Starts frontend dev server
- Reports process IDs and log locations
- Mimics production workflow

## Development Workflow

### Local Development
1. Start services: `./restart-services.sh`
2. Backend runs on port 8001
3. Frontend runs on port 5173
4. Edit components and styling
5. Test responsive behavior

### Deployment
1. Commit changes to `main`
2. Push to GitHub
3. GitHub Actions runs automatically
4. Files deploy to SiteGround via FTP
5. Production site updates immediately

## Critical Requirements

### Responsive Design
- Application must respond correctly to browser resizing
- Multi-panel layout must adapt to viewport changes
- Editing interface must remain functional at all viewport sizes

### Code Cleanliness
- No unused files or dead code in production
- No development artifacts (logs, debug files, etc.)
- Clean commit history
- Production-ready code only

### Existing Infrastructure
- Use existing debug/logging systems (do not rebuild)
- Maintain current folder structure
- Preserve all backend APIs
- Keep database schema intact

## Next Steps

1. **Complete GitHub Setup**
   - Add FTP secrets to GitHub repository
   - Verify GitHub Actions workflow

2. **SiteGround Configuration**
   - Configure PostgreSQL database
   - Set up environment variables
   - Test FTP deployment

3. **Styling Implementation**
   - Apply Figma designs to existing components
   - Maintain responsive behavior
   - Test across viewport sizes

4. **Production Deploy**
   - Push to `main` branch
   - Verify auto-deployment
   - Test live site at `prompt-portal-prod.raibach.net`

## Important Notes

- This is a **re-styling project**, not a rebuild
- All core functionality exists and works
- Focus is on visual design and branding
- Maintain production-grade code quality
- Single-branch deployment (no staging)
- Clean, minimal, professional codebase

---

**Last Updated**: 2026-02-09  
**Repository**: `https://github.com/Raibach/prompt-portal`  
**Live Site**: `https://prompt-portal-prod.raibach.net` (pending deployment)
# Pipeline Test - Mon Feb  9 08:26:48 CST 2026
# Test connection - Mon Feb  9 08:30:51 CST 2026
