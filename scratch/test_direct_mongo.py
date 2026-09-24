import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def test_connect():
    uri = "mongodb://skyvotes:skyhighvotes2027@cluster0-shard-00-00.lp41f.mongodb.net:27017,cluster0-shard-00-01.lp41f.mongodb.net:27017,cluster0-shard-00-02.lp41f.mongodb.net:27017/Nsesa?ssl=true&replicaSet=atlas-nh8x11-shard-0&authSource=admin&retryWrites=true&w=majority"
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    try:
        res = await client.admin.command('ping')
        print("Connected successfully! Ping response:", res)
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    asyncio.run(test_connect())
