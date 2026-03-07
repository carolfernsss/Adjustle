import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from database import init_db, db, users_table, close_db

async def check():
    await init_db()
    rows = await db.fetch_all(users_table.select())
    if rows:
        for r in rows:
            d = dict(r)
            print(f"  Username: {d['username']}, Password: {d['password']}, Role: {d['role']}, Branch: {d['branch']}")
    else:
        print("  NO USERS FOUND IN DATABASE!")
    await close_db()

asyncio.run(check())
