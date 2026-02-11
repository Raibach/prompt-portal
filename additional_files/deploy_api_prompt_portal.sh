#!/usr/bin/env bash

# Deployment helper for prompt-portal production API + frontend.
# Goal: replace markdown checklists pasted into the terminal with a
# single, repeatable script you can run step‑by‑step.
#
# Usage (from repo root):
#   bash deploy_api_prompt_portal.sh
#
# The script is intentionally conservative:
# - It ECHOS commands and explains what to do.
# - It only runs a few safe checks automatically.
# - For remote SiteGround steps, it tells you exactly what to paste
#   into the SSH session instead of trying to automate SSH itself.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

header() {
  echo
  echo "===================================================================="
  echo "$1"
  echo "===================================================================="
}

step() {
  echo
  echo "👉 $1"
}

pause() {
  read -r -p "Press Enter to continue..." _
}

header "Step 0 – Sanity check: git status"

step "Checking that your local repo is clean and on main..."
cd "$REPO_ROOT"
git status
echo
echo "If you see 'nothing to commit, working tree clean' and 'On branch main', you're good."
pause

header "Step 1 – Push latest code to GitHub"

step "This triggers the GitHub Actions workflow that builds and deploys."
echo
echo "Suggested command:"
echo "  git push origin main"
echo
echo "Run that in this terminal (or push via Cursor / GitHub Desktop)."
pause

header "Step 2 – SSH into SiteGround (API server box)"

step "Open a NEW terminal window and connect to the server:"
echo
echo "  ssh u2819-gkhlcvpg4gjm@ssh.raibach.net -p 18765"
echo
echo "Once connected, you should end up in:"
echo "  /home/u2819-gkhlcvpg4gjm"
pause

header "Step 3 – Ensure a single grace_api.py on port 8001"

step "In the SSH session, run these commands EXACTLY in order:"
cat <<'EOF'
cd ~/www/api.prompt-portal-prod.raibach.net

# Kill any old backend processes (ignore 'no process found' messages)
pkill -9 -f "grace_api.py" 2>/dev/null || true

# Start a fresh backend in the background
nohup python3 grace_api.py > /tmp/backend.log 2>&1 &

# Wait a few seconds, then check local health:
sleep 5
curl http://localhost:8001/api/health
EOF

echo
echo "You should see JSON with \"status\": \"ok\"."
echo "It's also okay if the JSON says llm_status: \"connection_refused\" if the LLM is not running on this box."
pause

header "Step 4 – Verify the API proxy (public HTTPS URL)"

step "Still in the SSH session, test the public health endpoint:"
cat <<'EOF'
curl -i https://api.prompt-portal-prod.raibach.net/api/health
EOF

echo
echo "You want to see 'HTTP/2 200' (or 'HTTP/1.1 200') and the same JSON body as localhost:8001."
echo "If you see '500 Internal Server Error', the .htaccess proxy or backend is misconfigured."
pause

header "Step 5 – If you get a 500, quick troubleshooting checklist"

step "On the server, check the API .htaccess file:"
cat <<'EOF'
cd ~/www/api.prompt-portal-prod.raibach.net/public_html
pwd
ls -la
cat .htaccess
EOF

echo
echo "It should look like the version in apache_proxy.htaccess in this repo."
echo "If it does NOT match, copy the contents from apache_proxy.htaccess into this .htaccess."
echo
echo "You can also inspect PHP/Apache errors from the main public_html site:"
cat <<'EOF'
cd /home/customer/www/raibach.net/public_html
ls -la
tail -n 80 php_errorlog
EOF

echo
echo "Look for rewrite/proxy errors. Fix .htaccess accordingly, then retry:"
echo "  curl -i https://api.prompt-portal-prod.raibach.net/api/health"
pause

header "All done"
echo "You now have a single script that walks you through deployment"
echo "instead of pasting markdown checklists directly into the shell."
echo
echo "You can re-run this script any time from the repo root:"
echo "  bash deploy_api_prompt_portal.sh"

