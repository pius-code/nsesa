import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    for i in ["00", "01", "02"]:
        host = f"cluster0-shard-00-{i}.lp41f.mongodb.net:27017"
        uri = f"mongodb://skyvotes:skyhighvotes2027@{host}/Nsesa?ssl=true&authSource=admin&directConnection=true"
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=4000)
        try:
            res = await client.admin.command('isMaster')
            print(f"Node {i} connected!")
            print("  setName:", res.get("setName"))
            print("  primary:", res.get("primary"))
            print("  hosts:", res.get("hosts"))
            return res.get("setName"), res.get("hosts")
        except Exception as e:
            print(f"Node {i} failed: {e}")

if __name__ == "__main__":
    asyncio.run(check())
