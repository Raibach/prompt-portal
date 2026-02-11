#!/bin/bash
# Check if all required SSH secrets are configured

echo "Checking SSH configuration..."

MISSING=()

if [ -z "$SSH_HOST" ]; then MISSING+=("SSH_HOST"); fi
if [ -z "$SSH_PORT" ]; then MISSING+=("SSH_PORT"); fi
if [ -z "$SSH_USERNAME" ]; then MISSING+=("SSH_USERNAME"); fi
if [ -z "$SSH_PASSWORD" ]; then MISSING+=("SSH_PASSWORD"); fi

if [ ${#MISSING[@]} -gt 0 ]; then
  echo "❌ MISSING SSH CREDENTIALS:"
  printf '   - %s\n' "${MISSING[@]}"
  echo ""
  echo "Please add these as GitHub Secrets"
  exit 1
fi

echo "✅ All SSH credentials configured"
