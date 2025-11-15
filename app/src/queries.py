import asyncio
import aiosqlite
import sys

async def connect_db(query: str):
    # the database would be stored in app/src/de/data.db 
    # if the file does not exist, make it using DB Browser
    async with aiosqlite.connect("app/src/db/data.db") as db:
        cursor = await db.execute(query)
        await db.commit()
        if query.lower().startswith("select"):
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            return results
        return None


if __name__ == "__main__":
    print(' '.join(sys.argv[1:]))
    asyncio.run(connect_db(' '.join(sys.argv[1:])))
    query = "SELECT * FROM user_information;"
    results = asyncio.run(connect_db(query))
    print(results)
