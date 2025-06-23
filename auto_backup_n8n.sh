#!/bin/bash

# Auto N8N Backup Script
# Run this before stopping n8n to ensure credentials and workflows are backed up

echo "🚀 Auto-backing up N8N data..."

# Check if n8n is running
if ! docker ps --format "{{.Names}}" | grep -q "^n8n$"; then
  echo "❌ N8N container is not running. Start it first to backup data."
  exit 1
fi

# Create backup directories
mkdir -p n8n/backup/{credentials,workflows}

# Backup credentials
echo "🔐 Backing up credentials..."
if docker exec n8n n8n export:credentials --backup --output=/backup/credentials 2> /dev/null; then
  echo "✅ Credentials backed up successfully"
else
  echo "⚠️  No credentials found or backup failed"
fi

# Backup workflows
echo "📋 Backing up workflows..."
if docker exec n8n n8n export:workflow --backup --output=/backup/workflows 2> /dev/null; then
  echo "✅ Workflows backed up successfully"
else
  echo "⚠️  No workflows found or backup failed"
fi

# Create timestamped backup
timestamp=$(date +"%Y%m%d_%H%M%S")
backup_dir="n8n/backups/${timestamp}"
mkdir -p "${backup_dir}"

if [ -d "n8n/backup/credentials" ] && [ "$(ls -A n8n/backup/credentials 2> /dev/null)" ]; then
  cp -r n8n/backup/credentials "${backup_dir}/"
fi

if [ -d "n8n/backup/workflows" ] && [ "$(ls -A n8n/backup/workflows 2> /dev/null)" ]; then
  cp -r n8n/backup/workflows "${backup_dir}/"
fi

echo "📦 Timestamped backup created: ${backup_dir}"
echo "✅ Backup complete! Your data is safe."
