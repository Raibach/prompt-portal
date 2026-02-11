# Production API Subdomain Deployment Instructions

## Summary

This document provides step-by-step instructions for completing the production API subdomain setup. Most of the code changes have been automated, but some manual configuration is required.

## Automated Changes (Already Completed)

✅ **Apache proxy configuration** - Created `apache_proxy.htaccess`
✅ **Frontend environment file** - Created `frontend/.env.production`
✅ **Frontend API services** - Updated to use environment variables
✅ **Backend production mode** - Updated `grace_api.py` to bind to localhost in production
✅ **GitHub Actions workflow** - Updated to create environment files and pass Ngrok URL

## Manual Steps Required

### Step 1: Create API Subdomain in SiteGround

1. Log into SiteGround → Site Tools
2. Navigate to **Domain → Subdomains**
3. Click **Create Subdomain**
4. Enter subdomain name: `api`
5. Full domain will be: `api.prompt-portal-prod.raibach.net`
6. Set document root to: `/home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api`
7. Click **Create**
8. Verify SSL certificate is auto-provisioned (should happen automatically)

### Step 2: Deploy Apache Proxy Configuration

The `.htaccess` file has been created at the root of the repository as `apache_proxy.htaccess`. You need to deploy it to SiteGround:

**Option A: Via FTP**
1. Connect to SiteGround via FTP using your credentials
2. Navigate to `/home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api/`
3. Upload `apache_proxy.htaccess` and rename it to `.htaccess`

**Option B: Via Site Tools File Manager**
1. Log into SiteGround → Site Tools
2. Navigate to **Site → File Manager**
3. Go to `/home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api/`
4. Create a new file named `.htaccess`
5. Paste the contents from `apache_proxy.htaccess`
6. Save the file

### Step 3: Add GitHub Secret for Ngrok URL

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `NGROK_MODEL_URL`
5. Value: Your permanent Ngrok tunnel URL (e.g., `https://xxxxx.ngrok-free.dev`)
   - **Important**: Do NOT include the `/v1/chat/completions` path - just the base URL
   - Example: `https://abc123.ngrok-free.app` (NOT `https://abc123.ngrok-free.app/v1/chat/completions`)
6. Click **Add secret**

### Step 4: Deploy and Test

1. **Commit and push the changes:**
   ```bash
   git add .
   git commit -m "Add production API subdomain support"
   git push origin main
   ```

2. **Monitor the GitHub Actions deployment:**
   - Go to GitHub → Actions tab
   - Watch the deployment workflow
   - Ensure all steps complete successfully

3. **Verify API endpoint is accessible:**
   ```bash
   curl https://api.prompt-portal-prod.raibach.net/api/health
   ```
   Should return: `{"status": "ok", ...}`

4. **Test frontend connectivity:**
   - Open browser to `https://prompt-portal-prod.raibach.net`
   - Open browser console (F12 → Console tab)
   - Check for API calls to `api.prompt-portal-prod.raibach.net`
   - Verify no CORS errors
   - Test submitting a query to Grace AI

5. **Verify backend logs:**
   ```bash
   # SSH into SiteGround
   ssh jtftp@raibach.net@raibach.net
   
   # Check backend logs
   tail -f /tmp/backend.log
   
   # Should see "Starting Grace API in PRODUCTION mode"
   ```

## Troubleshooting

### Frontend shows "Cannot connect to server"

**Check:**
- Subdomain DNS has propagated (can take a few minutes)
- SSL certificate is active for `api.prompt-portal-prod.raibach.net`
- `.htaccess` file is in the correct location
- Backend is running on `localhost:8001`

**Debug:**
```bash
# Check if backend is running
ps aux | grep grace_api.py

# Check backend logs
tail -50 /tmp/backend.log

# Test backend directly (from SSH)
curl http://localhost:8001/api/health
```

### API returns 502 Bad Gateway

**Check:**
- Backend process is running
- Backend is listening on port 8001
- `.htaccess` proxy configuration is correct

**Fix:**
```bash
# Restart backend
pkill -f grace_api.py
cd /home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api
nohup python3 grace_api.py > /tmp/backend.log 2>&1 &
```

### Ngrok tunnel not working

**Check:**
- `NGROK_MODEL_URL` secret is set correctly in GitHub
- Environment variables are being created in deployment
- Backend logs show the Ngrok URL being used

**Debug:**
```bash
# Check .env file on server
cat /home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api/.env

# Should contain:
# LM_API_URL=https://xxxxx.ngrok-free.dev/v1/chat/completions
# KAREN_API_URL=https://xxxxx.ngrok-free.dev/v1/chat/completions
```

### CORS errors in browser console

**Check:**
- Backend CORS configuration allows `api.prompt-portal-prod.raibach.net`
- `.htaccess` is setting proper forwarding headers

**Fix (if needed):**
Update `grace_api.py` CORS configuration to include the API subdomain.

## Rollback Plan

If issues occur, you can rollback:

1. **Remove `.htaccess` from SiteGround:**
   ```bash
   rm /home/jtftp@raibach.net/prompt-portal-prod.raibach.net/api/.htaccess
   ```

2. **Revert code changes:**
   ```bash
   git revert HEAD
   git push origin main
   ```

3. Frontend will fail to connect but won't break completely

## Success Criteria

- ✅ Frontend loads without console errors
- ✅ API calls route to `api.prompt-portal-prod.raibach.net`
- ✅ Backend responds to API requests
- ✅ AI model queries work via Ngrok tunnel
- ✅ Storybook remains functional
- ✅ Deployment automation continues working

## Files Modified

### Created Files:
- `apache_proxy.htaccess` - Apache reverse proxy configuration
- `frontend/.env.production` - Production API URL
- `DEPLOYMENT_INSTRUCTIONS.md` - This file

### Modified Files:
- `frontend/src/services/graceApi.ts` - Added environment variable support
- `grace_api.py` - Added production mode with localhost binding
- `.github/workflows/deploy.yml` - Added environment variables and Ngrok URL

## Notes

- The backend binds to `127.0.0.1:8001` in production (localhost only)
- Apache proxy forwards requests from `api.prompt-portal-prod.raibach.net` to `localhost:8001`
- Frontend uses `VITE_API_URL` environment variable to route requests to API subdomain
- Ngrok tunnel remains on local machine, accessed from SiteGround backend via HTTPS
