#!/bin/bash

# N8N Management Script
# Easy backup and restore for n8n credentials and workflows

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/n8n/backup"
CONTAINER_NAME="n8n"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
  echo -e "${RED}❌ $1${NC}"
}

check_container_running() {
  if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    return 1
  fi
  return 0
}

backup_credentials() {
  log_info "Backing up n8n credentials..."

  if ! check_container_running; then
    log_error "n8n container is not running. Start it first."
    return 1
  fi

  mkdir -p "$BACKUP_DIR/credentials"

  if docker exec "$CONTAINER_NAME" n8n export:credentials --backup --output=/backup/credentials; then
    log_success "Credentials backed up successfully"
    return 0
  else
    log_error "Failed to backup credentials"
    return 1
  fi
}

backup_workflows() {
  log_info "Backing up n8n workflows..."

  if ! check_container_running; then
    log_error "n8n container is not running. Start it first."
    return 1
  fi

  mkdir -p "$BACKUP_DIR/workflows"

  if docker exec "$CONTAINER_NAME" n8n export:workflow --backup --output=/backup/workflows; then
    log_success "Workflows backed up successfully"
    return 0
  else
    log_error "Failed to backup workflows"
    return 1
  fi
}

restore_credentials() {
  log_info "Restoring n8n credentials..."

  if ! check_container_running; then
    log_error "n8n container is not running. Start it first."
    return 1
  fi

  if [ ! -d "$BACKUP_DIR/credentials" ] || [ -z "$(ls -A "$BACKUP_DIR/credentials" 2> /dev/null)" ]; then
    log_warning "No credentials found to restore"
    return 1
  fi

  if docker exec "$CONTAINER_NAME" n8n import:credentials --separate --input=/backup/credentials; then
    log_success "Credentials restored successfully"
    return 0
  else
    log_error "Failed to restore credentials"
    return 1
  fi
}

restore_workflows() {
  log_info "Restoring n8n workflows..."

  if ! check_container_running; then
    log_error "n8n container is not running. Start it first."
    return 1
  fi

  if [ ! -d "$BACKUP_DIR/workflows" ] || [ -z "$(ls -A "$BACKUP_DIR/workflows" 2> /dev/null)" ]; then
    log_warning "No workflows found to restore"
    return 1
  fi

  if docker exec "$CONTAINER_NAME" n8n import:workflow --separate --input=/backup/workflows; then
    log_success "Workflows restored successfully"
    return 0
  else
    log_error "Failed to restore workflows"
    return 1
  fi
}

create_timestamped_backup() {
  local timestamp=$(date +"%Y%m%d_%H%M%S")
  local timestamped_dir="$SCRIPT_DIR/n8n/backups/$timestamp"

  log_info "Creating timestamped backup: $timestamp"

  mkdir -p "$timestamped_dir"

  # Backup current state
  backup_credentials
  backup_workflows

  # Copy to timestamped directory
  if [ -d "$BACKUP_DIR/credentials" ]; then
    cp -r "$BACKUP_DIR/credentials" "$timestamped_dir/"
  fi

  if [ -d "$BACKUP_DIR/workflows" ]; then
    cp -r "$BACKUP_DIR/workflows" "$timestamped_dir/"
  fi

  log_success "Timestamped backup created: $timestamped_dir"
}

show_status() {
  log_info "N8N Status Check"
  echo "=================="

  if check_container_running; then
    log_success "n8n container is running"
  else
    log_warning "n8n container is not running"
  fi

  echo ""
  echo "Backup Status:"
  echo "--------------"

  if [ -d "$BACKUP_DIR/credentials" ] && [ -n "$(ls -A "$BACKUP_DIR/credentials" 2> /dev/null)" ]; then
    local cred_count=$(ls -1 "$BACKUP_DIR/credentials" | wc -l)
    log_success "Credentials: $cred_count files found"
  else
    log_warning "Credentials: No backup found"
  fi

  if [ -d "$BACKUP_DIR/workflows" ] && [ -n "$(ls -A "$BACKUP_DIR/workflows" 2> /dev/null)" ]; then
    local workflow_count=$(ls -1 "$BACKUP_DIR/workflows" | wc -l)
    log_success "Workflows: $workflow_count files found"
  else
    log_warning "Workflows: No backup found"
  fi

  echo ""
  echo "Timestamped Backups:"
  echo "-------------------"
  if [ -d "$SCRIPT_DIR/n8n/backups" ]; then
    ls -la "$SCRIPT_DIR/n8n/backups" | grep "^d" | awk '{print $9}' | grep -v "^\.$\|^\.\.$" | sort -r | head -5
  else
    echo "No timestamped backups found"
  fi
}

show_help() {
  echo "N8N Management Script"
  echo "===================="
  echo ""
  echo "Usage: $0 [command]"
  echo ""
  echo "Commands:"
  echo "  backup              - Backup both credentials and workflows"
  echo "  restore             - Restore both credentials and workflows"
  echo "  backup-creds        - Backup only credentials"
  echo "  restore-creds       - Restore only credentials"
  echo "  backup-workflows    - Backup only workflows"
  echo "  restore-workflows   - Restore only workflows"
  echo "  timestamped         - Create timestamped backup"
  echo "  status              - Show current status"
  echo "  help                - Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./manage_n8n.sh backup"
  echo "  ./manage_n8n.sh restore"
  echo "  ./manage_n8n.sh status"
}

# Main script logic
case "${1:-}" in
  "backup")
    backup_credentials
    backup_workflows
    ;;
  "restore")
    restore_credentials
    restore_workflows
    ;;
  "backup-creds")
    backup_credentials
    ;;
  "restore-creds")
    restore_credentials
    ;;
  "backup-workflows")
    backup_workflows
    ;;
  "restore-workflows")
    restore_workflows
    ;;
  "timestamped")
    create_timestamped_backup
    ;;
  "status")
    show_status
    ;;
  "help" | "--help" | "-h")
    show_help
    ;;
  "")
    show_help
    ;;
  *)
    log_error "Unknown command: $1"
    echo ""
    show_help
    exit 1
    ;;
esac
