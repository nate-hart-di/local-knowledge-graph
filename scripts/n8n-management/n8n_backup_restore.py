#!/usr/bin/env python3
"""
N8N Backup and Restore Script
Prevents credential loss by creating automated backups and restores
"""
import os
import subprocess
import json
import shutil
import datetime
from pathlib import Path

class N8NBackupManager:
    def __init__(self):
        self.backup_dir = Path("n8n/backup")
        self.credentials_dir = self.backup_dir / "credentials"
        self.workflows_dir = self.backup_dir / "workflows"
        self.container_name = "n8n"
        
        # Ensure backup directories exist
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
    
    def is_container_running(self):
        """Check if n8n container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}", "--filter", f"name={self.container_name}"],
                capture_output=True, text=True, check=True
            )
            return self.container_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def backup_credentials(self):
        """Export credentials from running n8n container"""
        if not self.is_container_running():
            print("❌ N8N container is not running. Start it first to backup credentials.")
            return False
        
        try:
            # Export credentials
            print("🔄 Backing up credentials...")
            subprocess.run([
                "docker", "exec", self.container_name,
                "n8n", "export:credentials", "--backup", "--output=/backup/credentials"
            ], check=True)
            
            print("✅ Credentials backed up successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to backup credentials: {e}")
            return False
    
    def backup_workflows(self):
        """Export workflows from running n8n container"""
        if not self.is_container_running():
            print("❌ N8N container is not running. Start it first to backup workflows.")
            return False
        
        try:
            # Export workflows
            print("🔄 Backing up workflows...")
            subprocess.run([
                "docker", "exec", self.container_name,
                "n8n", "export:workflow", "--backup", "--output=/backup/workflows"
            ], check=True)
            
            print("✅ Workflows backed up successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to backup workflows: {e}")
            return False
    
    def create_timestamped_backup(self):
        """Create a timestamped backup of current state"""
        if not self.is_container_running():
            print("❌ N8N container is not running. Cannot create timestamped backup.")
            return False
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped_dir = Path(f"n8n/backups/{timestamp}")
        timestamped_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup both credentials and workflows
        success = True
        success &= self.backup_credentials()
        success &= self.backup_workflows()
        
        if success:
            # Copy to timestamped backup
            if self.credentials_dir.exists():
                shutil.copytree(self.credentials_dir, timestamped_dir / "credentials", dirs_exist_ok=True)
            if self.workflows_dir.exists():
                shutil.copytree(self.workflows_dir, timestamped_dir / "workflows", dirs_exist_ok=True)
            
            print(f"✅ Timestamped backup created: {timestamped_dir}")
        
        return success
    
    def restore_credentials(self):
        """Import credentials to n8n container"""
        if not self.credentials_dir.exists() or not any(self.credentials_dir.iterdir()):
            print("❌ No credentials found to restore")
            return False
        
        if not self.is_container_running():
            print("❌ N8N container is not running. Start it first to restore credentials.")
            return False
        
        try:
            print("🔄 Restoring credentials...")
            subprocess.run([
                "docker", "exec", self.container_name,
                "n8n", "import:credentials", "--separate", "--input=/backup/credentials"
            ], check=True)
            
            print("✅ Credentials restored successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to restore credentials: {e}")
            return False
    
    def restore_workflows(self):
        """Import workflows to n8n container"""
        if not self.workflows_dir.exists() or not any(self.workflows_dir.iterdir()):
            print("❌ No workflows found to restore")
            return False
        
        if not self.is_container_running():
            print("❌ N8N container is not running. Start it first to restore workflows.")
            return False
        
        try:
            print("🔄 Restoring workflows...")
            subprocess.run([
                "docker", "exec", self.container_name,
                "n8n", "import:workflow", "--separate", "--input=/backup/workflows"
            ], check=True)
            
            print("✅ Workflows restored successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to restore workflows: {e}")
            return False
    
    def full_backup(self):
        """Perform a complete backup"""
        print("🚀 Starting full backup...")
        success = True
        success &= self.backup_credentials()
        success &= self.backup_workflows()
        
        if success:
            print("✅ Full backup completed successfully")
        else:
            print("❌ Full backup completed with errors")
        
        return success
    
    def full_restore(self):
        """Perform a complete restore"""
        print("🚀 Starting full restore...")
        success = True
        success &= self.restore_credentials()
        success &= self.restore_workflows()
        
        if success:
            print("✅ Full restore completed successfully")
        else:
            print("❌ Full restore completed with errors")
        
        return success

def main():
    import sys
    
    manager = N8NBackupManager()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python n8n_backup_restore.py backup          # Backup credentials and workflows")
        print("  python n8n_backup_restore.py restore         # Restore credentials and workflows")
        print("  python n8n_backup_restore.py backup-creds    # Backup only credentials")
        print("  python n8n_backup_restore.py restore-creds   # Restore only credentials")
        print("  python n8n_backup_restore.py backup-flows    # Backup only workflows")
        print("  python n8n_backup_restore.py restore-flows   # Restore only workflows")
        print("  python n8n_backup_restore.py timestamped     # Create timestamped backup")
        return
    
    command = sys.argv[1].lower()
    
    if command == "backup":
        manager.full_backup()
    elif command == "restore":
        manager.full_restore()
    elif command == "backup-creds":
        manager.backup_credentials()
    elif command == "restore-creds":
        manager.restore_credentials()
    elif command == "backup-flows":
        manager.backup_workflows()
    elif command == "restore-flows":
        manager.restore_workflows()
    elif command == "timestamped":
        manager.create_timestamped_backup()
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main() 
