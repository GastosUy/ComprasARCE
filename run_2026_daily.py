"""
Run 2026 scraper day by day with automatic resume capability.
Processes each day from Jan 1, 2026 to today.
Tracks progress and can resume if stopped.
"""

import os
import json
import subprocess
import sys
import time
import sqlite3
from datetime import datetime, timedelta

PROGRESS_FILE = "2026_daily_progress.json"
DB_FILE = "compras_2026.db"
START_DATE = datetime(2026, 1, 1)

def load_progress():
    """Load progress from file."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'last_completed_date': None,
        'days_processed': [],
        'started_at': datetime.now().isoformat()
    }

def save_progress(progress):
    """Save progress to file."""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)

def get_db_stats():
    """Get current database statistics."""
    if not os.path.exists(DB_FILE):
        return {'total': 0, 'pending': 0, 'completed': 0}
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM releases")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM releases WHERE scrape_status = 'pending'")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM releases WHERE scrape_status = 'completed'")
    completed = cursor.fetchone()[0]
    
    conn.close()
    return {'total': total, 'pending': pending, 'completed': completed}

def process_day(date: datetime):
    """Process a single day: discover IDs and scrape them."""
    date_str = date.strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print(f"Processing: {date_str}")
    print(f"{'='*60}")
    
    # Get stats before
    before = get_db_stats()
    
    # Discover IDs for this day
    print(f"[1/2] Discovering IDs for {date_str}...")
    subprocess.run([
        sys.executable, "scraper_2026.py",
        "--discover",
        "--start-date", date_str,
        "--end-date", date_str,
        "--db", DB_FILE
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Get stats after discover
    after_discover = get_db_stats()
    new_ids = after_discover['total'] - before['total']
    print(f"    Discovered {new_ids} new IDs (Total: {after_discover['total']:,})")
    
    # Scrape all pending
    print(f"[2/2] Scraping {after_discover['pending']} pending releases...")
    subprocess.run([
        sys.executable, "scraper_2026.py",
        "--scrape",
        "--db", DB_FILE
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Get stats after scrape
    after_scrape = get_db_stats()
    scraped = after_scrape['completed'] - before['completed']
    print(f"    Scraped {scraped} releases (Total completed: {after_scrape['completed']:,})")
    
    return new_ids, scraped

def get_next_date(progress):
    """Get the next date to process based on progress."""
    if progress['last_completed_date']:
        last_date = datetime.strptime(progress['last_completed_date'], '%Y-%m-%d')
        return last_date + timedelta(days=1)
    return START_DATE

def main():
    print("=" * 60)
    print("2026 DAILY SCRAPER WITH RESUME")
    print("=" * 60)
    
    # Load progress
    progress = load_progress()
    
    if progress['last_completed_date']:
        print(f"Resuming from after: {progress['last_completed_date']}")
        print(f"Days already processed: {len(progress['days_processed'])}")
    else:
        print("Starting fresh from January 1, 2026")
    
    # Show current DB stats
    stats = get_db_stats()
    print(f"Current DB: {stats['total']:,} total, {stats['completed']:,} completed, {stats['pending']:,} pending")
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_date = get_next_date(progress)
    
    # Calculate remaining days
    if current_date <= today:
        remaining_days = (today - current_date).days + 1
        print(f"Days remaining to process: {remaining_days}")
    else:
        print("\nAll days up to today have been processed!")
        return
    
    print("\nStarting in 3 seconds... (Ctrl+C to stop)")
    time.sleep(3)
    
    session_start = time.time()
    days_this_session = 0
    
    try:
        while current_date <= today:
            new_ids, scraped = process_day(current_date)
            days_this_session += 1
            
            # Update and save progress
            date_str = current_date.strftime('%Y-%m-%d')
            progress['last_completed_date'] = date_str
            progress['days_processed'].append(date_str)
            save_progress(progress)
            
            # Progress summary
            elapsed = time.time() - session_start
            remaining = (today - current_date).days
            
            if remaining > 0 and days_this_session > 0:
                avg_time_per_day = elapsed / days_this_session
                eta_minutes = (avg_time_per_day * remaining) / 60
                print(f"    [{remaining} days left | ETA: {eta_minutes:.0f} min]")
            
            current_date += timedelta(days=1)
            
            # Small delay between days
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("STOPPED BY USER - Progress saved!")
        print(f"Resume by running: python run_2026_daily.py")
        print("=" * 60)
    
    # Final summary
    elapsed = time.time() - session_start
    stats = get_db_stats()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Days processed this session: {days_this_session}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Last date completed: {progress['last_completed_date']}")
    print(f"Total days processed: {len(progress['days_processed'])}")
    print(f"\nDatabase stats:")
    print(f"  Total releases: {stats['total']:,}")
    print(f"  Completed: {stats['completed']:,}")
    print(f"  Pending: {stats['pending']:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
