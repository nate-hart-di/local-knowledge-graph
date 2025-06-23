#!/bin/bash

# Auto N8N Backup Script
# This script automatically backs up N8N credentials and workflows

set -e # Exit on any error

echo "🚀 Auto-backing up N8N data..."

# Check if n8n is running
if ! docker ps --format "{{.Names}}" | grep -q "^n8n$"; then
  echo "❌ N8N container is not running. Cannot backup data."
  exit 1
fi

# Create backup directories
mkdir -p n8n/backup/{credentials,workflows}

echo "🔐 Backing up credentials..."
if docker exec n8n n8n export:credentials --backup --output=/backup/credentials 2> /dev/null; then
  CRED_COUNT=$(ls n8n/backup/credentials/*.json 2> /dev/null | wc -l || echo 0)
  echo "✅ Successfully backed up $CRED_COUNT credentials"
else
  echo "⚠️  No credentials found or backup failed"
fi

echo "📋 Backing up workflows..."
if docker exec n8n n8n export:workflow --backup --output=/backup/workflows 2> /dev/null; then
  WORKFLOW_COUNT=$(ls n8n/backup/workflows/*.json 2> /dev/null | wc -l || echo 0)
  echo "✅ Successfully backed up $WORKFLOW_COUNT workflows"
else
  echo "⚠️  No workflows found or backup failed"
fi

# Add timestamp to backup
echo "📅 Backup completed at: $(date)" > n8n/backup/last_backup.txt

echo ""
echo "🎉 BACKUP COMPLETE!"
echo "📁 Your data is safely stored in:"
echo "   🔐 Credentials: n8n/backup/credentials/"
echo "   📋 Workflows: n8n/backup/workflows/"
echo ""
echo "💡 Your credentials will be automatically restored when you restart n8n!"
