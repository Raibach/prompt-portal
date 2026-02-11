# Production API Subdomain Setup - Implementation Summary

## ✅ Completed Automated Tasks

All code changes have been implemented and are ready for deployment:

### 1. Apache Reverse Proxy Configuration
- **File**: `apache_proxy.htaccess`
- **Purpose**: Routes requests from `api.prompt-portal-prod.raibach.net` to backend on `localhost:8001`
- **Action Required**: Deploy this file to SiteGround as `.htaccess`

### 2. Frontend Environment Configuration
- **File**: `frontend/.env.production`
- **Content**: `VITE_API_URL=https://api.prompt-portal-prod.raibach.net`
- **Purpose**: Tells frontend to use API subdomain in production
- **Status**: Ready for deployment (GitHub Actions will use this)

### 3. Frontend API Service Updates
- **File**: `frontend/src/services/graceApi.ts`
- **Change**: Added environment variable support to baseUrl
- **Status**: Updated and ready

### 4. Backend Production Mode
- **File**: `grace_api.py`
- **Change**: Added `PRODUCTION` environment variable check
  - Production: Binds to `127.0.0.1:8001` (localhost only, for Apache proxy)
  - Development: Binds to `0.0.0.0:8001` (allows external connections)
- **Status**: Updated and ready

### 5. GitHub Actions Deployment
- **File**: `.github/workflows/deploy.yml`
- **Changes**:
  - Creates `frontend/.env.production` before build
  - Adds `PRODUCTION=true` to backend `.env`
  - Adds `LM_API_URL` and `KAREN_API_URL` from GitHub secret
- **Status**: Updated and ready

## ⏳ Manual Tasks Required (In Order)

### Task 1: Create API Subdomain in SiteGround
1. Log into SiteGround → Site Tools
2. Domain → Subdomains → Create
3. Name: `api` (creates `api.prompt-portal-prod.raibach.net`)
4. Document root: `/home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api`
5. Verify SSL auto-provisions

### Task 2: Deploy `.htaccess` to SiteGround
Upload `apache_proxy.htaccess` to `/home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api/.htaccess`

### Task 3: Add GitHub Secret
1. GitHub → Settings → Secrets → Actions
2. New secret: `NGROK_MODEL_URL`
3. Value: Your Ngrok URL (e.g., `https://xxxxx.ngrok-free.dev`)
   - **Important**: Base URL only, no `/v1/chat/completions` path

### Task 4: Deploy and Test
1. Commit and push changes:
   ```bash
   git add .
   git commit -m "Add production API subdomain support"
   git push origin main
   ```

2. Test API endpoint:
   ```bash
   curl https://api.prompt-portal-prod.raibach.net/api/health
   ```

3. Test frontend at `https://prompt-portal-prod.raibach.net`

## 📁 Files Created/Modified

### Created:
- `apache_proxy.htaccess` - Apache reverse proxy config
- `frontend/.env.production` - Production environment variables
- `DEPLOYMENT_INSTRUCTIONS.md` - Detailed deployment guide
- `PRODUCTION_SETUP_SUMMARY.md` - This file

### Modified:
- `frontend/src/services/graceApi.ts` - Environment variable support
- `grace_api.py` - Production mode binding
- `.github/workflows/deploy.yml` - Environment setup

## 🔄 Architecture Flow

```
User Browser
    ↓ HTTPS
Frontend (prompt-portal-prod.raibach.net)
    ↓ HTTPS
API Subdomain (api.prompt-portal-prod.raibach.net)
    ↓ Apache Proxy
Backend (localhost:8001)
    ↓ HTTPS Tunnel
Ngrok (on local machine)
    ↓ Local Network
AI Models (localhost:8080/8081)
```

## 📝 Next Steps

1. Complete manual tasks 1-3 above
2. Review `DEPLOYMENT_INSTRUCTIONS.md` for detailed instructions
3. Deploy using task 4
4. Verify with test commands
5. Monitor logs and browser console for any issues

## 🆘 Support

See `DEPLOYMENT_INSTRUCTIONS.md` for:
- Detailed troubleshooting steps
- Debug commands
- Rollback procedures
- Success criteria checklist
