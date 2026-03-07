import sqlite3
import os

db_path = r'c:\Users\Carol Fernandes\Downloads\Adjustle\Backend\adjustle.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- MERGE REQUESTS ---")
    try:
        cursor.execute("SELECT id, subject, requestor_branch, target_branch, status, target_consent, requester_consent FROM merge_requests")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error reading merge_requests: {e}")
        
    print("\n--- NOTIFICATIONS ---")
    try:
        cursor.execute("SELECT id, title, type, branch, created_at FROM notifications WHERE type='merge_request'")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error reading notifications: {e}")
        
    conn.close()
