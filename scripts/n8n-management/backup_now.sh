#!/bin/bash

# Simple backup command - run this anytime to save your n8n data
echo "💾 Saving your N8N credentials and workflows..."

# Change to the script directory to ensure relative paths work
cd "$(dirname "$0")"
./auto_backup_n8n.sh

echo ""
echo "✨ DONE! Your credentials are now safe and will be automatically restored next time you start n8n."
