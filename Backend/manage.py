# Management utility for Adjustle database
# Use this to sync, seed, or migrate the db
import argparse
import asyncio
import os
from datetime import datetime
from Backend.database import (
    init_db, close_db, db, users_table, schedule_table, timetable_table, notifications_table,
    _seed_timetable_grid, _seed_schedule_alerts, add_notification
)

# // Function to run any necessary SQL database migrations to update the schema
async def run_migration():
    # This runs the sql commands to update the schema
    print("--- Running Migrations ---")
    await init_db()
    try:
        # Add missing columns if they don't exist
        print("Migrating 'schedules' table schema...")
        
        # Ensure columns exist first
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS original_time VARCHAR(255) NULL;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS new_time VARCHAR(255) NULL;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS reason VARCHAR(255) NULL;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS total_students INTEGER DEFAULT 40;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS branch VARCHAR(255) DEFAULT 'BCA';")
        await db.execute("ALTER TABLE timetable ADD COLUMN IF NOT EXISTS branch VARCHAR(255) DEFAULT 'BCA';")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS test_period_start VARCHAR(255) NULL;")
        await db.execute("ALTER TABLE schedules ADD COLUMN IF NOT EXISTS test_weeks_total INTEGER DEFAULT 2;")
        
        # Explicitly force VARCHAR type for string columns to avoid type mismatch with ISO strings
        # This fixes the 'str object has no attribute hour' error
        print("Enforcing column types...")
        await db.execute("ALTER TABLE schedules ALTER COLUMN original_time TYPE VARCHAR(255);")
        await db.execute("ALTER TABLE schedules ALTER COLUMN new_time TYPE VARCHAR(255);")
        await db.execute("ALTER TABLE schedules ALTER COLUMN test_period_start TYPE VARCHAR(255);")
        
        # User and Notification branch migration
        await db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS branch VARCHAR(255) DEFAULT 'BCA';")
        await db.execute("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS branch VARCHAR(255) DEFAULT 'BCA';")
        
        # Merge Requests Migrations
        print("Migrating 'merge_requests' table schema...")
        await db.execute("ALTER TABLE merge_requests ADD COLUMN IF NOT EXISTS requestor_username VARCHAR(255) NULL;")
        
        print("Done! Migrations applied.")
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
    finally:
        await close_db()

# // Function to populate the database with initial starter data for testing
async def seed_data(include_users=False):
    # This clears and re-seeds the tables
    print("--- Seeding Database ---")
    await init_db()
    try:
        # 1. Clear existing data (optional, but good for fresh start)
        print("Wiping old timetable and schedules...")
        await db.execute(schedule_table.delete())
        await db.execute(timetable_table.delete())
        
        if include_users:
            print("Wiping users table...")
            await db.execute(users_table.delete())
            print("Adding fresh users (Carol, Teacher, Student, Jerusha)...")
            carol_pwd = os.getenv("CAROL_PASSWORD")
            bca_teacher_pwd = os.getenv("BCA_TEACHER_PASSWORD")
            bcada_teacher_pwd = os.getenv("BCADA_TEACHER_PASSWORD")
            jerusha_pwd = os.getenv("JERUSHA_PASSWORD")
            
            await db.execute(users_table.insert().values(
                username="Carol", email="carol@adjustle.com", password=carol_pwd, role="student", branch="BCA"
            ))
            await db.execute(users_table.insert().values(
                username="BCATeacher", email="bcateacher@adjustle.com", password=bca_teacher_pwd, role="teacher", branch="BCA"
            ))
            await db.execute(users_table.insert().values(
                username="BCADATeacher", email="bcada@adjustle.com", password=bcada_teacher_pwd, role="teacher", branch="BCADA"
            ))
            await db.execute(users_table.insert().values(
                username="Jerusha", email="jerusha@adjustle.com", password=jerusha_pwd, role="student", branch="BCADA"
            ))

        print("Seeding Timetable Grid...")
        await _seed_timetable_grid()
        
        # 3. Seed Schedule Alerts
        print("Seeding Schedule Status Alerts...")
        await _seed_schedule_alerts()
        
        # 4. Add Initial Notification
        await add_notification(
            title="System Ready",
            message="The Adjustle system has been initialized.",
            n_type="system"
        )
        if not include_users:
            print("Sweet! Seeding finished.")
        else:
            print("Sweet! Users and data seeded.")
    except Exception as e:
        print(f"Oops! Seeding failed: {e}")
    finally:
        await close_db()

# // Utility to remove all current notifications from the system database
async def cleanup_notifications():
    print("--- Cleaning Notifications ---")
    await init_db()
    try:
        # Just a general cleanup if needed, but not targeting MA anymore
        print("Cleaning up generic system notifications...")
        query = notifications_table.delete().where(
            notifications_table.c.title.ilike("%Temporary%")
        )
        await db.execute(query)
        print("Cleanup done.")
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        await close_db()

async def update_password():
    await init_db()
    try:
        new_pwd = os.getenv("CAROL_PASSWORD")
        if not new_pwd:
            print("Error: CAROL_PASSWORD not found in environment.")
            return

        query = users_table.update().where(
            users_table.c.username == "Carol"
        ).values(password=new_pwd)
        await db.execute(query)
        print("Carol's password updated successfully using environment variable.")
    except Exception as e:
        print(f"Cleanup error: {e}")
    finally:
        await close_db()

# // Sync logic to reconcile the backend tables with the predefined code maps
async def sync_system():
    print("--- System Sync Started ---")
    await init_db()
    try:
        # 1. Rebuild Grid
        print("Rebuilding timetable grid...")
        await _seed_timetable_grid()

        # 2. Calculate and Seed Schedule Alerts (This also auto-sends notifications)
        print("Updating schedule status alerts and broadcasting changes...")
        await _seed_schedule_alerts()

        print("Everything looks solid. System sync complete.")
    except Exception as e:
        print(f"Sync failed: {e}")
    finally:
        await close_db()

# // Main entry point for the command line management utility script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adjustle Database Management Tool")
    parser.add_argument("--migrate", action="store_true", help="Run database migrations")
    parser.add_argument("--seed", action="store_true", help="Seed database with initial data")
    parser.add_argument("--seed-users", action="store_true", help="Seed database with users (CAUTION: deletes existing users)")
    parser.add_argument("--sync", action="store_true", help="Full system sync (Rebuild grid + Status updates)")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup notifications")

    args = parser.parse_args()

    if args.migrate:
        asyncio.run(run_migration())
    elif args.seed:
        asyncio.run(seed_data(include_users=False))
    elif args.seed_users:
        asyncio.run(seed_data(include_users=True))
    elif args.cleanup:
        asyncio.run(cleanup_notifications())
    elif args.sync:
        asyncio.run(sync_system())
    else:
        # Default behavior: sync
        asyncio.run(sync_system())
