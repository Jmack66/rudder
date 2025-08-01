#!/usr/bin/env python3
"""
Database Reset Script for Printer Logbook

This script safely resets the application data by:
1. Clearing the database (removes all print jobs and maintenance events)
2. Cleaning up uploaded G-code files
3. Optionally backing up existing data before reset

Usage:
    python reset_data.py                    # Interactive mode with prompts
    python reset_data.py --force            # Reset without confirmation
    python reset_data.py --backup-only      # Only create backup, don't reset
    python reset_data.py --restore BACKUP   # Restore from backup file
"""

import os
import sys
import shutil
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

def get_database_path():
    """Get the database file path."""
    # Check common locations
    possible_paths = [
        'instance/printer_logbook.db',
        'printer_logbook.db',
        os.path.join(os.path.dirname(__file__), 'instance', 'printer_logbook.db'),
        os.path.join(os.path.dirname(__file__), 'printer_logbook.db')
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def get_uploads_path():
    """Get the uploads directory path."""
    possible_paths = [
        'uploads',
        os.path.join(os.path.dirname(__file__), 'uploads')
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def count_records(db_path):
    """Count records in database tables."""
    if not os.path.exists(db_path):
        return {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        counts = {}
        tables = ['print_job', 'maintenance_event', 'print_parameters']

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0

        conn.close()
        return counts
    except Exception as e:
        print(f"Error reading database: {e}")
        return {}

def count_files(uploads_path):
    """Count files in uploads directory."""
    if not uploads_path or not os.path.exists(uploads_path):
        return 0

    return len([f for f in os.listdir(uploads_path) if os.path.isfile(os.path.join(uploads_path, f))])

def create_backup(db_path, uploads_path):
    """Create a backup of the current data."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f"backup_{timestamp}"

    print(f"Creating backup in {backup_dir}/...")
    os.makedirs(backup_dir, exist_ok=True)

    # Backup database
    if db_path and os.path.exists(db_path):
        backup_db_path = os.path.join(backup_dir, 'printer_logbook.db')
        shutil.copy2(db_path, backup_db_path)
        print(f"  ✅ Database backed up to {backup_db_path}")

    # Backup uploads
    if uploads_path and os.path.exists(uploads_path):
        backup_uploads_path = os.path.join(backup_dir, 'uploads')
        shutil.copytree(uploads_path, backup_uploads_path)
        print(f"  ✅ Uploads backed up to {backup_uploads_path}")

    # Create backup info file
    info_file = os.path.join(backup_dir, 'backup_info.txt')
    with open(info_file, 'w') as f:
        f.write(f"Printer Logbook Backup\n")
        f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Database: {db_path}\n")
        f.write(f"Uploads: {uploads_path}\n")

    print(f"  ✅ Backup complete: {backup_dir}")
    return backup_dir

def reset_database(db_path):
    """Reset the database by dropping and recreating tables."""
    if not os.path.exists(db_path):
        print("  ℹ️  No database found to reset")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Drop tables if they exist
        tables = ['print_job', 'maintenance_event', 'print_parameters']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")

        conn.commit()
        conn.close()

        print(f"  ✅ Database reset: {db_path}")
    except Exception as e:
        print(f"  ❌ Error resetting database: {e}")

def reset_uploads(uploads_path):
    """Clear all files from uploads directory."""
    if not uploads_path or not os.path.exists(uploads_path):
        print("  ℹ️  No uploads directory found to reset")
        return

    try:
        for filename in os.listdir(uploads_path):
            file_path = os.path.join(uploads_path, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        print(f"  ✅ Uploads cleared: {uploads_path}")
    except Exception as e:
        print(f"  ❌ Error clearing uploads: {e}")

def restore_from_backup(backup_path):
    """Restore data from a backup directory."""
    if not os.path.exists(backup_path):
        print(f"❌ Backup directory not found: {backup_path}")
        return False

    print(f"Restoring from backup: {backup_path}")

    # Restore database
    backup_db = os.path.join(backup_path, 'printer_logbook.db')
    if os.path.exists(backup_db):
        # Ensure instance directory exists
        os.makedirs('instance', exist_ok=True)
        shutil.copy2(backup_db, 'instance/printer_logbook.db')
        print("  ✅ Database restored")

    # Restore uploads
    backup_uploads = os.path.join(backup_path, 'uploads')
    if os.path.exists(backup_uploads):
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        # Clear existing uploads
        for filename in os.listdir('uploads'):
            file_path = os.path.join('uploads', filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        # Copy backup files
        for filename in os.listdir(backup_uploads):
            src = os.path.join(backup_uploads, filename)
            dst = os.path.join('uploads', filename)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        print("  ✅ Uploads restored")

    print("Restore complete!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Reset Printer Logbook data')
    parser.add_argument('--force', action='store_true',
                       help='Reset without confirmation prompts')
    parser.add_argument('--backup-only', action='store_true',
                       help='Only create backup, do not reset')
    parser.add_argument('--restore', type=str, metavar='BACKUP_DIR',
                       help='Restore from backup directory')
    parser.add_argument('--no-backup', action='store_true',
                       help='Reset without creating backup (dangerous!)')

    args = parser.parse_args()

    print("🖨️  Printer Logbook Data Reset Tool")
    print("=" * 40)

    # Handle restore operation
    if args.restore:
        return 0 if restore_from_backup(args.restore) else 1

    # Find data locations
    db_path = get_database_path()
    uploads_path = get_uploads_path()

    # Show current data status
    print("Current data status:")
    if db_path:
        counts = count_records(db_path)
        print(f"  📊 Database: {db_path}")
        for table, count in counts.items():
            print(f"     {table}: {count} records")
    else:
        print("  📊 Database: Not found")

    if uploads_path:
        file_count = count_files(uploads_path)
        print(f"  📁 Uploads: {uploads_path} ({file_count} files)")
    else:
        print("  📁 Uploads: Not found")

    # Check if there's any data to reset
    has_data = False
    if db_path:
        counts = count_records(db_path)
        has_data = any(count > 0 for count in counts.values())
    if uploads_path:
        has_data = has_data or count_files(uploads_path) > 0

    if not has_data:
        print("\n✅ No data found to reset. Database is already clean.")
        return 0

    # Backup-only mode
    if args.backup_only:
        print("\n📦 Creating backup only (no reset)...")
        create_backup(db_path, uploads_path)
        return 0

    # Confirmation prompt
    if not args.force:
        print(f"\n⚠️  This will permanently delete all data!")
        if not args.no_backup:
            print("   (A backup will be created first)")
        response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Reset cancelled.")
            return 0

    # Create backup unless explicitly disabled
    backup_dir = None
    if not args.no_backup:
        print("\n📦 Creating backup...")
        backup_dir = create_backup(db_path, uploads_path)

    # Perform reset
    print("\n🔄 Resetting data...")

    if db_path:
        reset_database(db_path)

    if uploads_path:
        reset_uploads(uploads_path)

    print(f"\n✅ Reset complete!")
    if backup_dir:
        print(f"   Backup saved to: {backup_dir}")
        print(f"   To restore: python reset_data.py --restore {backup_dir}")

    print("\nNext steps:")
    print("1. Start the application: python app.py")
    print("2. The database will be recreated automatically on first run")

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nReset cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
