#!/usr/bin/env python3
"""
Duplicate Print Cleanup Utility

This script helps identify and clean up duplicate print entries in the Rudder database.
It can be run safely multiple times and provides options for automatic or interactive cleanup.
"""

import sqlite3
import os
from datetime import datetime
import argparse

def connect_to_db():
    """Connect to the SQLite database"""
    # Try the instance folder first (Flask default location)
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'printer_logbook.db')
    if not os.path.exists(db_path):
        # Fallback to script directory
        db_path = os.path.join(os.path.dirname(__file__), 'printer_logbook.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Tried locations:")
        print(f"  - {os.path.join(os.path.dirname(__file__), 'instance', 'printer_logbook.db')}")
        print(f"  - {os.path.join(os.path.dirname(__file__), 'printer_logbook.db')}")
        return None

    print(f"Found database at: {db_path}")
    return sqlite3.connect(db_path)

def find_duplicates(conn):
    """Find duplicate print jobs by filename"""
    cursor = conn.cursor()

    # Find filenames that appear more than once
    cursor.execute("""
        SELECT filename, COUNT(*) as count
        FROM print_job
        GROUP BY filename
        HAVING COUNT(*) > 1
        ORDER BY count DESC, filename
    """)

    duplicate_groups = cursor.fetchall()

    detailed_duplicates = []
    for filename, count in duplicate_groups:
        # Get all prints for this filename
        cursor.execute("""
            SELECT id, filename, start_time, status, quality_rating, gcode_path
            FROM print_job
            WHERE filename = ?
            ORDER BY start_time
        """, (filename,))

        prints = cursor.fetchall()
        detailed_duplicates.append({
            'filename': filename,
            'count': count,
            'prints': prints
        })

    return detailed_duplicates

def analyze_duplicates(duplicates):
    """Analyze duplicates and suggest which ones to keep/remove"""
    recommendations = []

    for group in duplicates:
        filename = group['filename']
        prints = group['prints']

        # Sort by start_time (already sorted from query)
        keep_print = None
        remove_prints = []

        # Strategy: Keep the print with the most complete data
        # Priority: 1) Has quality rating, 2) Has status='success', 3) Most recent

        scored_prints = []
        for print_data in prints:
            id_, filename, start_time, status, quality_rating, gcode_path = print_data
            score = 0

            # Points for having quality rating
            if quality_rating is not None:
                score += 10

            # Points for successful status
            if status == 'success':
                score += 5
            elif status == 'pending':
                score += 1

            # Points for having gcode file
            if gcode_path and gcode_path.strip():
                score += 3

            # Small bonus for being more recent (milliseconds since epoch)
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                score += dt.timestamp() / 1000000  # Very small bonus for recency
            except:
                pass

            scored_prints.append((score, print_data))

        # Sort by score (highest first)
        scored_prints.sort(key=lambda x: x[0], reverse=True)

        # Keep the highest scored print
        keep_print = scored_prints[0][1]
        remove_prints = [p[1] for p in scored_prints[1:]]

        recommendations.append({
            'filename': filename,
            'keep': keep_print,
            'remove': remove_prints
        })

    return recommendations

def display_recommendations(recommendations):
    """Display cleanup recommendations to the user"""
    print("\n" + "="*80)
    print("DUPLICATE CLEANUP RECOMMENDATIONS")
    print("="*80)

    total_to_remove = 0

    for i, rec in enumerate(recommendations, 1):
        filename = rec['filename']
        keep = rec['keep']
        remove = rec['remove']

        print(f"\n{i}. Filename: {filename}")
        print(f"   Found {len(remove) + 1} duplicates")

        print(f"\n   KEEP:   ID={keep[0]}, Start={keep[2]}, Status={keep[3]}, Quality={keep[4]}")

        print(f"   REMOVE:")
        for r in remove:
            print(f"           ID={r[0]}, Start={r[2]}, Status={r[3]}, Quality={r[4]}")
            total_to_remove += 1

    print(f"\n" + "="*80)
    print(f"SUMMARY: {total_to_remove} duplicate entries recommended for removal")
    print("="*80)

    return total_to_remove

def remove_duplicates(conn, recommendations, interactive=True):
    """Remove duplicate entries based on recommendations"""
    removed_count = 0

    for rec in recommendations:
        filename = rec['filename']
        keep = rec['keep']
        remove = rec['remove']

        if not remove:
            continue

        if interactive:
            print(f"\nProcessing: {filename}")
            print(f"Keep ID {keep[0]} (Start: {keep[2]}, Status: {keep[3]})")

            response = input(f"Remove {len(remove)} duplicates? [y/N]: ").strip().lower()
            if response not in ['y', 'yes']:
                print("Skipped.")
                continue

        # Remove the duplicate entries
        cursor = conn.cursor()
        for r in remove:
            print_id = r[0]

            # First remove associated parameters
            cursor.execute("DELETE FROM print_parameters WHERE print_job_id = ?", (print_id,))

            # Then remove the print job
            cursor.execute("DELETE FROM print_job WHERE id = ?", (print_id,))

            print(f"  Removed print ID {print_id}")
            removed_count += 1

        conn.commit()

    return removed_count

def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate print entries')
    parser.add_argument('--auto', action='store_true',
                       help='Automatically remove duplicates without prompting')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be removed without actually removing')

    args = parser.parse_args()

    # Connect to database
    conn = connect_to_db()
    if not conn:
        return 1

    try:
        print("Analyzing database for duplicate print entries...")

        # Find duplicates
        duplicates = find_duplicates(conn)

        if not duplicates:
            print("✅ No duplicate entries found!")
            return 0

        # Analyze and get recommendations
        recommendations = analyze_duplicates(duplicates)

        # Display recommendations
        total_to_remove = display_recommendations(recommendations)

        if args.dry_run:
            print("\n🔍 DRY RUN: No changes were made to the database.")
            return 0

        if total_to_remove == 0:
            print("\n✅ No duplicates need to be removed.")
            return 0

        # Remove duplicates
        if args.auto:
            print(f"\n🤖 AUTO MODE: Removing {total_to_remove} duplicates...")
            removed = remove_duplicates(conn, recommendations, interactive=False)
        else:
            print(f"\n🔧 INTERACTIVE MODE: Choose which duplicates to remove...")
            removed = remove_duplicates(conn, recommendations, interactive=True)

        print(f"\n✅ Successfully removed {removed} duplicate entries!")

        # Verify cleanup
        remaining_duplicates = find_duplicates(conn)
        if remaining_duplicates:
            print(f"⚠️  Warning: {len(remaining_duplicates)} duplicate groups still remain.")
        else:
            print("🎉 All duplicates have been cleaned up!")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    finally:
        conn.close()

if __name__ == '__main__':
    exit(main())
